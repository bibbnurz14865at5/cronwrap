"""Tests for cronwrap.audit_log."""
import json
from pathlib import Path

import pytest

from cronwrap.audit_log import AuditEvent, AuditLog


# ── helpers ──────────────────────────────────────────────────────────────────

def _log(tmp_path) -> AuditLog:
    return AuditLog(str(tmp_path / "audit.log"))


# ── AuditEvent ────────────────────────────────────────────────────────────────

def test_event_to_dict_required_keys():
    ev = AuditEvent(event="run_start", job="backup")
    d = ev.to_dict()
    assert d["event"] == "run_start"
    assert d["job"] == "backup"
    assert "timestamp" in d


def test_event_to_dict_optional_keys_omitted_when_none():
    ev = AuditEvent(event="run_start", job="backup")
    d = ev.to_dict()
    assert "detail" not in d
    assert "exit_code" not in d


def test_event_to_dict_includes_optional_when_set():
    ev = AuditEvent(event="run_end", job="backup", detail="ok", exit_code=0)
    d = ev.to_dict()
    assert d["detail"] == "ok"
    assert d["exit_code"] == 0


def test_event_roundtrip():
    ev = AuditEvent(event="alert_sent", job="sync", detail="slack", exit_code=1)
    assert AuditEvent.from_dict(ev.to_dict()).event == "alert_sent"


# ── AuditLog ──────────────────────────────────────────────────────────────────

def test_read_empty_when_no_file(tmp_path):
    assert _log(tmp_path).read() == []


def test_append_creates_file(tmp_path):
    lg = _log(tmp_path)
    lg.append(AuditEvent(event="run_start", job="j1"))
    assert Path(lg.path).exists()


def test_append_and_read_roundtrip(tmp_path):
    lg = _log(tmp_path)
    lg.append(AuditEvent(event="run_start", job="j1"))
    lg.append(AuditEvent(event="run_end", job="j1", exit_code=0))
    events = lg.read()
    assert len(events) == 2
    assert events[0].event == "run_start"
    assert events[1].exit_code == 0


def test_read_filters_by_job(tmp_path):
    lg = _log(tmp_path)
    lg.append(AuditEvent(event="run_start", job="j1"))
    lg.append(AuditEvent(event="run_start", job="j2"))
    assert len(lg.read(job="j1")) == 1
    assert lg.read(job="j1")[0].job == "j1"


def test_tail_limits_results(tmp_path):
    lg = _log(tmp_path)
    for i in range(10):
        lg.append(AuditEvent(event="run_end", job="j", exit_code=i))
    tail = lg.tail(n=3)
    assert len(tail) == 3
    assert tail[-1].exit_code == 9


def test_each_line_is_valid_json(tmp_path):
    lg = _log(tmp_path)
    lg.append(AuditEvent(event="run_start", job="j"))
    lines = Path(lg.path).read_text().strip().splitlines()
    for line in lines:
        json.loads(line)  # must not raise
