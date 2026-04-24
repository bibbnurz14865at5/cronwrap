"""Tests for cronwrap.job_escalation and escalation_cli."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.job_escalation import EscalationError, EscalationPolicy
from cronwrap.escalation_cli import build_parser, main


def _make(tmp_path: Path, threshold: int = 2, contacts=None) -> EscalationPolicy:
    return EscalationPolicy(
        job_name="test-job",
        failure_threshold=threshold,
        contacts=contacts or ["admin@example.com"],
        state_dir=str(tmp_path),
    )


# ---------------------------------------------------------------------------
# EscalationPolicy unit tests
# ---------------------------------------------------------------------------

def test_from_dict_required(tmp_path):
    p = EscalationPolicy.from_dict({
        "job_name": "j",
        "failure_threshold": 3,
        "contacts": ["a@b.com"],
        "state_dir": str(tmp_path),
    })
    assert p.job_name == "j"
    assert p.failure_threshold == 3
    assert p.contacts == ["a@b.com"]


def test_from_dict_missing_job_name_raises():
    with pytest.raises(EscalationError, match="job_name"):
        EscalationPolicy.from_dict({"failure_threshold": 1, "contacts": ["x"]})


def test_from_dict_missing_contacts_raises():
    with pytest.raises(EscalationError, match="contacts"):
        EscalationPolicy.from_dict({"job_name": "j", "failure_threshold": 1})


def test_invalid_threshold_raises(tmp_path):
    with pytest.raises(EscalationError, match="failure_threshold"):
        _make(tmp_path, threshold=0)


def test_empty_contacts_raises(tmp_path):
    with pytest.raises(EscalationError, match="contacts"):
        _make(tmp_path, contacts=[])


def test_to_dict_roundtrip(tmp_path):
    p = _make(tmp_path)
    d = p.to_dict()
    p2 = EscalationPolicy.from_dict(d)
    assert p2.job_name == p.job_name
    assert p2.failure_threshold == p.failure_threshold


def test_from_json_file(tmp_path):
    cfg = tmp_path / "esc.json"
    cfg.write_text(json.dumps({
        "job_name": "backup",
        "failure_threshold": 2,
        "contacts": ["ops@example.com"],
        "state_dir": str(tmp_path),
    }))
    p = EscalationPolicy.from_json_file(str(cfg))
    assert p.job_name == "backup"


def test_from_json_file_not_found():
    with pytest.raises(EscalationError, match="not found"):
        EscalationPolicy.from_json_file("/nonexistent/path.json")


def test_consecutive_failures_initially_zero(tmp_path):
    p = _make(tmp_path)
    assert p.consecutive_failures() == 0


def test_record_failure_increments(tmp_path):
    p = _make(tmp_path, threshold=3)
    p.record_failure()
    p.record_failure()
    assert p.consecutive_failures() == 2


def test_record_failure_returns_true_at_threshold(tmp_path):
    p = _make(tmp_path, threshold=2)
    p.record_failure()
    result = p.record_failure()
    assert result is True


def test_record_failure_returns_false_below_threshold(tmp_path):
    p = _make(tmp_path, threshold=3)
    result = p.record_failure()
    assert result is False


def test_record_success_resets_counter(tmp_path):
    p = _make(tmp_path, threshold=2)
    p.record_failure()
    p.record_failure()
    p.record_success()
    assert p.consecutive_failures() == 0


def test_should_escalate_true(tmp_path):
    p = _make(tmp_path, threshold=1)
    p.record_failure()
    assert p.should_escalate() is True


def test_should_escalate_false(tmp_path):
    p = _make(tmp_path, threshold=3)
    p.record_failure()
    assert p.should_escalate() is False


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

def _cfg_file(tmp_path: Path, threshold: int = 2) -> str:
    cfg = tmp_path / "esc.json"
    cfg.write_text(json.dumps({
        "job_name": "cli-job",
        "failure_threshold": threshold,
        "contacts": ["ops@example.com"],
        "state_dir": str(tmp_path),
    }))
    return str(cfg)


def _run(argv):
    return main(argv)


def test_build_parser_returns_parser():
    assert build_parser() is not None


def test_no_command_returns_1(tmp_path):
    assert _run(["--config", _cfg_file(tmp_path)]) == 1


def test_show_command(tmp_path):
    cfg = _cfg_file(tmp_path)
    assert _run(["--config", cfg, "show"]) == 0


def test_reset_command(tmp_path):
    cfg = _cfg_file(tmp_path)
    p = EscalationPolicy.from_json_file(cfg)
    p.record_failure()
    assert _run(["--config", cfg, "reset"]) == 0
    assert p.consecutive_failures() == 0


def test_check_not_escalated(tmp_path):
    assert _run(["--config", _cfg_file(tmp_path, threshold=3), "check"]) == 0


def test_check_escalated(tmp_path):
    cfg = _cfg_file(tmp_path, threshold=1)
    p = EscalationPolicy.from_json_file(cfg)
    p.record_failure()
    assert _run(["--config", cfg, "check"]) == 1


def test_bad_config_returns_2(tmp_path):
    assert _run(["--config", "/no/such/file.json", "show"]) == 2
