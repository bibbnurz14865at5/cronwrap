"""Tests for cronwrap.job_latency."""
import json
from datetime import datetime, timedelta

import pytest

from cronwrap.job_latency import JobLatency, LatencyRecord


def _make(tmp_path):
    return JobLatency(state_dir=str(tmp_path))


def _rec(job_name="backup", latency=5.0):
    scheduled = datetime(2024, 1, 15, 3, 0, 0)
    started = scheduled + timedelta(seconds=latency)
    return LatencyRecord.measure(job_name, scheduled, started)


def test_record_to_dict_keys():
    r = _rec()
    d = r.to_dict()
    assert "job_name" in d
    assert "scheduled_at" in d
    assert "started_at" in d
    assert "latency_seconds" in d


def test_record_extra_omitted_when_empty():
    r = _rec()
    assert "extra" not in r.to_dict()


def test_record_extra_included_when_set():
    scheduled = datetime(2024, 1, 15, 3, 0, 0)
    started = scheduled + timedelta(seconds=2)
    r = LatencyRecord.measure("job", scheduled, started, host="srv1")
    assert r.to_dict()["extra"] == {"host": "srv1"}


def test_record_roundtrip():
    r = _rec(latency=12.5)
    r2 = LatencyRecord.from_dict(r.to_dict())
    assert r2.job_name == r.job_name
    assert r2.latency_seconds == r.latency_seconds
    assert r2.scheduled_at == r.scheduled_at


def test_measure_clamps_negative_latency():
    scheduled = datetime(2024, 1, 15, 3, 0, 5)
    started = datetime(2024, 1, 15, 3, 0, 0)  # started before scheduled
    r = LatencyRecord.measure("job", scheduled, started)
    assert r.latency_seconds == 0.0


def test_measure_uses_utcnow_when_started_at_none():
    scheduled = datetime(2000, 1, 1)
    r = LatencyRecord.measure("job", scheduled)
    assert r.latency_seconds >= 0.0
    assert r.started_at is not None


def test_record_creates_file(tmp_path):
    tracker = _make(tmp_path)
    tracker.record(_rec())
    assert (tmp_path / "backup.latency.json").exists()


def test_get_records_empty(tmp_path):
    tracker = _make(tmp_path)
    assert tracker.get_records("backup") == []


def test_get_records_returns_all(tmp_path):
    tracker = _make(tmp_path)
    tracker.record(_rec(latency=3.0))
    tracker.record(_rec(latency=7.0))
    records = tracker.get_records("backup")
    assert len(records) == 2


def test_stats_empty(tmp_path):
    tracker = _make(tmp_path)
    s = tracker.stats("backup")
    assert s["count"] == 0
    assert s["mean"] is None


def test_stats_single(tmp_path):
    tracker = _make(tmp_path)
    tracker.record(_rec(latency=10.0))
    s = tracker.stats("backup")
    assert s["count"] == 1
    assert s["mean"] == 10.0
    assert s["min"] == 10.0
    assert s["max"] == 10.0


def test_stats_multiple(tmp_path):
    tracker = _make(tmp_path)
    for lat in [2.0, 4.0, 6.0]:
        tracker.record(_rec(latency=lat))
    s = tracker.stats("backup")
    assert s["count"] == 3
    assert s["mean"] == 4.0
    assert s["median"] == 4.0
    assert s["min"] == 2.0
    assert s["max"] == 6.0


def test_separate_jobs_isolated(tmp_path):
    tracker = _make(tmp_path)
    tracker.record(_rec(job_name="jobA", latency=1.0))
    tracker.record(_rec(job_name="jobB", latency=9.0))
    assert tracker.stats("jobA")["mean"] == 1.0
    assert tracker.stats("jobB")["mean"] == 9.0
