from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from uuid import uuid4

import asyncpg
import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from redis.asyncio import Redis

from pulsecare_core.logging import configure_json_logging
from pulsecare_core.schemas import DeviceSignal, RiskLevel
from pulsecare_core.scoring import create_default_scorer

SERVICE_NAME = "risk-scoring-service"
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://pulsecare:pulsecare@postgres:5432/pulsecare"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
ALERT_URL = os.getenv("ALERT_URL", "http://alert-service:8000/api/v1/alerts/evaluate")
MEMORY_LEAK_MODE = os.getenv("MEMORY_LEAK_MODE", "false").lower() == "true"
SCORING_DELAY_MS = int(os.getenv("SCORING_DELAY_MS", "0"))
REDIS_LATENCY_MS = int(os.getenv("REDIS_LATENCY_MS", "0"))

configure_json_logging(SERVICE_NAME)
logger = logging.getLogger(SERVICE_NAME)
scorer = create_default_scorer()
leak_bucket: list[dict] = []

REQUESTS = Counter(
    "pulsecare_scoring_requests_total", "Scoring requests", ["method", "route", "status"]
)
LATENCY = Histogram("pulsecare_scoring_latency_seconds", "Scoring latency")
RISK_LEVELS = Counter("pulsecare_scoring_risk_level_total", "Risk levels", ["risk_level"])
RULE_HITS = Counter("pulsecare_scoring_rule_hits_total", "Scoring rule hits", ["rule"])
REDIS_ERRORS = Counter("pulsecare_scoring_redis_errors_total", "Redis errors")
DOWNSTREAM_ERRORS = Counter(
    "downstream_errors_total", "Downstream errors", ["service", "downstream_service"]
)

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
            CREATE TABLE IF NOT EXISTS risk_scores (
                id BIGSERIAL PRIMARY KEY,
                device_id TEXT NOT NULL,
                region TEXT NOT NULL,
                health_score INTEGER NOT NULL,
                risk_level TEXT NOT NULL,
                risk_reasons JSONB NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    yield
    await redis_client.aclose()
    await db_pool.close()


app = FastAPI(title="PulseCare risk-scoring-service", lifespan=lifespan)


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


@app.post("/api/v1/score")
async def score_signal(signal: DeviceSignal, request: Request) -> dict:
    trace_id = request.headers.get("x-trace-id") or uuid4().hex
    if SCORING_DELAY_MS > 0:
        await asyncio.sleep(SCORING_DELAY_MS / 1000)

    has_recent_abnormal = False
    try:
        if REDIS_LATENCY_MS > 0:
            await asyncio.sleep(REDIS_LATENCY_MS / 1000)
        assert redis_client is not None
        previous_level = await redis_client.get(f"device:{signal.device_id}:risk_level")
        has_recent_abnormal = previous_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
    except Exception as exc:
        REDIS_ERRORS.inc()
        logger.error(
            "redis read failed",
            extra={
                "event": "redis_error",
                "trace_id": trace_id,
                "device_id": signal.device_id,
                "region": signal.region,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        )

    score = scorer.score(signal, has_recent_abnormal=has_recent_abnormal)
    if MEMORY_LEAK_MODE:
        leak_bucket.append(signal.model_dump(mode="json"))

    RISK_LEVELS.labels(score.risk_level.value).inc()
    for reason in score.risk_reasons:
        RULE_HITS.labels(reason).inc()

    assert db_pool is not None
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO risk_scores (device_id, region, health_score, risk_level, risk_reasons)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            """,
            score.device_id,
            score.region,
            score.health_score,
            score.risk_level.value,
            score.model_dump_json(include={"risk_reasons"}),
        )

    try:
        assert redis_client is not None
        await redis_client.setex(f"device:{signal.device_id}:risk_level", 600, score.risk_level.value)
        await redis_client.setex(f"device:{signal.device_id}:latest", 600, signal.model_dump_json())
    except Exception as exc:
        REDIS_ERRORS.inc()
        logger.error(
            "redis write failed",
            extra={
                "event": "redis_error",
                "trace_id": trace_id,
                "device_id": signal.device_id,
                "region": signal.region,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        )

    alert_result = None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            alert_response = await client.post(
                ALERT_URL,
                json=score.model_dump(mode="json"),
                headers={"x-trace-id": trace_id},
            )
            alert_response.raise_for_status()
            alert_result = alert_response.json()
    except httpx.HTTPError as exc:
        DOWNSTREAM_ERRORS.labels(SERVICE_NAME, "alert-service").inc()
        logger.error(
            "alert downstream error",
            extra={
                "event": "downstream_error",
                "trace_id": trace_id,
                "device_id": signal.device_id,
                "region": signal.region,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        )
        raise HTTPException(status_code=502, detail="alert-service unavailable") from exc

    logger.info(
        "device scored",
        extra={
            "event": "device_scored",
            "trace_id": trace_id,
            "device_id": signal.device_id,
            "region": signal.region,
        },
    )
    return {"score": score.model_dump(mode="json"), "alert": alert_result}
