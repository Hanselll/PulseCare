from pulsecare_core.schemas import DeviceSignal, RiskLevel
from pulsecare_core.scoring import create_default_scorer


def signal(**overrides) -> DeviceSignal:
    payload = {
        "device_id": "dev-001",
        "timestamp": "2026-05-18T08:00:00Z",
        "temperature": 70.0,
        "voltage": 3.3,
        "heartbeat": True,
        "error_code": None,
        "region": "gz-edge-1",
    }
    payload.update(overrides)
    return DeviceSignal.model_validate(payload)


def test_scores_low_risk():
    score = create_default_scorer().score(signal())

    assert score.health_score == 100
    assert score.risk_level == RiskLevel.LOW


def test_scores_medium_risk():
    score = create_default_scorer().score(signal(temperature=85.0))

    assert score.health_score == 75
    assert score.risk_level == RiskLevel.MEDIUM


def test_scores_high_risk():
    score = create_default_scorer().score(signal(temperature=85.0, voltage=2.8))

    assert score.health_score == 55
    assert score.risk_level == RiskLevel.HIGH


def test_scores_critical_risk():
    score = create_default_scorer().score(
        signal(temperature=110.0, voltage=2.5, heartbeat=False, error_code="E_OVERHEAT")
    )

    assert score.health_score == 0
    assert score.risk_level == RiskLevel.CRITICAL
    assert "heartbeat_lost" in score.risk_reasons


def test_consecutive_abnormal_adds_penalty():
    score = create_default_scorer().score(signal(temperature=85.0), has_recent_abnormal=True)

    assert score.health_score == 65
    assert "consecutive_abnormal" in score.risk_reasons
