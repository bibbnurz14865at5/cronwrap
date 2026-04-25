"""Tests for cronwrap.job_versioning and versioning_cli."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from cronwrap.job_versioning import JobVersioning, VersionRecord
from cronwrap.versioning_cli import build_parser, main


TS = "2024-06-01T12:00:00+00:00"


def _make(tmp_path) -> JobVersioning:
    return JobVersioning(str(tmp_path / "versions"))


def _rec(job="backup", version="1.0.0", **kw) -> VersionRecord:
    return VersionRecord(job_name=job, version=version, deployed_at=TS, **kw)


# --- VersionRecord ---

def test_to_dict_required_keys():
    d = _rec().to_dict()
    assert d["job_name"] == "backup"
    assert d["version"] == "1.0.0"
    assert d["deployed_at"] == TS


def test_to_dict_omits_optional_when_none():
    d = _rec().to_dict()
    assert "deployed_by" not in d
    assert "notes" not in d


def test_to_dict_includes_optional_when_set():
    d = _rec(deployed_by="alice", notes="hotfix").to_dict()
    assert d["deployed_by"] == "alice"
    assert d["notes"] == "hotfix"


def test_roundtrip():
    r = _rec(deployed_by="bob", notes="release")
    assert VersionRecord.from_dict(r.to_dict()).to_dict() == r.to_dict()


# --- JobVersioning ---

def test_current_none_when_no_records(tmp_path):
    store = _make(tmp_path)
    assert store.current("backup") is None


def test_record_and_current(tmp_path):
    store = _make(tmp_path)
    store.record(_rec(version="1.0.0"))
    cur = store.current("backup")
    assert cur is not None
    assert cur.version == "1.0.0"


def test_current_returns_latest(tmp_path):
    store = _make(tmp_path)
    store.record(_rec(version="1.0.0"))
    store.record(_rec(version="1.1.0"))
    assert store.current("backup").version == "1.1.0"


def test_history_ordered_oldest_first(tmp_path):
    store = _make(tmp_path)
    store.record(_rec(version="1.0.0"))
    store.record(_rec(version="2.0.0"))
    h = store.history("backup")
    assert len(h) == 2
    assert h[0].version == "1.0.0"
    assert h[1].version == "2.0.0"


def test_rollback_target_none_when_single_record(tmp_path):
    store = _make(tmp_path)
    store.record(_rec(version="1.0.0"))
    assert store.rollback_target("backup") is None


def test_rollback_target_returns_previous(tmp_path):
    store = _make(tmp_path)
    store.record(_rec(version="1.0.0"))
    store.record(_rec(version="2.0.0"))
    rb = store.rollback_target("backup")
    assert rb.version == "1.0.0"


def test_history_empty_list_for_unknown_job(tmp_path):
    store = _make(tmp_path)
    assert store.history("nonexistent") == []


# --- CLI ---

def _run(tmp_path, *args):
    return main(["--state-dir", str(tmp_path / "v"), *args])


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1(tmp_path):
    assert _run(tmp_path) == 1


def test_cli_record_returns_0(tmp_path):
    assert _run(tmp_path, "record", "myjob", "3.2.1") == 0


def test_cli_current_returns_0_after_record(tmp_path, capsys):
    _run(tmp_path, "record", "myjob", "3.2.1")
    rc = _run(tmp_path, "current", "myjob")
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["version"] == "3.2.1"


def test_cli_current_returns_2_when_missing(tmp_path):
    assert _run(tmp_path, "current", "ghost") == 2


def test_cli_rollback_target_returns_2_when_only_one(tmp_path):
    _run(tmp_path, "record", "myjob", "1.0")
    assert _run(tmp_path, "rollback-target", "myjob") == 2


def test_cli_history_returns_0(tmp_path, capsys):
    _run(tmp_path, "record", "myjob", "1.0")
    rc = _run(tmp_path, "history", "myjob")
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert isinstance(out, list)
    assert out[0]["version"] == "1.0"
