from __future__ import annotations

from collections.abc import Iterable

from pulsecare_core.schemas import Alert, AlertDecision, RiskLevel, RiskScore


def evaluate_alerts(
    score: RiskScore,
    deduplicated: bool = False,
    region_critical_count: int = 0,
    region_alert_already_open: bool = False,
) -> AlertDecision:
    if deduplicated:
        return AlertDecision(created=False, deduplicated=True)

    alerts: list[Alert] = []
    reason = primary_alert_reason(score.risk_reasons)

    if score.risk_level == RiskLevel.HIGH:
        alerts.append(
            Alert(
                device_id=score.device_id,
                region=score.region,
                severity="warning",
                reason=reason or "device_health_high_risk",
            )
        )
    elif score.risk_level == RiskLevel.CRITICAL:
        alerts.append(
            Alert(
                device_id=score.device_id,
                region=score.region,
                severity="critical",
                reason=reason or "device_health_critical",
            )
        )

    if (
        score.risk_level == RiskLevel.CRITICAL
        and region_critical_count >= 10
        and not region_alert_already_open
    ):
        alerts.append(
            Alert(
                device_id=None,
                region=score.region,
                severity="critical",
                reason="region_critical_devices_threshold",
            )
        )

    return AlertDecision(created=bool(alerts), alerts=alerts)


def primary_alert_reason(reasons: Iterable[str]) -> str | None:
    for reason in reasons:
        return reason
    return None
