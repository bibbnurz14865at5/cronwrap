"""Tests for cronwrap.retention module."""

import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from cronwrap.history import HistoryEntry, JobHistory
from cronwrap.retention import RetentionPolicy, prune_all, prune_history


def _write_entries(history_dir, job_name, entries):
    path = os.path.join(history_dir, f"{job_name}.json")
    with open(path, "w") as fh:
        json.dump([e.to_dict() for e in entries], fh)


def _make_entry(days_ago: int, success: bool = True) -> HistoryEntry:
    ts = (datetime.now(tz=timezone.utc) - timedelta(days=days_ago)).isoformat()
    return HistoryEntry(success=success, duration=1.0, exit_code=0 if success else 1, timestamp=ts)


# --- RetentionPolicy ---

def test_from_dict_defaults():
    p = RetentionPolicy.from_dict({"max_entries": 10})
    assert p.max_entries == 10
    assert p.max_days is None


def test_from_dict_both():
    p = RetentionPolicy.from_dict({"max_entries": 5, "max_days": 30})
    assert p.max_entries == 5
    assert p.max_days == 30


def test_to_dict_roundtrip():
    p = RetentionPolicy(max_entries=20, max_days=7)
    assert RetentionPolicy.from_dict(p.to_dict()).max_entries == 20


def test_no_constraints_raises():
    with pytest.raises(ValueError):
        RetentionPolicy()


# --- prune_history ---

def test_prune_by_max_entries(tmp_path):
    entries = [_make_entry(i) for i in range(10)]
    _write_entries(str(tmp_path), "myjob", entries)
    policy = RetentionPolicy(max_entries=3)
    removed = prune_history("myjob", str(tmp_path), policy)
    assert removed == 7
    history = JobHistory("myjob", str(tmp_path)).load()
    assert len(history) == 3


def test_prune_by_max_days(tmp_path):
    entries = [_make_entry(i) for i in range(5)]  # 0..4 days ago
    _write_entries(str(tmp_path), "myjob", entries)
    policy = RetentionPolicy(max_days=2)
    removed = prune_history("myjob", str(tmp_path), policy)
    assert removed == 2  # days 3 and 4 are removed
    history = JobHistory("myjob", str(tmp_path)).load()
    assert len(history) == 3


def test_prune_no_removal_needed(tmp_path):
    entries = [_make_entry(0), _make_entry(1)]
    _write_entries(str(tmp_path), "myjob", entries)
    policy = RetentionPolicy(max_entries=10)
    removed = prune_history("myjob", str(tmp_path), policy)
    assert removed == 0


def test_prune_empty_history(tmp_path):
    _write_entries(str(tmp_path), "myjob", [])
    policy = RetentionPolicy(max_entries=5)
    removed = prune_history("myjob", str(tmp_path), policy)
    assert removed == 0


# --- prune_all ---

def test_prune_all_multiple_jobs(tmp_path):
    for job in ("job_a", "job_b"):
        _write_entries(str(tmp_path), job, [_make_entry(i) for i in range(6)])
    policy = RetentionPolicy(max_entries=2)
    results = prune_all(str(tmp_path), policy)
    assert results["job_a"] == 4
    assert results["job_b"] == 4


def test_prune_all_missing_dir():
    results = prune_all("/nonexistent/path", RetentionPolicy(max_entries=5))
    assert results == {}
