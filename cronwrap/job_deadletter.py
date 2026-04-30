"""Dead-letter queue for failed cron job events."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


class DeadLetterError(Exception):
    """Raised for dead-letter queue errors."""


@dataclass
class DeadLetterEvent:
    job_name: str
    reason: str
    payload: Dict
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    attempt: int = 1
    extra: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        d = {
            "job_name": self.job_name,
            "reason": self.reason,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "attempt": self.attempt,
        }
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> "DeadLetterEvent":
        return cls(
            job_name=data["job_name"],
            reason=data["reason"],
            payload=data["payload"],
            timestamp=data["timestamp"],
            attempt=data.get("attempt", 1),
            extra=data.get("extra", {}),
        )


class DeadLetterQueue:
    def __init__(self, queue_dir: str) -> None:
        self.queue_dir = Path(queue_dir)
        self.queue_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        return self.queue_dir / f"{job_name}.jsonl"

    def push(self, event: DeadLetterEvent) -> None:
        with self._path(event.job_name).open("a") as fh:
            fh.write(json.dumps(event.to_dict()) + "\n")

    def list_events(self, job_name: str) -> List[DeadLetterEvent]:
        p = self._path(job_name)
        if not p.exists():
            return []
        events = []
        for line in p.read_text().splitlines():
            line = line.strip()
            if line:
                events.append(DeadLetterEvent.from_dict(json.loads(line)))
        return events

    def purge(self, job_name: str) -> int:
        p = self._path(job_name)
        if not p.exists():
            return 0
        count = sum(1 for ln in p.read_text().splitlines() if ln.strip())
        p.unlink()
        return count

    def all_job_names(self) -> List[str]:
        return sorted(
            f.stem for f in self.queue_dir.glob("*.jsonl")
        )
