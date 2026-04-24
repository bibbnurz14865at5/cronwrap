"""Tests for cronwrap.job_correlation."""
import pytest

from cronwrap.job_correlation import CorrelationRecord, CorrelationError, JobCorrelation


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make(tmp_path) -> JobCorrelation:
    return JobCorrelation(str(tmp_path / "corr"))


# ---------------------------------------------------------------------------
# CorrelationRecord
# ---------------------------------------------------------------------------

def test_record_to_dict_required_keys():
    r = CorrelationRecord(job_name="backup", correlation_id="abc-123")
    d = r.to_dict()
    assert d["job_name"] == "backup"
    assert d["correlation_id"] == "abc-123"


def test_record_to_dict_omits_parent_when_none():
    r = CorrelationRecord(job_name="backup", correlation_id="abc-123")
    assert "parent_id" not in r.to_dict()


def test_record_to_dict_includes_parent_when_set():
    r = CorrelationRecord(job_name="backup", correlation_id="abc-123", parent_id="parent-999")
    assert r.to_dict()["parent_id"] == "parent-999"


def test_record_to_dict_omits_extra_when_empty():
    r = CorrelationRecord(job_name="backup", correlation_id="abc-123")
    assert "extra" not in r.to_dict()


def test_record_to_dict_includes_extra_when_set():
    r = CorrelationRecord(job_name="backup", correlation_id="abc-123", extra={"trace": "xyz"})
    assert r.to_dict()["extra"] == {"trace": "xyz"}


def test_record_roundtrip():
    r = CorrelationRecord(job_name="sync", correlation_id="id-1", parent_id="id-0", extra={"env": "prod"})
    assert CorrelationRecord.from_dict(r.to_dict()) == r


# ---------------------------------------------------------------------------
# JobCorrelation
# ---------------------------------------------------------------------------

def test_generate_returns_record(tmp_path):
    jc = _make(tmp_path)
    rec = jc.generate("nightly")
    assert rec.job_name == "nightly"
    assert len(rec.correlation_id) == 36  # UUID4


def test_generate_persists_to_disk(tmp_path):
    jc = _make(tmp_path)
    jc.generate("nightly")
    assert jc.get("nightly") is not None


def test_get_returns_none_when_absent(tmp_path):
    jc = _make(tmp_path)
    assert jc.get("unknown") is None


def test_generate_with_parent_id(tmp_path):
    jc = _make(tmp_path)
    rec = jc.generate("child_job", parent_id="parent-abc")
    stored = jc.get("child_job")
    assert stored is not None
    assert stored.parent_id == "parent-abc"


def test_generate_with_extra(tmp_path):
    jc = _make(tmp_path)
    jc.generate("etl", extra={"region": "us-east-1"})
    stored = jc.get("etl")
    assert stored.extra == {"region": "us-east-1"}


def test_clear_removes_record(tmp_path):
    jc = _make(tmp_path)
    jc.generate("cleanup")
    jc.clear("cleanup")
    assert jc.get("cleanup") is None


def test_clear_nonexistent_is_noop(tmp_path):
    jc = _make(tmp_path)
    jc.clear("ghost")  # should not raise


def test_all_records_empty(tmp_path):
    jc = _make(tmp_path)
    assert jc.all_records() == []


def test_all_records_returns_all(tmp_path):
    jc = _make(tmp_path)
    jc.generate("alpha")
    jc.generate("beta")
    names = [r.job_name for r in jc.all_records()]
    assert sorted(names) == ["alpha", "beta"]


def test_generate_overwrites_previous(tmp_path):
    jc = _make(tmp_path)
    first = jc.generate("daily")
    second = jc.generate("daily")
    assert first.correlation_id != second.correlation_id
    assert jc.get("daily").correlation_id == second.correlation_id


def test_job_name_with_slash_is_safe(tmp_path):
    jc = _make(tmp_path)
    jc.generate("jobs/nightly/backup")
    assert jc.get("jobs/nightly/backup") is not None
