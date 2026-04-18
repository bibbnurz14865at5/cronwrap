"""Job priority levels and ordering utilities."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

PRIORITY_LEVELS = ("critical", "high", "normal", "low")
_LEVEL_ORDER = {lvl: i for i, lvl in enumerate(PRIORITY_LEVELS)}


class PriorityError(ValueError):
    pass


@dataclass
class JobPriority:
    job_name: str
    priority: str = "normal"
    weight: int = 0

    def __post_init__(self) -> None:
        if self.priority not in PRIORITY_LEVELS:
            raise PriorityError(
                f"Invalid priority {self.priority!r}. Choose from {PRIORITY_LEVELS}."
            )

    def to_dict(self) -> Dict:
        return {"job_name": self.job_name, "priority": self.priority, "weight": self.weight}

    @classmethod
    def from_dict(cls, data: Dict) -> "JobPriority":
        return cls(
            job_name=data["job_name"],
            priority=data.get("priority", "normal"),
            weight=int(data.get("weight", 0)),
        )

    @property
    def sort_key(self) -> tuple:
        return (_LEVEL_ORDER[self.priority], -self.weight)


class PriorityIndex:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._data: Dict[str, JobPriority] = {}
        if path.exists():
            raw = json.loads(path.read_text())
            for entry in raw:
                jp = JobPriority.from_dict(entry)
                self._data[jp.job_name] = jp

    def set(self, job_name: str, priority: str = "normal", weight: int = 0) -> None:
        self._data[job_name] = JobPriority(job_name=job_name, priority=priority, weight=weight)
        self._save()

    def get(self, job_name: str) -> Optional[JobPriority]:
        return self._data.get(job_name)

    def remove(self, job_name: str) -> None:
        self._data.pop(job_name, None)
        self._save()

    def sorted_jobs(self) -> List[JobPriority]:
        return sorted(self._data.values(), key=lambda jp: jp.sort_key)

    def _save(self) -> None:
        self._path.write_text(json.dumps([v.to_dict() for v in self._data.values()], indent=2))
