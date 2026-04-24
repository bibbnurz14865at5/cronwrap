"""Job checkpoint tracking — persist and query progress markers for long-running jobs."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


class CheckpointError(Exception):
    """Raised when a checkpoint operation fails."""


@dataclass
class Checkpoint:
    job_name: str
    step: str
    timestamp: float = field(default_factory=time.time)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "job_name": self.job_name,
            "step": self.step,
            "timestamp": self.timestamp,
        }
        if self.meta:
            d["meta"] = self.meta
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        return cls(
            job_name=data["job_name"],
            step=data["step"],
            timestamp=float(data.get("timestamp", time.time())),
            meta=dict(data.get("meta") or {}),
        )


class JobCheckpoint:
    """Persist and retrieve checkpoints for a named job."""

    def __init__(self, job_name: str, state_dir: str = "/tmp/cronwrap/checkpoints") -> None:
        self.job_name = job_name
        self._dir = Path(state_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / f"{job_name}.json"

    def save(self, step: str, meta: Optional[Dict[str, Any]] = None) -> Checkpoint:
        """Save a checkpoint for the current step."""
        cp = Checkpoint(job_name=self.job_name, step=step, meta=meta or {})
        try:
            self._path.write_text(json.dumps(cp.to_dict(), indent=2))
        except OSError as exc:
            raise CheckpointError(f"Failed to save checkpoint: {exc}") from exc
        return cp

    def load(self) -> Optional[Checkpoint]:
        """Return the last saved checkpoint, or None if none exists."""
        if not self._path.exists():
            return None
        try:
            data = json.loads(self._path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise CheckpointError(f"Failed to load checkpoint: {exc}") from exc
        return Checkpoint.from_dict(data)

    def clear(self) -> None:
        """Remove the stored checkpoint."""
        if self._path.exists():
            self._path.unlink()

    def has_checkpoint(self) -> bool:
        """Return True if a checkpoint file exists."""
        return self._path.exists()
