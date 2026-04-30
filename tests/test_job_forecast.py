"""Tests for cronwrap.job_forecast."""
from __future__ import annotations

import json
import pytest

from cronwrap.history import HistoryEntry, JobHistory
from cronwrap.job_forecast import (
    ForecastError,
    ForecastResult,
    _confidence_level,
    forecast_job,
)


def _write_history(tmp_path, job_name, entries):
    hist = JobHistory(job_name, str(tmp_path))
    for e in entries:
        hist.record(e)


def _entry(success=True, duration=10.0):
    return HistoryEntry(job_name="myjob", success=success, duration=duration)


# --- ForecastResult ---

def test_result_to_dict_keys():
    r = ForecastResult("j", 5, 10.0, 5.0, 15.0, "medium")
    d = r.to_dict()
    assert set(d) == {"job_name", "sample_size", "predicted_duration",
                      "lower_bound", "upper_bound", "confidence"}


def test_result_roundtrip():
    r = ForecastResult("j", 10, 12.5, 8.0, 17.0, "high")
    assert ForecastResult.from_dict(r.to_dict()).predicted_duration == pytest.approx(12.5)


def test_result_to_json_valid():
    r = ForecastResult("j", 3, 7.0, 4.0, 10.0, "low")
    parsed = json.loads(r.to_json())
    assert parsed["job_name"] == "j"


# --- _confidence_level ---

def test_confidence_low():
    assert _confidence_level(1) == "low"
    assert _confidence_level(4) == "low"


def test_confidence_medium():
    assert _confidence_level(5) == "medium"
    assert _confidence_level(19) == "medium"


def test_confidence_high():
    assert _confidence_level(20) == "high"
    assert _confidence_level(100) == "high"


# --- forecast_job ---

def test_forecast_no_history_raises(tmp_path):
    with pytest.raises(ForecastError, match="myjob"):
        forecast_job("myjob", str(tmp_path))


def test_forecast_only_failed_entries_raises(tmp_path):
    _write_history(tmp_path, "myjob", [_entry(success=False, duration=5.0)])
    with pytest.raises(ForecastError):
        forecast_job("myjob", str(tmp_path))


def test_forecast_single_entry(tmp_path):
    _write_history(tmp_path, "myjob", [_entry(duration=20.0)])
    r = forecast_job("myjob", str(tmp_path))
    assert r.predicted_duration == pytest.approx(20.0)
    assert r.sample_size == 1
    assert r.confidence == "low"
    assert r.lower_bound >= 0.0
    assert r.upper_bound > r.predicted_duration


def test_forecast_multiple_entries(tmp_path):
    durations = [10.0, 12.0, 11.0, 9.0, 13.0]
    _write_history(tmp_path, "myjob", [_entry(duration=d) for d in durations])
    r = forecast_job("myjob", str(tmp_path))
    assert r.sample_size == 5
    assert r.predicted_duration == pytest.approx(11.0)
    assert r.lower_bound < r.predicted_duration
    assert r.upper_bound > r.predicted_duration
    assert r.confidence == "medium"


def test_forecast_ignores_failed_entries(tmp_path):
    _write_history(tmp_path, "myjob", [
        _entry(success=True, duration=10.0),
        _entry(success=False, duration=999.0),
        _entry(success=True, duration=10.0),
    ])
    r = forecast_job("myjob", str(tmp_path))
    assert r.sample_size == 2
    assert r.predicted_duration == pytest.approx(10.0)


def test_forecast_lower_bound_never_negative(tmp_path):
    _write_history(tmp_path, "myjob", [
        _entry(duration=0.1),
        _entry(duration=0.1),
        _entry(duration=0.1),
    ])
    r = forecast_job("myjob", str(tmp_path))
    assert r.lower_bound >= 0.0
