"""Tests for cronwrap.profiler_cli."""
from __future__ import annotations

import json
import pytest

from cronwrap.profiler_cli import build_parser, main
from cronwrap.job_profiler import JobProfiler


def _run(args, tmp_path=None):
    """Run main() with given args list, return exit code."""
    return main(args)


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1(tmp_path):
    assert main([]) == 1


def test_show_empty_profile(tmp_path, capsys):
    rc = main(["show", "myjob", "--state-dir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["job_name"] == "myjob"
    assert data["durations"] == []


def test_show_with_data(tmp_path, capsys):
    profiler = JobProfiler(str(tmp_path))
    profiler.record("myjob", 5.0)
    rc = main(["show", "myjob", "--state-dir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert 5.0 in data["durations"]


def test_list_empty(tmp_path, capsys):
    rc = main(["list", "--state-dir", str(tmp_path)])
    assert rc == 0
    assert "No profiles found" in capsys.readouterr().out


def test_list_json_format(tmp_path, capsys):
    profiler = JobProfiler(str(tmp_path))
    profiler.record("job_x", 3.0)
    rc = main(["list", "--state-dir", str(tmp_path), "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert "job_x" in data


def test_check_no_regression(tmp_path, capsys):
    profiler = JobProfiler(str(tmp_path))
    for d in [1.0, 2.0, 3.0, 4.0, 5.0]:
        profiler.record("myjob", d)
    rc = main(["check", "myjob", "6.0", "--state-dir", str(tmp_path)])
    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_check_regression_detected(tmp_path, capsys):
    profiler = JobProfiler(str(tmp_path))
    for d in [1.0, 2.0, 3.0, 4.0, 5.0]:
        profiler.record("myjob", d)
    rc = main(["check", "myjob", "200.0", "--state-dir", str(tmp_path)])
    assert rc == 2
    assert "REGRESSION" in capsys.readouterr().out


def test_check_no_history_no_regression(tmp_path, capsys):
    rc = main(["check", "unknown_job", "999.0", "--state-dir", str(tmp_path)])
    assert rc == 0
