"""Tests for cronwrap.job_snapshot."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.history import JobHistory
from cronwrap.job_snapshot import (
    JobSnapshot,
    SnapshotReport,
    build_snapshot,
    save_snapshot,
)


def _write_history(tmp_path: Path, job_name: str, entries: list[dict]) -> None:
    history = JobHistory(str(tmp_path), job_name)
    for e in entries:
        history.record(
            status=e.get("status", "success"),
            duration=e.get("duration", 1.0),
            message=e.get("message"),
        )


# ---------------------------------------------------------------------------
# JobSnapshot
# ---------------------------------------------------------------------------

def test_job_snapshot_to_dict_keys():
    snap = JobSnapshot(
        job_name="backup",
        last_run="2024-01-01T00:00:00+00:00",
        last_status="success",
        success_rate=1.0,
        avg_duration=5.0,
        total_runs=10,
    )
    d = snap.to_dict()
    assert set(d.keys()) == {
        "job_name", "last_run", "last_status",
        "success_rate", "avg_duration", "total_runs",
    }


def test_job_snapshot_extra_included_when_set():
    snap = JobSnapshot(
        job_name="x", last_run=None, last_status=None,
        success_rate=0.0, avg_duration=0.0, total_runs=0,
        extra={"env": "prod"},
    )
    assert snap.to_dict()["extra"] == {"env": "prod"}


def test_job_snapshot_extra_omitted_when_empty():
    snap = JobSnapshot(
        job_name="x", last_run=None, last_status=None,
        success_rate=0.0, avg_duration=0.0, total_runs=0,
    )
    assert "extra" not in snap.to_dict()


# ---------------------------------------------------------------------------
# SnapshotReport
# ---------------------------------------------------------------------------

def test_snapshot_report_to_dict_keys():
    report = SnapshotReport(generated_at="2024-01-01T00:00:00+00:00")
    d = report.to_dict()
    assert "generated_at" in d
    assert "jobs" in d
    assert d["jobs"] == []


def test_snapshot_report_to_json_valid():
    report = SnapshotReport(generated_at="2024-01-01T00:00:00+00:00")
    parsed = json.loads(report.to_json())
    assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# build_snapshot
# ---------------------------------------------------------------------------

def test_build_snapshot_empty_dir(tmp_path):
    report = build_snapshot(str(tmp_path))
    assert report.jobs == []


def test_build_snapshot_nonexistent_dir(tmp_path):
    report = build_snapshot(str(tmp_path / "no_such_dir"))
    assert report.jobs == []


def test_build_snapshot_single_job(tmp_path):
    _write_history(tmp_path, "backup", [
        {"status": "success", "duration": 10.0},
        {"status": "success", "duration": 20.0},
    ])
    report = build_snapshot(str(tmp_path))
    assert len(report.jobs) == 1
    snap = report.jobs[0]
    assert snap.job_name == "backup"
    assert snap.total_runs == 2
    assert snap.last_status == "success"
    assert snap.success_rate == 1.0
    assert snap.avg_duration == pytest.approx(15.0, rel=1e-3)


def test_build_snapshot_multiple_jobs(tmp_path):
    _write_history(tmp_path, "alpha", [{"status": "success", "duration": 1.0}])
    _write_history(tmp_path, "beta", [{"status": "failure", "duration": 2.0}])
    report = build_snapshot(str(tmp_path))
    names = {s.job_name for s in report.jobs}
    assert names == {"alpha", "beta"}


def test_build_snapshot_generated_at_is_set(tmp_path):
    report = build_snapshot(str(tmp_path))
    assert report.generated_at  # non-empty string


# ---------------------------------------------------------------------------
# save_snapshot
# ---------------------------------------------------------------------------

def test_save_snapshot_creates_file(tmp_path):
    report = build_snapshot(str(tmp_path))
    out = tmp_path / "out" / "snapshot.json"
    save_snapshot(report, str(out))
    assert out.exists()
    data = json.loads(out.read_text())
    assert "generated_at" in data


def test_save_snapshot_creates_parent_dirs(tmp_path):
    report = SnapshotReport(generated_at="2024-01-01T00:00:00+00:00")
    out = tmp_path / "a" / "b" / "c" / "snap.json"
    save_snapshot(report, str(out))
    assert out.exists()
