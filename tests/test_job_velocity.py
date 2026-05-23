"""Tests for cronwrap.job_velocity."""
import json
import time
from pathlib import Path

import pytest

from cronwrap.job_velocity import (
    VelocityError,
    VelocityResult,
    compute_velocity,
)


def _write_history(tmp_path: Path, job_name: str, entries: list) -> None:
    (tmp_path / f"{job_name}.json").write_text(json.dumps(entries))


def _entry(success: bool, offset_seconds: int = 0) -> dict:
    """Return a history entry whose timestamp is *offset_seconds* ago."""
    return {
        "timestamp": time.time() - offset_seconds,
        "success": success,
    }


# ---------------------------------------------------------------------------
# VelocityResult unit tests
# ---------------------------------------------------------------------------

def test_result_to_dict_keys():
    r = VelocityResult(
        job_name="myjob",
        window_seconds=3600,
        run_count=10,
        success_count=8,
        failure_count=2,
        runs_per_minute=0.1667,
    )
    d = r.to_dict()
    for key in ("job_name", "window_seconds", "run_count",
                "success_count", "failure_count", "runs_per_minute"):
        assert key in d


def test_result_extra_omitted_when_empty():
    r = VelocityResult("j", 60, 1, 1, 0, 1.0)
    assert "extra" not in r.to_dict()


def test_result_extra_included_when_set():
    r = VelocityResult("j", 60, 1, 1, 0, 1.0, extra={"env": "prod"})
    assert r.to_dict()["extra"] == {"env": "prod"}


def test_result_roundtrip():
    r = VelocityResult("j", 120, 5, 4, 1, 2.5, extra={"k": "v"})
    assert VelocityResult.from_dict(r.to_dict()).run_count == 5


def test_result_to_json_valid():
    r = VelocityResult("j", 60, 3, 3, 0, 3.0)
    data = json.loads(r.to_json())
    assert data["job_name"] == "j"


# ---------------------------------------------------------------------------
# compute_velocity tests
# ---------------------------------------------------------------------------

def test_compute_velocity_no_history(tmp_path):
    result = compute_velocity("missing", str(tmp_path), window_seconds=3600)
    assert result.run_count == 0
    assert result.runs_per_minute == 0.0


def test_compute_velocity_all_recent(tmp_path):
    entries = [_entry(True, 10), _entry(True, 20), _entry(False, 30)]
    _write_history(tmp_path, "myjob", entries)
    result = compute_velocity("myjob", str(tmp_path), window_seconds=3600)
    assert result.run_count == 3
    assert result.success_count == 2
    assert result.failure_count == 1


def test_compute_velocity_filters_old_entries(tmp_path):
    entries = [_entry(True, 10), _entry(True, 7200)]  # second is 2 h ago
    _write_history(tmp_path, "myjob", entries)
    result = compute_velocity("myjob", str(tmp_path), window_seconds=3600)
    assert result.run_count == 1


def test_compute_velocity_runs_per_minute(tmp_path):
    # 60 runs in a 3600-second window => 1 run/min
    entries = [_entry(True, i * 60) for i in range(60)]
    _write_history(tmp_path, "myjob", entries)
    result = compute_velocity("myjob", str(tmp_path), window_seconds=3600)
    assert abs(result.runs_per_minute - 1.0) < 0.01


def test_compute_velocity_invalid_window_raises(tmp_path):
    with pytest.raises(VelocityError):
        compute_velocity("j", str(tmp_path), window_seconds=0)


def test_compute_velocity_extra_propagated(tmp_path):
    result = compute_velocity("j", str(tmp_path), extra={"env": "staging"})
    assert result.extra == {"env": "staging"}
