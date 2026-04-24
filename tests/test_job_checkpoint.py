"""Tests for cronwrap.job_checkpoint."""
import json
import time

import pytest

from cronwrap.job_checkpoint import Checkpoint, CheckpointError, JobCheckpoint


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make(tmp_path, name="test_job"):
    return JobCheckpoint(job_name=name, state_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# Checkpoint dataclass
# ---------------------------------------------------------------------------

def test_checkpoint_to_dict_required_keys():
    cp = Checkpoint(job_name="j", step="fetch")
    d = cp.to_dict()
    assert d["job_name"] == "j"
    assert d["step"] == "fetch"
    assert "timestamp" in d


def test_checkpoint_to_dict_omits_empty_meta():
    cp = Checkpoint(job_name="j", step="s", meta={})
    assert "meta" not in cp.to_dict()


def test_checkpoint_to_dict_includes_meta_when_set():
    cp = Checkpoint(job_name="j", step="s", meta={"rows": 10})
    assert cp.to_dict()["meta"] == {"rows": 10}


def test_checkpoint_roundtrip():
    cp = Checkpoint(job_name="etl", step="transform", meta={"offset": 99})
    restored = Checkpoint.from_dict(cp.to_dict())
    assert restored.job_name == cp.job_name
    assert restored.step == cp.step
    assert restored.meta == cp.meta
    assert abs(restored.timestamp - cp.timestamp) < 0.001


def test_checkpoint_from_dict_defaults_timestamp():
    data = {"job_name": "j", "step": "s"}
    cp = Checkpoint.from_dict(data)
    assert cp.timestamp > 0


# ---------------------------------------------------------------------------
# JobCheckpoint
# ---------------------------------------------------------------------------

def test_save_creates_file(tmp_path):
    jcp = _make(tmp_path)
    jcp.save("fetch")
    assert (tmp_path / "test_job.json").exists()


def test_save_returns_checkpoint(tmp_path):
    jcp = _make(tmp_path)
    cp = jcp.save("load", meta={"n": 5})
    assert isinstance(cp, Checkpoint)
    assert cp.step == "load"
    assert cp.meta == {"n": 5}


def test_load_returns_none_when_no_file(tmp_path):
    jcp = _make(tmp_path)
    assert jcp.load() is None


def test_load_returns_saved_checkpoint(tmp_path):
    jcp = _make(tmp_path)
    jcp.save("transform", meta={"rows": 42})
    cp = jcp.load()
    assert cp is not None
    assert cp.step == "transform"
    assert cp.meta == {"rows": 42}


def test_has_checkpoint_false_initially(tmp_path):
    assert not _make(tmp_path).has_checkpoint()


def test_has_checkpoint_true_after_save(tmp_path):
    jcp = _make(tmp_path)
    jcp.save("step1")
    assert jcp.has_checkpoint()


def test_clear_removes_file(tmp_path):
    jcp = _make(tmp_path)
    jcp.save("step1")
    jcp.clear()
    assert not jcp.has_checkpoint()


def test_clear_is_noop_when_no_file(tmp_path):
    jcp = _make(tmp_path)
    jcp.clear()  # should not raise


def test_load_raises_on_corrupt_file(tmp_path):
    jcp = _make(tmp_path)
    (tmp_path / "test_job.json").write_text("not json{{{")
    with pytest.raises(CheckpointError):
        jcp.load()


def test_multiple_saves_overwrite(tmp_path):
    jcp = _make(tmp_path)
    jcp.save("step1")
    jcp.save("step2")
    cp = jcp.load()
    assert cp.step == "step2"


def test_separate_jobs_use_separate_files(tmp_path):
    jcp_a = _make(tmp_path, "job_a")
    jcp_b = _make(tmp_path, "job_b")
    jcp_a.save("alpha")
    jcp_b.save("beta")
    assert jcp_a.load().step == "alpha"
    assert jcp_b.load().step == "beta"
