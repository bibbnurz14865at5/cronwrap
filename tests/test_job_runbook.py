"""Tests for cronwrap.job_runbook and cronwrap.runbook_cli."""
from __future__ import annotations

import pytest

from cronwrap.job_runbook import JobRunbook, RunbookEntry, RunbookError
from cronwrap.runbook_cli import build_parser, main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make(tmp_path) -> JobRunbook:
    return JobRunbook(str(tmp_path))


def _entry(**kwargs) -> RunbookEntry:
    defaults = {"job_name": "backup", "url": "https://wiki.example.com/backup", "notes": "See wiki.", "tags": ["infra"]}
    defaults.update(kwargs)
    return RunbookEntry(**defaults)


# ---------------------------------------------------------------------------
# RunbookEntry
# ---------------------------------------------------------------------------

def test_entry_to_dict_keys():
    e = _entry()
    d = e.to_dict()
    assert d["job_name"] == "backup"
    assert d["url"] == "https://wiki.example.com/backup"
    assert d["notes"] == "See wiki."
    assert d["tags"] == ["infra"]


def test_entry_to_dict_omits_optional_when_none():
    e = RunbookEntry(job_name="noop")
    d = e.to_dict()
    assert "url" not in d
    assert "notes" not in d
    assert "tags" not in d


def test_entry_roundtrip():
    e = _entry()
    assert RunbookEntry.from_dict(e.to_dict()).to_dict() == e.to_dict()


# ---------------------------------------------------------------------------
# JobRunbook
# ---------------------------------------------------------------------------

def test_get_missing_returns_none(tmp_path):
    rb = _make(tmp_path)
    assert rb.get("nonexistent") is None


def test_set_and_get(tmp_path):
    rb = _make(tmp_path)
    rb.set(_entry())
    result = rb.get("backup")
    assert result is not None
    assert result.url == "https://wiki.example.com/backup"


def test_set_persists_across_instances(tmp_path):
    _make(tmp_path).set(_entry())
    result = _make(tmp_path).get("backup")
    assert result is not None
    assert result.notes == "See wiki."


def test_remove_existing(tmp_path):
    rb = _make(tmp_path)
    rb.set(_entry())
    assert rb.remove("backup") is True
    assert rb.get("backup") is None


def test_remove_nonexistent_returns_false(tmp_path):
    rb = _make(tmp_path)
    assert rb.remove("ghost") is False


def test_all_entries_sorted(tmp_path):
    rb = _make(tmp_path)
    rb.set(RunbookEntry(job_name="zebra"))
    rb.set(RunbookEntry(job_name="alpha"))
    names = [e.job_name for e in rb.all_entries()]
    assert names == ["alpha", "zebra"]


def test_all_entries_empty(tmp_path):
    assert _make(tmp_path).all_entries() == []


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _run(tmp_path, *args):
    return main(["--state-dir", str(tmp_path), *args])


def test_build_parser_returns_parser():
    assert build_parser() is not None


def test_cli_set_returns_0(tmp_path):
    assert _run(tmp_path, "set", "myjob", "--url", "http://example.com") == 0


def test_cli_get_returns_0(tmp_path):
    _run(tmp_path, "set", "myjob", "--url", "http://example.com")
    assert _run(tmp_path, "get", "myjob") == 0


def test_cli_get_missing_returns_1(tmp_path):
    assert _run(tmp_path, "get", "ghost") == 1


def test_cli_remove_returns_0(tmp_path):
    _run(tmp_path, "set", "myjob")
    assert _run(tmp_path, "remove", "myjob") == 0


def test_cli_remove_missing_returns_1(tmp_path):
    assert _run(tmp_path, "remove", "ghost") == 1


def test_cli_list_returns_0(tmp_path):
    assert _run(tmp_path, "list") == 0


def test_cli_no_command_returns_1(tmp_path):
    assert _run(tmp_path) == 1
