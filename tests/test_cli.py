"""Tests for cronwrap.cli."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from cronwrap.cli import build_parser, main, _strip_double_dash
from cronwrap.runner import JobResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_result(success=True, summary_text="OK summary"):
    r = MagicMock(spec=JobResult)
    r.success = success
    r.summary.return_value = summary_text
    return r


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def test_build_parser_returns_parser():
    p = build_parser()
    assert p.prog == "cronwrap"


def test_strip_double_dash_removes_separator():
    assert _strip_double_dash(["--", "echo", "hi"]) == ["echo", "hi"]


def test_strip_double_dash_noop_without_separator():
    assert _strip_double_dash(["echo", "hi"]) == ["echo", "hi"]


def test_strip_double_dash_empty_list():
    assert _strip_double_dash([]) == []


# ---------------------------------------------------------------------------
# main() — success path
# ---------------------------------------------------------------------------

def test_main_success_no_notify():
    with patch("cronwrap.cli.run_job", return_value=_fake_result(success=True)) as mock_run, \
         patch("cronwrap.cli.dispatch") as mock_dispatch, \
         patch("cronwrap.cli.from_env", return_value=MagicMock()):
        rc = main(["--", sys.executable, "-c", "pass"])
    assert rc == 0
    mock_dispatch.assert_not_called()


def test_main_success_notify_on_success():
    with patch("cronwrap.cli.run_job", return_value=_fake_result(success=True)), \
         patch("cronwrap.cli.dispatch") as mock_dispatch, \
         patch("cronwrap.cli.from_env", return_value=MagicMock()):
        rc = main(["--notify-on-success", "--", "echo", "hi"])
    assert rc == 0
    mock_dispatch.assert_called_once()


def test_main_failure_dispatches_notification():
    with patch("cronwrap.cli.run_job", return_value=_fake_result(success=False)), \
         patch("cronwrap.cli.dispatch") as mock_dispatch, \
         patch("cronwrap.cli.from_env", return_value=MagicMock()):
        rc = main(["--", "false"])
    assert rc == 1
    mock_dispatch.assert_called_once()


def test_main_dispatch_error_does_not_crash(capsys):
    with patch("cronwrap.cli.run_job", return_value=_fake_result(success=False)), \
         patch("cronwrap.cli.dispatch", side_effect=RuntimeError("boom")), \
         patch("cronwrap.cli.from_env", return_value=MagicMock()):
        rc = main(["--", "false"])
    assert rc == 1
    captured = capsys.readouterr()
    assert "notification error" in captured.err


def test_main_dispatch_error_includes_message(capsys):
    """The stderr output should include the original exception message."""
    with patch("cronwrap.cli.run_job", return_value=_fake_result(success=False)), \
         patch("cronwrap.cli.dispatch", side_effect=RuntimeError("smtp timeout")), \
         patch("cronwrap.cli.from_env", return_value=MagicMock()):
        main(["--", "false"])
    captured = capsys.readouterr()
    assert "smtp timeout" in captured.err


def test_main_loads_config_file():
    with patch("cronwrap.cli.run_job", return_value=_fake_result(success=True)), \
         patch("cronwrap.cli.dispatch"), \
         patch("cronwrap.cli.from_json_file", return_value=MagicMock()) as moc