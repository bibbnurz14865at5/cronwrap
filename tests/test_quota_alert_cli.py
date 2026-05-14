"""Tests for cronwrap.quota_alert_cli."""
import json
from pathlib import Path

import pytest

from cronwrap.quota_alert_cli import build_parser, main


def _write_config(tmp_path, **kwargs) -> str:
    cfg = {
        "job_name": "cli-job",
        "warn_pct": 75.0,
        "critical_pct": 90.0,
        **kwargs,
    }
    p = tmp_path / "qa.json"
    p.write_text(json.dumps(cfg))
    return str(p)


def _run(argv):
    return main(argv)


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1(tmp_path):
    assert _run([]) == 1


def test_show_command(tmp_path):
    cfg = _write_config(tmp_path)
    assert _run(["show", "--config", cfg]) == 0


def test_show_missing_config_returns_2(tmp_path):
    assert _run(["show", "--config", str(tmp_path / "nope.json")]) == 2


def test_check_ok_returns_0(tmp_path):
    cfg = _write_config(tmp_path)
    assert _run(["check", "--config", cfg, "--used", "50", "--limit", "100"]) == 0


def test_check_warn_returns_1(tmp_path):
    cfg = _write_config(tmp_path)
    assert _run(["check", "--config", cfg, "--used", "80", "--limit", "100"]) == 1


def test_check_critical_returns_1(tmp_path):
    cfg = _write_config(tmp_path)
    assert _run(["check", "--config", cfg, "--used", "95", "--limit", "100"]) == 1


def test_check_json_format(tmp_path, capsys):
    cfg = _write_config(tmp_path)
    _run(["check", "--config", cfg, "--used", "50", "--limit", "100", "--format", "json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["level"] == "ok"
    assert data["job_name"] == "cli-job"


def test_check_bad_config_returns_2(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"warn_pct": 70.0}))  # missing job_name
    assert _run(["check", "--config", str(bad), "--used", "50", "--limit", "100"]) == 2
