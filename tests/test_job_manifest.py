"""Tests for cronwrap.job_manifest."""
import json
import pytest

from cronwrap.job_manifest import JobManifest, ManifestEntry, ManifestError


def _make(tmp_path):
    return JobManifest(str(tmp_path / "manifest.json"))


def _entry(**kwargs) -> ManifestEntry:
    defaults = {"job_name": "backup", "command": "backup.sh"}
    defaults.update(kwargs)
    return ManifestEntry(**defaults)


def test_entry_to_dict_required_keys():
    e = _entry()
    d = e.to_dict()
    assert d["job_name"] == "backup"
    assert d["command"] == "backup.sh"


def test_entry_to_dict_omits_optional_when_none():
    e = _entry()
    d = e.to_dict()
    assert "schedule" not in d
    assert "owner" not in d
    assert "description" not in d
    assert "tags" not in d


def test_entry_to_dict_includes_optional_when_set():
    e = _entry(schedule="0 * * * *", owner="ops", tags=["infra"], description="nightly")
    d = e.to_dict()
    assert d["schedule"] == "0 * * * *"
    assert d["owner"] == "ops"
    assert d["tags"] == ["infra"]
    assert d["description"] == "nightly"


def test_entry_roundtrip():
    e = _entry(schedule="0 2 * * *", owner="alice", tags=["db", "backup"])
    assert ManifestEntry.from_dict(e.to_dict()).to_dict() == e.to_dict()


def test_from_dict_missing_job_name_raises():
    with pytest.raises(ManifestError, match="job_name"):
        ManifestEntry.from_dict({"command": "x.sh"})


def test_from_dict_missing_command_raises():
    with pytest.raises(ManifestError, match="command"):
        ManifestEntry.from_dict({"job_name": "x"})


def test_register_persists(tmp_path):
    m = _make(tmp_path)
    m.register(_entry())
    m2 = JobManifest(str(tmp_path / "manifest.json"))
    assert m2.get("backup") is not None


def test_register_overwrites_existing(tmp_path):
    m = _make(tmp_path)
    m.register(_entry(command="old.sh"))
    m.register(_entry(command="new.sh"))
    assert m.get("backup").command == "new.sh"


def test_get_missing_returns_none(tmp_path):
    m = _make(tmp_path)
    assert m.get("nonexistent") is None


def test_remove_existing(tmp_path):
    m = _make(tmp_path)
    m.register(_entry())
    m.remove("backup")
    assert m.get("backup") is None


def test_remove_missing_raises(tmp_path):
    m = _make(tmp_path)
    with pytest.raises(ManifestError, match="not found"):
        m.remove("ghost")


def test_all_entries_sorted(tmp_path):
    m = _make(tmp_path)
    m.register(ManifestEntry(job_name="zzz", command="z.sh"))
    m.register(ManifestEntry(job_name="aaa", command="a.sh"))
    names = [e.job_name for e in m.all_entries()]
    assert names == sorted(names)


def test_all_entries_empty(tmp_path):
    m = _make(tmp_path)
    assert m.all_entries() == []


def test_to_dict_structure(tmp_path):
    m = _make(tmp_path)
    m.register(_entry())
    d = m.to_dict()
    assert "backup" in d
    assert d["backup"]["command"] == "backup.sh"


def test_persists_to_valid_json(tmp_path):
    path = tmp_path / "manifest.json"
    m = JobManifest(str(path))
    m.register(_entry(schedule="*/5 * * * *"))
    with open(path) as fh:
        data = json.load(fh)
    assert "backup" in data
