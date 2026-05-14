"""Alert policy for job quota usage thresholds."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class QuotaAlertError(Exception):
    """Raised for quota alert configuration errors."""


@dataclass
class QuotaAlertPolicy:
    job_name: str
    warn_pct: float = 75.0   # warn when usage >= this % of limit
    critical_pct: float = 90.0
    state_dir: str = "/tmp/cronwrap/quota_alert"
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.job_name:
            raise QuotaAlertError("job_name is required")
        if not (0 < self.warn_pct < 100):
            raise QuotaAlertError("warn_pct must be between 0 and 100")
        if not (0 < self.critical_pct <= 100):
            raise QuotaAlertError("critical_pct must be between 0 and 100")
        if self.warn_pct >= self.critical_pct:
            raise QuotaAlertError("warn_pct must be less than critical_pct")

    def to_dict(self) -> dict:
        d = {
            "job_name": self.job_name,
            "warn_pct": self.warn_pct,
            "critical_pct": self.critical_pct,
            "state_dir": self.state_dir,
        }
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "QuotaAlertPolicy":
        if "job_name" not in data:
            raise QuotaAlertError("job_name is required")
        known = {"job_name", "warn_pct", "critical_pct", "state_dir", "extra"}
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(
            job_name=data["job_name"],
            warn_pct=float(data.get("warn_pct", 75.0)),
            critical_pct=float(data.get("critical_pct", 90.0)),
            state_dir=data.get("state_dir", "/tmp/cronwrap/quota_alert"),
            extra={**data.get("extra", {}), **extra},
        )

    @classmethod
    def from_json_file(cls, path: str) -> "QuotaAlertPolicy":
        p = Path(path)
        if not p.exists():
            raise QuotaAlertError(f"Config file not found: {path}")
        return cls.from_dict(json.loads(p.read_text()))

    def evaluate(self, used: int, limit: int) -> "QuotaAlertResult":
        """Return an alert result given current usage."""
        if limit <= 0:
            raise QuotaAlertError("limit must be positive")
        pct = (used / limit) * 100.0
        if pct >= self.critical_pct:
            level = "critical"
        elif pct >= self.warn_pct:
            level = "warn"
        else:
            level = "ok"
        return QuotaAlertResult(job_name=self.job_name, used=used, limit=limit, pct=round(pct, 2), level=level)


@dataclass
class QuotaAlertResult:
    job_name: str
    used: int
    limit: int
    pct: float
    level: str  # "ok" | "warn" | "critical"

    @property
    def ok(self) -> bool:
        return self.level == "ok"

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "used": self.used,
            "limit": self.limit,
            "pct": self.pct,
            "level": self.level,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
