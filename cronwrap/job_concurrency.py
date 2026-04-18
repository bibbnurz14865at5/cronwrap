"""Concurrency policy: limit how many instances of a job may run simultaneously."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


class ConcurrencyError(Exception):
    """Raised when the concurrency limit is exceeded."""


@dataclass
class ConcurrencyPolicy:
    job_name: str
    max_instances: int = 1
    state_dir: str = "/tmp/cronwrap/concurrency"

    @classmethod
    def from_dict(cls, data: dict) -> "ConcurrencyPolicy":
        return cls(
            job_name=data["job_name"],
            max_instances=int(data.get("max_instances", 1)),
            state_dir=data.get("state_dir", "/tmp/cronwrap/concurrency"),
        )

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "max_instances": self.max_instances,
            "state_dir": self.state_dir,
        }

    def _state_path(self) -> Path:
        return Path(self.state_dir) / f"{self.job_name}.json"

    def _load_pids(self) -> List[int]:
        p = self._state_path()
        if not p.exists():
            return []
        try:
            data = json.loads(p.read_text())
            alive = [pid for pid in data.get("pids", []) if _pid_alive(pid)]
            return alive
        except (json.JSONDecodeError, OSError):
            return []

    def _save_pids(self, pids: List[int]) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"pids": pids}))

    def acquire(self, pid: int | None = None) -> None:
        """Register *pid* (default: current process) as a running instance."""
        pid = pid or os.getpid()
        pids = self._load_pids()
        if len(pids) >= self.max_instances:
            raise ConcurrencyError(
                f"Job '{self.job_name}' already has {len(pids)} running instance(s) "
                f"(limit={self.max_instances})"
            )
        pids.append(pid)
        self._save_pids(pids)

    def release(self, pid: int | None = None) -> None:
        """Deregister *pid* from the running set."""
        pid = pid or os.getpid()
        pids = self._load_pids()
        pids = [p for p in pids if p != pid]
        self._save_pids(pids)

    def running_count(self) -> int:
        return len(self._load_pids())


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
