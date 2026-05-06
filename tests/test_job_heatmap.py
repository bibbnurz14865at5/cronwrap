"""Tests for cronwrap.job_heatmap."""

from __future__ import annotations

import pytest

from cronwrap.job_heatmap import HeatmapError, HeatmapRecord, JobHeatmap


def _make(tmp_path) -> JobHeatmap:
    return JobHeatmap(str(tmp_path / "heatmaps"))


# --- HeatmapRecord unit tests ---

def test_record_to_dict_keys():
    rec = HeatmapRecord(job_name="myjob")
    d = rec.to_dict()
    assert "job_name" in d
    assert "buckets" in d
    assert len(d["buckets"]) == 24


def test_record_roundtrip():
    rec = HeatmapRecord(job_name="myjob", buckets=[i for i in range(24)])
    assert HeatmapRecord.from_dict(rec.to_dict()).buckets == rec.buckets


def test_record_from_dict_wrong_bucket_length_raises():
    with pytest.raises(HeatmapError):
        HeatmapRecord.from_dict({"job_name": "x", "buckets": [0] * 10})


def test_peak_hour_none_when_all_zero():
    rec = HeatmapRecord(job_name="j")
    assert rec.peak_hour() is None


def test_peak_hour_correct():
    buckets = [0] * 24
    buckets[14] = 5
    rec = HeatmapRecord(job_name="j", buckets=buckets)
    assert rec.peak_hour() == 14


def test_total_runs_zero():
    rec = HeatmapRecord(job_name="j")
    assert rec.total_runs() == 0


def test_total_runs_nonzero():
    buckets = [0] * 24
    buckets[3] = 7
    buckets[15] = 3
    rec = HeatmapRecord(job_name="j", buckets=buckets)
    assert rec.total_runs() == 10


# --- JobHeatmap integration tests ---

def test_record_increments_bucket(tmp_path):
    hm = _make(tmp_path)
    hm.record("job1", 9)
    hm.record("job1", 9)
    rec = hm.get("job1")
    assert rec.buckets[9] == 2


def test_record_invalid_hour_raises(tmp_path):
    hm = _make(tmp_path)
    with pytest.raises(HeatmapError):
        hm.record("job1", 24)


def test_record_negative_hour_raises(tmp_path):
    hm = _make(tmp_path)
    with pytest.raises(HeatmapError):
        hm.record("job1", -1)


def test_get_returns_empty_record_for_unknown_job(tmp_path):
    hm = _make(tmp_path)
    rec = hm.get("unknown")
    assert rec.total_runs() == 0
    assert rec.job_name == "unknown"


def test_reset_removes_state(tmp_path):
    hm = _make(tmp_path)
    hm.record("job1", 5)
    hm.reset("job1")
    assert hm.get("job1").total_runs() == 0


def test_reset_nonexistent_job_is_noop(tmp_path):
    hm = _make(tmp_path)
    hm.reset("ghost")  # should not raise


def test_all_jobs_lists_tracked_jobs(tmp_path):
    hm = _make(tmp_path)
    hm.record("alpha", 0)
    hm.record("beta", 1)
    assert hm.all_jobs() == ["alpha", "beta"]


def test_persists_across_instances(tmp_path):
    state_dir = str(tmp_path / "heatmaps")
    JobHeatmap(state_dir).record("job1", 12)
    rec = JobHeatmap(state_dir).get("job1")
    assert rec.buckets[12] == 1
