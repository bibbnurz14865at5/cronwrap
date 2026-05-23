"""Tests for cronwrap.quota_history_cli."""
import json
import sys
from io import StringIO

import pytest

from cronwrap.job_quota_history import QuotaHistory
from cronwrap import quota_history_cli


def _run(args, tmp_path=None, capsys=None):
    return quota_history_cli.main(args)


def test_build_parser_returns_parser():
    p = quota_history_cli.build_parser()
    assert p is not None


def test_no_command_returns_1(tmp_path):
    rc = quota_history_cli.main([])
    assert rc == 1


def test_show_empty_returns_0(tmp_path, capsys):
    rc = quota_history_cli.main(
        ["show", "my-job", f"--state-dir={tmp_path}"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "No quota history" in out


def test_show_text_format(tmp_path, capsys):
    qh = QuotaHistory(job_name="my-job", state_dir=str(tmp_path))
    qh.record(used=30, limit=100)
    rc = quota_history_cli.main(
        ["show", "my-job", f"--state-dir={tmp_path}", "--format=text"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "30/100" in out
    assert "30.0%" in out


def test_show_json_format(tmp_path, capsys):
    qh = QuotaHistory(job_name="my-job", state_dir=str(tmp_path))
    qh.record(used=50, limit=200)
    rc = quota_history_cli.main(
        ["show", "my-job", f"--state-dir={tmp_path}", "--format=json"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert data[0]["used"] == 50


def test_show_last_limits_entries(tmp_path, capsys):
    qh = QuotaHistory(job_name="my-job", state_dir=str(tmp_path))
    for i in range(5):
        qh.record(used=i, limit=10)
    rc = quota_history_cli.main(
        ["show", "my-job", f"--state-dir={tmp_path}", "--last=2", "--format=json"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) == 2
    assert data[-1]["used"] == 4


def test_clear_command_returns_0(tmp_path, capsys):
    qh = QuotaHistory(job_name="my-job", state_dir=str(tmp_path))
    qh.record(used=5, limit=10)
    rc = quota_history_cli.main(
        ["clear", "my-job", f"--state-dir={tmp_path}"]
    )
    assert rc == 0
    assert qh.snapshots() == []
