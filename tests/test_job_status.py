"""Tests for cronwrap.job_status."""
import time

import pytest

from cronwrap.job_status import (
    STATUS_FAILURE,
    STATUS_RUNNING,
    STATUS_SUCCESS,
    STATUS_UNKNOWN,
    JobStatusStore,
    StatusEntry,
    StatusError,
)


def _make_store(tmp_path):
    return JobStatusStore(state_dir=str(tmp_path / "status"))


# ---------------------------------------------------------------------------
# StatusEntry
# ---------------------------------------------------------------------------

def test_entry_to_dict_required_keys():
    e = StatusEntry(job_name="backup", status=STATUS_SUCCESS)
    d = e.to_dict()
    assert d["job_name"] == "backup"
    assert d["status"] == STATUS_SUCCESS
    assert "updated_at" in d


def test_entry_to_dict_omits_message_when_none():
    e = StatusEntry(job_name="backup", status=STATUS_SUCCESS)
    assert "message" not in e.to_dict()


def test_entry_to_dict_includes_message_when_set():
    e = StatusEntry(job_name="backup", status=STATUS_FAILURE, message="exit 1")
    assert e.to_dict()["message"] == "exit 1"


def test_entry_roundtrip():
    original = StatusEntry(job_name="sync", status=STATUS_RUNNING, message="pid 42")
    restored = StatusEntry.from_dict(original.to_dict())
    assert restored.job_name == original.job_name
    assert restored.status == original.status
    assert restored.message == original.message
    assert abs(restored.updated_at - original.updated_at) < 0.01


def test_entry_updated_at_auto_set():
    before = time.time()
    e = StatusEntry(job_name="x", status=STATUS_UNKNOWN)
    after = time.time()
    assert before <= e.updated_at <= after


# ---------------------------------------------------------------------------
# JobStatusStore
# ---------------------------------------------------------------------------

def test_get_unknown_when_no_file(tmp_path):
    store = _make_store(tmp_path)
    entry = store.get("nonexistent")
    assert entry.status == STATUS_UNKNOWN
    assert entry.job_name == "nonexistent"


def test_set_and_get_roundtrip(tmp_path):
    store = _make_store(tmp_path)
    store.set("daily-backup", STATUS_SUCCESS, message="ok")
    entry = store.get("daily-backup")
    assert entry.status == STATUS_SUCCESS
    assert entry.message == "ok"


def test_set_invalid_status_raises(tmp_path):
    store = _make_store(tmp_path)
    with pytest.raises(StatusError):
        store.set("job", "bogus")


def test_set_persists_to_disk(tmp_path):
    store = _make_store(tmp_path)
    store.set("myjob", STATUS_RUNNING)
    # New store instance reads same file
    store2 = JobStatusStore(state_dir=str(tmp_path / "status"))
    assert store2.get("myjob").status == STATUS_RUNNING


def test_all_returns_all_entries(tmp_path):
    store = _make_store(tmp_path)
    store.set("job-a", STATUS_SUCCESS)
    store.set("job-b", STATUS_FAILURE)
    entries = store.all()
    names = {e.job_name for e in entries}
    assert names == {"job-a", "job-b"}


def test_all_empty_when_no_entries(tmp_path):
    store = _make_store(tmp_path)
    assert store.all() == []


def test_delete_existing_returns_true(tmp_path):
    store = _make_store(tmp_path)
    store.set("job-x", STATUS_SUCCESS)
    assert store.delete("job-x") is True
    assert store.get("job-x").status == STATUS_UNKNOWN


def test_delete_nonexistent_returns_false(tmp_path):
    store = _make_store(tmp_path)
    assert store.delete("ghost") is False


def test_set_overwrites_previous(tmp_path):
    store = _make_store(tmp_path)
    store.set("job", STATUS_RUNNING)
    store.set("job", STATUS_SUCCESS, message="done")
    entry = store.get("job")
    assert entry.status == STATUS_SUCCESS
    assert entry.message == "done"
