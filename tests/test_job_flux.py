"""Tests for cronwrap.job_flux."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwrap.history import HistoryEntry, JobHistory
from cronwrap.job_flux import FluxError, FluxResult, analyse_flux


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_history(tmp_path: Path, job: str, entries: list[dict]) -> Path:
    hist_file = tmp_path / f"{job}.json"
    jh = JobHistory(hist_file)
    for e in entries:
        jh.record(HistoryEntry(**e))
    return tmp_path


def _entry(success: bool = True, duration: float = 1.0) -> dict:
    return {
        "job_name": "myjob",
        "success": success,
        "duration": duration,
        "timestamp": time.time(),
        "exit_code": 0 if success else 1,
    }


# ---------------------------------------------------------------------------
# FluxResult unit tests
# ---------------------------------------------------------------------------

def test_flux_result_to_dict_keys():
    r = FluxResult(
        job_name="j", sample_count=5, mean=2.0, stddev=0.5,
        cv=0.25, is_volatile=False, threshold=0.5,
    )
    d = r.to_dict()
    for key in ("job_name", "sample_count", "mean", "stddev", "cv", "is_volatile", "threshold"):
        assert key in d


def test_flux_result_extra_omitted_when_empty():
    r = FluxResult(job_name="j", sample_count=3, mean=1.0, stddev=0.1,
                   cv=0.1, is_volatile=False, threshold=0.5)
    assert "extra" not in r.to_dict()


def test_flux_result_extra_included_when_set():
    r = FluxResult(job_name="j", sample_count=3, mean=1.0, stddev=0.1,
                   cv=0.1, is_volatile=False, threshold=0.5, extra={"note": "x"})
    assert r.to_dict()["extra"] == {"note": "x"}


def test_flux_result_roundtrip():
    r = FluxResult(job_name="j", sample_count=4, mean=3.0, stddev=1.5,
                   cv=0.5, is_volatile=True, threshold=0.5)
    assert FluxResult.from_dict(r.to_dict()).cv == r.cv


def test_flux_result_to_json_valid():
    r = FluxResult(job_name="j", sample_count=3, mean=1.0, stddev=0.2,
                   cv=0.2, is_volatile=False, threshold=0.5)
    parsed = json.loads(r.to_json())
    assert parsed["job_name"] == "j"


# ---------------------------------------------------------------------------
# analyse_flux integration tests
# ---------------------------------------------------------------------------

def test_analyse_flux_no_history_raises(tmp_path):
    with pytest.raises(FluxError, match="No history file"):
        analyse_flux("ghost", str(tmp_path))


def test_analyse_flux_too_few_samples_raises(tmp_path):
    _write_history(tmp_path, "myjob", [_entry(duration=1.0), _entry(duration=2.0)])
    with pytest.raises(FluxError, match="at least"):
        analyse_flux("myjob", str(tmp_path), min_samples=3)


def test_analyse_flux_stable_not_volatile(tmp_path):
    entries = [_entry(duration=d) for d in (1.0, 1.05, 0.98, 1.02, 1.01)]
    _write_history(tmp_path, "myjob", entries)
    result = analyse_flux("myjob", str(tmp_path), threshold=0.5)
    assert not result.is_volatile
    assert result.sample_count == 5


def test_analyse_flux_volatile_when_high_cv(tmp_path):
    entries = [_entry(duration=d) for d in (1.0, 5.0, 0.5, 8.0, 2.0)]
    _write_history(tmp_path, "myjob", entries)
    result = analyse_flux("myjob", str(tmp_path), threshold=0.3)
    assert result.is_volatile


def test_analyse_flux_skips_failed_runs(tmp_path):
    entries = [
        _entry(success=False, duration=100.0),
        _entry(duration=1.0),
        _entry(duration=1.1),
        _entry(duration=0.9),
    ]
    _write_history(tmp_path, "myjob", entries)
    result = analyse_flux("myjob", str(tmp_path), min_samples=3)
    assert result.sample_count == 3
    assert result.mean < 5.0
