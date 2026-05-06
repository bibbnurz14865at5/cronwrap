"""Tests for cronwrap.job_counter."""
import json
import pytest

from cronwrap.job_counter import CounterRecord, CounterError, JobCounter


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make(tmp_path) -> JobCounter:
    return JobCounter(state_dir=str(tmp_path / "counters"))


# ---------------------------------------------------------------------------
# CounterRecord unit tests
# ---------------------------------------------------------------------------

def test_record_to_dict_required_keys():
    rec = CounterRecord(job_name="backup")
    d = rec.to_dict()
    assert set(d.keys()) >= {"job_name", "total", "successes", "failures"}


def test_record_to_dict_omits_extra_when_empty():
    rec = CounterRecord(job_name="backup")
    assert "extra" not in rec.to_dict()


def test_record_to_dict_includes_extra_when_set():
    rec = CounterRecord(job_name="backup", extra={"env": "prod"})
    assert rec.to_dict()["extra"] == {"env": "prod"}


def test_record_roundtrip():
    rec = CounterRecord(job_name="sync", total=5, successes=4, failures=1)
    assert CounterRecord.from_dict(rec.to_dict()).total == 5


def test_success_rate_none_when_total_zero():
    rec = CounterRecord(job_name="x")
    assert rec.success_rate is None


def test_success_rate_computed():
    rec = CounterRecord(job_name="x", total=4, successes=3, failures=1)
    assert rec.success_rate == 0.75


# ---------------------------------------------------------------------------
# JobCounter integration tests
# ---------------------------------------------------------------------------

def test_get_returns_zeroed_record_for_unknown_job(tmp_path):
    ctr = _make(tmp_path)
    rec = ctr.get("unknown")
    assert rec.total == 0
    assert rec.successes == 0
    assert rec.failures == 0


def test_increment_success(tmp_path):
    ctr = _make(tmp_path)
    rec = ctr.increment("myjob", success=True)
    assert rec.total == 1
    assert rec.successes == 1
    assert rec.failures == 0


def test_increment_failure(tmp_path):
    ctr = _make(tmp_path)
    rec = ctr.increment("myjob", success=False)
    assert rec.failures == 1
    assert rec.successes == 0


def test_increment_persists(tmp_path):
    ctr = _make(tmp_path)
    ctr.increment("myjob", success=True)
    ctr.increment("myjob", success=False)
    rec = ctr.get("myjob")
    assert rec.total == 2
    assert rec.successes == 1
    assert rec.failures == 1


def test_reset_zeroes_counters(tmp_path):
    ctr = _make(tmp_path)
    ctr.increment("myjob", success=True)
    ctr.increment("myjob", success=True)
    rec = ctr.reset("myjob")
    assert rec.total == 0
    assert ctr.get("myjob").total == 0


def test_state_dir_created_automatically(tmp_path):
    state_dir = tmp_path / "deep" / "nested" / "counters"
    ctr = JobCounter(state_dir=str(state_dir))
    ctr.increment("j", success=True)
    assert state_dir.exists()


def test_corrupt_file_raises_counter_error(tmp_path):
    ctr = _make(tmp_path)
    p = ctr._path("bad")
    p.write_text("not json")
    with pytest.raises(CounterError):
        ctr.get("bad")
