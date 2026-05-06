"""Tests for cronwrap.heatmap_cli."""

from __future__ import annotations

import json

import pytest

from cronwrap.heatmap_cli import build_parser, main
from cronwrap.job_heatmap import JobHeatmap


def _run(args: list[str]) -> int:
    return main(args)


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1():
    assert _run([]) == 1


def test_show_empty_job_returns_0(tmp_path):
    state_dir = str(tmp_path / "hm")
    assert _run(["show", "myjob", "--state-dir", state_dir]) == 0


def test_show_json_format(tmp_path, capsys):
    state_dir = str(tmp_path / "hm")
    hm = JobHeatmap(state_dir)
    hm.record("myjob", 7)
    _run(["show", "myjob", "--state-dir", state_dir, "--json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["job_name"] == "myjob"
    assert len(data["buckets"]) == 24
    assert data["buckets"][7] == 1


def test_show_text_format_contains_job_name(tmp_path, capsys):
    state_dir = str(tmp_path / "hm")
    _run(["show", "backup", "--state-dir", state_dir])
    out = capsys.readouterr().out
    assert "backup" in out


def test_list_command_returns_0(tmp_path):
    state_dir = str(tmp_path / "hm")
    assert _run(["list", "--state-dir", state_dir]) == 0


def test_list_shows_tracked_jobs(tmp_path, capsys):
    state_dir = str(tmp_path / "hm")
    hm = JobHeatmap(state_dir)
    hm.record("alpha", 0)
    hm.record("beta", 1)
    _run(["list", "--state-dir", state_dir])
    out = capsys.readouterr().out
    assert "alpha" in out
    assert "beta" in out


def test_reset_command_returns_0(tmp_path):
    state_dir = str(tmp_path / "hm")
    assert _run(["reset", "myjob", "--state-dir", state_dir]) == 0


def test_reset_clears_data(tmp_path, capsys):
    state_dir = str(tmp_path / "hm")
    hm = JobHeatmap(state_dir)
    hm.record("myjob", 3)
    _run(["reset", "myjob", "--state-dir", state_dir])
    assert hm.get("myjob").total_runs() == 0
