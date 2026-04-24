"""Tests for cronwrap.job_baseline."""
import json
import pytest
from cronwrap.job_baseline import BaselineError, BaselineRecord, JobBaseline


# ---------------------------------------------------------------------------
# BaselineRecord unit tests
# ---------------------------------------------------------------------------

def test_record_to_dict_keys():
    rec = BaselineRecord(job_name="myjob", durations=[1.0, 2.0], window=5)
    d = rec.to_dict()
    assert set(d.keys()) == {"job_name", "durations", "window"}


def test_record_roundtrip():
    rec = BaselineRecord(job_name="myjob", durations=[10.0, 20.0], window=10)
    assert BaselineRecord.from_dict(rec.to_dict()).durations == [10.0, 20.0]


def test_median_empty():
    rec = BaselineRecord(job_name="x")
    assert rec.median is None


def test_median_odd():
    rec = BaselineRecord(job_name="x", durations=[1.0, 3.0, 2.0])
    assert rec.median == 2.0


def test_median_even():
    rec = BaselineRecord(job_name="x", durations=[1.0, 2.0, 3.0, 4.0])
    assert rec.median == 2.5


def test_is_anomalous_no_baseline():
    rec = BaselineRecord(job_name="x")
    assert rec.is_anomalous(999.0) is False


def test_is_anomalous_false_within_factor():
    rec = BaselineRecord(job_name="x", durations=[10.0, 10.0, 10.0])
    assert rec.is_anomalous(15.0, factor=2.0) is False


def test_is_anomalous_true_exceeds_factor():
    rec = BaselineRecord(job_name="x", durations=[10.0, 10.0, 10.0])
    assert rec.is_anomalous(25.0, factor=2.0) is True


def test_record_trims_to_window():
    rec = BaselineRecord(job_name="x", window=3)
    for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
        rec.record(v)
    assert rec.durations == [3.0, 4.0, 5.0]


# ---------------------------------------------------------------------------
# JobBaseline integration tests
# ---------------------------------------------------------------------------

def _make(tmp_path):
    return JobBaseline(state_dir=str(tmp_path / "baselines"))


def test_load_missing_returns_empty_record(tmp_path):
    bl = _make(tmp_path)
    rec = bl.load("unknown-job")
    assert rec.job_name == "unknown-job"
    assert rec.durations == []


def test_save_and_load_roundtrip(tmp_path):
    bl = _make(tmp_path)
    rec = BaselineRecord(job_name="myjob", durations=[5.0, 6.0], window=10)
    bl.save(rec)
    loaded = bl.load("myjob")
    assert loaded.durations == [5.0, 6.0]
    assert loaded.window == 10


def test_update_persists_duration(tmp_path):
    bl = _make(tmp_path)
    bl.update("etl", 30.0)
    bl.update("etl", 32.0)
    rec = bl.load("etl")
    assert rec.durations == [30.0, 32.0]


def test_update_returns_record(tmp_path):
    bl = _make(tmp_path)
    rec = bl.update("etl", 10.0)
    assert isinstance(rec, BaselineRecord)
    assert 10.0 in rec.durations


def test_corrupt_file_raises_baseline_error(tmp_path):
    bl = _make(tmp_path)
    p = (tmp_path / "baselines" / "bad.baseline.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("not-json")
    with pytest.raises(BaselineError):
        bl.load("bad")


def test_job_name_with_slashes(tmp_path):
    bl = _make(tmp_path)
    bl.update("team/nightly", 5.0)
    rec = bl.load("team/nightly")
    assert rec.durations == [5.0]


def test_state_dir_created_automatically(tmp_path):
    deep = tmp_path / "a" / "b" / "c"
    JobBaseline(state_dir=str(deep))
    assert deep.exists()
