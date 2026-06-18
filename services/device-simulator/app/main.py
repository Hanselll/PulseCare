from __future__ import annotations

import asyncio
import logging
import os
import random
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from pulsecare_core.logging import configure_json_logging

SERVICE_NAME = "device-simulator"
DEVICE_COUNT = int(os.getenv("DEVICE_COUNT", "25"))
SEND_INTERVAL_MS = int(os.getenv("SEND_INTERVAL_MS", "1000"))
ERROR_MODE = os.getenv("ERROR_MODE", "normal")
TARGET_INGESTION_URL = os.getenv(
    "TARGET_INGESTION_URL", "http://ingestion-service:8000/api/v1/signals"
)
REGION_COUNT = int(os.getenv("REGION_COUNT", "3"))
SCENARIO_NAME = os.getenv("SCENARIO_NAME", "baseline")

configure_json_logging(SERVICE_NAME)
logger = logging.getLogger(SERVICE_NAME)

EVENTS = Counter("pulsecare_simulator_events_total", "Generated simulator events", ["mode"])
SEND_ERRORS = Counter("pulsecare_simulator_send_errors_total", "Simulator send errors")
SEND_LATENCY = Histogram("pulsecare_simulator_send_latency_seconds", "Simulator send latency")

runner_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global runner_task
    runner_task = asyncio.create_task(run_simulator())
    yield
    runner_task.cancel()
    try:
        await runner_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="PulseCare device-simulator", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready", "service": SERVICE_NAME}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


async def run_simulator() -> None:
    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            batch_size = 10 if ERROR_MODE == "traffic_spike" else 1
            for _ in range(batch_size):
                payload = generate_signal()
                trace_id = uuid4().hex
                start = time.perf_counter()
                try:
                    response = await client.post(
                        TARGET_INGESTION_URL,
                        json=payload,
                        headers={"x-trace-id": trace_id},
                    )
                    response.raise_for_status()
                    EVENTS.labels(ERROR_MODE).inc()
                    SEND_LATENCY.observe(time.perf_counter() - start)
                    logger.info(
                        "signal sent",
                        extra={
                            "event": "signal_sent",
                            "trace_id": trace_id,
                            "device_id": payload.get("device_id"),
                            "region": payload.get("region"),
                        },
                    )
                except Exception as exc:
                    SEND_ERRORS.inc()
                    logger.error(
                        "signal send failed",
                        extra={
                            "event": "signal_send_failed",
                            "trace_id": trace_id,
                            "device_id": payload.get("device_id"),
                            "region": payload.get("region"),
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                        },
                    )
            await asyncio.sleep(SEND_INTERVAL_MS / 1000)


def generate_signal() -> dict:
    device_number = random.randint(1, DEVICE_COUNT)
    region_number = random.randint(1, REGION_COUNT)
    payload = {
        "device_id": f"dev-{device_number:03d}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": round(random.uniform(45, 78), 2),
        "voltage": round(random.uniform(3.1, 4.2), 2),
        "heartbeat": True,
        "error_code": None,
        "region": f"gz-edge-{region_number}",
        "firmware_version": "1.0.3",
    }

    if ERROR_MODE == "overheat":
        payload["temperature"] = round(random.uniform(85, 120), 2)
        payload["error_code"] = "E_OVERHEAT"
    elif ERROR_MODE == "low_voltage":
        payload["voltage"] = round(random.uniform(2.2, 2.9), 2)
        payload["error_code"] = "E_LOW_VOLTAGE"
    elif ERROR_MODE == "heartbeat_loss":
        payload["heartbeat"] = random.random() > 0.7
        payload["error_code"] = None if payload["heartbeat"] else "E_HEARTBEAT_LOSS"
    elif ERROR_MODE == "batch_offline":
        if device_number <= max(1, DEVICE_COUNT // 3):
            payload["heartbeat"] = False
            payload["error_code"] = "E_OFFLINE"
    elif ERROR_MODE == "invalid_schema":
        payload.pop("temperature")

    logger.debug("generated signal for scenario %s", SCENARIO_NAME)
    return payload
