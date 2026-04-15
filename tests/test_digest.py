"""Tests for cronwrap.digest — build_digest and Digest rendering."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.digest import DigestEntry, Digest, build_digest
from cronwrap.history import JobHistory


def _write_history(tmp_path: Path, job: str, entries: list[dict]) -> None:
    jh = JobHistory(job, tmp_path)
    for e in entries:
        from cronwrap.history import HistoryEntry
        jh.record(
            HistoryEntry(
                job_name=job,
                success=e["success"],
                exit_code=e.get("exit_code", 0),
                duration=e.get("duration", 1.0),
                stdout=e.get("stdout", ""),
                stderr=e.get("stderr", ""),
            )
        )


def test_digest_entry_to_dict_keys():
    e = DigestEntry(
        job_name="backup",
        success_rate=100.0,
        avg_duration=2.5,
        total_runs=10,
        last_run="2024-01-01T00:00:00+00:00",
        last_status="ok",
    )
    d = e.to_dict()
    assert set(d.keys()) == {
        "job_name", "success_rate", "avg_duration",
        "total_runs", "last_run", "last_status",
    }


def test_build_digest_empty_dir(tmp_path):
    digest = build_digest(tmp_path)
    assert digest.entries == []


def test_build_digest_nonexistent_dir(tmp_path):
    digest = build_digest(tmp_path / "nope")
    assert digest.entries == []


def test_build_digest_single_job(tmp_path):
    _write_history(tmp_path, "myjob", [
        {"success": True, "duration": 2.0},
        {"success": True, "duration": 4.0},
    ])
    digest = build_digest(tmp_path)
    assert len(digest.entries) == 1
    entry = digest.entries[0]
    assert entry.job_name == "myjob"
    assert entry.total_runs == 2
    assert entry.success_rate == pytest.approx(100.0)
    assert entry.avg_duration == pytest.approx(3.0)
    assert entry.last_status == "ok"


def test_build_digest_mixed_success(tmp_path):
    _write_history(tmp_path, "flaky", [
        {"success": True, "duration": 1.0},
        {"success": False, "exit_code": 1, "duration": 0.5},
    ])
    digest = build_digest(tmp_path)
    entry = digest.entries[0]
    assert entry.success_rate == pytest.approx(50.0)
    assert entry.last_status == "fail"


def test_digest_to_json_valid(tmp_path):
    _write_history(tmp_path, "job1", [{"success": True, "duration": 1.0}])
    digest = build_digest(tmp_path)
    parsed = json.loads(digest.to_json())
    assert "generated_at" in parsed
    assert len(parsed["entries"]) == 1


def test_digest_to_text_contains_job_name(tmp_path):
    _write_history(tmp_path, "cleanup", [{"success": True, "duration": 3.0}])
    digest = build_digest(tmp_path)
    text = digest.to_text()
    assert "cleanup" in text
    assert "success=100.0%" in text


def test_digest_to_text_empty():
    digest = Digest()
    text = digest.to_text()
    assert "No job history found" in text
