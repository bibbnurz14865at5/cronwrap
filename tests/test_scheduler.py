"""Tests for cronwrap.scheduler."""

from datetime import datetime

import pytest

from cronwrap.scheduler import (
    ScheduleError,
    _parse_field,
    next_run,
    parse_cron,
    validate_cron,
)


# ---------------------------------------------------------------------------
# _parse_field
# ---------------------------------------------------------------------------

def test_parse_field_wildcard():
    assert _parse_field("*", 0, 4) == [0, 1, 2, 3, 4]


def test_parse_field_single():
    assert _parse_field("5", 0, 59) == [5]


def test_parse_field_range():
    assert _parse_field("1-3", 0, 59) == [1, 2, 3]


def test_parse_field_step():
    assert _parse_field("*/15", 0, 59) == [0, 15, 30, 45]


def test_parse_field_list():
    assert _parse_field("1,3,5", 0, 59) == [1, 3, 5]


def test_parse_field_out_of_range_raises():
    with pytest.raises(ScheduleError):
        _parse_field("60", 0, 59)


# ---------------------------------------------------------------------------
# validate_cron / parse_cron
# ---------------------------------------------------------------------------

def test_validate_cron_valid():
    assert validate_cron("*/5 * * * *") is True


def test_validate_cron_invalid_too_few_fields():
    assert validate_cron("* * * *") is False


def test_validate_cron_invalid_value():
    assert validate_cron("60 * * * *") is False


def test_parse_cron_returns_all_keys():
    result = parse_cron("0 12 * * 1")
    assert set(result.keys()) == {"minute", "hour", "dom", "month", "dow"}


def test_parse_cron_specific_values():
    result = parse_cron("30 6 1 1 0")
    assert result["minute"] == [30]
    assert result["hour"] == [6]
    assert result["dom"] == [1]
    assert result["month"] == [1]
    assert result["dow"] == [0]


def test_parse_cron_invalid_raises():
    with pytest.raises(ScheduleError):
        parse_cron("not a cron")


# ---------------------------------------------------------------------------
# next_run
# ---------------------------------------------------------------------------

def test_next_run_every_minute():
    anchor = datetime(2024, 6, 1, 12, 0, 0)
    nxt = next_run("* * * * *", after=anchor)
    assert nxt == datetime(2024, 6, 1, 12, 1, 0)


def test_next_run_hourly():
    anchor = datetime(2024, 6, 1, 12, 30, 0)
    nxt = next_run("0 * * * *", after=anchor)
    assert nxt == datetime(2024, 6, 1, 13, 0, 0)


def test_next_run_specific_time():
    anchor = datetime(2024, 6, 1, 11, 59, 0)
    nxt = next_run("0 12 * * *", after=anchor)
    assert nxt == datetime(2024, 6, 1, 12, 0, 0)


def test_next_run_advances_day():
    anchor = datetime(2024, 6, 1, 12, 1, 0)
    nxt = next_run("0 12 * * *", after=anchor)
    assert nxt == datetime(2024, 6, 2, 12, 0, 0)


def test_next_run_returns_datetime():
    nxt = next_run("*/10 * * * *")
    assert isinstance(nxt, datetime)
