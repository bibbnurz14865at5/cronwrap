"""Job chaining: define ordered sequences of jobs with pass/fail routing."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


class ChainError(Exception):
    """Raised for job chain configuration or execution errors."""


@dataclass
class ChainStep:
    job_name: str
    on_success: Optional[str] = None  # next job_name or None to stop
    on_failure: Optional[str] = None  # next job_name or None to stop
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict = {"job_name": self.job_name}
        if self.on_success is not None:
            d["on_success"] = self.on_success
        if self.on_failure is not None:
            d["on_failure"] = self.on_failure
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ChainStep":
        return cls(
            job_name=data["job_name"],
            on_success=data.get("on_success"),
            on_failure=data.get("on_failure"),
            extra={k: v for k, v in data.items()
                   if k not in ("job_name", "on_success", "on_failure")},
        )


@dataclass
class JobChain:
    chain_name: str
    steps: List[ChainStep] = field(default_factory=list)

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "chain_name": self.chain_name,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobChain":
        if "chain_name" not in data:
            raise ChainError("'chain_name' is required")
        steps = [ChainStep.from_dict(s) for s in data.get("steps", [])]
        return cls(chain_name=data["chain_name"], steps=steps)

    @classmethod
    def from_json_file(cls, path: str) -> "JobChain":
        p = Path(path)
        if not p.exists():
            raise ChainError(f"Chain config not found: {path}")
        return cls.from_dict(json.loads(p.read_text()))

    # ------------------------------------------------------------------
    def step_for(self, job_name: str) -> Optional[ChainStep]:
        """Return the ChainStep for *job_name*, or None if not in chain."""
        for s in self.steps:
            if s.job_name == job_name:
                return s
        return None

    def next_job(self, job_name: str, success: bool) -> Optional[str]:
        """Return the next job name given the result of *job_name*."""
        step = self.step_for(job_name)
        if step is None:
            raise ChainError(f"Job '{job_name}' not found in chain '{self.chain_name}'")
        return step.on_success if success else step.on_failure

    def ordered_names(self) -> List[str]:
        """Return job names in declaration order."""
        return [s.job_name for s in self.steps]
