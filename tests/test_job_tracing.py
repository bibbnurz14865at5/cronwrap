"""Tests for cronwrap.job_tracing."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from cronwrap.job_tracing import JobTracing, TraceRecord, TracingError


NOW = datetime.now(timezone.utc).isoformat()


def _make(tmp_path) -> JobTracing:
    return JobTracing(str(tmp_path))


# ---------------------------------------------------------------------------
# TraceRecord serialisation
# ---------------------------------------------------------------------------

def test_record_to_dict_required_keys():
    r = TraceRecord(job_name="j", trace_id="t", span_id="s", started_at=NOW)
    d = r.to_dict()
    for key in ("job_name", "trace_id", "span_id", "started_at"):
        assert key in d


def test_record_to_dict_omits_optional_when_none():
    r = TraceRecord(job_name="j", trace_id="t", span_id="s", started_at=NOW)
    d = r.to_dict()
    assert "ended_at" not in d
    assert "parent_span_id" not in d
    assert "status" not in d
    assert "extra" not in d


def test_record_to_dict_includes_optional_when_set():
    r = TraceRecord(
        job_name="j", trace_id="t", span_id="s", started_at=NOW,
        ended_at=NOW, parent_span_id="p", status="success", extra={"k": "v"},
    )
    d = r.to_dict()
    assert d["ended_at"] == NOW
    assert d["parent_span_id"] == "p"
    assert d["status"] == "success"
    assert d["extra"] == {"k": "v"}


def test_record_roundtrip():
    r = TraceRecord(
        job_name="j", trace_id="t", span_id="s", started_at=NOW,
        ended_at=NOW, parent_span_id="p", status="failure", extra={"x": 1},
    )
    assert TraceRecord.from_dict(r.to_dict()).to_dict() == r.to_dict()


# ---------------------------------------------------------------------------
# JobTracing operations
# ---------------------------------------------------------------------------

def test_start_trace_creates_file(tmp_path):
    t = _make(tmp_path)
    t.start_trace("myjob", NOW)
    assert (tmp_path / "myjob.trace.json").exists()


def test_start_trace_generates_ids(tmp_path):
    t = _make(tmp_path)
    r = t.start_trace("myjob", NOW)
    assert r.trace_id
    assert r.span_id
    assert r.trace_id != r.span_id


def test_start_trace_accepts_existing_trace_id(tmp_path):
    t = _make(tmp_path)
    r = t.start_trace("myjob", NOW, trace_id="fixed-trace")
    assert r.trace_id == "fixed-trace"


def test_start_trace_stores_parent_span_id(tmp_path):
    t = _make(tmp_path)
    r = t.start_trace("myjob", NOW, parent_span_id="parent-span")
    assert r.parent_span_id == "parent-span"


def test_get_returns_none_when_no_trace(tmp_path):
    t = _make(tmp_path)
    assert t.get("ghost") is None


def test_get_returns_record_after_start(tmp_path):
    t = _make(tmp_path)
    t.start_trace("myjob", NOW)
    r = t.get("myjob")
    assert r is not None
    assert r.job_name == "myjob"


def test_finish_trace_updates_status(tmp_path):
    t = _make(tmp_path)
    t.start_trace("myjob", NOW)
    r = t.finish_trace("myjob", ended_at=NOW, status="success")
    assert r.status == "success"
    assert r.ended_at == NOW


def test_finish_trace_persists(tmp_path):
    t = _make(tmp_path)
    t.start_trace("myjob", NOW)
    t.finish_trace("myjob", ended_at=NOW, status="failure")
    r = t.get("myjob")
    assert r.status == "failure"


def test_finish_trace_raises_when_no_active_trace(tmp_path):
    t = _make(tmp_path)
    with pytest.raises(TracingError):
        t.finish_trace("ghost", ended_at=NOW, status="success")


def test_clear_removes_file(tmp_path):
    t = _make(tmp_path)
    t.start_trace("myjob", NOW)
    t.clear("myjob")
    assert t.get("myjob") is None


def test_clear_noop_when_no_file(tmp_path):
    t = _make(tmp_path)
    t.clear("ghost")  # should not raise


def test_extra_stored_and_retrieved(tmp_path):
    t = _make(tmp_path)
    t.start_trace("myjob", NOW, extra={"env": "prod"})
    r = t.get("myjob")
    assert r.extra == {"env": "prod"}
