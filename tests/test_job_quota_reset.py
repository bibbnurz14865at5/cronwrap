"""Tests for cronwrap.job_quota_reset and cronwrap.quota_reset_cli."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cronwrap.job_quota_reset import QuotaResetError, QuotaResetPolicy
from cronwrap.quota_reset_cli import build_parser, main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make(tmp_path: Path, **kwargs) -> QuotaResetPolicy:
    defaults = {
        "job_name": "backup",
        "period": "daily",
        "state_dir": str(tmp_path / "state"),
    }
    defaults.update(kwargs)
    return QuotaResetPolicy.from_dict(defaults)


# ---------------------------------------------------------------------------
# from_dict / to_dict
# ---------------------------------------------------------------------------

def test_from_dict_required(tmp_path):
    p = _make(tmp_path)
    assert p.job_name == "backup"
    assert p.period == "daily"


def test_from_dict_missing_raises():
    with pytest.raises(QuotaResetError, match="Missing required keys"):
        QuotaResetPolicy.from_dict({"period": "daily"})


def test_invalid_period_raises():
    with pytest.raises(QuotaResetError, match="Invalid period"):
        QuotaResetPolicy.from_dict({"job_name": "x", "period": "yearly"})


def test_to_dict_roundtrip(tmp_path):
    p = _make(tmp_path)
    d = p.to_dict()
    p2 = QuotaResetPolicy.from_dict(d)
    assert p2.job_name == p.job_name
    assert p2.period == p.period


# ---------------------------------------------------------------------------
# needs_reset / reset
# ---------------------------------------------------------------------------

def test_needs_reset_no_state(tmp_path):
    p = _make(tmp_path)
    assert p.needs_reset() is True


def test_needs_reset_false_after_recent_reset(tmp_path):
    p = _make(tmp_path)
    now = datetime.now(timezone.utc)
    p.reset(now=now)
    assert p.needs_reset(now=now + timedelta(seconds=60)) is False


def test_needs_reset_true_after_period_elapsed(tmp_path):
    p = _make(tmp_path, period="hourly")
    old = datetime.now(timezone.utc) - timedelta(hours=2)
    p.reset(now=old)
    assert p.needs_reset() is True


def test_reset_returns_iso_timestamp(tmp_path):
    p = _make(tmp_path)
    ts = p.reset()
    datetime.fromisoformat(ts)  # should not raise


def test_last_reset_time_none_initially(tmp_path):
    p = _make(tmp_path)
    assert p.last_reset_time() is None


def test_last_reset_time_after_reset(tmp_path):
    p = _make(tmp_path)
    ts = p.reset()
    assert p.last_reset_time() == ts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _run(tmp_path, args):
    return main(args)


def _write_config(tmp_path, **kwargs) -> Path:
    cfg = {"job_name": "myjob", "period": "daily",
           "state_dir": str(tmp_path / "state")}
    cfg.update(kwargs)
    p = tmp_path / "reset_policy.json"
    p.write_text(json.dumps(cfg))
    return p


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1(tmp_path):
    assert main([]) == 1


def test_check_command_no_prior_reset(tmp_path):
    cfg = _write_config(tmp_path)
    rc = main(["check", "--config", str(cfg)])
    assert rc == 3  # DUE


def test_check_command_after_reset(tmp_path):
    cfg = _write_config(tmp_path)
    main(["reset", "--config", str(cfg)])
    rc = main(["check", "--config", str(cfg)])
    assert rc == 0  # OK


def test_reset_command_returns_0(tmp_path):
    cfg = _write_config(tmp_path)
    assert main(["reset", "--config", str(cfg)]) == 0


def test_show_command_no_reset(tmp_path, capsys):
    cfg = _write_config(tmp_path)
    rc = main(["show", "--config", str(cfg)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "no reset recorded" in out


def test_show_command_after_reset(tmp_path, capsys):
    cfg = _write_config(tmp_path)
    main(["reset", "--config", str(cfg)])
    rc = main(["show", "--config", str(cfg)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "last_reset" in out


def test_missing_config_returns_2(tmp_path):
    rc = main(["check", "--config", str(tmp_path / "nope.json")])
    assert rc == 2
