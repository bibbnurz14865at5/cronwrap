"""Tests for cronwrap.timeout_policy."""
import json
import pytest
from pathlib import Path

from cronwrap.timeout_policy import TimeoutPolicy


def test_from_dict_defaults():
    p = TimeoutPolicy.from_dict({})
    assert p.timeout_seconds is None
    assert p.warn_seconds is None
    assert p.alert_on_warn is False


def test_from_dict_custom():
    p = TimeoutPolicy.from_dict({"timeout_seconds": 60, "warn_seconds": 30, "alert_on_warn": True})
    assert p.timeout_seconds == 60
    assert p.warn_seconds == 30
    assert p.alert_on_warn is True


def test_from_dict_ignores_unknown():
    p = TimeoutPolicy.from_dict({"timeout_seconds": 10, "unknown_key": "x"})
    assert p.timeout_seconds == 10
    assert not hasattr(p, "unknown_key")


def test_to_dict_roundtrip():
    original = TimeoutPolicy(timeout_seconds=120, warn_seconds=90, alert_on_warn=True)
    restored = TimeoutPolicy.from_dict(original.to_dict())
    assert restored.timeout_seconds == 120
    assert restored.warn_seconds == 90
    assert restored.alert_on_warn is True


def test_is_timed_out_no_limit():
    p = TimeoutPolicy()
    assert p.is_timed_out(9999) is False


def test_is_timed_out_under():
    p = TimeoutPolicy(timeout_seconds=60)
    assert p.is_timed_out(59.9) is False


def test_is_timed_out_at_boundary():
    p = TimeoutPolicy(timeout_seconds=60)
    assert p.is_timed_out(60) is True


def test_is_warned_no_threshold():
    p = TimeoutPolicy()
    assert p.is_warned(500) is False


def test_is_warned_exceeded():
    p = TimeoutPolicy(warn_seconds=30)
    assert p.is_warned(31) is True


def test_evaluate_all_clear():
    p = TimeoutPolicy(timeout_seconds=60, warn_seconds=30, alert_on_warn=True)
    result = p.evaluate(10)
    assert result["timed_out"] is False
    assert result["warned"] is False
    assert result["alert"] is False


def test_evaluate_warn_with_alert():
    p = TimeoutPolicy(warn_seconds=30, alert_on_warn=True)
    result = p.evaluate(35)
    assert result["warned"] is True
    assert result["alert"] is True


def test_evaluate_warn_no_alert():
    p = TimeoutPolicy(warn_seconds=30, alert_on_warn=False)
    result = p.evaluate(35)
    assert result["warned"] is True
    assert result["alert"] is False


def test_from_json_file(tmp_path):
    cfg = {"timeout_seconds": 45, "warn_seconds": 20, "alert_on_warn": True}
    f = tmp_path / "tp.json"
    f.write_text(json.dumps(cfg))
    p = TimeoutPolicy.from_json_file(str(f))
    assert p.timeout_seconds == 45


def test_from_json_file_not_found():
    with pytest.raises(FileNotFoundError):
        TimeoutPolicy.from_json_file("/nonexistent/timeout.json")
