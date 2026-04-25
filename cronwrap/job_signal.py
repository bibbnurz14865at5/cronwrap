"""Job signal handling — send OS signals to running cron jobs by PID."""
from __future__ import annotations

import json
import os
import signal
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class SignalError(Exception):
    """Raised when a signal operation fails."""


@dataclass
class SignalRecord:
    job_name: str
    pid: int
    signal_name: str
    sent_at: str
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "job_name": self.job_name,
            "pid": self.pid,
            "signal_name": self.signal_name,
            "sent_at": self.sent_at,
        }
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "SignalRecord":
        return cls(
            job_name=data["job_name"],
            pid=data["pid"],
            signal_name=data["signal_name"],
            sent_at=data["sent_at"],
            extra=data.get("extra", {}),
        )


class JobSignal:
    """Send signals to jobs and record signal history."""

    ALLOWED_SIGNALS = {"SIGTERM", "SIGKILL", "SIGHUP", "SIGUSR1", "SIGUSR2"}

    def __init__(self, state_dir: str) -> None:
        self._dir = Path(state_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _log_path(self, job_name: str) -> Path:
        return self._dir / f"{job_name}.signal_log.json"

    def _load_log(self, job_name: str) -> list:
        p = self._log_path(job_name)
        if not p.exists():
            return []
        return json.loads(p.read_text())

    def _save_log(self, job_name: str, records: list) -> None:
        self._log_path(job_name).write_text(json.dumps(records, indent=2))

    def send(self, job_name: str, pid: int, signal_name: str, extra: Optional[dict] = None) -> SignalRecord:
        """Send *signal_name* to *pid* and record the event."""
        if signal_name not in self.ALLOWED_SIGNALS:
            raise SignalError(f"Signal '{signal_name}' is not allowed. Choose from {self.ALLOWED_SIGNALS}")
        sig = getattr(signal, signal_name, None)
        if sig is None:
            raise SignalError(f"Signal '{signal_name}' not available on this platform")
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            raise SignalError(f"No process with PID {pid}")
        except PermissionError:
            raise SignalError(f"Permission denied sending {signal_name} to PID {pid}")

        from datetime import datetime, timezone
        record = SignalRecord(
            job_name=job_name,
            pid=pid,
            signal_name=signal_name,
            sent_at=datetime.now(timezone.utc).isoformat(),
            extra=extra or {},
        )
        log = self._load_log(job_name)
        log.append(record.to_dict())
        self._save_log(job_name, log)
        return record

    def history(self, job_name: str) -> list[SignalRecord]:
        """Return all signal records for *job_name*."""
        return [SignalRecord.from_dict(d) for d in self._load_log(job_name)]

    def clear_history(self, job_name: str) -> int:
        """Delete signal log for *job_name*. Returns number of records removed."""
        p = self._log_path(job_name)
        if not p.exists():
            return 0
        count = len(self._load_log(job_name))
        p.unlink()
        return count
