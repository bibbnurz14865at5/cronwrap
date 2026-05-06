"""Tests for cronwrap.job_trend."""
import json
import time
from pathlib import Path

import pytest

from cronwrap.history import HistoryEntry, JobHistory
from cronwrap.job_trend import TrendError, TrendResult, analyse_trend


def _write_history(tmp_path: Path, job: str, entries):
    hist = JobHistory(job, str(tmp_path))
    for e in entries:
        hist.record(e)


def _entry(success: bool, duration: float) -> HistoryEntry:
    return HistoryEntry(success=success, duration=duration)


# ---------------------------------------------------------------------------
# TrendResult
# ---------------------------------------------------------------------------

def test_trend_result_to_dict_keys():
    r = TrendResult("myjob", 10, 95.0, 1.23, "stable", 10)
    d = r.to_dict()
    assert set(d) == {"job_name", "window", "success_rate_pct", "avg_duration_s",
                      "trend_direction", "sample_count"}


def test_trend_result_extra_included_when_set():
    r = TrendResult("j", 5, 80.0, 0.5, "improving", 5, extra={"note": "x"})
    assert "extra" in r.to_dict()


def test_trend_result_extra_omitted_when_empty():
    r = TrendResult("j", 5, 80.0, 0.5, "stable", 5)
    assert "extra" not in r.to_dict()


def test_trend_result_to_json_valid():
    r = TrendResult("j", 5, 100.0, 2.0, "stable", 5)
    parsed = json.loads(r.to_json())
    assert parsed["job_name"] == "j"


# ---------------------------------------------------------------------------
# analyse_trend
# ---------------------------------------------------------------------------

def test_analyse_trend_no_history(tmp_path):
    result = analyse_trend("ghost", str(tmp_path), window=10)
    assert result.sample_count == 0
    assert result.trend_direction == "unknown"
    assert result.success_rate_pct == 0.0


def test_analyse_trend_window_too_small(tmp_path):
    with pytest.raises(TrendError):
        analyse_trend("j", str(tmp_path), window=1)


def test_analyse_trend_all_success(tmp_path):
    entries = [_entry(True, 1.0) for _ in range(10)]
    _write_history(tmp_path, "job1", entries)
    result = analyse_trend("job1", str(tmp_path), window=10)
    assert result.success_rate_pct == 100.0
    assert result.sample_count == 10


def test_analyse_trend_mixed_success(tmp_path):
    entries = [_entry(i % 2 == 0, 1.0) for i in range(10)]
    _write_history(tmp_path, "job2", entries)
    result = analyse_trend("job2", str(tmp_path), window=10)
    assert result.success_rate_pct == pytest.approx(50.0)


def test_analyse_trend_improving_direction(tmp_path):
    # Early runs slow, late runs fast -> improving
    early = [_entry(True, 10.0) for _ in range(5)]
    late = [_entry(True, 1.0) for _ in range(5)]
    _write_history(tmp_path, "job3", early + late)
    result = analyse_trend("job3", str(tmp_path), window=10)
    assert result.trend_direction == "improving"


def test_analyse_trend_degrading_direction(tmp_path):
    # Early runs fast, late runs slow -> degrading
    early = [_entry(True, 1.0) for _ in range(5)]
    late = [_entry(True, 10.0) for _ in range(5)]
    _write_history(tmp_path, "job4", early + late)
    result = analyse_trend("job4", str(tmp_path), window=10)
    assert result.trend_direction == "degrading"


def test_analyse_trend_stable_direction(tmp_path):
    entries = [_entry(True, 2.0) for _ in range(10)]
    _write_history(tmp_path, "job5", entries)
    result = analyse_trend("job5", str(tmp_path), window=10)
    assert result.trend_direction == "stable"


def test_analyse_trend_fewer_entries_than_window(tmp_path):
    entries = [_entry(True, 1.5) for _ in range(4)]
    _write_history(tmp_path, "job6", entries)
    result = analyse_trend("job6", str(tmp_path), window=20)
    assert result.sample_count == 4


def test_analyse_trend_avg_duration_rounded(tmp_path):
    entries = [_entry(True, 1.0 / 3.0) for _ in range(6)]
    _write_history(tmp_path, "job7", entries)
    result = analyse_trend("job7", str(tmp_path), window=6)
    d = result.to_dict()
    # Should be rounded to 3 decimal places
    assert d["avg_duration_s"] == round(result.avg_duration_s, 3)
