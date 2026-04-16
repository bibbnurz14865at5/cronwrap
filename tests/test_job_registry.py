"""Tests for cronwrap.job_registry."""
import json
import pytest
from pathlib import Path
from cronwrap.job_registry import JobEntry, JobRegistry, RegistryError


def _entry(**kwargs) -> JobEntry:
    defaults = dict(name="backup", schedule="0 2 * * *", command="/usr/bin/backup.sh")
    defaults.update(kwargs)
    return JobEntry(**defaults)


def test_entry_to_dict_keys():
    e = _entry()
    d = e.to_dict()
    assert set(d) == {"name", "schedule", "command", "tags", "description", "enabled"}


def test_entry_roundtrip():
    e = _entry(tags=["infra"], description="nightly backup", enabled=False)
    assert JobEntry.from_dict(e.to_dict()) == e


def test_entry_from_dict_defaults():
    e = JobEntry.from_dict({"name": "x", "schedule": "* * * * *", "command": "echo hi"})
    assert e.tags == []
    assert e.description == ""
    assert e.enabled is True


def test_register_persists(tmp_path):
    reg = JobRegistry(tmp_path / "registry.json")
    reg.register(_entry())
    data = json.loads((tmp_path / "registry.json").read_text())
    assert len(data["jobs"]) == 1
    assert data["jobs"][0]["name"] == "backup"


def test_registry_loads_existing(tmp_path):
    p = tmp_path / "registry.json"
    reg = JobRegistry(p)
    reg.register(_entry(name="job1"))
    reg2 = JobRegistry(p)
    assert reg2.get("job1") is not None


def test_all_jobs(tmp_path):
    reg = JobRegistry(tmp_path / "r.json")
    reg.register(_entry(name="a"))
    reg.register(_entry(name="b"))
    assert len(reg.all_jobs()) == 2


def test_enabled_jobs_filters(tmp_path):
    reg = JobRegistry(tmp_path / "r.json")
    reg.register(_entry(name="on", enabled=True))
    reg.register(_entry(name="off", enabled=False))
    enabled = reg.enabled_jobs()
    assert len(enabled) == 1
    assert enabled[0].name == "on"


def test_unregister(tmp_path):
    reg = JobRegistry(tmp_path / "r.json")
    reg.register(_entry(name="gone"))
    reg.unregister("gone")
    assert reg.get("gone") is None


def test_unregister_missing_raises(tmp_path):
    reg = JobRegistry(tmp_path / "r.json")
    with pytest.raises(RegistryError, match="not found"):
        reg.unregister("nope")


def test_register_overwrites(tmp_path):
    reg = JobRegistry(tmp_path / "r.json")
    reg.register(_entry(name="j", schedule="0 1 * * *"))
    reg.register(_entry(name="j", schedule="0 3 * * *"))
    assert reg.get("j").schedule == "0 3 * * *"
    assert len(reg.all_jobs()) == 1
