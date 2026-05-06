"""Tests for cronwrap.job_drain and cronwrap.drain_cli."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.job_drain import DrainError, DrainState, JobDrain
from cronwrap.drain_cli import build_parser, main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make(tmp_path: Path) -> JobDrain:
    return JobDrain(state_dir=str(tmp_path / "drain"))


# ---------------------------------------------------------------------------
# DrainState unit tests
# ---------------------------------------------------------------------------

def test_drain_state_to_dict_required_keys():
    s = DrainState(job_name="myjob", drained_at="2024-01-01T00:00:00+00:00")
    d = s.to_dict()
    assert d["job_name"] == "myjob"
    assert "drained_at" in d
    assert "reason" not in d


def test_drain_state_to_dict_includes_reason():
    s = DrainState(job_name="j", drained_at="ts", reason="maintenance")
    assert s.to_dict()["reason"] == "maintenance"


def test_drain_state_roundtrip():
    s = DrainState(job_name="j", drained_at="ts", reason="x")
    assert DrainState.from_dict(s.to_dict()).reason == "x"


def test_drain_state_is_active():
    s = DrainState(job_name="j", drained_at="ts")
    assert s.is_active() is True


# ---------------------------------------------------------------------------
# JobDrain tests
# ---------------------------------------------------------------------------

def test_drain_creates_file(tmp_path):
    jd = _make(tmp_path)
    jd.drain("backup")
    assert (tmp_path / "drain" / "backup.drain.json").exists()


def test_drain_persists_reason(tmp_path):
    jd = _make(tmp_path)
    jd.drain("backup", reason="deploy")
    state = jd.get("backup")
    assert state is not None
    assert state.reason == "deploy"


def test_is_draining_true_after_drain(tmp_path):
    jd = _make(tmp_path)
    jd.drain("myjob")
    assert jd.is_draining("myjob") is True


def test_is_draining_false_before_drain(tmp_path):
    jd = _make(tmp_path)
    assert jd.is_draining("myjob") is False


def test_undrain_removes_file(tmp_path):
    jd = _make(tmp_path)
    jd.drain("myjob")
    jd.undrain("myjob")
    assert not jd.is_draining("myjob")


def test_undrain_noop_when_not_draining(tmp_path):
    jd = _make(tmp_path)
    jd.undrain("nonexistent")  # should not raise


def test_get_returns_none_when_not_draining(tmp_path):
    jd = _make(tmp_path)
    assert jd.get("missing") is None


def test_list_draining_empty(tmp_path):
    jd = _make(tmp_path)
    assert jd.list_draining() == []


def test_list_draining_multiple(tmp_path):
    jd = _make(tmp_path)
    jd.drain("beta")
    jd.drain("alpha")
    assert jd.list_draining() == ["alpha", "beta"]


def test_drain_empty_name_raises(tmp_path):
    jd = _make(tmp_path)
    with pytest.raises(DrainError):
        jd.drain("")


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

def _run(tmp_path, *args):
    sd = str(tmp_path / "drain")
    return main(["--state-dir", sd, *args])


def test_build_parser_returns_parser():
    assert build_parser() is not None


def test_no_command_returns_1(tmp_path):
    assert _run(tmp_path) == 1


def test_drain_command_returns_0(tmp_path):
    assert _run(tmp_path, "drain", "myjob") == 0


def test_undrain_command_returns_0(tmp_path):
    _run(tmp_path, "drain", "myjob")
    assert _run(tmp_path, "undrain", "myjob") == 0


def test_status_not_draining(tmp_path, capsys):
    _run(tmp_path, "status", "myjob")
    out = capsys.readouterr().out
    assert "NOT draining" in out


def test_status_draining(tmp_path, capsys):
    _run(tmp_path, "drain", "myjob", "--reason", "maintenance")
    _run(tmp_path, "status", "myjob")
    out = capsys.readouterr().out
    assert "DRAINING" in out


def test_list_command_empty(tmp_path, capsys):
    _run(tmp_path, "list")
    out = capsys.readouterr().out
    assert "No jobs" in out


def test_list_command_shows_jobs(tmp_path, capsys):
    _run(tmp_path, "drain", "job_a")
    _run(tmp_path, "drain", "job_b")
    _run(tmp_path, "list")
    out = capsys.readouterr().out
    assert "job_a" in out
    assert "job_b" in out
