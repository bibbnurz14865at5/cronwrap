"""Job capacity tracking — monitor and enforce slot-based concurrency limits."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


class CapacityError(Exception):
    """Raised when a capacity operation fails."""


@dataclass
class CapacityPolicy:
    job_name: str
    max_slots: int
    state_dir: str = "/tmp/cronwrap/capacity"
    extra: Dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "CapacityPolicy":
        data = dict(data)
        job_name = data.pop("job_name", None)
        if not job_name:
            raise CapacityError("'job_name' is required")
        max_slots = data.pop("max_slots", None)
        if max_slots is None:
            raise CapacityError("'max_slots' is required")
        if not isinstance(max_slots, int) or max_slots < 1:
            raise CapacityError("'max_slots' must be a positive integer")
        state_dir = data.pop("state_dir", "/tmp/cronwrap/capacity")
        return cls(job_name=job_name, max_slots=max_slots, state_dir=state_dir, extra=data)

    def to_dict(self) -> dict:
        d = {"job_name": self.job_name, "max_slots": self.max_slots, "state_dir": self.state_dir}
        d.update(self.extra)
        return d

    def _state_path(self) -> Path:
        return Path(self.state_dir) / f"{self.job_name}.capacity.json"

    def _load_state(self) -> List[int]:
        p = self._state_path()
        if not p.exists():
            return []
        try:
            return json.loads(p.read_text())
        except Exception:
            return []

    def _save_state(self, pids: List[int]) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(pids))

    def used_slots(self) -> int:
        pids = self._load_state()
        alive = [pid for pid in pids if _pid_alive(pid)]
        if len(alive) != len(pids):
            self._save_state(alive)
        return len(alive)

    def acquire(self) -> None:
        pids = self._load_state()
        alive = [pid for pid in pids if _pid_alive(pid)]
        if len(alive) >= self.max_slots:
            raise CapacityError(
                f"Job '{self.job_name}' has reached max capacity ({self.max_slots} slots)"
            )
        alive.append(os.getpid())
        self._save_state(alive)

    def release(self) -> None:
        pid = os.getpid()
        pids = self._load_state()
        pids = [p for p in pids if p != pid]
        self._save_state(pids)

    def available_slots(self) -> int:
        return max(0, self.max_slots - self.used_slots())


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
