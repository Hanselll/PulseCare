from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from uuid import uuid4

import asyncpg
import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from pulsecare_core.logging import configure_json_logging
from pulsecare_core.validation import validate_signal

SERVICE_NAME = "ingestion-service"
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://pulsecare:pulsecare@postgres:5432/pulsecare"
)
SCORING_URL = os.getenv("SCORING_URL", "http://risk-scoring-service:8000/api/v1/score")

configure_json_logging(SERVICE_NAME)
logger = logging.getLogger(SERVICE_NAME)

REQUESTS = Counter(
    "pulsecare_ingestion_requests_total", "Ingestion requests", ["method", "route", "status"]
)
LATENCY = Histogram("pulsecare_ingestion_request_latency_seconds", "Ingestion latency")
DOWNSTREAM_ERRORS = Counter(
    "pulsecare_ingestion_downstream_errors_total", "Downstream errors", ["downstream_service"]
)
VALIDATION_FAILURES = Counter(
    "pulsecare_ingestion_validation_failures_total", "Validation failures at ingestion"
)
DEVICE_SIGNALS = Counter("device_signals_total", "Accepted device signals", ["region"])

db_pool: asyncpg.Pool | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS device_signals (
                id BIGSERIAL PRIMARY KEY,
                device_id TEXT NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                temperature DOUBLE PRECISION NOT NULL,
                voltage DOUBLE PRECISION NOT NULL,
                heartbeat BOOLEAN NOT NULL,
                error_code TEXT,
                region TEXT NOT NULL,
                firmware_version TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    yield 


app = FastAPI(title="PulseCare ingestion-service", lifespan=lifespan)


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
    if db_pool is None:
        raise HTTPException(status_code=503, detail="database not initialized")
    async with db_pool.acquire() as conn:
        await conn.execute("SELECT 1")
    return {"status": "ready", "service": SERVICE_NAME}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/v1/signals")
async def ingest_signal(payload: dict, request: Request) -> dict:
    trace_id = request.headers.get("x-trace-id") or uuid4().hex
    ok, signal, errors = validate_signal(payload)
    if not ok or signal is None:
        VALIDATION_FAILURES.inc()
        logger.info(
            "invalid device signal",
            extra={"event": "signal_invalid", "trace_id": trace_id, "error_message": errors},
        )
        raise HTTPException(status_code=400, detail={"valid": False, "errors": errors})

    logger.info(
        "device signal received",
        extra={
            "event": "signal_received",
            "trace_id": trace_id,
            "device_id": signal.device_id,
            "region": signal.region,
        },
    )

    assert db_pool is not None
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO device_signals (
                device_id, timestamp, temperature, voltage, heartbeat, error_code, region,
                firmware_version
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            signal.device_id,
            signal.timestamp,
            signal.temperature,
            signal.voltage,
            signal.heartbeat,
            signal.error_code,
            signal.region,
            signal.firmware_version,
        )

    DEVICE_SIGNALS.labels(signal.region).inc()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            scoring_response = await client.post(
                SCORING_URL,
                json=signal.model_dump(mode="json"),
                headers={"x-trace-id": trace_id},
            )
            scoring_response.raise_for_status()
    except httpx.HTTPError as exc:
        DOWNSTREAM_ERRORS.labels("risk-scoring-service").inc()
        logger.error(
            "scoring downstream error",
            extra={
                "event": "downstream_error",
                "trace_id": trace_id,
                "device_id": signal.device_id,
                "region": signal.region,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        )
        raise HTTPException(status_code=502, detail="risk-scoring-service unavailable") from exc

    return {"accepted": True, "trace_id": trace_id, "score": scoring_response.json()}
