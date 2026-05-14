"""Tests for cronwrap.job_capacity."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from cronwrap.job_capacity import CapacityError, CapacityPolicy, _pid_alive


def _make(tmp_path, max_slots=2) -> CapacityPolicy:
    return CapacityPolicy(
        job_name="test_job",
        max_slots=max_slots,
        state_dir=str(tmp_path),
    )


def test_from_dict_required(tmp_path):
    p = CapacityPolicy.from_dict({"job_name": "j", "max_slots": 3, "state_dir": str(tmp_path)})
    assert p.job_name == "j"
    assert p.max_slots == 3


def test_from_dict_default_state_dir():
    p = CapacityPolicy.from_dict({"job_name": "j", "max_slots": 1})
    assert p.state_dir == "/tmp/cronwrap/capacity"


def test_from_dict_missing_job_name_raises():
    with pytest.raises(CapacityError, match="job_name"):
        CapacityPolicy.from_dict({"max_slots": 1})


def test_from_dict_missing_max_slots_raises():
    with pytest.raises(CapacityError, match="max_slots"):
        CapacityPolicy.from_dict({"job_name": "j"})


def test_from_dict_invalid_max_slots_raises():
    with pytest.raises(CapacityError, match="positive integer"):
        CapacityPolicy.from_dict({"job_name": "j", "max_slots": 0})


def test_to_dict_roundtrip(tmp_path):
    p = _make(tmp_path)
    d = p.to_dict()
    p2 = CapacityPolicy.from_dict(d)
    assert p2.job_name == p.job_name
    assert p2.max_slots == p.max_slots


def test_initial_used_slots_zero(tmp_path):
    p = _make(tmp_path)
    assert p.used_slots() == 0


def test_acquire_registers_pid(tmp_path):
    p = _make(tmp_path)
    p.acquire()
    pids = json.loads(p._state_path().read_text())
    assert os.getpid() in pids


def test_acquire_increments_used_slots(tmp_path):
    p = _make(tmp_path)
    p.acquire()
    assert p.used_slots() == 1


def test_acquire_exceeds_limit_raises(tmp_path):
    p = _make(tmp_path, max_slots=1)
    p.acquire()
    # Simulate another PID by injecting a fake alive PID
    state_path = p._state_path()
    existing = json.loads(state_path.read_text())
    existing.append(os.getpid() + 99999)  # likely not alive, so use current pid trick
    # Force max by writing two entries of current pid
    state_path.write_text(json.dumps([os.getpid(), os.getpid()]))
    # used_slots deduplication: write two different fake pids instead
    state_path.write_text(json.dumps([os.getpid()]))
    with pytest.raises(CapacityError, match="max capacity"):
        p.acquire()  # already at 1/1


def test_release_removes_pid(tmp_path):
    p = _make(tmp_path)
    p.acquire()
    assert p.used_slots() == 1
    p.release()
    assert p.used_slots() == 0


def test_available_slots(tmp_path):
    p = _make(tmp_path, max_slots=3)
    assert p.available_slots() == 3
    p.acquire()
    assert p.available_slots() == 2


def test_pid_alive_current():
    assert _pid_alive(os.getpid()) is True


def test_pid_alive_invalid():
    assert _pid_alive(99999999) is False
