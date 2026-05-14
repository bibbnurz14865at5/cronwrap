"""Tests for cronwrap.capacity_cli."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from cronwrap.capacity_cli import build_parser, main


def _run(args, tmp_path=None):
    return main(args)


def test_build_parser_returns_parser():
    parser = build_parser()
    assert parser is not None


def test_no_command_returns_1(tmp_path):
    assert main([]) == 1


def test_show_command_text(tmp_path):
    rc = main(["show", "myjob", "--max-slots", "2", "--state-dir", str(tmp_path)])
    assert rc == 0


def test_show_command_json_format(tmp_path, capsys):
    rc = main(["show", "myjob", "--max-slots", "2", "--state-dir", str(tmp_path), "--format", "json"])
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["job_name"] == "myjob"
    assert data["max_slots"] == 2
    assert data["used"] == 0
    assert data["available"] == 2


def test_show_reflects_acquired_slot(tmp_path, capsys):
    from cronwrap.job_capacity import CapacityPolicy
    p = CapacityPolicy(job_name="myjob", max_slots=3, state_dir=str(tmp_path))
    p.acquire()
    rc = main(["show", "myjob", "--max-slots", "3", "--state-dir", str(tmp_path), "--format", "json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["used"] == 1
    assert data["available"] == 2


def test_release_command_returns_0(tmp_path):
    from cronwrap.job_capacity import CapacityPolicy
    p = CapacityPolicy(job_name="myjob", max_slots=2, state_dir=str(tmp_path))
    p.acquire()
    rc = main(["release", "myjob", "--state-dir", str(tmp_path)])
    assert rc == 0


def test_release_removes_slot(tmp_path):
    from cronwrap.job_capacity import CapacityPolicy
    p = CapacityPolicy(job_name="myjob", max_slots=2, state_dir=str(tmp_path))
    p.acquire()
    assert p.used_slots() == 1
    main(["release", "myjob", "--state-dir", str(tmp_path)])
    assert p.used_slots() == 0
