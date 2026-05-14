"""Tests for cronwrap.bandwidth_cli."""
import json
import pytest
from pathlib import Path

from cronwrap.bandwidth_cli import build_parser, main
from cronwrap.job_bandwidth import BandwidthPolicy


def _run(args, tmp_path=None):
    return main(args)


def _write_record(tmp_path, job_name="test-job", bytes_used=500, limit=1000):
    p = BandwidthPolicy(
        job_name=job_name,
        max_bytes_per_run=limit,
        state_dir=str(tmp_path),
    )
    p.record(bytes_used)
    return p


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1():
    assert main([]) == 1


def test_show_command_text(tmp_path, capsys):
    _write_record(tmp_path)
    rc = main(["show", "test-job", "--state-dir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "bytes" in out
    assert "500" in out


def test_show_command_json_format(tmp_path, capsys):
    _write_record(tmp_path)
    rc = main(["show", "test-job", "--state-dir", str(tmp_path), "--format", "json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["bytes_used"] == 500


def test_show_missing_job_returns_0(tmp_path, capsys):
    rc = main(["show", "no-such-job", "--state-dir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "No bandwidth record" in out
