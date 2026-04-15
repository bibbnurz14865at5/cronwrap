"""Tests for cronwrap.metrics."""

from __future__ import annotations

import os
import json
import tempfile
from pathlib import Path

import pytest

from cronwrap.history import HistoryEntry, JobHistory
from cronwrap.metrics import JobMetrics, compute_metrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_history(tmp_path: Path, job: str, entries: list[dict]) -> JobHistory:
    hist = JobHistory(str(tmp_path))
    for e in entries:
        entry = HistoryEntry(
            job_name=job,
            exit_code=e.get("exit_code", 0),
            duration=e.get("duration", 1.0),
            timed_out=e.get("timed_out", False),
            stdout=e.get("stdout", ""),
            stderr=e.get("stderr", ""),
        )
        hist.record(entry)
    return hist


# ---------------------------------------------------------------------------
# JobMetrics unit tests
# ---------------------------------------------------------------------------

def test_job_metrics_empty():
    m = JobMetrics(job_name="myjob")
    assert m.total_runs == 0
    assert m.success_rate == 0.0
    assert m.avg_duration is None
    assert m.max_duration is None
    assert m.min_duration is None


def test_job_metrics_to_dict_keys():
    m = JobMetrics(job_name="myjob", total_runs=1, success_count=1, durations=[2.5])
    d = m.to_dict()
    expected_keys = {
        "job_name", "total_runs", "success_count", "failure_count",
        "timeout_count", "success_rate", "avg_duration", "max_duration", "min_duration",
    }
    assert expected_keys == set(d.keys())


# ---------------------------------------------------------------------------
# compute_metrics integration tests
# ---------------------------------------------------------------------------

def test_compute_metrics_all_success(tmp_path):
    hist = _make_history(tmp_path, "job1", [
        {"exit_code": 0, "duration": 1.0},
        {"exit_code": 0, "duration": 3.0},
    ])
    m = compute_metrics("job1", hist)
    assert m.total_runs == 2
    assert m.success_count == 2
    assert m.failure_count == 0
    assert m.success_rate == 1.0
    assert m.avg_duration == pytest.approx(2.0)


def test_compute_metrics_mixed(tmp_path):
    hist = _make_history(tmp_path, "job2", [
        {"exit_code": 0, "duration": 2.0},
        {"exit_code": 1, "duration": 0.5},
        {"exit_code": 0, "duration": 3.0},
    ])
    m = compute_metrics("job2", hist)
    assert m.total_runs == 3
    assert m.success_count == 2
    assert m.failure_count == 1
    assert m.success_rate == pytest.approx(2 / 3)


def test_compute_metrics_timeout(tmp_path):
    hist = _make_history(tmp_path, "job3", [
        {"exit_code": -1, "duration": 60.0, "timed_out": True},
    ])
    m = compute_metrics("job3", hist)
    assert m.timeout_count == 1
    assert m.failure_count == 1
    assert m.success_count == 0


def test_compute_metrics_limit(tmp_path):
    hist = _make_history(tmp_path, "job4", [
        {"exit_code": 1},
        {"exit_code": 1},
        {"exit_code": 0},
        {"exit_code": 0},
    ])
    m = compute_metrics("job4", hist, limit=2)
    assert m.total_runs == 2
    assert m.success_count == 2


def test_compute_metrics_no_history(tmp_path):
    hist = JobHistory(str(tmp_path))
    m = compute_metrics("nonexistent", hist)
    assert m.total_runs == 0
    assert m.avg_duration is None


def test_compute_metrics_duration_stats(tmp_path):
    hist = _make_history(tmp_path, "job5", [
        {"exit_code": 0, "duration": 1.0},
        {"exit_code": 0, "duration": 5.0},
        {"exit_code": 0, "duration": 3.0},
    ])
    m = compute_metrics("job5", hist)
    assert m.min_duration == pytest.approx(1.0)
    assert m.max_duration == pytest.approx(5.0)
    assert m.avg_duration == pytest.approx(3.0)
