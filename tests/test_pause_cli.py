import time
import pytest
from cronwrap.pause_cli import build_parser, main
from cronwrap.job_pause import JobPause


def _run(args, tmp_path):
    return main(["--state-dir", str(tmp_path / "pause")] + args)


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_pause_command_returns_0(tmp_path):
    assert _run(["pause", "myjob"], tmp_path) == 0


def test_pause_creates_paused_state(tmp_path):
    _run(["pause", "myjob"], tmp_path)
    jp = JobPause(str(tmp_path / "pause"))
    assert jp.is_paused("myjob")


def test_resume_command_returns_0(tmp_path):
    _run(["pause", "myjob"], tmp_path)
    assert _run(["resume", "myjob"], tmp_path) == 0


def test_resume_clears_pause(tmp_path):
    _run(["pause", "myjob"], tmp_path)
    _run(["resume", "myjob"], tmp_path)
    jp = JobPause(str(tmp_path / "pause"))
    assert not jp.is_paused("myjob")


def test_check_returns_1_when_paused(tmp_path):
    _run(["pause", "myjob"], tmp_path)
    assert _run(["check", "myjob"], tmp_path) == 1


def test_check_returns_0_when_active(tmp_path):
    assert _run(["check", "myjob"], tmp_path) == 0


def test_list_shows_paused(tmp_path, capsys):
    _run(["pause", "alpha"], tmp_path)
    _run(["list"], tmp_path)
    out = capsys.readouterr().out
    assert "alpha" in out


def test_list_empty(tmp_path, capsys):
    _run(["list"], tmp_path)
    out = capsys.readouterr().out
    assert "No jobs paused" in out


def test_no_command_returns_1(tmp_path):
    assert _run([], tmp_path) == 1
