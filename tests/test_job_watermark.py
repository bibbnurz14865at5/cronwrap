"""Tests for cronwrap.job_watermark."""
import pytest

from cronwrap.job_watermark import JobWatermark, WatermarkError, WatermarkRecord


TS = "2024-06-01T12:00:00"
TS2 = "2024-06-02T08:00:00"


def _make(tmp_path):
    return JobWatermark(state_dir=str(tmp_path / "watermarks"))


def test_record_to_dict_required_keys():
    rec = WatermarkRecord(job_name="backup", max_duration=42.5, recorded_at=TS)
    d = rec.to_dict()
    assert d["job_name"] == "backup"
    assert d["max_duration"] == 42.5
    assert d["recorded_at"] == TS
    assert "extra" not in d


def test_record_to_dict_includes_extra_when_set():
    rec = WatermarkRecord(job_name="j", max_duration=1.0, recorded_at=TS,
                          extra={"host": "srv1"})
    assert rec.to_dict()["extra"] == {"host": "srv1"}


def test_record_roundtrip():
    rec = WatermarkRecord(job_name="sync", max_duration=99.9, recorded_at=TS,
                          extra={"env": "prod"})
    assert WatermarkRecord.from_dict(rec.to_dict()).to_dict() == rec.to_dict()


def test_get_returns_none_when_no_record(tmp_path):
    wm = _make(tmp_path)
    assert wm.get("nonexistent") is None


def test_update_creates_record(tmp_path):
    wm = _make(tmp_path)
    rec = wm.update("backup", 30.0, TS)
    assert rec.job_name == "backup"
    assert rec.max_duration == 30.0


def test_update_persists_to_disk(tmp_path):
    wm = _make(tmp_path)
    wm.update("backup", 30.0, TS)
    wm2 = JobWatermark(state_dir=str(tmp_path / "watermarks"))
    rec = wm2.get("backup")
    assert rec is not None
    assert rec.max_duration == 30.0


def test_update_replaces_when_higher(tmp_path):
    wm = _make(tmp_path)
    wm.update("backup", 30.0, TS)
    rec = wm.update("backup", 55.0, TS2)
    assert rec.max_duration == 55.0
    assert wm.get("backup").max_duration == 55.0


def test_update_keeps_existing_when_lower(tmp_path):
    wm = _make(tmp_path)
    wm.update("backup", 50.0, TS)
    rec = wm.update("backup", 20.0, TS2)
    assert rec.max_duration == 50.0
    assert wm.get("backup").max_duration == 50.0


def test_update_stores_extra(tmp_path):
    wm = _make(tmp_path)
    wm.update("backup", 10.0, TS, extra={"host": "box1"})
    rec = wm.get("backup")
    assert rec.extra == {"host": "box1"}


def test_reset_removes_record(tmp_path):
    wm = _make(tmp_path)
    wm.update("backup", 10.0, TS)
    wm.reset("backup")
    assert wm.get("backup") is None


def test_reset_raises_when_no_record(tmp_path):
    wm = _make(tmp_path)
    with pytest.raises(WatermarkError):
        wm.reset("ghost")
