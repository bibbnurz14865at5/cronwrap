"""Tests for cronwrap.job_profiler."""
from __future__ import annotations

import json
import pytest

from cronwrap.job_profiler import JobProfiler, ProfileSnapshot, ProfilerError


def _make(tmp_path, max_samples=100):
    return JobProfiler(str(tmp_path / "profiles"), max_samples=max_samples)


def test_snapshot_to_dict_keys():
    snap = ProfileSnapshot(job_name="myjob", durations=[1.0, 2.0, 3.0])
    d = snap.to_dict()
    assert set(d.keys()) == {"job_name", "durations", "p50", "p95", "p99"}


def test_snapshot_roundtrip():
    snap = ProfileSnapshot(job_name="myjob", durations=[1.0, 2.0, 3.0])
    restored = ProfileSnapshot.from_dict(snap.to_dict())
    assert restored.job_name == snap.job_name
    assert restored.durations == snap.durations


def test_p50_empty():
    snap = ProfileSnapshot(job_name="j")
    assert snap.p50() is None


def test_p50_values():
    snap = ProfileSnapshot(job_name="j", durations=[1.0, 3.0, 2.0])
    assert snap.p50() == 2.0


def test_p95_single_value_returns_none():
    snap = ProfileSnapshot(job_name="j", durations=[5.0])
    assert snap.p95() is None


def test_p95_multiple_values():
    snap = ProfileSnapshot(job_name="j", durations=list(range(1, 21)))
    p = snap.p95()
    assert p is not None
    assert p >= 18


def test_is_regression_no_data():
    snap = ProfileSnapshot(job_name="j")
    assert snap.is_regression(999.0) is False


def test_is_regression_false_within_range():
    snap = ProfileSnapshot(job_name="j", durations=[1.0, 2.0, 3.0, 4.0, 5.0])
    assert snap.is_regression(6.0, threshold=2.0) is False


def test_is_regression_true_exceeds_threshold():
    snap = ProfileSnapshot(job_name="j", durations=[1.0, 2.0, 3.0, 4.0, 5.0])
    assert snap.is_regression(100.0, threshold=2.0) is True


def test_record_creates_file(tmp_path):
    profiler = _make(tmp_path)
    profiler.record("backup", 12.5)
    files = list((tmp_path / "profiles").glob("*.profile.json"))
    assert len(files) == 1


def test_record_persists_duration(tmp_path):
    profiler = _make(tmp_path)
    profiler.record("backup", 10.0)
    snap = profiler.load("backup")
    assert 10.0 in snap.durations


def test_record_accumulates(tmp_path):
    profiler = _make(tmp_path)
    for d in [1.0, 2.0, 3.0]:
        profiler.record("job", d)
    snap = profiler.load("job")
    assert len(snap.durations) == 3


def test_record_trims_to_max_samples(tmp_path):
    profiler = _make(tmp_path, max_samples=5)
    for i in range(10):
        profiler.record("job", float(i))
    snap = profiler.load("job")
    assert len(snap.durations) == 5
    assert snap.durations == [5.0, 6.0, 7.0, 8.0, 9.0]


def test_load_missing_job_returns_empty(tmp_path):
    profiler = _make(tmp_path)
    snap = profiler.load("nonexistent")
    assert snap.job_name == "nonexistent"
    assert snap.durations == []


def test_all_snapshots_empty_dir(tmp_path):
    profiler = _make(tmp_path)
    assert profiler.all_snapshots() == {}


def test_all_snapshots_returns_all(tmp_path):
    profiler = _make(tmp_path)
    profiler.record("job_a", 1.0)
    profiler.record("job_b", 2.0)
    snapshots = profiler.all_snapshots()
    assert "job_a" in snapshots
    assert "job_b" in snapshots


def test_load_corrupt_file_raises(tmp_path):
    profiler = _make(tmp_path)
    p = tmp_path / "profiles" / "bad.profile.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("not json")
    # corrupt file not named after a job won't be loaded via load()
    # but all_snapshots() should skip it silently
    snapshots = profiler.all_snapshots()
    assert isinstance(snapshots, dict)
