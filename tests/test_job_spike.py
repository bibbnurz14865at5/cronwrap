"""Tests for cronwrap.job_spike."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwrap.history import JobHistory, HistoryEntry
from cronwrap.job_spike import SpikeError, SpikeResult, detect_spike


def _write_history(tmp_path: Path, job: str, durations, success=True):
    h = JobHistory(job, str(tmp_path))
    for d in durations:
        e = HistoryEntry(
            job_name=job,
            success=success,
            exit_code=0 if success else 1,
            duration=d,
        )
        h.record(e)


# ---------------------------------------------------------------------------
# SpikeResult
# ---------------------------------------------------------------------------

def test_result_to_dict_keys():
    r = SpikeResult("backup", 10.0, 5.0, 2.0, True)
    d = r.to_dict()
    assert set(d.keys()) == {"job_name", "duration", "baseline_avg",
                             "threshold_multiplier", "is_spike"}


def test_result_extra_included_when_set():
    r = SpikeResult("backup", 10.0, 5.0, 2.0, True, extra={"env": "prod"})
    assert r.to_dict()["extra"] == {"env": "prod"}


def test_result_extra_omitted_when_empty():
    r = SpikeResult("backup", 10.0, 5.0, 2.0, False)
    assert "extra" not in r.to_dict()


def test_result_roundtrip():
    r = SpikeResult("job", 12.5, 6.0, 3.0, True, extra={"k": "v"})
    assert SpikeResult.from_dict(r.to_dict()).job_name == "job"
    assert SpikeResult.from_dict(r.to_dict()).is_spike is True


def test_result_to_json_valid():
    r = SpikeResult("job", 1.0, 1.0, 2.0, False)
    parsed = json.loads(r.to_json())
    assert parsed["job_name"] == "job"


# ---------------------------------------------------------------------------
# detect_spike
# ---------------------------------------------------------------------------

def test_detect_spike_insufficient_samples_never_spike(tmp_path):
    _write_history(tmp_path, "j", [1.0, 2.0])  # only 2 samples, min=3
    result = detect_spike("j", 999.0, str(tmp_path))
    assert result.is_spike is False


def test_detect_spike_not_a_spike(tmp_path):
    _write_history(tmp_path, "j", [10.0, 10.0, 10.0])
    result = detect_spike("j", 15.0, str(tmp_path), threshold_multiplier=2.0)
    assert result.is_spike is False
    assert result.baseline_avg == pytest.approx(10.0)


def test_detect_spike_is_spike(tmp_path):
    _write_history(tmp_path, "j", [10.0, 10.0, 10.0])
    result = detect_spike("j", 25.0, str(tmp_path), threshold_multiplier=2.0)
    assert result.is_spike is True


def test_detect_spike_ignores_failed_entries(tmp_path):
    _write_history(tmp_path, "j", [1.0, 1.0, 1.0], success=False)
    # All entries are failures — fewer than min_samples successes
    result = detect_spike("j", 999.0, str(tmp_path))
    assert result.is_spike is False


def test_detect_spike_no_history_not_spike(tmp_path):
    result = detect_spike("unknown", 50.0, str(tmp_path))
    assert result.is_spike is False


def test_detect_spike_invalid_multiplier(tmp_path):
    with pytest.raises(SpikeError):
        detect_spike("j", 1.0, str(tmp_path), threshold_multiplier=0)


def test_detect_spike_invalid_min_samples(tmp_path):
    with pytest.raises(SpikeError):
        detect_spike("j", 1.0, str(tmp_path), min_samples=0)


def test_detect_spike_extra_forwarded(tmp_path):
    _write_history(tmp_path, "j", [5.0, 5.0, 5.0])
    result = detect_spike("j", 50.0, str(tmp_path), extra={"host": "srv1"})
    assert result.extra == {"host": "srv1"}
