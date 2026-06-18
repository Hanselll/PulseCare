from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from uuid import uuid4

import asyncpg
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from redis.asyncio import Redis

from pulsecare_core.alerting import evaluate_alerts, primary_alert_reason
from pulsecare_core.logging import configure_json_logging
from pulsecare_core.schemas import RiskLevel, RiskScore

SERVICE_NAME = "alert-service"
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://pulsecare:pulsecare@postgres:5432/pulsecare"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_LATENCY_MS = int(os.getenv("REDIS_LATENCY_MS", "0"))

configure_json_logging(SERVICE_NAME)
logger = logging.getLogger(SERVICE_NAME)

REQUESTS = Counter(
    "pulsecare_alert_requests_total", "Alert service requests", ["method", "route", "status"]
)
LATENCY = Histogram("pulsecare_alert_evaluation_latency_seconds", "Alert evaluation latency")
CREATED = Counter("pulsecare_alerts_created_total", "Created alerts", ["severity", "reason"])
DEDUPED = Counter("pulsecare_alerts_deduplicated_total", "Deduplicated alerts")
SUPPRESSED = Counter("pulsecare_alerts_suppressed_total", "Suppressed alerts")
REDIS_ERRORS = Counter("pulsecare_alert_redis_errors_total", "Redis errors")

db_pool: asyncpg.Pool | None = None
redis_client: Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, redis_client
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id BIGSERIAL PRIMARY KEY,
                alert_id TEXT NOT NULL UNIQUE,
                device_id TEXT,
                region TEXT NOT NULL,
                severity TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                resolved_at TIMESTAMPTZ
            )
            """
        )
    yield
    await redis_client.aclose()
    await db_pool.close()


app = FastAPI(title="PulseCare alert-service", lifespan=lifespan)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    status = "500"
    try:
        response = await call_next(request)
        status = str(response.status_code)
        return response
    finally:
        if request.url.path != "/metrics":
            REQUESTS.labels(request.method, request.url.path, status).inc()
            LATENCY.observe(time.perf_counter() - start)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    if db_pool is None or redis_client is None:
        raise HTTPException(status_code=503, detail="dependencies not initialized")
    async with db_pool.acquire() as conn:
        await conn.execute("SELECT 1")
    await redis_client.ping()
    return {"status": "ready", "service": SERVICE_NAME}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/v1/alerts/evaluate")
async def evaluate(score: RiskScore, request: Request) -> dict:
    trace_id = request.headers.get("x-trace-id") or uuid4().hex
    deduplicated = False
    region_critical_count = 0
    region_alert_open = False
    reason = primary_alert_reason(score.risk_reasons) or "device_health_critical"

    try:
        if REDIS_LATENCY_MS > 0:
            await asyncio.sleep(REDIS_LATENCY_MS / 1000)
        assert redis_client is not None
        dedupe_key = f"alert-dedupe:{score.device_id}:{reason}"
        deduplicated = not bool(await redis_client.set(dedupe_key, "1", ex=300, nx=True))
        if score.risk_level == RiskLevel.CRITICAL:
            region_count_key = f"region:{score.region}:critical_count"
            region_critical_count = int(await redis_client.incr(region_count_key))
            await redis_client.expire(region_count_key, 300)
            region_alert_open = bool(await redis_client.get(f"region:{score.region}:alert_open"))
    except Exception as exc:
        REDIS_ERRORS.inc()
        logger.error(
            "redis unavailable during alert evaluation",
            extra={
                "event": "redis_error",
                "trace_id": trace_id,
                "device_id": score.device_id,
                "region": score.region,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        )

    decision = evaluate_alerts(
        score,
        deduplicated=deduplicated,
        region_critical_count=region_critical_count,
        region_alert_already_open=region_alert_open,
    )
    if decision.deduplicated:
        DEDUPED.inc()
    if decision.suppressed:
        SUPPRESSED.inc()

    assert db_pool is not None
    async with db_pool.acquire() as conn:
        for alert in decision.alerts:
            await conn.execute(
                """
                INSERT INTO alerts (
                    alert_id, device_id, region, severity, reason, status, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (alert_id) DO NOTHING
                """,
                alert.alert_id,
                alert.device_id,
                alert.region,
                alert.severity,
                alert.reason,
                alert.status.value,
                alert.created_at,
            )
            CREATED.labels(alert.severity, alert.reason).inc()
            if alert.device_id is None:
                try:
                    assert redis_client is not None
                    await redis_client.setex(f"region:{score.region}:alert_open", 600, alert.alert_id)
                except Exception:
                    REDIS_ERRORS.inc()

    logger.info(
        "alert evaluated",
        extra={
            "event": "alert_evaluated",
            "trace_id": trace_id,
            "device_id": score.device_id,
            "region": score.region,
        },
    )
    return decision.model_dump(mode="json")


@app.get("/api/v1/alerts")
async def list_alerts(limit: int = 50) -> dict:
    assert db_pool is not None
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT alert_id, device_id, region, severity, reason, status, created_at
            FROM alerts
            ORDER BY created_at DESC
            LIMIT $1
            """,
            min(limit, 200),
        )
    return {"alerts": [dict(row) for row in rows]}
