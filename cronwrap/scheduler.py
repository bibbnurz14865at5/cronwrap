"""Lightweight cron expression validator and next-run calculator."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional


CRON_RE = re.compile(
    r"^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)$"
)


class ScheduleError(ValueError):
    """Raised when a cron expression is invalid."""


def _parse_field(field: str, lo: int, hi: int) -> list[int]:
    """Expand a single cron field into a sorted list of integers."""
    values: set[int] = set()

    for part in field.split(","):
        if part == "*":
            values.update(range(lo, hi + 1))
        elif "/" in part:
            base, step_str = part.split("/", 1)
            step = int(step_str)
            start = lo if base == "*" else int(base)
            values.update(range(start, hi + 1, step))
        elif "-" in part:
            a, b = part.split("-", 1)
            values.update(range(int(a), int(b) + 1))
        else:
            values.add(int(part))

    for v in values:
        if not lo <= v <= hi:
            raise ScheduleError(
                f"Value {v} out of range [{lo}, {hi}] in field '{field}'"
            )
    return sorted(values)


def validate_cron(expression: str) -> bool:
    """Return True if *expression* is a valid 5-field cron string."""
    try:
        parse_cron(expression)
        return True
    except ScheduleError:
        return False


def parse_cron(expression: str) -> dict[str, list[int]]:
    """Parse a cron expression and return expanded field lists."""
    m = CRON_RE.match(expression.strip())
    if not m:
        raise ScheduleError(f"Invalid cron expression: {expression!r}")

    minute_s, hour_s, dom_s, month_s, dow_s = m.groups()
    return {
        "minute": _parse_field(minute_s, 0, 59),
        "hour": _parse_field(hour_s, 0, 23),
        "dom": _parse_field(dom_s, 1, 31),
        "month": _parse_field(month_s, 1, 12),
        "dow": _parse_field(dow_s, 0, 6),
    }


def next_run(expression: str, after: Optional[datetime] = None) -> datetime:
    """Return the next datetime at which *expression* would fire.

    Iterates minute-by-minute up to one year ahead.
    """
    fields = parse_cron(expression)
    dt = (after or datetime.utcnow()).replace(second=0, microsecond=0)
    dt += timedelta(minutes=1)  # start from the *next* minute

    limit = dt + timedelta(days=366)
    while dt < limit:
        if (
            dt.month in fields["month"]
            and dt.day in fields["dom"]
            and dt.weekday() % 7 in fields["dow"]  # Python: Mon=0; cron: Sun=0
            and dt.hour in fields["hour"]
            and dt.minute in fields["minute"]
        ):
            return dt
        dt += timedelta(minutes=1)

    raise ScheduleError("No next run found within one year for expression")
