"""Tests for cronwrap.job_metadata and cronwrap.metadata_cli."""
from __future__ import annotations

import json

import pytest

from cronwrap.job_metadata import JobMetadata, MetadataError
from cronwrap.metadata_cli import build_parser, main


def _make(tmp_path, job_name="backup"):
    return JobMetadata(job_name=job_name, state_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# JobMetadata unit tests
# ---------------------------------------------------------------------------

def test_set_and_get(tmp_path):
    m = _make(tmp_path)
    m.set("env", "production")
    assert m.get("env") == "production"


def test_get_missing_returns_none(tmp_path):
    m = _make(tmp_path)
    assert m.get("nonexistent") is None


def test_get_missing_returns_default(tmp_path):
    m = _make(tmp_path)
    assert m.get("nonexistent", "fallback") == "fallback"


def test_set_persists_across_instances(tmp_path):
    m1 = _make(tmp_path)
    m1.set("version", "1.2.3")
    m2 = _make(tmp_path)
    assert m2.get("version") == "1.2.3"


def test_remove_existing_key(tmp_path):
    m = _make(tmp_path)
    m.set("key", "val")
    m.remove("key")
    assert m.get("key") is None


def test_remove_absent_key_is_noop(tmp_path):
    m = _make(tmp_path)
    m.remove("ghost")  # should not raise


def test_all_returns_copy(tmp_path):
    m = _make(tmp_path)
    m.set("a", 1)
    m.set("b", 2)
    data = m.all()
    assert set(data.keys()) == {"a", "b"}
    data["c"] = 3
    assert m.get("c") is None  # original unaffected


def test_clear_removes_all(tmp_path):
    m = _make(tmp_path)
    m.set("x", "1")
    m.set("y", "2")
    m.clear()
    assert m.all() == {}


def test_set_empty_key_raises(tmp_path):
    m = _make(tmp_path)
    with pytest.raises(MetadataError):
        m.set("", "value")


def test_to_dict_keys(tmp_path):
    m = _make(tmp_path)
    m.set("region", "us-east-1")
    d = m.to_dict()
    assert "job_name" in d
    assert "metadata" in d
    assert d["metadata"]["region"] == "us-east-1"


def test_from_dict_roundtrip(tmp_path):
    original = _make(tmp_path)
    original.set("foo", "bar")
    d = original.to_dict()
    restored = JobMetadata.from_dict(d, state_dir=str(tmp_path / "restored"))
    assert restored.get("foo") == "bar"


def test_from_dict_missing_job_name_raises(tmp_path):
    with pytest.raises(MetadataError):
        JobMetadata.from_dict({"metadata": {}}, state_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

def _run(tmp_path, *args):
    return main(["--state-dir", str(tmp_path), *args])


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1(tmp_path):
    assert _run(tmp_path) == 1


def test_cli_set_and_get(tmp_path):
    assert _run(tmp_path, "set", "myjob", "owner", "alice") == 0
    assert _run(tmp_path, "get", "myjob", "owner") == 0


def test_cli_get_missing_returns_2(tmp_path, capsys):
    code = _run(tmp_path, "get", "myjob", "missing_key")
    assert code == 2


def test_cli_remove_returns_0(tmp_path):
    _run(tmp_path, "set", "myjob", "k", "v")
    assert _run(tmp_path, "remove", "myjob", "k") == 0


def test_cli_list_returns_json(tmp_path, capsys):
    _run(tmp_path, "set", "myjob", "env", "prod")
    assert _run(tmp_path, "list", "myjob") == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["env"] == "prod"


def test_cli_clear_returns_0(tmp_path):
    _run(tmp_path, "set", "myjob", "k", "v")
    assert _run(tmp_path, "clear", "myjob") == 0
