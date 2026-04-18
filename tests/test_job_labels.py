"""Tests for cronwrap.job_labels."""
import pytest
from pathlib import Path
from cronwrap.job_labels import JobLabels, LabelError


def _make_labels(tmp_path: Path) -> JobLabels:
    return JobLabels(tmp_path / "labels.json")


def test_set_and_get(tmp_path):
    jl = _make_labels(tmp_path)
    jl.set("backup", "env", "prod")
    assert jl.get("backup", "env") == "prod"


def test_get_missing_returns_none(tmp_path):
    jl = _make_labels(tmp_path)
    assert jl.get("nonexistent", "key") is None


def test_set_persists_across_instances(tmp_path):
    p = tmp_path / "labels.json"
    jl1 = JobLabels(p)
    jl1.set("sync", "team", "infra")
    jl2 = JobLabels(p)
    assert jl2.get("sync", "team") == "infra"


def test_remove_existing_label(tmp_path):
    jl = _make_labels(tmp_path)
    jl.set("job", "k", "v")
    assert jl.remove("job", "k") is True
    assert jl.get("job", "k") is None


def test_remove_nonexistent_returns_false(tmp_path):
    jl = _make_labels(tmp_path)
    assert jl.remove("job", "missing") is False


def test_remove_last_label_cleans_job_entry(tmp_path):
    jl = _make_labels(tmp_path)
    jl.set("job", "only", "1")
    jl.remove("job", "only")
    assert "job" not in jl.to_dict()


def test_labels_for(tmp_path):
    jl = _make_labels(tmp_path)
    jl.set("job", "a", "1")
    jl.set("job", "b", "2")
    assert jl.labels_for("job") == {"a": "1", "b": "2"}


def test_labels_for_unknown_job(tmp_path):
    jl = _make_labels(tmp_path)
    assert jl.labels_for("ghost") == {}


def test_jobs_with_label_key_only(tmp_path):
    jl = _make_labels(tmp_path)
    jl.set("a", "env", "prod")
    jl.set("b", "env", "staging")
    jl.set("c", "team", "infra")
    assert jl.jobs_with_label("env") == ["a", "b"]


def test_jobs_with_label_key_and_value(tmp_path):
    jl = _make_labels(tmp_path)
    jl.set("a", "env", "prod")
    jl.set("b", "env", "staging")
    assert jl.jobs_with_label("env", "prod") == ["a"]


def test_set_empty_key_raises(tmp_path):
    jl = _make_labels(tmp_path)
    with pytest.raises(LabelError):
        jl.set("job", "", "value")


def test_set_empty_job_raises(tmp_path):
    jl = _make_labels(tmp_path)
    with pytest.raises(LabelError):
        jl.set("", "key", "value")


def test_to_dict_roundtrip(tmp_path):
    jl = _make_labels(tmp_path)
    jl.set("j", "x", "y")
    d = jl.to_dict()
    assert d == {"j": {"x": "y"}}
