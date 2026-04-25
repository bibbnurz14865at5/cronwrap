"""Tests for cronwrap.tracing_cli."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from cronwrap.tracing_cli import build_parser, main
from cronwrap.job_tracing import JobTracing


NOW = datetime.now(timezone.utc).isoformat()


def _run(argv, tmp_path=None):
    """Helper: run main with argv, return exit code."""
    return main(argv)


def _write_trace(tmp_path, job_name="myjob"):
    t = JobTracing(str(tmp_path))
    t.start_trace(job_name, NOW)
    return t


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1(tmp_path):
    assert main([]) == 1


def test_show_missing_job_returns_2(tmp_path, capsys):
    code = main(["show", "ghost", "--state-dir", str(tmp_path)])
    assert code == 2
    captured = capsys.readouterr()
    assert "ghost" in captured.err


def test_show_existing_job_returns_0(tmp_path, capsys):
    _write_trace(tmp_path, "myjob")
    code = main(["show", "myjob", "--state-dir", str(tmp_path)])
    assert code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["job_name"] == "myjob"


def test_show_output_contains_trace_id(tmp_path, capsys):
    _write_trace(tmp_path, "myjob")
    main(["show", "myjob", "--state-dir", str(tmp_path)])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "trace_id" in data
    assert "span_id" in data


def test_clear_existing_job_returns_0(tmp_path, capsys):
    _write_trace(tmp_path, "myjob")
    code = main(["clear", "myjob", "--state-dir", str(tmp_path)])
    assert code == 0
    out = capsys.readouterr().out
    assert "myjob" in out


def test_clear_removes_trace(tmp_path):
    t = _write_trace(tmp_path, "myjob")
    main(["clear", "myjob", "--state-dir", str(tmp_path)])
    assert t.get("myjob") is None


def test_clear_nonexistent_job_returns_0(tmp_path):
    # clear on a job with no trace should be a no-op, not an error
    code = main(["clear", "ghost", "--state-dir", str(tmp_path)])
    assert code == 0
