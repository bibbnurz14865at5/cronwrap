"""Tests for cronwrap.job_quota_forecast."""
import pytest

from cronwrap.job_quota_forecast import (
    QuotaForecastError,
    QuotaForecastResult,
    forecast_quota,
)


# ---------------------------------------------------------------------------
# QuotaForecastResult helpers
# ---------------------------------------------------------------------------

def _result(**kw) -> QuotaForecastResult:
    defaults = dict(
        job_name="backup",
        quota_limit=100,
        current_usage=30,
        avg_usage_per_period=10.0,
        periods_remaining=7.0,
        will_exhaust=False,
    )
    defaults.update(kw)
    return QuotaForecastResult(**defaults)


def test_to_dict_required_keys():
    r = _result()
    d = r.to_dict()
    for key in ("job_name", "quota_limit", "current_usage",
                "avg_usage_per_period", "periods_remaining", "will_exhaust"):
        assert key in d


def test_to_dict_omits_extra_when_empty():
    r = _result()
    assert "extra" not in r.to_dict()


def test_to_dict_includes_extra_when_set():
    r = _result(extra={"note": "test"})
    assert r.to_dict()["extra"] == {"note": "test"}


def test_roundtrip():
    r = _result(extra={"x": 1})
    assert QuotaForecastResult.from_dict(r.to_dict()).to_dict() == r.to_dict()


def test_to_json_valid():
    import json
    r = _result()
    data = json.loads(r.to_json())
    assert data["job_name"] == "backup"


# ---------------------------------------------------------------------------
# forecast_quota logic
# ---------------------------------------------------------------------------

def test_forecast_no_history_not_exhausted():
    r = forecast_quota("job", quota_limit=100, usage_history=[], current_usage=0)
    assert r.avg_usage_per_period == 0.0
    assert r.periods_remaining is None
    assert r.will_exhaust is False


def test_forecast_plenty_of_quota():
    r = forecast_quota("job", quota_limit=100, usage_history=[10, 10, 10], current_usage=10)
    assert r.periods_remaining == pytest.approx(9.0)
    assert r.will_exhaust is False


def test_forecast_will_exhaust_this_period():
    # current_usage=95, limit=100, avg=10 → remaining=5, periods=0.5 < 1
    r = forecast_quota("job", quota_limit=100, usage_history=[10, 10, 10], current_usage=95)
    assert r.will_exhaust is True
    assert r.periods_remaining == pytest.approx(0.5)


def test_forecast_exactly_one_period_left():
    r = forecast_quota("job", quota_limit=100, usage_history=[50], current_usage=50)
    assert r.periods_remaining == pytest.approx(1.0)
    assert r.will_exhaust is False


def test_forecast_current_usage_exceeds_limit():
    r = forecast_quota("job", quota_limit=50, usage_history=[10], current_usage=60)
    assert r.periods_remaining == pytest.approx(0.0)
    assert r.will_exhaust is True


def test_forecast_invalid_limit_raises():
    with pytest.raises(QuotaForecastError):
        forecast_quota("job", quota_limit=0, usage_history=[], current_usage=0)


def test_forecast_extra_passed_through():
    r = forecast_quota(
        "job", quota_limit=100, usage_history=[5],
        current_usage=0, extra={"env": "prod"}
    )
    assert r.extra == {"env": "prod"}


def test_forecast_avg_rounded_in_dict():
    r = forecast_quota("job", quota_limit=100, usage_history=[1, 2], current_usage=0)
    d = r.to_dict()
    # avg = 1.5 exactly — ensure it's a float
    assert isinstance(d["avg_usage_per_period"], float)
