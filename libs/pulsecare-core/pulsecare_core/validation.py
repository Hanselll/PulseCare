from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import ValidationError

from pulsecare_core.schemas import DeviceSignal


DEFAULT_REQUIRED_FIELDS = [
    "device_id",
    "timestamp",
    "temperature",
    "voltage",
    "heartbeat",
    "region",
]


def validate_signal(
    payload: dict[str, Any],
    required_fields: list[str] | None = None,
    now: datetime | None = None,
) -> tuple[bool, DeviceSignal | None, list[dict[str, str]]]:
    required = required_fields or DEFAULT_REQUIRED_FIELDS
    errors: list[dict[str, str]] = []

    for field in required:
        if field not in payload or payload[field] in (None, ""):
            errors.append({"field": field, "message": f"missing field {field}"})

    if errors:
        return False, None, errors

    try:
        signal = DeviceSignal.model_validate(payload)
    except ValidationError as exc:
        for item in exc.errors():
            field = ".".join(str(part) for part in item["loc"])
            errors.append({"field": field, "message": item["msg"]})
        return False, None, errors

    current_time = now or datetime.now(timezone.utc)
    if signal.timestamp > current_time + timedelta(minutes=5):
        return False, None, [{"field": "timestamp", "message": "timestamp too far in future"}]

    return True, signal, []
