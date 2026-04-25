"""Distributed trace context for cron jobs."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any


class TracingError(Exception):
    """Raised when a tracing operation fails."""


@dataclass
class TraceRecord:
    job_name: str
    trace_id: str
    span_id: str
    started_at: str
    ended_at: Optional[str] = None
    parent_span_id: Optional[str] = None
    status: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "job_name": self.job_name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "started_at": self.started_at,
        }
        if self.ended_at is not None:
            d["ended_at"] = self.ended_at
        if self.parent_span_id is not None:
            d["parent_span_id"] = self.parent_span_id
        if self.status is not None:
            d["status"] = self.status
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TraceRecord":
        return cls(
            job_name=data["job_name"],
            trace_id=data["trace_id"],
            span_id=data["span_id"],
            started_at=data["started_at"],
            ended_at=data.get("ended_at"),
            parent_span_id=data.get("parent_span_id"),
            status=data.get("status"),
            extra=data.get("extra", {}),
        )


class JobTracing:
    def __init__(self, state_dir: str) -> None:
        self._dir = Path(state_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        return self._dir / f"{job_name}.trace.json"

    def start_trace(
        self,
        job_name: str,
        started_at: str,
        parent_span_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> TraceRecord:
        record = TraceRecord(
            job_name=job_name,
            trace_id=trace_id or str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            started_at=started_at,
            parent_span_id=parent_span_id,
            extra=extra or {},
        )
        self._path(job_name).write_text(json.dumps(record.to_dict(), indent=2))
        return record

    def finish_trace(
        self, job_name: str, ended_at: str, status: str
    ) -> TraceRecord:
        p = self._path(job_name)
        if not p.exists():
            raise TracingError(f"No active trace for job '{job_name}'")
        record = TraceRecord.from_dict(json.loads(p.read_text()))
        record.ended_at = ended_at
        record.status = status
        p.write_text(json.dumps(record.to_dict(), indent=2))
        return record

    def get(self, job_name: str) -> Optional[TraceRecord]:
        p = self._path(job_name)
        if not p.exists():
            return None
        return TraceRecord.from_dict(json.loads(p.read_text()))

    def clear(self, job_name: str) -> None:
        p = self._path(job_name)
        if p.exists():
            p.unlink()
