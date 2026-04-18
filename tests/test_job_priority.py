"""Tests for cronwrap.job_priority."""
import json
import pytest
from pathlib import Path
from cronwrap.job_priority import JobPriority, PriorityIndex, PriorityError, PRIORITY_LEVELS


def _make_index(tmp_path) -> PriorityIndex:
    return PriorityIndex(tmp_path / "priorities.json")


def test_job_priority_default_level():
    jp = JobPriority(job_name="myjob")
    assert jp.priority == "normal"


def test_job_priority_invalid_level():
    with pytest.raises(PriorityError):
        JobPriority(job_name="myjob", priority="urgent")


def test_job_priority_to_dict_keys():
    jp = JobPriority(job_name="myjob", priority="high", weight=5)
    d = jp.to_dict()
    assert set(d.keys()) == {"job_name", "priority", "weight"}


def test_job_priority_roundtrip():
    jp = JobPriority(job_name="myjob", priority="critical", weight=3)
    assert JobPriority.from_dict(jp.to_dict()).priority == "critical"
    assert JobPriority.from_dict(jp.to_dict()).weight == 3


def test_sort_key_ordering():
    critical = JobPriority(job_name="a", priority="critical")
    low = JobPriority(job_name="b", priority="low")
    assert critical.sort_key < low.sort_key


def test_weight_breaks_tie():
    a = JobPriority(job_name="a", priority="high", weight=10)
    b = JobPriority(job_name="b", priority="high", weight=1)
    assert a.sort_key < b.sort_key


def test_set_and_get(tmp_path):
    idx = _make_index(tmp_path)
    idx.set("backup", priority="critical", weight=5)
    jp = idx.get("backup")
    assert jp is not None
    assert jp.priority == "critical"


def test_get_missing_returns_none(tmp_path):
    idx = _make_index(tmp_path)
    assert idx.get("nonexistent") is None


def test_set_persists(tmp_path):
    p = tmp_path / "priorities.json"
    idx = PriorityIndex(p)
    idx.set("job1", priority="low")
    idx2 = PriorityIndex(p)
    assert idx2.get("job1").priority == "low"


def test_remove(tmp_path):
    idx = _make_index(tmp_path)
    idx.set("job1")
    idx.remove("job1")
    assert idx.get("job1") is None


def test_sorted_jobs_order(tmp_path):
    idx = _make_index(tmp_path)
    idx.set("low_job", priority="low")
    idx.set("crit_job", priority="critical")
    idx.set("norm_job", priority="normal")
    names = [jp.job_name for jp in idx.sorted_jobs()]
    assert names.index("crit_job") < names.index("norm_job") < names.index("low_job")


def test_all_priority_levels_valid():
    for lvl in PRIORITY_LEVELS:
        jp = JobPriority(job_name="test", priority=lvl)
        assert jp.priority == lvl
