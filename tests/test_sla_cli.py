"""Tests for cronwrap.sla_cli."""
from __future__ import annotations

import json
import pytest

from cronwrap.sla_cli import build_parser, main


def _run(argv):
    return main(argv)


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1():
    assert _run([]) == 1


def test_show_command(tmp_path):
    cfg = tmp_path / "sla.json"
    cfg.write_text(json.dumps({"job_name": "myjob", "max_duration_seconds": 60}))
    rc = _run(["show", str(cfg)])
    assert rc == 0


def test_show_missing_file_returns_2(tmp_path):
    rc = _run(["show", str(tmp_path / "missing.json")])
    assert rc == 2


def test_check_within_limits(tmp_path):
    cfg = tmp_path / "sla.json"
    cfg.write_text(json.dumps({"job_name": "j", "max_duration_seconds": 100}))
    rc = _run(["check", str(cfg), "--duration", "50"])
    assert rc == 0


def test_check_duration_breach(tmp_path):
    cfg = tmp_path / "sla.json"
    cfg.write_text(json.dumps({"job_name": "j", "max_duration_seconds": 10}))
    rc = _run(["check", str(cfg), "--duration", "20"])
    assert rc == 1


def test_check_deadline_breach(tmp_path, capsys):
    cfg = tmp_path / "sla.json"
    cfg.write_text(json.dumps({"job_name": "j", "must_run_by": "03:00"}))
    rc = _run(["check", str(cfg), "--duration", "1", "--run-time", "04:00"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "BREACHED" in out


def test_check_deadline_ok(tmp_path, capsys):
    cfg = tmp_path / "sla.json"
    cfg.write_text(json.dumps({"job_name": "j", "must_run_by": "06:00"}))
    rc = _run(["check", str(cfg), "--duration", "1", "--run-time", "05:00"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out
