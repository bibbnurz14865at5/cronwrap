"""Tests for cronwrap.job_sla."""
from __future__ import annotations

import json
import pytest

from cronwrap.job_sla import SLAError, SLAPolicy, SLAResult, check_sla


# ---------------------------------------------------------------------------
# SLAPolicy construction
# ---------------------------------------------------------------------------

def test_from_dict_required_only():
    p = SLAPolicy.from_dict({"job_name": "backup"})
    assert p.job_name == "backup"
    assert p.max_duration_seconds is None
    assert p.must_run_by is None
    assert p.state_dir == "/tmp/cronwrap_sla"


def test_from_dict_full():
    p = SLAPolicy.from_dict({
        "job_name": "report",
        "max_duration_seconds": 120.0,
        "must_run_by": "05:30",
        "state_dir": "/tmp/sla",
    })
    assert p.max_duration_seconds == 120.0
    assert p.must_run_by == "05:30"
    assert p.state_dir == "/tmp/sla"


def test_from_dict_missing_job_name_raises():
    with pytest.raises(SLAError, match="job_name"):
        SLAPolicy.from_dict({"max_duration_seconds": 60})


def test_to_dict_roundtrip():
    original = SLAPolicy(
        job_name="sync",
        max_duration_seconds=60.0,
        must_run_by="04:00",
        state_dir="/tmp/x",
    )
    restored = SLAPolicy.from_dict(original.to_dict())
    assert restored.job_name == original.job_name
    assert restored.max_duration_seconds == original.max_duration_seconds
    assert restored.must_run_by == original.must_run_by
    assert restored.state_dir == original.state_dir


def test_from_json_file(tmp_path):
    cfg = tmp_path / "sla.json"
    cfg.write_text(json.dumps({"job_name": "job1", "max_duration_seconds": 30}))
    p = SLAPolicy.from_json_file(str(cfg))
    assert p.job_name == "job1"
    assert p.max_duration_seconds == 30


def test_from_json_file_not_found():
    with pytest.raises(SLAError, match="not found"):
        SLAPolicy.from_json_file("/nonexistent/sla.json")


# ---------------------------------------------------------------------------
# check_sla logic
# ---------------------------------------------------------------------------

def _policy(**kwargs) -> SLAPolicy:
    return SLAPolicy(job_name="test_job", **kwargs)


def test_check_sla_no_limits_always_ok():
    result = check_sla(_policy(), duration_seconds=9999)
    assert not result.breached
    assert result.reason is None


def test_check_sla_duration_within_limit():
    result = check_sla(_policy(max_duration_seconds=100), duration_seconds=99.9)
    assert not result.breached


def test_check_sla_duration_exceeds_limit():
    result = check_sla(_policy(max_duration_seconds=100), duration_seconds=101)
    assert result.breached
    assert "101" in result.reason or "100" in result.reason


def test_check_sla_deadline_met():
    result = check_sla(_policy(must_run_by="06:00"), duration_seconds=1, run_time="05:59")
    assert not result.breached


def test_check_sla_deadline_missed():
    result = check_sla(_policy(must_run_by="06:00"), duration_seconds=1, run_time="06:01")
    assert result.breached
    assert "06:01" in result.reason


def test_check_sla_deadline_no_run_time_skips_check():
    # must_run_by set but no run_time provided — skip deadline check
    result = check_sla(_policy(must_run_by="01:00"), duration_seconds=1, run_time=None)
    assert not result.breached


def test_check_sla_both_limits_duration_breach():
    result = check_sla(
        _policy(max_duration_seconds=10, must_run_by="23:59"),
        duration_seconds=11,
        run_time="00:01",
    )
    assert result.breached
    assert "duration" in result.reason


def test_sla_result_job_name_preserved():
    p = _policy(max_duration_seconds=5)
    result = check_sla(p, duration_seconds=1)
    assert result.job_name == "test_job"
