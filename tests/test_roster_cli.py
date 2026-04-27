"""Tests for cronwrap.roster_cli."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwrap.roster_cli import build_parser, main


def _run(tmp_path, *args):
    roster = str(tmp_path / "roster.json")
    history = str(tmp_path / "history")
    argv = ["--roster", roster, "--history-dir", history, *args]
    return main(argv)


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1(tmp_path):
    assert _run(tmp_path) == 1


def test_register_returns_0(tmp_path):
    rc = _run(tmp_path, "register", "backup", "--interval", "3600")
    assert rc == 0


def test_register_persists_entry(tmp_path):
    _run(tmp_path, "register", "backup", "--interval", "3600")
    roster_path = tmp_path / "roster.json"
    data = json.loads(roster_path.read_text())
    assert data[0]["job_name"] == "backup"
    assert data[0]["expected_interval_seconds"] == 3600


def test_register_with_description(tmp_path):
    _run(tmp_path, "register", "sync", "--interval", "60", "--description", "nightly sync")
    data = json.loads((tmp_path / "roster.json").read_text())
    assert data[0]["description"] == "nightly sync"


def test_unregister_returns_0(tmp_path):
    _run(tmp_path, "register", "backup", "--interval", "3600")
    rc = _run(tmp_path, "unregister", "backup")
    assert rc == 0


def test_unregister_unknown_returns_2(tmp_path):
    rc = _run(tmp_path, "unregister", "ghost")
    assert rc == 2


def test_list_empty(tmp_path, capsys):
    rc = _run(tmp_path, "list")
    assert rc == 0
    out = capsys.readouterr().out
    assert "No jobs registered" in out


def test_list_shows_registered_jobs(tmp_path, capsys):
    _run(tmp_path, "register", "backup", "--interval", "3600")
    rc = _run(tmp_path, "list")
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed[0]["job_name"] == "backup"


def test_check_all_on_schedule(tmp_path, capsys):
    # No jobs registered → nothing missing
    rc = _run(tmp_path, "check")
    assert rc == 0
    assert "on schedule" in capsys.readouterr().out


def test_check_returns_3_when_overdue(tmp_path):
    _run(tmp_path, "register", "backup", "--interval", "1")
    # No history → immediately overdue
    rc = _run(tmp_path, "check")
    assert rc == 3
