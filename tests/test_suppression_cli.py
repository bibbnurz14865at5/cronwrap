"""Tests for cronwrap.suppression_cli."""
from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta

import pytest

from cronwrap.suppression_cli import build_parser, main
from cronwrap.job_suppression import JobSuppression


def _run(args, tmp_path):
    state_dir = str(tmp_path / "suppression")
    return main(args + ["--state-dir", state_dir])


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1(tmp_path):
    assert _run([], tmp_path) == 1


def test_suppress_command_returns_0(tmp_path):
    assert _run(["suppress", "myjob", "--minutes", "30"], tmp_path) == 0


def test_suppress_creates_state(tmp_path):
    state_dir = str(tmp_path / "suppression")
    main(["suppress", "myjob", "--minutes", "60", "--state-dir", state_dir])
    js = JobSuppression(state_dir=state_dir)
    assert js.is_suppressed("myjob") is True


def test_suppress_with_reason(tmp_path):
    state_dir = str(tmp_path / "suppression")
    main(["suppress", "myjob", "--reason", "deploy", "--state-dir", state_dir])
    js = JobSuppression(state_dir=state_dir)
    state = js.get("myjob")
    assert state is not None
    assert state.reason == "deploy"


def test_resume_command_returns_0(tmp_path):
    state_dir = str(tmp_path / "suppression")
    main(["suppress", "myjob", "--state-dir", state_dir])
    rc = main(["resume", "myjob", "--state-dir", state_dir])
    assert rc == 0


def test_resume_clears_suppression(tmp_path):
    state_dir = str(tmp_path / "suppression")
    main(["suppress", "myjob", "--state-dir", state_dir])
    main(["resume", "myjob", "--state-dir", state_dir])
    js = JobSuppression(state_dir=state_dir)
    assert js.is_suppressed("myjob") is False


def test_check_suppressed_returns_2(tmp_path):
    state_dir = str(tmp_path / "suppression")
    main(["suppress", "myjob", "--state-dir", state_dir])
    rc = main(["check", "myjob", "--state-dir", state_dir])
    assert rc == 2


def test_check_not_suppressed_returns_0(tmp_path):
    rc = _run(["check", "nosuchjob"], tmp_path)
    assert rc == 0


def test_list_command_returns_0(tmp_path):
    assert _run(["list"], tmp_path) == 0
