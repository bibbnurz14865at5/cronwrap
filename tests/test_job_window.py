"""Tests for cronwrap.job_window."""
from __future__ import annotations

import json
from datetime import datetime, time
from pathlib import Path

import pytest

from cronwrap.job_window import WindowError, WindowPolicy


def _make(tmp_path, **kwargs) -> WindowPolicy:
    defaults = {"job_name": "test-job", "windows": [], "timezone": "UTC"}
    defaults.update(kwargs)
    return WindowPolicy.from_dict(defaults)


# ---------------------------------------------------------------------------
# from_dict / to_dict
# ---------------------------------------------------------------------------

def test_from_dict_required_only():
    p = WindowPolicy.from_dict({"job_name": "j"})
    assert p.job_name == "j"
    assert p.windows == []
    assert p.timezone == "UTC"


def test_from_dict_full():
    p = WindowPolicy.from_dict({
        "job_name": "j",
        "windows": [{"start": "09:00", "end": "17:00"}],
        "timezone": "Europe/London",
    })
    assert len(p.windows) == 1
    assert p.timezone == "Europe/London"


def test_from_dict_missing_job_name_raises():
    with pytest.raises(WindowError, match="job_name"):
        WindowPolicy.from_dict({"windows": []})


def test_to_dict_roundtrip():
    data = {"job_name": "j", "windows": [{"start": "08:00", "end": "18:00"}], "timezone": "UTC"}
    assert WindowPolicy.from_dict(data).to_dict() == data


# ---------------------------------------------------------------------------
# from_json_file
# ---------------------------------------------------------------------------

def test_from_json_file(tmp_path):
    cfg = tmp_path / "w.json"
    cfg.write_text(json.dumps({"job_name": "j", "windows": []}))
    p = WindowPolicy.from_json_file(str(cfg))
    assert p.job_name == "j"


def test_from_json_file_not_found(tmp_path):
    with pytest.raises(WindowError, match="not found"):
        WindowPolicy.from_json_file(str(tmp_path / "missing.json"))


# ---------------------------------------------------------------------------
# is_allowed / assert_allowed
# ---------------------------------------------------------------------------

def test_no_windows_always_allowed():
    p = WindowPolicy.from_dict({"job_name": "j"})
    assert p.is_allowed() is True


def test_within_window_allowed():
    p = WindowPolicy.from_dict({
        "job_name": "j",
        "windows": [{"start": "08:00", "end": "18:00"}],
    })
    dt = datetime(2024, 1, 15, 12, 0)  # Monday noon
    assert p.is_allowed(dt) is True


def test_outside_window_blocked():
    p = WindowPolicy.from_dict({
        "job_name": "j",
        "windows": [{"start": "08:00", "end": "10:00"}],
    })
    dt = datetime(2024, 1, 15, 23, 0)
    assert p.is_allowed(dt) is False


def test_weekday_filter_allows_matching_day():
    p = WindowPolicy.from_dict({
        "job_name": "j",
        "windows": [{"start": "00:00", "end": "23:59", "weekdays": [0]}],  # Monday only
    })
    monday = datetime(2024, 1, 15, 9, 0)  # 2024-01-15 is a Monday
    assert p.is_allowed(monday) is True


def test_weekday_filter_blocks_non_matching_day():
    p = WindowPolicy.from_dict({
        "job_name": "j",
        "windows": [{"start": "00:00", "end": "23:59", "weekdays": [0]}],  # Monday only
    })
    tuesday = datetime(2024, 1, 16, 9, 0)  # 2024-01-16 is a Tuesday
    assert p.is_allowed(tuesday) is False


def test_assert_allowed_raises_when_blocked():
    p = WindowPolicy.from_dict({
        "job_name": "j",
        "windows": [{"start": "08:00", "end": "10:00"}],
    })
    dt = datetime(2024, 1, 15, 23, 0)
    with pytest.raises(WindowError, match="not allowed"):
        p.assert_allowed(dt)


def test_assert_allowed_passes_when_inside_window():
    p = WindowPolicy.from_dict({
        "job_name": "j",
        "windows": [{"start": "00:00", "end": "23:59"}],
    })
    p.assert_allowed(datetime(2024, 1, 15, 12, 0))  # should not raise
