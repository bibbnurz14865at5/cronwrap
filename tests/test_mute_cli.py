"""Tests for cronwrap.mute_cli."""

from __future__ import annotations

import time

import pytest

from cronwrap.mute_cli import build_parser, main


def _run(args, tmp_path):
    state_dir = str(tmp_path / "mute")
    return main([*args, "--state-dir", state_dir])


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1(tmp_path):
    state_dir = str(tmp_path / "mute")
    assert main(["--state-dir", state_dir]) == 1  # type: ignore[list-item]


def test_mute_command_returns_0(tmp_path):
    assert _run(["mute", "backup", "3600"], tmp_path) == 0


def test_mute_creates_muted_state(tmp_path):
    from cronwrap.job_mute import JobMute
    state_dir = str(tmp_path / "mute")
    main(["mute", "backup", "3600", "--state-dir", state_dir])
    jm = JobMute(state_dir=state_dir)
    assert jm.is_muted("backup") is True


def test_unmute_command_returns_0(tmp_path):
    _run(["mute", "sync", "3600"], tmp_path)
    assert _run(["unmute", "sync"], tmp_path) == 0


def test_status_muted(tmp_path, capsys):
    _run(["mute", "daily", "7200", "--reason", "maintenance"], tmp_path)
    rc = _run(["status", "daily"], tmp_path)
    assert rc == 0
    out = capsys.readouterr().out
    assert "MUTED" in out
    assert "maintenance" in out


def test_status_not_muted(tmp_path, capsys):
    rc = _run(["status", "ghost"], tmp_path)
    assert rc == 0
    out = capsys.readouterr().out
    assert "NOT muted" in out


def test_mute_invalid_duration_returns_2(tmp_path):
    assert _run(["mute", "x", "0"], tmp_path) == 2
