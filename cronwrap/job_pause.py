"""Pause/resume jobs by writing a pause marker file."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class PauseError(Exception):
    pass


@dataclass
class PauseState:
    job_name: str
    paused_at: float = field(default_factory=time.time)
    reason: Optional[str] = None
    resume_after: Optional[float] = None  # epoch seconds

    def to_dict(self) -> dict:
        d: dict = {
            "job_name": self.job_name,
            "paused_at": self.paused_at,
        }
        if self.reason is not None:
            d["reason"] = self.reason
        if self.resume_after is not None:
            d["resume_after"] = self.resume_after
        return d

    @staticmethod
    def from_dict(data: dict) -> "PauseState":
        return PauseState(
            job_name=data["job_name"],
            paused_at=float(data.get("paused_at", 0)),
            reason=data.get("reason"),
            resume_after=data.get("resume_after"),
        )


class JobPause:
    def __init__(self, state_dir: str) -> None:
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        safe = job_name.replace("/", "_")
        return self.state_dir / f"{safe}.pause.json"

    def pause(self, job_name: str, reason: Optional[str] = None, resume_after: Optional[float] = None) -> PauseState:
        state = PauseState(job_name=job_name, reason=reason, resume_after=resume_after)
        self._path(job_name).write_text(json.dumps(state.to_dict()))
        return state

    def resume(self, job_name: str) -> None:
        p = self._path(job_name)
        if p.exists():
            p.unlink()

    def is_paused(self, job_name: str) -> bool:
        p = self._path(job_name)
        if not p.exists():
            return False
        state = PauseState.from_dict(json.loads(p.read_text()))
        if state.resume_after is not None and time.time() >= state.resume_after:
            p.unlink()
            return False
        return True

    def get_state(self, job_name: str) -> Optional[PauseState]:
        p = self._path(job_name)
        if not p.exists():
            return None
        return PauseState.from_dict(json.loads(p.read_text()))

    def list_paused(self) -> list[str]:
        names = []
        for f in sorted(self.state_dir.glob("*.pause.json")):
            job_name = json.loads(f.read_text()).get("job_name", f.stem)
            if self.is_paused(job_name):
                names.append(job_name)
        return names
