"""Tests for cronwrap.job_heartbeat."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from cronwrap.job_heartbeat import JobHeartbeat, HeartbeatRecord, MissedHeartbeat


def _make(tmp_path) -> JobHeartbeat:
    return JobHeartbeat(str(tmp_path / "heartbeats"))


# ---------------------------------------------------------------------------
# HeartbeatRecord serialisation
# ---------------------------------------------------------------------------

def test_record_to_dict_keys():
    now = datetime.now(tz=timezone.utc)
    r = HeartbeatRecord(job_name="backup", last_ping=now, interval_seconds=300)
    d = r.to_dict()
    assert set(d.keys()) >= {"job_name", "last_ping", "interval_seconds"}


def test_record_roundtrip():
    now = datetime.now(tz=timezone.utc).replace(microsecond=0)
    r = HeartbeatRecord(job_name="sync", last_ping=now, interval_seconds=60, extra={"host": "web1"})
    r2 = HeartbeatRecord.from_dict(r.to_dict())
    assert r2.job_name == r.job_name
    assert r2.last_ping == r.last_ping
    assert r2.interval_seconds == r.interval_seconds
    assert r2.extra == {"host": "web1"}


def test_record_extra_omitted_when_empty():
    now = datetime.now(tz=timezone.utc)
    r = HeartbeatRecord(job_name="x", last_ping=now, interval_seconds=10)
    assert "extra" not in r.to_dict()


# ---------------------------------------------------------------------------
# ping / last
# ---------------------------------------------------------------------------

def test_ping_creates_file(tmp_path):
    hb = _make(tmp_path)
    record = hb.ping("myjob", interval_seconds=120)
    assert record.job_name == "myjob"
    assert record.interval_seconds == 120


def test_last_returns_none_when_no_ping(tmp_path):
    hb = _make(tmp_path)
    assert hb.last("ghost") is None


def test_last_returns_record_after_ping(tmp_path):
    hb = _make(tmp_path)
    hb.ping("daily", interval_seconds=86400)
    r = hb.last("daily")
    assert r is not None
    assert r.job_name == "daily"
    assert r.interval_seconds == 86400


def test_ping_overwrites_previous(tmp_path):
    hb = _make(tmp_path)
    hb.ping("job", interval_seconds=60)
    hb.ping("job", interval_seconds=120)
    r = hb.last("job")
    assert r.interval_seconds == 120


def test_ping_with_extra(tmp_path):
    hb = _make(tmp_path)
    hb.ping("job", interval_seconds=60, extra={"node": "n1"})
    r = hb.last("job")
    assert r.extra == {"node": "n1"}


# ---------------------------------------------------------------------------
# check_missed
# ---------------------------------------------------------------------------

def test_check_missed_no_record_returns_none(tmp_path):
    hb = _make(tmp_path)
    assert hb.check_missed("unknown") is None


def test_check_missed_within_interval_returns_none(tmp_path):
    hb = _make(tmp_path)
    hb.ping("job", interval_seconds=300)
    now = datetime.now(tz=timezone.utc) + timedelta(seconds=100)
    assert hb.check_missed("job", now=now) is None


def test_check_missed_overdue_returns_missed(tmp_path):
    hb = _make(tmp_path)
    hb.ping("job", interval_seconds=60)
    now = datetime.now(tz=timezone.utc) + timedelta(seconds=200)
    result = hb.check_missed("job", now=now)
    assert isinstance(result, MissedHeartbeat)
    assert result.job_name == "job"
    assert result.seconds_overdue > 0


def test_missed_heartbeat_repr(tmp_path):
    hb = _make(tmp_path)
    hb.ping("nightly", interval_seconds=30)
    now = datetime.now(tz=timezone.utc) + timedelta(seconds=90)
    m = hb.check_missed("nightly", now=now)
    assert "nightly" in repr(m)
    assert "overdue_by" in repr(m)
