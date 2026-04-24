"""Tests for cronwrap.snapshot_cli."""
from __future__ import annotations

import json
from pathlib import Path

from cronwrap.history import JobHistory
from cronwrap.snapshot_cli import build_parser, main


def _write_history(tmp_path: Path, job_name: str) -> None:
    history = JobHistory(str(tmp_path), job_name)
    history.record(status="success", duration=5.0)


def _run(argv: list[str]) -> tuple[int, str]:
    """Run main() capturing stdout via capsys would need pytest; keep simple."""
    return main(argv)


def test_build_parser_returns_parser():
    parser = build_parser()
    assert parser is not None
    assert parser.prog == "cronwrap-snapshot"


def test_main_empty_dir_returns_0(tmp_path):
    rc = main(["--history-dir", str(tmp_path)])
    assert rc == 0


def test_main_nonexistent_dir_returns_0(tmp_path):
    rc = main(["--history-dir", str(tmp_path / "missing")])
    assert rc == 0


def test_main_writes_output_file(tmp_path):
    _write_history(tmp_path, "myjob")
    out = tmp_path / "snap.json"
    rc = main([
        "--history-dir", str(tmp_path),
        "--output", str(out),
    ])
    assert rc == 0
    assert out.exists()
    data = json.loads(out.read_text())
    assert "jobs" in data
    assert data["jobs"][0]["job_name"] == "myjob"


def test_main_output_file_contains_generated_at(tmp_path):
    out = tmp_path / "snap.json"
    main(["--history-dir", str(tmp_path), "--output", str(out)])
    data = json.loads(out.read_text())
    assert "generated_at" in data


def test_main_creates_nested_output_dir(tmp_path):
    out = tmp_path / "a" / "b" / "snap.json"
    rc = main(["--history-dir", str(tmp_path), "--output", str(out)])
    assert rc == 0
    assert out.exists()
