"""Tests for cronwrap.job_cleanup."""
import time
from pathlib import Path

import pytest

from cronwrap.job_cleanup import CleanupError, CleanupPolicy, CleanupResult


def _make(tmp_path, **kwargs) -> CleanupPolicy:
    defaults = {"state_dir": str(tmp_path), "max_age_seconds": 60}
    defaults.update(kwargs)
    return CleanupPolicy.from_dict(defaults)


def test_from_dict_required(tmp_path):
    p = CleanupPolicy.from_dict({"state_dir": str(tmp_path)})
    assert p.state_dir == str(tmp_path)
    assert p.max_age_seconds == 3600
    assert ".lock" in p.extensions


def test_from_dict_custom(tmp_path):
    p = CleanupPolicy.from_dict({
        "state_dir": str(tmp_path),
        "max_age_seconds": 120,
        "extensions": [".tmp"],
    })
    assert p.max_age_seconds == 120
    assert p.extensions == [".tmp"]


def test_from_dict_missing_state_dir_raises():
    with pytest.raises(CleanupError, match="state_dir"):
        CleanupPolicy.from_dict({})


def test_to_dict_roundtrip(tmp_path):
    p = _make(tmp_path)
    d = p.to_dict()
    p2 = CleanupPolicy.from_dict(d)
    assert p2.state_dir == p.state_dir
    assert p2.max_age_seconds == p.max_age_seconds
    assert p2.extensions == p.extensions


def test_run_removes_old_lock(tmp_path):
    old_file = tmp_path / "job.lock"
    old_file.write_text("pid")
    old_time = time.time() - 7200
    import os
    os.utime(old_file, (old_time, old_time))
    p = _make(tmp_path, max_age_seconds=3600)
    result = p.run()
    assert str(old_file) in result.removed
    assert not old_file.exists()


def test_run_skips_recent_file(tmp_path):
    recent = tmp_path / "job.lock"
    recent.write_text("pid")
    p = _make(tmp_path, max_age_seconds=3600)
    result = p.run()
    assert str(recent) in result.skipped
    assert recent.exists()


def test_run_skips_unknown_extension(tmp_path):
    f = tmp_path / "job.log"
    f.write_text("log data")
    p = _make(tmp_path)
    result = p.run()
    assert str(f) in result.skipped
    assert f.exists()


def test_run_empty_dir_returns_ok(tmp_path):
    p = _make(tmp_path)
    result = p.run()
    assert result.ok
    assert result.removed == []
    assert result.skipped == []


def test_run_nonexistent_dir_returns_ok(tmp_path):
    p = _make(tmp_path / "no_such_dir")
    result = p.run()
    assert result.ok


def test_cleanup_result_to_dict_keys():
    r = CleanupResult(removed=["a"], skipped=["b"], errors=[])
    d = r.to_dict()
    assert set(d.keys()) == {"removed", "skipped", "errors", "ok"}
    assert d["ok"] is True


def test_cleanup_result_not_ok_when_errors():
    r = CleanupResult(errors=["something went wrong"])
    assert not r.ok
    assert r.to_dict()["ok"] is False
