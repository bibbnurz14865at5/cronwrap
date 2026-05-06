"""Tests for cronwrap.job_progress and cronwrap.progress_cli."""
from __future__ import annotations

import json
import pytest

from cronwrap.job_progress import JobProgress, ProgressRecord, ProgressError
from cronwrap.progress_cli import build_parser, main


def _make(tmp_path):
    return JobProgress(state_dir=str(tmp_path / "progress"))


# --- ProgressRecord ---

def test_record_to_dict_keys():
    r = ProgressRecord(job_name="backup", step=3, total=10, message="running")
    d = r.to_dict()
    assert set(d.keys()) >= {"job_name", "step", "total", "pct", "message", "updated_at"}


def test_record_pct_normal():
    r = ProgressRecord(job_name="j", step=5, total=10, message="")
    assert r.pct == 50.0


def test_record_pct_zero_total():
    r = ProgressRecord(job_name="j", step=0, total=0, message="")
    assert r.pct == 0.0


def test_record_extra_omitted_when_empty():
    r = ProgressRecord(job_name="j", step=1, total=5, message="ok")
    assert "extra" not in r.to_dict()


def test_record_extra_included_when_set():
    r = ProgressRecord(job_name="j", step=1, total=5, message="ok", extra={"host": "srv1"})
    assert r.to_dict()["extra"] == {"host": "srv1"}


def test_record_roundtrip():
    r = ProgressRecord(job_name="sync", step=7, total=20, message="halfway", extra={"k": "v"})
    r2 = ProgressRecord.from_dict(r.to_dict())
    assert r2.job_name == r.job_name
    assert r2.step == r.step
    assert r2.total == r.total
    assert r2.message == r.message
    assert r2.extra == r.extra


# --- JobProgress ---

def test_update_creates_file(tmp_path):
    tracker = _make(tmp_path)
    tracker.update("myjob", step=2, total=10, message="started")
    assert any(tracker.state_dir.iterdir())


def test_get_returns_none_when_absent(tmp_path):
    tracker = _make(tmp_path)
    assert tracker.get("nonexistent") is None


def test_get_returns_record_after_update(tmp_path):
    tracker = _make(tmp_path)
    tracker.update("myjob", step=3, total=9, message="in progress")
    rec = tracker.get("myjob")
    assert rec is not None
    assert rec.step == 3
    assert rec.total == 9


def test_clear_removes_file(tmp_path):
    tracker = _make(tmp_path)
    tracker.update("myjob", step=1, total=5, message="")
    tracker.clear("myjob")
    assert tracker.get("myjob") is None


def test_clear_noop_when_absent(tmp_path):
    tracker = _make(tmp_path)
    tracker.clear("ghost")  # should not raise


def test_update_raises_on_negative_step(tmp_path):
    tracker = _make(tmp_path)
    with pytest.raises(ProgressError):
        tracker.update("j", step=-1, total=10, message="")


def test_update_raises_on_negative_total(tmp_path):
    tracker = _make(tmp_path)
    with pytest.raises(ProgressError):
        tracker.update("j", step=0, total=-5, message="")


# --- CLI ---

def _run(args):
    return main(args)


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1():
    assert _run([]) == 1


def test_show_missing_job_returns_2(tmp_path):
    assert _run(["show", "ghost", "--state-dir", str(tmp_path)]) == 2


def test_show_existing_job_returns_0(tmp_path, capsys):
    tracker = JobProgress(state_dir=str(tmp_path))
    tracker.update("myjob", step=4, total=8, message="ok")
    rc = _run(["show", "myjob", "--state-dir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["step"] == 4


def test_clear_command_returns_0(tmp_path):
    tracker = JobProgress(state_dir=str(tmp_path))
    tracker.update("myjob", step=1, total=3, message="")
    rc = _run(["clear", "myjob", "--state-dir", str(tmp_path)])
    assert rc == 0
    assert tracker.get("myjob") is None
