"""Tests for cronwrap.job_mute."""

from __future__ import annotations

import time

import pytest

from cronwrap.job_mute import JobMute, MuteError, MuteState


def _make(tmp_path) -> JobMute:
    return JobMute(state_dir=str(tmp_path / "mute"))


# ---------------------------------------------------------------------------
# MuteState unit tests
# ---------------------------------------------------------------------------

def test_mute_state_to_dict_keys():
    s = MuteState(job_name="backup", muted_until=9999.0, reason="maintenance")
    d = s.to_dict()
    assert set(d.keys()) == {"job_name", "muted_until", "reason"}


def test_mute_state_to_dict_omits_reason_when_none():
    s = MuteState(job_name="backup", muted_until=9999.0)
    assert "reason" not in s.to_dict()


def test_mute_state_roundtrip():
    s = MuteState(job_name="sync", muted_until=12345.6, reason="deploy")
    assert MuteState.from_dict(s.to_dict()) == s


def test_mute_state_is_active_true():
    s = MuteState(job_name="x", muted_until=time.time() + 3600)
    assert s.is_active() is True


def test_mute_state_is_active_false():
    s = MuteState(job_name="x", muted_until=time.time() - 1)
    assert s.is_active() is False


# ---------------------------------------------------------------------------
# JobMute integration tests
# ---------------------------------------------------------------------------

def test_mute_creates_state(tmp_path):
    jm = _make(tmp_path)
    state = jm.mute("nightly", 3600)
    assert state.job_name == "nightly"
    assert state.muted_until > time.time()


def test_is_muted_true_after_mute(tmp_path):
    jm = _make(tmp_path)
    jm.mute("nightly", 3600)
    assert jm.is_muted("nightly") is True


def test_is_muted_false_before_mute(tmp_path):
    jm = _make(tmp_path)
    assert jm.is_muted("nightly") is False


def test_unmute_clears_state(tmp_path):
    jm = _make(tmp_path)
    jm.mute("nightly", 3600)
    jm.unmute("nightly")
    assert jm.is_muted("nightly") is False


def test_unmute_noop_when_not_muted(tmp_path):
    jm = _make(tmp_path)
    jm.unmute("ghost")  # should not raise


def test_get_returns_none_when_absent(tmp_path):
    jm = _make(tmp_path)
    assert jm.get("unknown") is None


def test_mute_with_reason(tmp_path):
    jm = _make(tmp_path)
    jm.mute("deploy", 600, reason="planned outage")
    state = jm.get("deploy")
    assert state is not None
    assert state.reason == "planned outage"


def test_mute_invalid_duration_raises(tmp_path):
    jm = _make(tmp_path)
    with pytest.raises(MuteError):
        jm.mute("x", 0)


def test_expired_mute_not_active(tmp_path):
    jm = _make(tmp_path)
    jm.mute("old", 1)
    assert jm.is_muted("old", now=time.time() + 9999) is False


def test_mute_overwrites_existing_mute(tmp_path):
    """Re-muting a job should extend (overwrite) the existing mute state."""
    jm = _make(tmp_path)
    first = jm.mute("nightly", 60)
    second = jm.mute("nightly", 7200)
    assert second.muted_until > first.muted_until
    assert jm.is_muted("nightly") is True
