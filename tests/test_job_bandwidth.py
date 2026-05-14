"""Tests for cronwrap.job_bandwidth."""
import json
import pytest
from pathlib import Path

from cronwrap.job_bandwidth import BandwidthPolicy, BandwidthError


def _make(tmp_path, **kwargs) -> BandwidthPolicy:
    defaults = {
        "job_name": "test-job",
        "max_bytes_per_run": 1000,
        "state_dir": str(tmp_path),
    }
    defaults.update(kwargs)
    return BandwidthPolicy(**defaults)


def test_from_dict_required(tmp_path):
    p = BandwidthPolicy.from_dict(
        {"job_name": "j", "max_bytes_per_run": 500, "state_dir": str(tmp_path)}
    )
    assert p.job_name == "j"
    assert p.max_bytes_per_run == 500


def test_from_dict_default_state_dir():
    p = BandwidthPolicy.from_dict({"job_name": "j", "max_bytes_per_run": 100})
    assert p.state_dir == "/tmp/cronwrap/bandwidth"


def test_from_dict_missing_raises():
    with pytest.raises(BandwidthError, match="Missing required fields"):
        BandwidthPolicy.from_dict({"job_name": "j"})


def test_to_dict_roundtrip(tmp_path):
    p = _make(tmp_path)
    d = p.to_dict()
    p2 = BandwidthPolicy.from_dict(d)
    assert p2.job_name == p.job_name
    assert p2.max_bytes_per_run == p.max_bytes_per_run


def test_record_under_limit(tmp_path):
    p = _make(tmp_path)
    result = p.record(500)
    assert result["exceeded"] is False
    assert result["bytes_used"] == 500


def test_record_exceeds_limit_raises(tmp_path):
    p = _make(tmp_path)
    with pytest.raises(BandwidthError, match="limit is 1000"):
        p.record(2000)


def test_record_persists_to_disk(tmp_path):
    p = _make(tmp_path)
    p.record(100)
    state = json.loads((tmp_path / "test-job.json").read_text())
    assert state["bytes_used"] == 100


def test_record_negative_bytes_raises(tmp_path):
    p = _make(tmp_path)
    with pytest.raises(BandwidthError, match="non-negative"):
        p.record(-1)


def test_last_record_none_when_no_state(tmp_path):
    p = _make(tmp_path)
    assert p.last_record() is None


def test_last_record_returns_last_entry(tmp_path):
    p = _make(tmp_path)
    p.record(300)
    r = p.last_record()
    assert r is not None
    assert r["bytes_used"] == 300


def test_warn_flag_set_when_near_limit(tmp_path):
    p = _make(tmp_path, warn_pct=80.0)
    result = p.record(850)
    assert result["warn"] is True


def test_warn_flag_clear_when_well_under(tmp_path):
    p = _make(tmp_path, warn_pct=80.0)
    result = p.record(100)
    assert result["warn"] is False
