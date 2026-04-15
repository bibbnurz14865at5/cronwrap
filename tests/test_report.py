"""Tests for cronwrap.report."""
from __future__ import annotations

import json
import os
import pathlib
import time

import pytest

from cronwrap.report import _pct, summarise_job, summarise_all, tail


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_entry(history_dir: str, job: str, success: bool, duration: float) -> None:
    path = pathlib.Path(history_dir) / f"{job}.jsonl"
    entry = {
        "job_name": job,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "success": success,
        "exit_code": 0 if success else 1,
        "duration_s": duration,
        "output": "",
    }
    with open(path, "a") as fh:
        fh.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# _pct
# ---------------------------------------------------------------------------

def test_pct_normal():
    assert _pct(1, 4) == "25.0%"


def test_pct_zero_denominator():
    assert _pct(0, 0) == "n/a"


def test_pct_full():
    assert _pct(3, 3) == "100.0%"


# ---------------------------------------------------------------------------
# summarise_job
# ---------------------------------------------------------------------------

def test_summarise_job_no_history(tmp_path):
    result = summarise_job("missing", str(tmp_path))
    assert result["runs"] == 0
    assert result["success_rate"] == "n/a"
    assert result["last_status"] is None


def test_summarise_job_all_success(tmp_path):
    for _ in range(5):
        _write_entry(str(tmp_path), "backup", success=True, duration=1.0)
    result = summarise_job("backup", str(tmp_path))
    assert result["runs"] == 5
    assert result["success_rate"] == "100.0%"
    assert result["last_status"] == "ok"
    assert result["avg_duration_s"] == 1.0


def test_summarise_job_mixed(tmp_path):
    _write_entry(str(tmp_path), "sync", success=True, duration=2.0)
    _write_entry(str(tmp_path), "sync", success=False, duration=3.0)
    result = summarise_job("sync", str(tmp_path))
    assert result["runs"] == 2
    assert result["success_rate"] == "50.0%"
    assert result["last_status"] == "fail"
    assert result["avg_duration_s"] == 2.5


# ---------------------------------------------------------------------------
# summarise_all
# ---------------------------------------------------------------------------

def test_summarise_all_empty_dir(tmp_path):
    assert summarise_all(str(tmp_path)) == []


def test_summarise_all_missing_dir():
    assert summarise_all("/nonexistent/path/xyz") == []


def test_summarise_all_multiple_jobs(tmp_path):
    for job in ("alpha", "beta"):
        _write_entry(str(tmp_path), job, success=True, duration=1.0)
    results = summarise_all(str(tmp_path))
    names = [r["job"] for r in results]
    assert "alpha" in names
    assert "beta" in names


# ---------------------------------------------------------------------------
# tail
# ---------------------------------------------------------------------------

def test_tail_returns_last_n(tmp_path):
    for i in range(15):
        _write_entry(str(tmp_path), "job", success=True, duration=float(i))
    entries = tail("job", str(tmp_path), n=5)
    assert len(entries) == 5
    assert entries[-1].duration_s == 14.0


def test_tail_empty(tmp_path):
    assert tail("nojob", str(tmp_path)) == []
