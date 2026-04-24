"""Tests for cronwrap.blackout_cli."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.blackout_cli import build_parser, main


def _run(args: list[str]) -> int:
    return main(args)


def _write_config(tmp_path: Path, data: dict) -> str:
    p = tmp_path / "blackout.json"
    p.write_text(json.dumps(data))
    return str(p)


_SIMPLE = {
    "job_name": "myjob",
    "windows": [{"start": "08:00", "end": "09:00"}],
}


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1():
    assert _run([]) == 1


def test_show_command(tmp_path: Path, capsys):
    cfg = _write_config(tmp_path, _SIMPLE)
    rc = _run(["show", cfg])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["job_name"] == "myjob"


def test_show_missing_file_returns_2():
    assert _run(["show", "/no/such/file.json"]) == 2


def test_check_active(tmp_path: Path, capsys):
    cfg = _write_config(tmp_path, _SIMPLE)
    # 2024-01-15T12:00 is outside 08:00–09:00
    rc = _run(["check", cfg, "--at", "2024-01-15T12:00"])
    assert rc == 0
    assert "active" in capsys.readouterr().out


def test_check_blacked_out(tmp_path: Path, capsys):
    cfg = _write_config(tmp_path, _SIMPLE)
    # 2024-01-15T08:30 is inside 08:00–09:00
    rc = _run(["check", cfg, "--at", "2024-01-15T08:30"])
    assert rc == 0
    assert "BLACKED OUT" in capsys.readouterr().out


def test_check_invalid_at_format_returns_2(tmp_path: Path):
    cfg = _write_config(tmp_path, _SIMPLE)
    assert _run(["check", cfg, "--at", "not-a-date"]) == 2


def test_check_missing_file_returns_2():
    assert _run(["check", "/no/such/file.json"]) == 2
