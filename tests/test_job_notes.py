"""Tests for cronwrap.job_notes and cronwrap.notes_cli."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.job_notes import JobNotes, NoteEntry, NotesError
from cronwrap.notes_cli import build_parser, main


def _make(tmp_path) -> JobNotes:
    return JobNotes(str(tmp_path / "notes"))


# ---------------------------------------------------------------------------
# NoteEntry unit tests
# ---------------------------------------------------------------------------

def test_entry_to_dict_required_keys():
    e = NoteEntry(job_name="backup", text="looks good")
    d = e.to_dict()
    assert d["job_name"] == "backup"
    assert d["text"] == "looks good"
    assert "timestamp" in d
    assert "author" not in d


def test_entry_to_dict_includes_author_when_set():
    e = NoteEntry(job_name="backup", text="ok", author="alice")
    assert e.to_dict()["author"] == "alice"


def test_entry_roundtrip():
    e = NoteEntry(job_name="job1", text="hello", author="bob", timestamp="2024-01-01T00:00:00+00:00")
    assert NoteEntry.from_dict(e.to_dict()).text == "hello"
    assert NoteEntry.from_dict(e.to_dict()).author == "bob"


# ---------------------------------------------------------------------------
# JobNotes store tests
# ---------------------------------------------------------------------------

def test_add_creates_file(tmp_path):
    store = _make(tmp_path)
    store.add(NoteEntry(job_name="j", text="first"))
    notes_file = tmp_path / "notes" / "j.notes.json"
    assert notes_file.exists()


def test_list_empty_returns_empty(tmp_path):
    store = _make(tmp_path)
    assert store.list_notes("unknown") == []


def test_add_and_list(tmp_path):
    store = _make(tmp_path)
    store.add(NoteEntry(job_name="j", text="note1"))
    store.add(NoteEntry(job_name="j", text="note2"))
    notes = store.list_notes("j")
    assert len(notes) == 2
    assert notes[0].text == "note1"
    assert notes[1].text == "note2"


def test_clear_removes_all(tmp_path):
    store = _make(tmp_path)
    store.add(NoteEntry(job_name="j", text="a"))
    store.add(NoteEntry(job_name="j", text="b"))
    count = store.clear("j")
    assert count == 2
    assert store.list_notes("j") == []


def test_remove_by_index(tmp_path):
    store = _make(tmp_path)
    store.add(NoteEntry(job_name="j", text="keep"))
    store.add(NoteEntry(job_name="j", text="drop"))
    removed = store.remove_by_index("j", 1)
    assert removed.text == "drop"
    assert len(store.list_notes("j")) == 1


def test_remove_invalid_index_raises(tmp_path):
    store = _make(tmp_path)
    store.add(NoteEntry(job_name="j", text="only"))
    with pytest.raises(NotesError):
        store.remove_by_index("j", 5)


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

def _run(tmp_path, *args):
    notes_dir = str(tmp_path / "notes")
    return main(["--notes-dir", notes_dir, *args])


def test_build_parser_returns_parser():
    assert build_parser() is not None


def test_no_command_returns_1(tmp_path):
    assert _run(tmp_path) == 1


def test_add_command_returns_0(tmp_path):
    assert _run(tmp_path, "add", "myjob", "some note") == 0


def test_list_command_returns_0(tmp_path):
    _run(tmp_path, "add", "myjob", "hello")
    assert _run(tmp_path, "list", "myjob") == 0


def test_list_empty_returns_0(tmp_path):
    assert _run(tmp_path, "list", "ghost") == 0


def test_clear_command_returns_0(tmp_path):
    _run(tmp_path, "add", "myjob", "x")
    assert _run(tmp_path, "clear", "myjob") == 0


def test_remove_invalid_index_returns_2(tmp_path):
    _run(tmp_path, "add", "myjob", "only")
    assert _run(tmp_path, "remove", "myjob", "99") == 2
