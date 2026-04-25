"""Tests for cronwrap.job_watchdog."""
from __future__ import annotations

import json
import time

import pytest

from cronwrap.job_watchdog import (
    JobWatchdog,
    StuckJob,
    WatchdogEntry,
    WatchdogError,
)


def _make(tmp_path) -> JobWatchdog:
    return JobWatchdog(state_dir=str(tmp_path / "watchdog"))


# ---------------------------------------------------------------------------
# WatchdogEntry serialisation
# ---------------------------------------------------------------------------

def test_entry_to_dict_required_keys():
    e = WatchdogEntry(job_name="backup", pid=1234, started_at=1_000_000.0)
    d = e.to_dict()
    assert d["job_name"] == "backup"
    assert d["pid"] == 1234
    assert d["started_at"] == 1_000_000.0


def test_entry_to_dict_omits_extra_when_empty():
    e = WatchdogEntry(job_name="x", pid=1, started_at=0.0)
    assert "extra" not in e.to_dict()


def test_entry_to_dict_includes_extra_when_set():
    e = WatchdogEntry(job_name="x", pid=1, started_at=0.0, extra={"env": "prod"})
    assert e.to_dict()["extra"] == {"env": "prod"}


def test_entry_roundtrip():
    e = WatchdogEntry(job_name="sync", pid=999, started_at=42.5, extra={"k": "v"})
    assert WatchdogEntry.from_dict(e.to_dict()) == e


# ---------------------------------------------------------------------------
# register / clear / get
# ---------------------------------------------------------------------------

def test_register_creates_file(tmp_path):
    wd = _make(tmp_path)
    entry = wd.register("myjob", pid=5678)
    assert entry.job_name == "myjob"
    assert entry.pid == 5678
    p = list((tmp_path / "watchdog").glob("*.watchdog.json"))
    assert len(p) == 1


def test_register_stores_started_at(tmp_path):
    before = time.time()
    wd = _make(tmp_path)
    entry = wd.register("job", pid=1)
    after = time.time()
    assert before <= entry.started_at <= after


def test_get_returns_entry(tmp_path):
    wd = _make(tmp_path)
    wd.register("job", pid=42)
    retrieved = wd.get("job")
    assert retrieved is not None
    assert retrieved.pid == 42


def test_get_returns_none_when_absent(tmp_path):
    wd = _make(tmp_path)
    assert wd.get("nonexistent") is None


def test_clear_removes_entry(tmp_path):
    wd = _make(tmp_path)
    wd.register("job", pid=1)
    wd.clear("job")
    assert wd.get("job") is None


def test_clear_noop_when_absent(tmp_path):
    wd = _make(tmp_path)
    wd.clear("ghost")  # should not raise


# ---------------------------------------------------------------------------
# find_stuck
# ---------------------------------------------------------------------------

def test_find_stuck_empty_when_no_jobs(tmp_path):
    wd = _make(tmp_path)
    assert wd.find_stuck(60) == []


def test_find_stuck_returns_overdue_job(tmp_path):
    wd = _make(tmp_path)
    # Manually write an entry with an old timestamp
    entry = WatchdogEntry(job_name="slow", pid=11, started_at=time.time() - 3600)
    state_dir = tmp_path / "watchdog"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "slow.watchdog.json").write_text(json.dumps(entry.to_dict()))
    stuck = wd.find_stuck(threshold_seconds=60)
    assert len(stuck) == 1
    assert stuck[0].entry.job_name == "slow"
    assert stuck[0].elapsed >= 3600


def test_find_stuck_excludes_recent_job(tmp_path):
    wd = _make(tmp_path)
    wd.register("fast", pid=2)
    stuck = wd.find_stuck(threshold_seconds=3600)
    assert stuck == []


def test_stuck_job_repr():
    entry = WatchdogEntry(job_name="foo", pid=7, started_at=0.0)
    s = StuckJob(entry=entry, elapsed=120.5)
    r = repr(s)
    assert "foo" in r
    assert "120.5" in r


def test_register_uses_current_pid_when_none(tmp_path):
    import os
    wd = _make(tmp_path)
    entry = wd.register("me")
    assert entry.pid == os.getpid()
