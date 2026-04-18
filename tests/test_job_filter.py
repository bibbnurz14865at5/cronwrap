import time
import pytest
from cronwrap.job_filter import JobFilter, apply_filter
from cronwrap.history import HistoryEntry


def _entry(exit_code=0, timed_out=False, offset=0):
    e = HistoryEntry(exit_code=exit_code, duration=1.0, timed_out=timed_out)
    e.timestamp = time.time() + offset
    return e


def test_from_dict_defaults():
    f = JobFilter.from_dict({})
    assert f.tags == []
    assert f.statuses == []
    assert f.job_names == []
    assert f.since is None
    assert f.until is None


def test_to_dict_roundtrip():
    f = JobFilter(tags=["nightly"], statuses=["fail"], job_names=["backup"], since=1.0, until=2.0)
    assert JobFilter.from_dict(f.to_dict()).tags == ["nightly"]


def test_matches_no_filter():
    f = JobFilter()
    assert f.matches(_entry(), "any_job") is True


def test_matches_job_name_include():
    f = JobFilter(job_names=["backup"])
    assert f.matches(_entry(), "backup") is True
    assert f.matches(_entry(), "other") is False


def test_matches_status_ok():
    f = JobFilter(statuses=["ok"])
    assert f.matches(_entry(exit_code=0), "job") is True
    assert f.matches(_entry(exit_code=1), "job") is False


def test_matches_status_fail():
    f = JobFilter(statuses=["fail"])
    assert f.matches(_entry(exit_code=1), "job") is True
    assert f.matches(_entry(exit_code=0), "job") is False


def test_matches_status_timeout():
    f = JobFilter(statuses=["timeout"])
    assert f.matches(_entry(exit_code=1, timed_out=True), "job") is True
    assert f.matches(_entry(exit_code=1, timed_out=False), "job") is False


def test_matches_tags():
    f = JobFilter(tags=["nightly"])
    assert f.matches(_entry(), "job", job_tags=["nightly", "db"]) is True
    assert f.matches(_entry(), "job", job_tags=["daily"]) is False
    assert f.matches(_entry(), "job", job_tags=None) is False


def test_matches_since():
    now = time.time()
    f = JobFilter(since=now)
    assert f.matches(_entry(offset=1), "job") is True
    assert f.matches(_entry(offset=-10), "job") is False


def test_matches_until():
    now = time.time()
    f = JobFilter(until=now)
    assert f.matches(_entry(offset=-1), "job") is True
    assert f.matches(_entry(offset=10), "job") is False


def test_apply_filter_returns_subset():
    entries = [_entry(exit_code=0), _entry(exit_code=1), _entry(exit_code=0)]
    f = JobFilter(statuses=["ok"])
    result = apply_filter(entries, "job", f)
    assert len(result) == 2
    assert all(e.exit_code == 0 for e in result)


def test_apply_filter_empty():
    f = JobFilter(statuses=["fail"])
    assert apply_filter([], "job", f) == []
