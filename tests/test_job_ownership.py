"""Tests for cronwrap.job_ownership and cronwrap.ownership_cli."""

from __future__ import annotations

from pathlib import Path

import pytest

from cronwrap.job_ownership import JobOwnership, OwnerRecord, OwnershipError
from cronwrap.ownership_cli import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make(tmp_path: Path) -> JobOwnership:
    return JobOwnership(tmp_path / "ownership.json")


def _rec(job="backup", owner="alice", team="ops", email="alice@example.com") -> OwnerRecord:
    return OwnerRecord(job_name=job, owner=owner, team=team, email=email)


# ---------------------------------------------------------------------------
# OwnerRecord
# ---------------------------------------------------------------------------

def test_to_dict_required_keys():
    r = OwnerRecord(job_name="job", owner="bob")
    d = r.to_dict()
    assert d["job_name"] == "job"
    assert d["owner"] == "bob"
    assert "team" not in d
    assert "email" not in d


def test_to_dict_optional_keys_included():
    r = _rec()
    d = r.to_dict()
    assert d["team"] == "ops"
    assert d["email"] == "alice@example.com"


def test_roundtrip():
    r = _rec()
    assert OwnerRecord.from_dict(r.to_dict()) == r


# ---------------------------------------------------------------------------
# JobOwnership
# ---------------------------------------------------------------------------

def test_set_and_get(tmp_path):
    store = _make(tmp_path)
    store.set(_rec())
    got = store.get("backup")
    assert got is not None
    assert got.owner == "alice"


def test_get_missing_returns_none(tmp_path):
    store = _make(tmp_path)
    assert store.get("nonexistent") is None


def test_set_persists_across_instances(tmp_path):
    p = tmp_path / "ownership.json"
    JobOwnership(p).set(_rec())
    assert JobOwnership(p).get("backup").owner == "alice"


def test_remove_existing(tmp_path):
    store = _make(tmp_path)
    store.set(_rec())
    store.remove("backup")
    assert store.get("backup") is None


def test_remove_missing_raises(tmp_path):
    store = _make(tmp_path)
    with pytest.raises(OwnershipError):
        store.remove("ghost")


def test_jobs_for_team(tmp_path):
    store = _make(tmp_path)
    store.set(OwnerRecord("job-a", "alice", team="ops"))
    store.set(OwnerRecord("job-b", "bob", team="dev"))
    store.set(OwnerRecord("job-c", "carol", team="ops"))
    assert store.jobs_for_team("ops") == ["job-a", "job-c"]


def test_all_records_sorted(tmp_path):
    store = _make(tmp_path)
    store.set(OwnerRecord("zzz", "z"))
    store.set(OwnerRecord("aaa", "a"))
    names = [r.job_name for r in store.all_records()]
    assert names == ["aaa", "zzz"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _run(tmp_path, *args):
    store = str(tmp_path / "ownership.json")
    return main(["--store", store, *args])


def test_no_command_returns_1(tmp_path):
    assert _run(tmp_path) == 1


def test_set_command_returns_0(tmp_path):
    assert _run(tmp_path, "set", "myjob", "dave", "--team", "sre") == 0


def test_get_command_returns_0(tmp_path):
    _run(tmp_path, "set", "myjob", "dave")
    assert _run(tmp_path, "get", "myjob") == 0


def test_get_missing_returns_1(tmp_path):
    assert _run(tmp_path, "get", "ghost") == 1


def test_remove_command_returns_0(tmp_path):
    _run(tmp_path, "set", "myjob", "dave")
    assert _run(tmp_path, "remove", "myjob") == 0


def test_remove_missing_returns_1(tmp_path):
    assert _run(tmp_path, "remove", "ghost") == 1


def test_team_command_returns_0(tmp_path):
    _run(tmp_path, "set", "j1", "alice", "--team", "ops")
    assert _run(tmp_path, "team", "ops") == 0


def test_list_command_returns_0(tmp_path):
    assert _run(tmp_path, "list") == 0
