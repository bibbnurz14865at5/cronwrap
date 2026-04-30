"""Tests for cronwrap.job_deadletter and deadletter_cli."""
from __future__ import annotations

import json
import pytest

from cronwrap.job_deadletter import DeadLetterEvent, DeadLetterQueue
from cronwrap.deadletter_cli import build_parser, main


def _make(tmp_path):
    return DeadLetterQueue(str(tmp_path / "dlq"))


# --- DeadLetterEvent ---

def test_event_to_dict_required_keys():
    e = DeadLetterEvent(job_name="backup", reason="timeout", payload={"rc": 1})
    d = e.to_dict()
    assert "job_name" in d
    assert "reason" in d
    assert "payload" in d
    assert "timestamp" in d
    assert "attempt" in d


def test_event_to_dict_omits_extra_when_empty():
    e = DeadLetterEvent(job_name="backup", reason="timeout", payload={})
    assert "extra" not in e.to_dict()


def test_event_to_dict_includes_extra_when_set():
    e = DeadLetterEvent(job_name="backup", reason="timeout", payload={}, extra={"host": "srv1"})
    assert e.to_dict()["extra"] == {"host": "srv1"}


def test_event_roundtrip():
    e = DeadLetterEvent(job_name="sync", reason="nonzero", payload={"rc": 2}, attempt=3)
    e2 = DeadLetterEvent.from_dict(e.to_dict())
    assert e2.job_name == "sync"
    assert e2.reason == "nonzero"
    assert e2.attempt == 3


# --- DeadLetterQueue ---

def test_push_and_list(tmp_path):
    q = _make(tmp_path)
    e = DeadLetterEvent(job_name="job1", reason="fail", payload={"rc": 1})
    q.push(e)
    events = q.list_events("job1")
    assert len(events) == 1
    assert events[0].job_name == "job1"


def test_list_empty_returns_empty(tmp_path):
    q = _make(tmp_path)
    assert q.list_events("no_such_job") == []


def test_push_multiple_events(tmp_path):
    q = _make(tmp_path)
    for i in range(3):
        q.push(DeadLetterEvent(job_name="job1", reason="err", payload={"i": i}))
    assert len(q.list_events("job1")) == 3


def test_purge_removes_file(tmp_path):
    q = _make(tmp_path)
    q.push(DeadLetterEvent(job_name="job1", reason="err", payload={}))
    count = q.purge("job1")
    assert count == 1
    assert q.list_events("job1") == []


def test_purge_nonexistent_returns_zero(tmp_path):
    q = _make(tmp_path)
    assert q.purge("ghost") == 0


def test_all_job_names(tmp_path):
    q = _make(tmp_path)
    q.push(DeadLetterEvent(job_name="alpha", reason="x", payload={}))
    q.push(DeadLetterEvent(job_name="beta", reason="x", payload={}))
    names = q.all_job_names()
    assert names == ["alpha", "beta"]


# --- CLI ---

def _run(tmp_path, *args):
    return main(["--queue-dir", str(tmp_path / "dlq")] + list(args))


def test_build_parser_returns_parser():
    assert build_parser() is not None


def test_no_command_returns_1(tmp_path):
    assert _run(tmp_path) == 1


def test_list_empty_returns_0(tmp_path, capsys):
    assert _run(tmp_path, "list") == 0
    out = capsys.readouterr().out
    assert "No dead-letter" in out


def test_show_no_events_returns_0(tmp_path, capsys):
    assert _run(tmp_path, "show", "myjob") == 0
    out = capsys.readouterr().out
    assert "No dead-letter events for job" in out


def test_show_with_events_returns_0(tmp_path, capsys):
    q = DeadLetterQueue(str(tmp_path / "dlq"))
    q.push(DeadLetterEvent(job_name="myjob", reason="fail", payload={"rc": 1}))
    assert _run(tmp_path, "show", "myjob") == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["job_name"] == "myjob"


def test_purge_returns_0(tmp_path, capsys):
    q = DeadLetterQueue(str(tmp_path / "dlq"))
    q.push(DeadLetterEvent(job_name="myjob", reason="fail", payload={}))
    assert _run(tmp_path, "purge", "myjob") == 0
    assert "Purged 1" in capsys.readouterr().out
