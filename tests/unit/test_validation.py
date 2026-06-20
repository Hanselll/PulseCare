from datetime import UTC, datetime, timedelta

from pulsecare_core.validation import validate_signal


def valid_payload() -> dict:
    return {
        "device_id": "dev-001",
        "timestamp": "2026-05-18T08:00:00Z",
        "temperature": 78.5,
        "voltage": 3.2,
        "heartbeat": True,
        "error_code": None,
        "region": "gz-edge-1",
        "firmware_version": "1.0.3",
    }


def test_validate_signal_accepts_valid_payload():
    ok, signal, errors = validate_signal(
        valid_payload(),
        now=datetime(2026, 5, 18, 8, 0, tzinfo=UTC),
    )

    assert ok is True
    assert signal is not None
    assert signal.device_id == "dev-001"
    assert errors == []


def test_validate_signal_reports_missing_configured_field():
    ok, signal, errors = validate_signal(
        valid_payload(),
        required_fields=["device_id", "firmware_build"],
    )

    assert ok is False
    assert signal is None
    assert errors == [{"field": "firmware_build", "message": "missing field firmware_build"}]


def test_validate_signal_rejects_out_of_range_temperature():
    payload = valid_payload()
    payload["temperature"] = 200

    ok, signal, errors = validate_signal(payload)

    assert ok is False
    assert signal is None
    assert errors[0]["field"] == "temperature"


def test_validate_signal_rejects_future_timestamp():
    now = datetime.now(UTC)
    payload = valid_payload()
    payload["timestamp"] = (now + timedelta(minutes=10)).isoformat()

    ok, _, errors = validate_signal(payload, now=now)

    assert ok is False
    assert errors == [{"field": "timestamp", "message": "timestamp too far in future"}]
