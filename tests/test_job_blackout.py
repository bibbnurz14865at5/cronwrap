"""Tests for cronwrap.job_blackout."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from cronwrap.job_blackout import BlackoutError, BlackoutPolicy, BlackoutWindow


# ---------------------------------------------------------------------------
# BlackoutWindow
# ---------------------------------------------------------------------------

def test_window_to_dict_minimal():
    w = BlackoutWindow(start="08:00", end="09:00")
    d = w.to_dict()
    assert d == {"start": "08:00", "end": "09:00"}


def test_window_to_dict_full():
    w = BlackoutWindow(start="08:00", end="09:00", weekdays=[0, 1], label="standup")
    d = w.to_dict()
    assert d["weekdays"] == [0, 1]
    assert d["label"] == "standup"


def test_window_roundtrip():
    w = BlackoutWindow(start="22:00", end="06:00", weekdays=[5, 6], label="weekend")
    assert BlackoutWindow.from_dict(w.to_dict()).to_dict() == w.to_dict()


def test_window_invalid_time_raises():
    with pytest.raises(BlackoutError, match="Invalid time"):
        BlackoutWindow(start="25:00", end="09:00")


def test_window_invalid_weekday_raises():
    with pytest.raises(BlackoutError, match="Invalid weekday"):
        BlackoutWindow(start="08:00", end="09:00", weekdays=[7])


def test_is_active_within_window():
    w = BlackoutWindow(start="08:00", end="09:00")
    assert w.is_active(datetime(2024, 1, 15, 8, 30)) is True


def test_is_active_outside_window():
    w = BlackoutWindow(start="08:00", end="09:00")
    assert w.is_active(datetime(2024, 1, 15, 10, 0)) is False


def test_is_active_overnight_window_before_midnight():
    w = BlackoutWindow(start="22:00", end="06:00")
    assert w.is_active(datetime(2024, 1, 15, 23, 0)) is True


def test_is_active_overnight_window_after_midnight():
    w = BlackoutWindow(start="22:00", end="06:00")
    assert w.is_active(datetime(2024, 1, 16, 3, 0)) is True


def test_is_active_overnight_window_outside():
    w = BlackoutWindow(start="22:00", end="06:00")
    assert w.is_active(datetime(2024, 1, 15, 12, 0)) is False


def test_is_active_weekday_filter_match():
    # 2024-01-15 is Monday (weekday=0)
    w = BlackoutWindow(start="08:00", end="09:00", weekdays=[0])
    assert w.is_active(datetime(2024, 1, 15, 8, 30)) is True


def test_is_active_weekday_filter_no_match():
    # 2024-01-16 is Tuesday (weekday=1), window only for Monday
    w = BlackoutWindow(start="08:00", end="09:00", weekdays=[0])
    assert w.is_active(datetime(2024, 1, 16, 8, 30)) is False


# ---------------------------------------------------------------------------
# BlackoutPolicy
# ---------------------------------------------------------------------------

def test_policy_to_dict_keys():
    p = BlackoutPolicy(job_name="myjob", windows=[])
    d = p.to_dict()
    assert "job_name" in d
    assert "windows" in d


def test_policy_from_dict_required_only():
    p = BlackoutPolicy.from_dict({"job_name": "myjob"})
    assert p.job_name == "myjob"
    assert p.windows == []


def test_policy_from_dict_missing_job_name_raises():
    with pytest.raises(BlackoutError, match="job_name"):
        BlackoutPolicy.from_dict({"windows": []})


def test_policy_is_blacked_out_true():
    p = BlackoutPolicy.from_dict({
        "job_name": "j",
        "windows": [{"start": "08:00", "end": "09:00"}],
    })
    assert p.is_blacked_out(datetime(2024, 1, 15, 8, 30)) is True


def test_policy_is_blacked_out_false():
    p = BlackoutPolicy.from_dict({
        "job_name": "j",
        "windows": [{"start": "08:00", "end": "09:00"}],
    })
    assert p.is_blacked_out(datetime(2024, 1, 15, 12, 0)) is False


def test_policy_is_blacked_out_no_windows():
    p = BlackoutPolicy(job_name="j", windows=[])
    assert p.is_blacked_out() is False


def test_policy_from_json_file(tmp_path: Path):
    cfg = {"job_name": "filejob", "windows": [{"start": "01:00", "end": "02:00"}]}
    f = tmp_path / "blackout.json"
    f.write_text(json.dumps(cfg))
    p = BlackoutPolicy.from_json_file(str(f))
    assert p.job_name == "filejob"
    assert len(p.windows) == 1


def test_policy_from_json_file_not_found():
    with pytest.raises(BlackoutError, match="not found"):
        BlackoutPolicy.from_json_file("/nonexistent/blackout.json")
