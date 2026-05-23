"""Tests for cronwrap.job_healthcheck."""

import pytest

from cronwrap.job_healthcheck import (
    HEALTH_DEGRADED,
    HEALTH_OK,
    HEALTH_UNHEALTHY,
    HealthCheckError,
    HealthStatus,
    JobHealthCheck,
)


def _make(tmp_path) -> JobHealthCheck:
    return JobHealthCheck(state_dir=str(tmp_path / "health"))


# ---------------------------------------------------------------------------
# HealthStatus
# ---------------------------------------------------------------------------

def test_status_to_dict_required_keys():
    s = HealthStatus(job_name="backup", status=HEALTH_OK)
    d = s.to_dict()
    assert d["job_name"] == "backup"
    assert d["status"] == HEALTH_OK
    assert "checked_at" in d


def test_status_to_dict_omits_message_when_none():
    s = HealthStatus(job_name="backup", status=HEALTH_OK)
    assert "message" not in s.to_dict()


def test_status_to_dict_includes_message_when_set():
    s = HealthStatus(job_name="backup", status=HEALTH_DEGRADED, message="slow")
    assert s.to_dict()["message"] == "slow"


def test_status_to_dict_omits_extra_when_empty():
    s = HealthStatus(job_name="backup", status=HEALTH_OK)
    assert "extra" not in s.to_dict()


def test_status_to_dict_includes_extra_when_set():
    s = HealthStatus(job_name="backup", status=HEALTH_OK, extra={"region": "us-east"})
    assert s.to_dict()["extra"] == {"region": "us-east"}


def test_status_roundtrip():
    s = HealthStatus(
        job_name="nightly",
        status=HEALTH_UNHEALTHY,
        message="timed out",
        extra={"attempts": 3},
    )
    s2 = HealthStatus.from_dict(s.to_dict())
    assert s2.job_name == s.job_name
    assert s2.status == s.status
    assert s2.message == s.message
    assert s2.extra == s.extra


def test_invalid_status_raises():
    with pytest.raises(HealthCheckError, match="Invalid status"):
        HealthStatus(job_name="backup", status="unknown")


# ---------------------------------------------------------------------------
# JobHealthCheck
# ---------------------------------------------------------------------------

def test_get_returns_none_when_no_record(tmp_path):
    hc = _make(tmp_path)
    assert hc.get("nonexistent") is None


def test_record_and_get(tmp_path):
    hc = _make(tmp_path)
    s = HealthStatus(job_name="sync", status=HEALTH_OK, message="all good")
    hc.record(s)
    result = hc.get("sync")
    assert result is not None
    assert result.status == HEALTH_OK
    assert result.message == "all good"


def test_record_overwrites_previous(tmp_path):
    hc = _make(tmp_path)
    hc.record(HealthStatus(job_name="sync", status=HEALTH_OK))
    hc.record(HealthStatus(job_name="sync", status=HEALTH_UNHEALTHY, message="failed"))
    result = hc.get("sync")
    assert result.status == HEALTH_UNHEALTHY


def test_is_healthy_true_when_ok(tmp_path):
    hc = _make(tmp_path)
    hc.record(HealthStatus(job_name="job", status=HEALTH_OK))
    assert hc.is_healthy("job") is True


def test_is_healthy_false_when_degraded(tmp_path):
    hc = _make(tmp_path)
    hc.record(HealthStatus(job_name="job", status=HEALTH_DEGRADED))
    assert hc.is_healthy("job") is False


def test_is_healthy_false_when_no_record(tmp_path):
    hc = _make(tmp_path)
    assert hc.is_healthy("missing") is False


def test_state_dir_created_automatically(tmp_path):
    state_dir = tmp_path / "deep" / "health"
    hc = JobHealthCheck(state_dir=str(state_dir))
    hc.record(HealthStatus(job_name="x", status=HEALTH_OK))
    assert state_dir.exists()
