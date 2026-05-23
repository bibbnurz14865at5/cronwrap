"""Tests for cronwrap.job_quota_history."""
import json
import os
import pytest

from cronwrap.job_quota_history import QuotaUsageSnapshot, QuotaHistory, QuotaHistoryError


def _make(tmp_path, job_name="test-job"):
    return QuotaHistory(job_name=job_name, state_dir=str(tmp_path))


def test_snapshot_to_dict_required_keys():
    s = QuotaUsageSnapshot(job_name="j", used=10, limit=100)
    d = s.to_dict()
    assert "job_name" in d
    assert "used" in d
    assert "limit" in d
    assert "pct_used" in d
    assert "timestamp" in d


def test_snapshot_pct_used_normal():
    s = QuotaUsageSnapshot(job_name="j", used=25, limit=100)
    assert s.pct_used == 25.0


def test_snapshot_pct_used_zero_limit():
    s = QuotaUsageSnapshot(job_name="j", used=5, limit=0)
    assert s.pct_used == 0.0


def test_snapshot_extra_omitted_when_empty():
    s = QuotaUsageSnapshot(job_name="j", used=1, limit=10)
    assert "extra" not in s.to_dict()


def test_snapshot_extra_included_when_set():
    s = QuotaUsageSnapshot(job_name="j", used=1, limit=10, extra={"note": "ok"})
    d = s.to_dict()
    assert "extra" in d
    assert d["extra"]["note"] == "ok"


def test_snapshot_roundtrip():
    s = QuotaUsageSnapshot(job_name="j", used=7, limit=50, timestamp="2024-01-01T00:00:00+00:00")
    s2 = QuotaUsageSnapshot.from_dict(s.to_dict())
    assert s2.job_name == s.job_name
    assert s2.used == s.used
    assert s2.limit == s.limit
    assert s2.timestamp == s.timestamp


def test_record_creates_file(tmp_path):
    qh = _make(tmp_path)
    qh.record(used=10, limit=100)
    files = list(tmp_path.iterdir())
    assert len(files) == 1
    assert files[0].name.endswith(".quota_history.json")


def test_record_appends_entries(tmp_path):
    qh = _make(tmp_path)
    qh.record(used=10, limit=100)
    qh.record(used=20, limit=100)
    snaps = qh.snapshots()
    assert len(snaps) == 2
    assert snaps[0].used == 10
    assert snaps[1].used == 20


def test_snapshots_empty_when_no_file(tmp_path):
    qh = _make(tmp_path)
    assert qh.snapshots() == []


def test_clear_removes_file(tmp_path):
    qh = _make(tmp_path)
    qh.record(used=5, limit=10)
    qh.clear()
    assert qh.snapshots() == []


def test_clear_noop_when_no_file(tmp_path):
    qh = _make(tmp_path)
    qh.clear()  # should not raise


def test_record_with_extra(tmp_path):
    qh = _make(tmp_path)
    snap = qh.record(used=3, limit=10, extra={"source": "api"})
    assert snap.extra["source"] == "api"
    loaded = qh.snapshots()
    assert loaded[0].extra["source"] == "api"


def test_multiple_jobs_separate_files(tmp_path):
    qh1 = QuotaHistory(job_name="job-a", state_dir=str(tmp_path))
    qh2 = QuotaHistory(job_name="job-b", state_dir=str(tmp_path))
    qh1.record(used=1, limit=10)
    qh2.record(used=9, limit=10)
    assert len(qh1.snapshots()) == 1
    assert len(qh2.snapshots()) == 1
    assert qh1.snapshots()[0].used == 1
    assert qh2.snapshots()[0].used == 9
