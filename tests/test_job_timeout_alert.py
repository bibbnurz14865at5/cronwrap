"""Tests for cronwrap.job_timeout_alert."""
import json
import pytest
from cronwrap.job_timeout_alert import TimeoutAlertPolicy, TimeoutAlertResult, evaluate


def _policy(**kwargs):
    base = {"job_name": "backup", "warn_seconds": 60.0, "critical_seconds": 120.0}
    base.update(kwargs)
    return TimeoutAlertPolicy.from_dict(base)


def test_from_dict_required_only():
    p = TimeoutAlertPolicy.from_dict({"job_name": "myjob"})
    assert p.job_name == "myjob"
    assert p.warn_seconds is None
    assert p.critical_seconds is None
    assert p.notify_slack is False
    assert p.notify_email is False


def test_from_dict_full():
    p = _policy(notify_slack=True, notify_email=True)
    assert p.warn_seconds == 60.0
    assert p.critical_seconds == 120.0
    assert p.notify_slack is True
    assert p.notify_email is True


def test_to_dict_roundtrip():
    p = _policy(notify_slack=True)
    assert TimeoutAlertPolicy.from_dict(p.to_dict()).to_dict() == p.to_dict()


def test_from_json_file(tmp_path):
    cfg = {"job_name": "sync", "warn_seconds": 30.0}
    f = tmp_path / "ta.json"
    f.write_text(json.dumps(cfg))
    p = TimeoutAlertPolicy.from_json_file(str(f))
    assert p.job_name == "sync"
    assert p.warn_seconds == 30.0


def test_from_json_file_not_found():
    with pytest.raises(FileNotFoundError):
        TimeoutAlertPolicy.from_json_file("/no/such/file.json")


def test_evaluate_ok():
    p = _policy()
    r = evaluate(p, 30.0)
    assert r.level == "ok"
    assert not r.triggered


def test_evaluate_warn():
    p = _policy()
    r = evaluate(p, 90.0)
    assert r.level == "warn"
    assert r.triggered


def test_evaluate_critical():
    p = _policy()
    r = evaluate(p, 150.0)
    assert r.level == "critical"
    assert r.triggered


def test_evaluate_critical_boundary():
    p = _policy()
    r = evaluate(p, 120.0)
    assert r.level == "critical"


def test_evaluate_warn_boundary():
    p = _policy()
    r = evaluate(p, 60.0)
    assert r.level == "warn"


def test_evaluate_no_thresholds():
    p = TimeoutAlertPolicy.from_dict({"job_name": "x"})
    r = evaluate(p, 9999.0)
    assert r.level == "ok"


def test_result_repr():
    p = _policy()
    r = evaluate(p, 75.5)
    assert "warn" in repr(r)
    assert "backup" in repr(r)


def test_result_attributes():
    p = _policy()
    r = evaluate(p, 50.0)
    assert r.job_name == "backup"
    assert r.duration == 50.0
    assert r.warn_seconds == 60.0
    assert r.critical_seconds == 120.0
