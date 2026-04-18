"""Tests for cronwrap.job_annotations."""
import json
import pytest
from cronwrap.job_annotations import JobAnnotations, AnnotationError


def _make(tmp_path, job="myjob"):
    return JobAnnotations(str(tmp_path), job)


def test_set_and_get(tmp_path):
    a = _make(tmp_path)
    a.set("owner", "alice")
    assert a.get("owner") == "alice"


def test_get_missing_returns_none(tmp_path):
    a = _make(tmp_path)
    assert a.get("nonexistent") is None


def test_set_persists_across_instances(tmp_path):
    _make(tmp_path).set("env", "prod")
    assert _make(tmp_path).get("env") == "prod"


def test_remove_existing(tmp_path):
    a = _make(tmp_path)
    a.set("k", "v")
    assert a.remove("k") is True
    assert a.get("k") is None


def test_remove_missing_returns_false(tmp_path):
    a = _make(tmp_path)
    assert a.remove("ghost") is False


def test_all_returns_dict(tmp_path):
    a = _make(tmp_path)
    a.set("a", "1")
    a.set("b", "2")
    assert a.all() == {"a": "1", "b": "2"}


def test_keys(tmp_path):
    a = _make(tmp_path)
    a.set("x", "1")
    a.set("y", "2")
    assert sorted(a.keys()) == ["x", "y"]


def test_clear(tmp_path):
    a = _make(tmp_path)
    a.set("x", "1")
    a.clear()
    assert a.all() == {}


def test_to_dict_keys(tmp_path):
    a = _make(tmp_path, job="backup")
    a.set("tier", "gold")
    d = a.to_dict()
    assert d["job"] == "backup"
    assert d["annotations"]["tier"] == "gold"


def test_corrupt_file_raises(tmp_path):
    a = _make(tmp_path)
    path = tmp_path / "myjob.annotations.json"
    path.write_text("not json")
    with pytest.raises(AnnotationError):
        a.get("key")


def test_multiple_jobs_isolated(tmp_path):
    a = _make(tmp_path, "job_a")
    b = _make(tmp_path, "job_b")
    a.set("k", "from_a")
    assert b.get("k") is None
