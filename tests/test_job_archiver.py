"""Tests for cronwrap.job_archiver."""

from __future__ import annotations

import gzip
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from cronwrap.job_archiver import (
    ArchiveError,
    ArchivePolicy,
    ArchiveResult,
    archive_history,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _ts(days_ago: float) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.isoformat()


def _write_history(path: Path, entries: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        json.dump(entries, fh)


# ---------------------------------------------------------------------------
# ArchivePolicy
# ---------------------------------------------------------------------------

def test_from_dict_required_only():
    p = ArchivePolicy.from_dict(
        {"job_name": "j", "history_dir": "/h", "archive_dir": "/a"}
    )
    assert p.older_than_days == 30
    assert p.compress is True


def test_from_dict_custom():
    p = ArchivePolicy.from_dict(
        {"job_name": "j", "history_dir": "/h", "archive_dir": "/a",
         "older_than_days": 7, "compress": False}
    )
    assert p.older_than_days == 7
    assert p.compress is False


def test_from_dict_missing_raises():
    with pytest.raises(ArchiveError, match="Missing required keys"):
        ArchivePolicy.from_dict({"job_name": "j"})


def test_to_dict_roundtrip():
    data = {"job_name": "j", "history_dir": "/h", "archive_dir": "/a",
            "older_than_days": 14, "compress": True}
    assert ArchivePolicy.from_dict(data).to_dict() == data


# ---------------------------------------------------------------------------
# ArchiveResult
# ---------------------------------------------------------------------------

def test_archive_result_repr():
    r = ArchiveResult(archived=3, skipped=1, archive_path="/a/x.json.gz")
    assert "archived=3" in repr(r)
    assert "skipped=1" in repr(r)


# ---------------------------------------------------------------------------
# archive_history
# ---------------------------------------------------------------------------

def test_archive_no_history_file(tmp_path):
    p = ArchivePolicy.from_dict(
        {"job_name": "myjob", "history_dir": str(tmp_path / "h"),
         "archive_dir": str(tmp_path / "a")}
    )
    result = archive_history(p)
    assert result.archived == 0
    assert result.archive_path is None


def test_archive_nothing_old(tmp_path):
    history_dir = tmp_path / "h"
    entries = [{"timestamp": _ts(1), "success": True}]
    _write_history(history_dir / "myjob.json", entries)
    p = ArchivePolicy.from_dict(
        {"job_name": "myjob", "history_dir": str(history_dir),
         "archive_dir": str(tmp_path / "a")}
    )
    result = archive_history(p)
    assert result.archived == 0
    assert result.skipped == 1


def test_archive_old_entries_compressed(tmp_path):
    history_dir = tmp_path / "h"
    entries = [
        {"timestamp": _ts(60), "success": True},
        {"timestamp": _ts(1), "success": False},
    ]
    _write_history(history_dir / "myjob.json", entries)
    p = ArchivePolicy.from_dict(
        {"job_name": "myjob", "history_dir": str(history_dir),
         "archive_dir": str(tmp_path / "a"), "compress": True}
    )
    result = archive_history(p)
    assert result.archived == 1
    assert result.skipped == 1
    assert result.archive_path is not None
    assert result.archive_path.endswith(".gz")
    # archive file is valid gzip JSON
    with gzip.open(result.archive_path, "rt") as gz:
        archived = json.load(gz)
    assert len(archived) == 1
    # remaining history has only recent entry
    remaining = json.loads((history_dir / "myjob.json").read_text())
    assert len(remaining) == 1


def test_archive_old_entries_uncompressed(tmp_path):
    history_dir = tmp_path / "h"
    entries = [{"timestamp": _ts(90), "success": True}]
    _write_history(history_dir / "myjob.json", entries)
    p = ArchivePolicy.from_dict(
        {"job_name": "myjob", "history_dir": str(history_dir),
         "archive_dir": str(tmp_path / "a"), "compress": False}
    )
    result = archive_history(p)
    assert result.archived == 1
    assert result.archive_path.endswith(".json")
    assert not result.archive_path.endswith(".gz")


def test_archive_corrupt_history_raises(tmp_path):
    history_dir = tmp_path / "h"
    history_dir.mkdir()
    (history_dir / "myjob.json").write_text("not json")
    p = ArchivePolicy.from_dict(
        {"job_name": "myjob", "history_dir": str(history_dir),
         "archive_dir": str(tmp_path / "a")}
    )
    with pytest.raises(ArchiveError, match="Corrupt history file"):
        archive_history(p)
