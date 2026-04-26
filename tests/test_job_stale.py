"""Tests for cronwrap.job_stale and cronwrap.stale_cli."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from cronwrap.history import HistoryEntry, JobHistory
from cronwrap.job_stale import StaleError, StalePolicy, StaleResult, check_stale
from cronwrap.stale_cli import build_parser, main


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_history(tmp_path: Path, job: str, ts: datetime) -> None:
    h = JobHistory(str(tmp_path), job)
    entry = HistoryEntry(job_name=job, success=True, exit_code=0, duration=1.0)
    entry.timestamp = ts
    h.record(entry)


# ---------------------------------------------------------------------------
# StalePolicy
# ---------------------------------------------------------------------------

def test_from_dict_required():
    p = StalePolicy.from_dict({"job_name": "myjob", "max_age_seconds": 3600})
    assert p.job_name == "myjob"
    assert p.max_age_seconds == 3600


def test_from_dict_default_history_dir():
    p = StalePolicy.from_dict({"job_name": "j", "max_age_seconds": 60})
    assert p.history_dir == "/var/lib/cronwrap/history"


def test_from_dict_custom_history_dir():
    p = StalePolicy.from_dict(
        {"job_name": "j", "max_age_seconds": 60, "history_dir": "/tmp/h"}
    )
    assert p.history_dir == "/tmp/h"


def test_from_dict_missing_job_name_raises():
    with pytest.raises(StaleError, match="job_name"):
        StalePolicy.from_dict({"max_age_seconds": 60})


def test_from_dict_missing_max_age_raises():
    with pytest.raises(StaleError, match="max_age_seconds"):
        StalePolicy.from_dict({"job_name": "j"})


def test_to_dict_roundtrip():
    p = StalePolicy(job_name="j", max_age_seconds=120, history_dir="/h")
    assert StalePolicy.from_dict(p.to_dict()).to_dict() == p.to_dict()


def test_from_json_file(tmp_path: Path):
    cfg = tmp_path / "stale.json"
    cfg.write_text(json.dumps({"job_name": "j", "max_age_seconds": 300}))
    p = StalePolicy.from_json_file(str(cfg))
    assert p.max_age_seconds == 300


def test_from_json_file_not_found():
    with pytest.raises(StaleError, match="not found"):
        StalePolicy.from_json_file("/nonexistent/stale.json")


# ---------------------------------------------------------------------------
# check_stale
# ---------------------------------------------------------------------------

def test_check_stale_no_history_not_stale(tmp_path: Path):
    policy = StalePolicy("myjob", 3600, str(tmp_path))
    result = check_stale(policy)
    assert result.is_stale is False
    assert result.last_run is None
    assert "no history" in result.reason


def test_check_stale_recent_run_not_stale(tmp_path: Path):
    now = datetime.now(timezone.utc)
    _write_history(tmp_path, "myjob", now - timedelta(seconds=60))
    policy = StalePolicy("myjob", 3600, str(tmp_path))
    result = check_stale(policy, now=now)
    assert result.is_stale is False
    assert result.age_seconds is not None
    assert result.age_seconds < 3600


def test_check_stale_old_run_is_stale(tmp_path: Path):
    now = datetime.now(timezone.utc)
    _write_history(tmp_path, "myjob", now - timedelta(seconds=7200))
    policy = StalePolicy("myjob", 3600, str(tmp_path))
    result = check_stale(policy, now=now)
    assert result.is_stale is True
    assert "STALE" not in result.reason  # reason uses plain text
    assert "limit" in result.reason


def test_check_stale_result_attributes(tmp_path: Path):
    now = datetime.now(timezone.utc)
    _write_history(tmp_path, "j", now - timedelta(seconds=10))
    policy = StalePolicy("j", 3600, str(tmp_path))
    r = check_stale(policy, now=now)
    assert r.job_name == "j"
    assert r.max_age_seconds == 3600
    assert r.last_run is not None


# ---------------------------------------------------------------------------
# stale_cli
# ---------------------------------------------------------------------------

def _run(argv):
    return main(argv)


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1():
    assert _run([]) == 1


def test_check_missing_config_returns_2(tmp_path: Path):
    assert _run(["check", "--config", str(tmp_path / "nope.json")]) == 2


def test_check_not_stale_returns_0(tmp_path: Path, capsys):
    now = datetime.now(timezone.utc)
    _write_history(tmp_path, "j", now - timedelta(seconds=10))
    cfg = tmp_path / "stale.json"
    cfg.write_text(json.dumps({"job_name": "j", "max_age_seconds": 3600, "history_dir": str(tmp_path)}))
    rc = _run(["check", "--config", str(cfg)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out


def test_check_stale_returns_1(tmp_path: Path, capsys):
    now = datetime.now(timezone.utc)
    _write_history(tmp_path, "j", now - timedelta(seconds=7200))
    cfg = tmp_path / "stale.json"
    cfg.write_text(json.dumps({"job_name": "j", "max_age_seconds": 3600, "history_dir": str(tmp_path)}))
    rc = _run(["check", "--config", str(cfg)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "STALE" in out


def test_check_json_output(tmp_path: Path, capsys):
    now = datetime.now(timezone.utc)
    _write_history(tmp_path, "j", now - timedelta(seconds=10))
    cfg = tmp_path / "stale.json"
    cfg.write_text(json.dumps({"job_name": "j", "max_age_seconds": 3600, "history_dir": str(tmp_path)}))
    _run(["check", "--config", str(cfg), "--json"])
    data = json.loads(capsys.readouterr().out)
    assert "is_stale" in data
    assert data["job_name"] == "j"
