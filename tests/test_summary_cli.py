"""Tests for cronwrap.summary_cli."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.summary_cli import build_parser, main
from cronwrap.history import JobHistory, HistoryEntry


def _write_history(tmp_path: Path, job_name: str, n_ok: int = 2):
    h = JobHistory(job_name, history_dir=str(tmp_path))
    for _ in range(n_ok):
        h.record(HistoryEntry(exit_code=0, duration=1.0, timed_out=False))


def _run(args, capsys=None):
    return main(args)


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1():
    assert _run([]) == 1


def test_show_empty_dir_returns_0(tmp_path):
    rc = main(["show", "--history-dir", str(tmp_path)])
    assert rc == 0


def test_show_nonexistent_dir_returns_0(tmp_path):
    rc = main(["show", "--history-dir", str(tmp_path / "missing")])
    assert rc == 0


def test_show_table_output(tmp_path, capsys):
    _write_history(tmp_path, "backup")
    main(["show", "--history-dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert "backup" in out
    assert "JOB" in out


def test_show_json_output(tmp_path, capsys):
    _write_history(tmp_path, "backup")
    rc = main(["show", "--history-dir", str(tmp_path), "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert data[0]["job_name"] == "backup"


def test_show_empty_dir_table_message(tmp_path, capsys):
    main(["show", "--history-dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert "no jobs found" in out
