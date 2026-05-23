"""Tests for cronwrap.job_grace_period and grace_period_cli."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

import pytest

from cronwrap.job_grace_period import GracePeriodError, GracePeriodPolicy
from cronwrap.grace_period_cli import build_parser, main


def _make(tmp_path, duration=300, **kw):
    return GracePeriodPolicy(
        job_name="myjob",
        duration_seconds=duration,
        state_dir=str(tmp_path),
        **kw,
    )


# --- GracePeriodPolicy unit tests ---

def test_from_dict_required_only():
    p = GracePeriodPolicy.from_dict({"job_name": "j", "duration_seconds": 60})
    assert p.job_name == "j"
    assert p.duration_seconds == 60
    assert p.reason is None


def test_from_dict_custom():
    p = GracePeriodPolicy.from_dict({
        "job_name": "j", "duration_seconds": 120,
        "state_dir": "/tmp/x", "reason": "deploy",
    })
    assert p.state_dir == "/tmp/x"
    assert p.reason == "deploy"


def test_from_dict_missing_job_name_raises():
    with pytest.raises(GracePeriodError, match="job_name"):
        GracePeriodPolicy.from_dict({"duration_seconds": 60})


def test_from_dict_missing_duration_raises():
    with pytest.raises(GracePeriodError, match="duration_seconds"):
        GracePeriodPolicy.from_dict({"job_name": "j"})


def test_from_dict_zero_duration_raises():
    with pytest.raises(GracePeriodError, match="positive"):
        GracePeriodPolicy.from_dict({"job_name": "j", "duration_seconds": 0})


def test_to_dict_roundtrip():
    p = GracePeriodPolicy.from_dict({"job_name": "j", "duration_seconds": 60, "reason": "r"})
    d = p.to_dict()
    assert d["job_name"] == "j"
    assert d["duration_seconds"] == 60
    assert d["reason"] == "r"


def test_to_dict_omits_reason_when_none():
    p = GracePeriodPolicy.from_dict({"job_name": "j", "duration_seconds": 60})
    assert "reason" not in p.to_dict()


def test_activate_creates_state_file(tmp_path):
    p = _make(tmp_path)
    p.activate()
    assert (tmp_path / "myjob.grace.json").exists()


def test_is_active_true_within_window(tmp_path):
    p = _make(tmp_path, duration=300)
    now = datetime.now(timezone.utc)
    p.activate(now=now)
    assert p.is_active(now=now + timedelta(seconds=100)) is True


def test_is_active_false_after_window(tmp_path):
    p = _make(tmp_path, duration=60)
    now = datetime.now(timezone.utc)
    p.activate(now=now)
    assert p.is_active(now=now + timedelta(seconds=120)) is False


def test_is_active_false_when_no_state(tmp_path):
    p = _make(tmp_path)
    assert p.is_active() is False


def test_deactivate_removes_state_file(tmp_path):
    p = _make(tmp_path)
    p.activate()
    p.deactivate()
    assert not (tmp_path / "myjob.grace.json").exists()


def test_deactivate_noop_when_no_state(tmp_path):
    p = _make(tmp_path)
    p.deactivate()  # should not raise


# --- CLI tests ---

def _run(args):
    return main(args)


def test_build_parser_returns_parser():
    assert build_parser() is not None


def test_no_command_returns_1():
    assert _run([]) == 1


def test_activate_command_returns_0(tmp_path):
    rc = _run(["activate", "--job", "j", "--duration", "120", "--state-dir", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "j.grace.json").exists()


def test_check_command_text_active(tmp_path, capsys):
    p = GracePeriodPolicy(job_name="j", duration_seconds=300, state_dir=str(tmp_path))
    p.activate()
    _run(["check", "--job", "j", "--state-dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert "ACTIVE" in out


def test_check_command_json_inactive(tmp_path, capsys):
    _run(["check", "--job", "j", "--state-dir", str(tmp_path), "--format", "json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["grace_active"] is False


def test_deactivate_command_returns_0(tmp_path):
    p = GracePeriodPolicy(job_name="j", duration_seconds=60, state_dir=str(tmp_path))
    p.activate()
    rc = _run(["deactivate", "--job", "j", "--state-dir", str(tmp_path)])
    assert rc == 0
    assert not (tmp_path / "j.grace.json").exists()
