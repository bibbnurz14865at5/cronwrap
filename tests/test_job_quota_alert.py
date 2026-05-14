"""Tests for cronwrap.job_quota_alert."""
import json
import pytest

from cronwrap.job_quota_alert import QuotaAlertError, QuotaAlertPolicy, QuotaAlertResult


def _make(tmp_path, **kwargs):
    defaults = {
        "job_name": "my-job",
        "warn_pct": 75.0,
        "critical_pct": 90.0,
        "state_dir": str(tmp_path),
    }
    defaults.update(kwargs)
    return QuotaAlertPolicy.from_dict(defaults)


def test_from_dict_required_only(tmp_path):
    p = QuotaAlertPolicy.from_dict({"job_name": "j"})
    assert p.job_name == "j"
    assert p.warn_pct == 75.0
    assert p.critical_pct == 90.0


def test_from_dict_custom(tmp_path):
    p = _make(tmp_path, warn_pct=50.0, critical_pct=80.0)
    assert p.warn_pct == 50.0
    assert p.critical_pct == 80.0


def test_from_dict_missing_job_name_raises():
    with pytest.raises(QuotaAlertError, match="job_name"):
        QuotaAlertPolicy.from_dict({"warn_pct": 70.0})


def test_invalid_warn_pct_raises():
    with pytest.raises(QuotaAlertError, match="warn_pct"):
        QuotaAlertPolicy.from_dict({"job_name": "j", "warn_pct": 0.0})


def test_invalid_critical_pct_raises():
    with pytest.raises(QuotaAlertError, match="critical_pct"):
        QuotaAlertPolicy.from_dict({"job_name": "j", "critical_pct": 0.0})


def test_warn_gte_critical_raises():
    with pytest.raises(QuotaAlertError, match="warn_pct must be less"):
        QuotaAlertPolicy.from_dict({"job_name": "j", "warn_pct": 90.0, "critical_pct": 80.0})


def test_to_dict_roundtrip(tmp_path):
    p = _make(tmp_path)
    d = p.to_dict()
    p2 = QuotaAlertPolicy.from_dict(d)
    assert p2.job_name == p.job_name
    assert p2.warn_pct == p.warn_pct
    assert p2.critical_pct == p.critical_pct


def test_to_dict_omits_extra_when_empty(tmp_path):
    p = _make(tmp_path)
    assert "extra" not in p.to_dict()


def test_to_dict_includes_extra_when_set(tmp_path):
    p = _make(tmp_path, extra={"owner": "ops"})
    assert p.to_dict()["extra"] == {"owner": "ops"}


def test_from_json_file(tmp_path):
    cfg = {"job_name": "file-job", "warn_pct": 60.0, "critical_pct": 85.0}
    f = tmp_path / "qa.json"
    f.write_text(json.dumps(cfg))
    p = QuotaAlertPolicy.from_json_file(str(f))
    assert p.job_name == "file-job"


def test_from_json_file_not_found():
    with pytest.raises(QuotaAlertError, match="not found"):
        QuotaAlertPolicy.from_json_file("/nonexistent/quota_alert.json")


def test_evaluate_ok(tmp_path):
    p = _make(tmp_path)
    r = p.evaluate(used=50, limit=100)
    assert r.level == "ok"
    assert r.ok is True
    assert r.pct == 50.0


def test_evaluate_warn(tmp_path):
    p = _make(tmp_path)
    r = p.evaluate(used=80, limit=100)
    assert r.level == "warn"
    assert r.ok is False


def test_evaluate_critical(tmp_path):
    p = _make(tmp_path)
    r = p.evaluate(used=95, limit=100)
    assert r.level == "critical"
    assert r.ok is False


def test_evaluate_zero_limit_raises(tmp_path):
    p = _make(tmp_path)
    with pytest.raises(QuotaAlertError, match="limit must be positive"):
        p.evaluate(used=10, limit=0)


def test_result_to_dict_keys(tmp_path):
    p = _make(tmp_path)
    r = p.evaluate(used=70, limit=100)
    d = r.to_dict()
    for key in ("job_name", "used", "limit", "pct", "level"):
        assert key in d


def test_result_to_json_valid(tmp_path):
    p = _make(tmp_path)
    r = p.evaluate(used=70, limit=100)
    data = json.loads(r.to_json())
    assert data["job_name"] == "my-job"
