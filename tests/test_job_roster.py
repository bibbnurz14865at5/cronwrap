"""Tests for cronwrap.job_roster."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwrap.job_roster import JobRoster, RosterEntry, MissingJob, RosterError


def _make(tmp_path) -> JobRoster:
    return JobRoster(
        roster_path=str(tmp_path / "roster.json"),
        history_dir=str(tmp_path / "history"),
    )


def _entry(name="backup", interval=3600) -> RosterEntry:
    return RosterEntry(job_name=name, expected_interval_seconds=interval)


def _write_history(tmp_path, job_name: str, timestamp: str) -> None:
    hdir = tmp_path / "history"
    hdir.mkdir(exist_ok=True)
    (hdir / f"{job_name}.json").write_text(
        json.dumps([{"timestamp": timestamp, "exit_code": 0}])
    )


# --- RosterEntry ---

def test_entry_to_dict_required_keys():
    e = _entry()
    d = e.to_dict()
    assert d["job_name"] == "backup"
    assert d["expected_interval_seconds"] == 3600


def test_entry_to_dict_omits_optional_when_none():
    e = _entry()
    d = e.to_dict()
    assert "description" not in d
    assert "extra" not in d


def test_entry_to_dict_includes_description():
    e = RosterEntry(job_name="x", expected_interval_seconds=60, description="hello")
    assert e.to_dict()["description"] == "hello"


def test_entry_roundtrip():
    e = RosterEntry(
        job_name="sync", expected_interval_seconds=120,
        description="sync job", extra={"env": "prod"}
    )
    assert RosterEntry.from_dict(e.to_dict()).job_name == "sync"
    assert RosterEntry.from_dict(e.to_dict()).extra == {"env": "prod"}


# --- JobRoster: register / list ---

def test_register_persists(tmp_path):
    r = _make(tmp_path)
    r.register(_entry("backup", 3600))
    entries = r.list_entries()
    assert len(entries) == 1
    assert entries[0].job_name == "backup"


def test_register_overwrites_existing(tmp_path):
    r = _make(tmp_path)
    r.register(_entry("backup", 3600))
    r.register(_entry("backup", 7200))
    entries = r.list_entries()
    assert len(entries) == 1
    assert entries[0].expected_interval_seconds == 7200


def test_list_empty_when_no_file(tmp_path):
    r = _make(tmp_path)
    assert r.list_entries() == []


# --- JobRoster: unregister ---

def test_unregister_removes_entry(tmp_path):
    r = _make(tmp_path)
    r.register(_entry("backup"))
    r.unregister("backup")
    assert r.list_entries() == []


def test_unregister_unknown_raises(tmp_path):
    r = _make(tmp_path)
    with pytest.raises(RosterError, match="backup"):
        r.unregister("backup")


# --- JobRoster: check_missing ---

def test_check_missing_no_history_is_overdue(tmp_path):
    r = _make(tmp_path)
    r.register(_entry("backup", 3600))
    now = datetime.now(timezone.utc)
    missing = r.check_missing(now=now)
    assert len(missing) == 1
    assert missing[0].job_name == "backup"
    assert missing[0].seconds_overdue > 0


def test_check_missing_recent_run_not_overdue(tmp_path):
    r = _make(tmp_path)
    r.register(_entry("backup", 3600))
    now = datetime.now(timezone.utc)
    ts = now.isoformat()
    _write_history(tmp_path, "backup", ts)
    missing = r.check_missing(now=now)
    assert missing == []


def test_check_missing_old_run_is_overdue(tmp_path):
    r = _make(tmp_path)
    r.register(_entry("backup", 60))
    from datetime import timedelta
    old = datetime(2000, 1, 1, tzinfo=timezone.utc)
    _write_history(tmp_path, "backup", old.isoformat())
    now = datetime.now(timezone.utc)
    missing = r.check_missing(now=now)
    assert len(missing) == 1
    assert missing[0].seconds_overdue > 60


def test_missing_job_repr(tmp_path):
    r = _make(tmp_path)
    r.register(_entry("backup", 3600))
    missing = r.check_missing()
    assert "backup" in repr(missing[0])
