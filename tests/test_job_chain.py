"""Tests for cronwrap.job_chain."""
import json
import pytest
from cronwrap.job_chain import ChainStep, JobChain, ChainError


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make(tmp_path, data: dict) -> str:
    p = tmp_path / "chain.json"
    p.write_text(json.dumps(data))
    return str(p)


def _simple_chain() -> JobChain:
    return JobChain.from_dict({
        "chain_name": "pipe",
        "steps": [
            {"job_name": "a", "on_success": "b", "on_failure": None},
            {"job_name": "b", "on_success": None, "on_failure": "c"},
            {"job_name": "c"},
        ],
    })


# ---------------------------------------------------------------------------
# ChainStep
# ---------------------------------------------------------------------------

def test_step_to_dict_required_keys():
    s = ChainStep(job_name="x")
    d = s.to_dict()
    assert d["job_name"] == "x"
    assert "on_success" not in d
    assert "on_failure" not in d


def test_step_to_dict_includes_routing_when_set():
    s = ChainStep(job_name="x", on_success="y", on_failure="z")
    d = s.to_dict()
    assert d["on_success"] == "y"
    assert d["on_failure"] == "z"


def test_step_roundtrip():
    orig = ChainStep(job_name="foo", on_success="bar", on_failure=None)
    restored = ChainStep.from_dict(orig.to_dict())
    assert restored.job_name == orig.job_name
    assert restored.on_success == orig.on_success


def test_step_extra_captured():
    s = ChainStep.from_dict({"job_name": "x", "timeout": 30})
    assert s.extra.get("timeout") == 30


# ---------------------------------------------------------------------------
# JobChain construction
# ---------------------------------------------------------------------------

def test_from_dict_basic():
    chain = _simple_chain()
    assert chain.chain_name == "pipe"
    assert len(chain.steps) == 3


def test_from_dict_missing_chain_name_raises():
    with pytest.raises(ChainError, match="chain_name"):
        JobChain.from_dict({"steps": []})


def test_from_dict_empty_steps():
    chain = JobChain.from_dict({"chain_name": "empty"})
    assert chain.steps == []


def test_to_dict_roundtrip():
    chain = _simple_chain()
    restored = JobChain.from_dict(chain.to_dict())
    assert restored.chain_name == chain.chain_name
    assert restored.ordered_names() == chain.ordered_names()


def test_from_json_file(tmp_path):
    data = {"chain_name": "test", "steps": [{"job_name": "j1"}]}
    path = _make(tmp_path, data)
    chain = JobChain.from_json_file(path)
    assert chain.chain_name == "test"


def test_from_json_file_not_found():
    with pytest.raises(ChainError, match="not found"):
        JobChain.from_json_file("/nonexistent/chain.json")


# ---------------------------------------------------------------------------
# JobChain logic
# ---------------------------------------------------------------------------

def test_ordered_names():
    chain = _simple_chain()
    assert chain.ordered_names() == ["a", "b", "c"]


def test_step_for_existing():
    chain = _simple_chain()
    assert chain.step_for("b") is not None
    assert chain.step_for("b").job_name == "b"


def test_step_for_missing_returns_none():
    chain = _simple_chain()
    assert chain.step_for("zzz") is None


def test_next_job_on_success():
    chain = _simple_chain()
    assert chain.next_job("a", success=True) == "b"


def test_next_job_on_failure():
    chain = _simple_chain()
    assert chain.next_job("b", success=False) == "c"


def test_next_job_returns_none_at_end():
    chain = _simple_chain()
    assert chain.next_job("a", success=False) is None


def test_next_job_unknown_raises():
    chain = _simple_chain()
    with pytest.raises(ChainError, match="not found"):
        chain.next_job("unknown", success=True)
