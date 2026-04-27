"""Tests for cronwrap.job_tag_filter."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.job_tag_filter import (
    TagFilterError,
    TagFilterResult,
    filter_by_tag,
    jobs_sharing_tags,
)
from cronwrap.tags import TagIndex


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_index(tmp_path: Path) -> Path:
    tags_file = tmp_path / "tags.json"
    idx = TagIndex(path=tags_file)
    idx.add("backup", ["daily", "storage"])
    idx.add("cleanup", ["daily", "maintenance"])
    idx.add("report", ["weekly", "storage"])
    idx.save()
    return tags_file


# ---------------------------------------------------------------------------
# TagFilterResult
# ---------------------------------------------------------------------------

def test_result_to_dict_keys():
    r = TagFilterResult(tag="daily", matched=["a", "b"], total=2)
    d = r.to_dict()
    assert set(d.keys()) == {"tag", "matched", "total"}


def test_result_to_json_valid():
    r = TagFilterResult(tag="x", matched=["job1"], total=1)
    parsed = json.loads(r.to_json())
    assert parsed["tag"] == "x"
    assert parsed["matched"] == ["job1"]


# ---------------------------------------------------------------------------
# filter_by_tag
# ---------------------------------------------------------------------------

def test_filter_returns_all_matching_jobs(tmp_path):
    tags_file = _make_index(tmp_path)
    result = filter_by_tag("daily", tags_file)
    assert result.tag == "daily"
    assert sorted(result.matched) == ["backup", "cleanup"]
    assert result.total == 2


def test_filter_empty_tag_returns_empty(tmp_path):
    tags_file = _make_index(tmp_path)
    result = filter_by_tag("nonexistent", tags_file)
    assert result.matched == []
    assert result.total == 0


def test_filter_nonexistent_file_returns_empty(tmp_path):
    tags_file = tmp_path / "missing.json"
    result = filter_by_tag("daily", tags_file)
    assert result.matched == []


def test_filter_with_allowlist(tmp_path):
    tags_file = _make_index(tmp_path)
    result = filter_by_tag("daily", tags_file, allowed_jobs=["backup"])
    assert result.matched == ["backup"]
    assert result.total == 1


def test_filter_allowlist_excludes_all(tmp_path):
    tags_file = _make_index(tmp_path)
    result = filter_by_tag("daily", tags_file, allowed_jobs=["report"])
    assert result.matched == []


def test_filter_raises_on_corrupt_file(tmp_path):
    tags_file = tmp_path / "tags.json"
    tags_file.write_text("not-json")
    with pytest.raises(TagFilterError):
        filter_by_tag("daily", tags_file)


# ---------------------------------------------------------------------------
# jobs_sharing_tags
# ---------------------------------------------------------------------------

def test_sharing_returns_related_jobs(tmp_path):
    tags_file = _make_index(tmp_path)
    related = jobs_sharing_tags("backup", tags_file)
    # backup shares 'daily' with cleanup and 'storage' with report
    assert "cleanup" in related
    assert "report" in related
    assert "backup" not in related


def test_sharing_excludes_self(tmp_path):
    tags_file = _make_index(tmp_path)
    related = jobs_sharing_tags("backup", tags_file)
    assert "backup" not in related


def test_sharing_no_file_returns_empty(tmp_path):
    tags_file = tmp_path / "missing.json"
    assert jobs_sharing_tags("backup", tags_file) == []


def test_sharing_no_tags_returns_empty(tmp_path):
    tags_file = _make_index(tmp_path)
    # 'orphan' has no tags
    related = jobs_sharing_tags("orphan", tags_file)
    assert related == []
