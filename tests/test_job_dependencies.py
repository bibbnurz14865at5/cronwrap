"""Tests for cronwrap.job_dependencies."""
import json
import time
from pathlib import Path

import pytest

from cronwrap.job_dependencies import (
    DependencyConfig,
    DependencyError,
    assert_dependencies,
    check_dependencies,
)
from cronwrap.history import JobHistory


def _write_success(history_dir: Path, job: str, offset: int = 0) -> None:
    jdir = history_dir / job
    jdir.mkdir(parents=True, exist_ok=True)
    h = JobHistory(str(jdir))
    h.record(job, success=True, duration=1.0, exit_code=0, timestamp=time.time() - offset)


def test_from_dict_required_only():
    cfg = DependencyConfig.from_dict({"job_name": "myjob"})
    assert cfg.job_name == "myjob"
    assert cfg.depends_on == []
    assert cfg.require_success_within_seconds is None


def test_from_dict_full():
    cfg = DependencyConfig.from_dict({
        "job_name": "report",
        "depends_on": ["fetch", "prep"],
        "require_success_within_seconds": 7200,
    })
    assert cfg.depends_on == ["fetch", "prep"]
    assert cfg.require_success_within_seconds == 7200


def test_to_dict_roundtrip():
    cfg = DependencyConfig(job_name="x", depends_on=["a"], require_success_within_seconds=60)
    assert DependencyConfig.from_dict(cfg.to_dict()).depends_on == ["a"]


def test_from_json_file(tmp_path):
    p = tmp_path / "dep.json"
    p.write_text(json.dumps({"job_name": "j", "depends_on": ["k"]}))
    cfg = DependencyConfig.from_json_file(str(p))
    assert cfg.job_name == "j"


def test_from_json_file_not_found():
    with pytest.raises(FileNotFoundError):
        DependencyConfig.from_json_file("/nonexistent/path.json")


def test_check_dependencies_no_deps(tmp_path):
    cfg = DependencyConfig(job_name="x", depends_on=[])
    assert check_dependencies(cfg, str(tmp_path)) == []


def test_check_dependencies_missing_history(tmp_path):
    cfg = DependencyConfig(job_name="x", depends_on=["missing_job"])
    unmet = check_dependencies(cfg, str(tmp_path))
    assert "missing_job" in unmet


def test_check_dependencies_success_present(tmp_path):
    _write_success(tmp_path, "fetch")
    cfg = DependencyConfig(job_name="report", depends_on=["fetch"])
    assert check_dependencies(cfg, str(tmp_path)) == []


def test_check_dependencies_stale_success(tmp_path):
    _write_success(tmp_path, "fetch", offset=7200)
    cfg = DependencyConfig(job_name="report", depends_on=["fetch"],
                           require_success_within_seconds=3600)
    unmet = check_dependencies(cfg, str(tmp_path))
    assert "fetch" in unmet


def test_check_dependencies_fresh_success(tmp_path):
    _write_success(tmp_path, "fetch", offset=100)
    cfg = DependencyConfig(job_name="report", depends_on=["fetch"],
                           require_success_within_seconds=3600)
    assert check_dependencies(cfg, str(tmp_path)) == []


def test_assert_dependencies_raises(tmp_path):
    cfg = DependencyConfig(job_name="x", depends_on=["ghost"])
    with pytest.raises(DependencyError, match="ghost"):
        assert_dependencies(cfg, str(tmp_path))


def test_assert_dependencies_passes(tmp_path):
    _write_success(tmp_path, "step1")
    cfg = DependencyConfig(job_name="step2", depends_on=["step1"])
    assert_dependencies(cfg, str(tmp_path))  # should not raise
