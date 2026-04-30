"""Tests for cronwrap.forecast_cli."""
from __future__ import annotations

import json

import pytest

from cronwrap.forecast_cli import build_parser, main
from cronwrap.history import HistoryEntry, JobHistory


def _write_history(tmp_path, job_name, durations):
    hist = JobHistory(job_name, str(tmp_path))
    for d in durations:
        hist.record(HistoryEntry(job_name=job_name, success=True, duration=d))


def _run(argv):
    return main(argv)


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1():
    assert _run([]) == 1


def test_show_missing_history_returns_2(tmp_path):
    rc = _run(["show", "ghost", "--history-dir", str(tmp_path)])
    assert rc == 2


def test_show_returns_0(tmp_path):
    _write_history(tmp_path, "myjob", [10.0, 12.0, 11.0])
    rc = _run(["show", "myjob", "--history-dir", str(tmp_path)])
    assert rc == 0


def test_show_json_output(tmp_path, capsys):
    _write_history(tmp_path, "myjob", [10.0, 12.0])
    rc = _run(["show", "myjob", "--history-dir", str(tmp_path), "--json"])
    assert rc == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["job_name"] == "myjob"
    assert "predicted_duration" in parsed
    assert "confidence" in parsed


def test_show_text_output(tmp_path, capsys):
    _write_history(tmp_path, "myjob", [5.0, 6.0, 7.0])
    rc = _run(["show", "myjob", "--history-dir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Predicted" in out
    assert "Confidence" in out


def test_show_custom_multiplier(tmp_path):
    _write_history(tmp_path, "myjob", [10.0, 10.0, 10.0])
    rc = _run(["show", "myjob", "--history-dir", str(tmp_path), "--multiplier", "3.0"])
    assert rc == 0
