from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pulsecare_core.schemas import DeviceSignal, RiskLevel, RiskScore


class ScoringRule(Protocol):
    reason: str

    def penalty(self, signal: DeviceSignal, has_recent_abnormal: bool) -> int: ...


@dataclass(frozen=True)
class TemperatureRule:
    reason: str = "temperature_above_threshold"

    def penalty(self, signal: DeviceSignal, has_recent_abnormal: bool) -> int:
        if signal.temperature > 100:
            return 45
        if signal.temperature > 80:
            return 25
        return 0


@dataclass(frozen=True)
class VoltageRule:
    reason: str = "voltage_below_threshold"

    def penalty(self, signal: DeviceSignal, has_recent_abnormal: bool) -> int:
        return 20 if signal.voltage < 3.0 else 0


@dataclass(frozen=True)
class HeartbeatRule:
    reason: str = "heartbeat_lost"

    def penalty(self, signal: DeviceSignal, has_recent_abnormal: bool) -> int:
        return 40 if not signal.heartbeat else 0


@dataclass(frozen=True)
class ErrorCodeRule:
    reason: str = "device_error_code_present"

    def penalty(self, signal: DeviceSignal, has_recent_abnormal: bool) -> int:
        return 20 if signal.error_code else 0


@dataclass(frozen=True)
class ConsecutiveAbnormalRule:
    reason: str = "consecutive_abnormal"

    def penalty(self, signal: DeviceSignal, has_recent_abnormal: bool) -> int:
        return 10 if has_recent_abnormal else 0


class RiskScorer:
    def __init__(self, rules: list[ScoringRule] | None = None) -> None:
        self.rules = rules or [
            TemperatureRule(),
            VoltageRule(),
            HeartbeatRule(),
            ErrorCodeRule(),
            ConsecutiveAbnormalRule(),
        ]

    def score(self, signal: DeviceSignal, has_recent_abnormal: bool = False) -> RiskScore:
        health_score = 100
        reasons: list[str] = []

        for rule in self.rules:
            penalty = rule.penalty(signal, has_recent_abnormal)
            if penalty > 0:
                health_score -= penalty
                reasons.append(rule.reason)

        health_score = max(0, min(100, health_score))
        return RiskScore(
            device_id=signal.device_id,
            region=signal.region,
            health_score=health_score,
            risk_level=risk_level_for_score(health_score),
            risk_reasons=reasons,
            timestamp=signal.timestamp,
        )


def risk_level_for_score(score: int) -> RiskLevel:
    if score >= 80:
        return RiskLevel.LOW
    if score >= 60:
        return RiskLevel.MEDIUM
    if score >= 40:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


def create_default_scorer() -> RiskScorer:
    return RiskScorer()
