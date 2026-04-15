"""Tests for cronwrap.history."""

import json
import pytest

from cronwrap.history import HistoryEntry, JobHistory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entry(job_name="backup", command="/usr/bin/backup", exit_code=0,
           duration=1.5, timed_out=False, timestamp=None):
    return HistoryEntry(
        job_name=job_name,
        command=command,
        exit_code=exit_code,
        duration=duration,
        timed_out=timed_out,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# HistoryEntry
# ---------------------------------------------------------------------------

def test_entry_to_dict_roundtrip():
    e = _entry(timestamp="2024-01-01T00:00:00+00:00")
    d = e.to_dict()
    assert d["job_name"] == "backup"
    assert d["exit_code"] == 0
    assert d["timed_out"] is False
    restored = HistoryEntry.from_dict(d)
    assert restored.job_name == e.job_name
    assert restored.timestamp == e.timestamp


def test_entry_timestamp_auto_set():
    e = _entry()
    assert e.timestamp is not None and "T" in e.timestamp


def test_entry_to_dict_contains_all_keys():
    keys = {"job_name", "command", "exit_code", "duration", "timed_out", "timestamp"}
    assert keys == set(_entry().to_dict().keys())


# ---------------------------------------------------------------------------
# JobHistory.record / load_all
# ---------------------------------------------------------------------------

def test_record_creates_file(tmp_path):
    h = JobHistory(path=str(tmp_path / "hist.json"))
    h.record(_entry())
    assert (tmp_path / "hist.json").exists()


def test_record_and_load_all(tmp_path):
    h = JobHistory(path=str(tmp_path / "hist.json"))
    h.record(_entry(job_name="job1"))
    h.record(_entry(job_name="job2"))
    entries = h.load_all()
    assert len(entries) == 2
    assert entries[0].job_name == "job1"
    assert entries[1].job_name == "job2"


def test_load_all_empty_when_no_file(tmp_path):
    h = JobHistory(path=str(tmp_path / "missing.json"))
    assert h.load_all() == []


def test_load_all_returns_empty_on_corrupt_file(tmp_path):
    p = tmp_path / "hist.json"
    p.write_text("not json")
    h = JobHistory(path=str(p))
    assert h.load_all() == []


def test_max_entries_pruning(tmp_path):
    h = JobHistory(path=str(tmp_path / "hist.json"), max_entries=3)
    for i in range(5):
        h.record(_entry(job_name=f"job{i}"))
    entries = h.load_all()
    assert len(entries) == 3
    assert entries[0].job_name == "job2"  # oldest kept


# ---------------------------------------------------------------------------
# JobHistory.load_for_job
# ---------------------------------------------------------------------------

def test_load_for_job_filters_correctly(tmp_path):
    h = JobHistory(path=str(tmp_path / "hist.json"))
    h.record(_entry(job_name="alpha"))
    h.record(_entry(job_name="beta"))
    h.record(_entry(job_name="alpha"))
    result = h.load_for_job("alpha")
    assert len(result) == 2
    assert all(e.job_name == "alpha" for e in result)


def test_load_for_job_empty_when_no_match(tmp_path):
    h = JobHistory(path=str(tmp_path / "hist.json"))
    h.record(_entry(job_name="other"))
    assert h.load_for_job("missing") == []
