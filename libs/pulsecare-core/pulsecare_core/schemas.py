from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(StrEnum):
    OPEN = "OPEN"
    ACKED = "ACKED"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"


class DeviceSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1)
    timestamp: datetime
    temperature: float = Field(ge=-40, le=150)
    voltage: float = Field(ge=0, le=5)
    heartbeat: bool
    error_code: str | None = None
    region: str = Field(min_length=1)
    firmware_version: str | None = None

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class RiskScore(BaseModel):
    device_id: str
    region: str
    health_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    risk_reasons: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Alert(BaseModel):
    alert_id: str = Field(default_factory=lambda: f"alert-{uuid4().hex[:12]}")
    device_id: str | None = None
    region: str
    severity: str
    reason: str
    status: AlertStatus = AlertStatus.OPEN
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AlertDecision(BaseModel):
    created: bool
    alerts: list[Alert] = Field(default_factory=list)
    deduplicated: bool = False
    suppressed: bool = False
