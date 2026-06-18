from pulsecare_core.alerting import evaluate_alerts
from pulsecare_core.schemas import RiskLevel, RiskScore


def score(level: RiskLevel, reasons: list[str] | None = None) -> RiskScore:
    health = {
        RiskLevel.LOW: 90,
        RiskLevel.MEDIUM: 70,
        RiskLevel.HIGH: 50,
        RiskLevel.CRITICAL: 20,
    }[level]
    return RiskScore(
        device_id="dev-001",
        region="gz-edge-1",
        health_score=health,
        risk_level=level,
        risk_reasons=reasons or [],
    )


def test_no_alert_for_low_or_medium():
    assert evaluate_alerts(score(RiskLevel.LOW)).created is False
    assert evaluate_alerts(score(RiskLevel.MEDIUM)).created is False


def test_high_creates_warning_alert():
    decision = evaluate_alerts(score(RiskLevel.HIGH, ["voltage_below_threshold"]))

    assert decision.created is True
    assert decision.alerts[0].severity == "warning"
    assert decision.alerts[0].reason == "voltage_below_threshold"


def test_critical_creates_critical_alert():
    decision = evaluate_alerts(score(RiskLevel.CRITICAL))

    assert decision.created is True
    assert decision.alerts[0].severity == "critical"


def test_deduplicated_alert_is_not_created():
    decision = evaluate_alerts(score(RiskLevel.CRITICAL), deduplicated=True)

    assert decision.created is False
    assert decision.deduplicated is True


def test_region_alert_when_critical_count_reaches_threshold():
    decision = evaluate_alerts(score(RiskLevel.CRITICAL), region_critical_count=10)

    assert len(decision.alerts) == 2
    assert decision.alerts[1].device_id is None
    assert decision.alerts[1].reason == "region_critical_devices_threshold"
