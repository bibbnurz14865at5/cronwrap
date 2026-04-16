"""Tests for cronwrap.tags."""
import json
import pytest
from pathlib import Path
from cronwrap.tags import TagIndex, filter_jobs_by_tags


def test_add_and_jobs_for_tag():
    idx = TagIndex()
    idx.add("backup", ["critical", "nightly"])
    assert "backup" in idx.jobs_for_tag("critical")
    assert "backup" in idx.jobs_for_tag("nightly")


def test_add_deduplicates():
    idx = TagIndex()
    idx.add("backup", ["critical"])
    idx.add("backup", ["critical"])
    assert idx.jobs_for_tag("critical").count("backup") == 1


def test_tags_for_job():
    idx = TagIndex()
    idx.add("backup", ["critical", "nightly"])
    idx.add("billing", ["critical"])
    tags = idx.tags_for_job("backup")
    assert "critical" in tags
    assert "nightly" in tags
    assert "billing" not in tags


def test_all_tags_sorted():
    idx = TagIndex()
    idx.add("j", ["z", "a", "m"])
    assert idx.all_tags() == ["a", "m", "z"]


def test_to_dict_roundtrip():
    idx = TagIndex()
    idx.add("backup", ["nightly"])
    idx.add("billing", ["critical"])
    restored = TagIndex.from_dict(idx.to_dict())
    assert restored.jobs_for_tag("nightly") == ["backup"]
    assert restored.jobs_for_tag("critical") == ["billing"]


def test_save_and_load(tmp_path):
    idx = TagIndex()
    idx.add("backup", ["critical"])
    p = tmp_path / "tags.json"
    idx.save(p)
    loaded = TagIndex.load(p)
    assert "backup" in loaded.jobs_for_tag("critical")


def test_load_missing_file(tmp_path):
    idx = TagIndex.load(tmp_path / "nonexistent.json")
    assert idx.all_tags() == []


def test_filter_include():
    idx = TagIndex()
    idx.add("backup", ["nightly"])
    idx.add("billing", ["critical"])
    result = filter_jobs_by_tags(["backup", "billing", "report"], idx, include_tags=["nightly"])
    assert result == ["backup"]


def test_filter_exclude():
    idx = TagIndex()
    idx.add("billing", ["critical"])
    result = filter_jobs_by_tags(["backup", "billing"], idx, exclude_tags=["critical"])
    assert result == ["backup"]


def test_filter_include_and_exclude():
    idx = TagIndex()
    idx.add("backup", ["nightly", "critical"])
    idx.add("billing", ["critical"])
    result = filter_jobs_by_tags(
        ["backup", "billing"], idx,
        include_tags=["critical"],
        exclude_tags=["nightly"]
    )
    assert result == ["billing"]


def test_filter_no_filters_returns_all():
    idx = TagIndex()
    jobs = ["a", "b", "c"]
    assert filter_jobs_by_tags(jobs, idx) == jobs
