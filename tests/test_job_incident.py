"""Tests for cronwrap.job_incident and cronwrap.incident_cli."""
from __future__ import annotations

import json

import pytest

from cronwrap.job_incident import IncidentError, IncidentRecord, JobIncident
from cronwrap.incident_cli import build_parser, main


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make(tmp_path):
    return JobIncident(str(tmp_path))


# ---------------------------------------------------------------------------
# IncidentRecord
# ---------------------------------------------------------------------------

def test_record_to_dict_required_keys():
    rec = IncidentRecord(job_name="j", incident_id="abc", opened_at="2024-01-01T00:00:00+00:00", status="open")
    d = rec.to_dict()
    assert set(d.keys()) == {"job_name", "incident_id", "opened_at", "status"}


def test_record_to_dict_includes_optional_when_set():
    rec = IncidentRecord(
        job_name="j", incident_id="abc", opened_at="ts", status="resolved",
        reason="timeout", resolved_at="ts2", extra={"host": "x"}
    )
    d = rec.to_dict()
    assert d["reason"] == "timeout"
    assert d["resolved_at"] == "ts2"
    assert d["extra"] == {"host": "x"}


def test_record_roundtrip():
    rec = IncidentRecord(
        job_name="backup", incident_id="id1", opened_at="ts", status="open",
        reason="exit 1"
    )
    assert IncidentRecord.from_dict(rec.to_dict()).reason == "exit 1"


# ---------------------------------------------------------------------------
# JobIncident
# ---------------------------------------------------------------------------

def test_open_creates_record(tmp_path):
    store = _make(tmp_path)
    rec = store.open("myjob", reason="nonzero exit")
    assert rec.status == "open"
    assert rec.job_name == "myjob"
    assert rec.incident_id


def test_open_persists_to_disk(tmp_path):
    store = _make(tmp_path)
    rec = store.open("myjob")
    path = tmp_path / "myjob.incidents.json"
    data = json.loads(path.read_text())
    assert len(data) == 1
    assert data[0]["incident_id"] == rec.incident_id


def test_list_all_returns_all_records(tmp_path):
    store = _make(tmp_path)
    store.open("j")
    store.open("j", reason="again")
    assert len(store.list_all("j")) == 2


def test_list_open_filters_resolved(tmp_path):
    store = _make(tmp_path)
    r1 = store.open("j")
    store.open("j")
    store.resolve("j", r1.incident_id)
    assert len(store.list_open("j")) == 1


def test_resolve_updates_status(tmp_path):
    store = _make(tmp_path)
    rec = store.open("j")
    resolved = store.resolve("j", rec.incident_id)
    assert resolved.status == "resolved"
    assert resolved.resolved_at is not None


def test_resolve_unknown_id_raises(tmp_path):
    store = _make(tmp_path)
    store.open("j")
    with pytest.raises(IncidentError):
        store.resolve("j", "no-such-id")


def test_resolve_already_resolved_raises(tmp_path):
    store = _make(tmp_path)
    rec = store.open("j")
    store.resolve("j", rec.incident_id)
    with pytest.raises(IncidentError):
        store.resolve("j", rec.incident_id)


def test_list_open_empty_when_no_file(tmp_path):
    store = _make(tmp_path)
    assert store.list_open("ghost") == []


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _run(tmp_path, *args):
    return main(["--state-dir", str(tmp_path), *args])


def test_build_parser_returns_parser():
    assert build_parser() is not None


def test_no_command_returns_1(tmp_path):
    assert _run(tmp_path) == 1


def test_cli_open_returns_0(tmp_path):
    assert _run(tmp_path, "open", "myjob") == 0


def test_cli_list_text(tmp_path, capsys):
    _run(tmp_path, "open", "myjob", "--reason", "boom")
    assert _run(tmp_path, "list", "myjob") == 0
    out = capsys.readouterr().out
    assert "OPEN" in out


def test_cli_list_json(tmp_path, capsys):
    _run(tmp_path, "open", "myjob")
    assert _run(tmp_path, "list", "myjob", "--format", "json") == 0
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list)
    assert data[0]["status"] == "open"


def test_cli_resolve_returns_0(tmp_path, capsys):
    _run(tmp_path, "open", "myjob")
    store = JobIncident(str(tmp_path))
    rec = store.list_open("myjob")[0]
    assert _run(tmp_path, "resolve", "myjob", rec.incident_id) == 0


def test_cli_resolve_bad_id_returns_2(tmp_path):
    _run(tmp_path, "open", "myjob")
    assert _run(tmp_path, "resolve", "myjob", "no-such-id") == 2
