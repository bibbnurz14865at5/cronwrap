import time
import pytest
from cronwrap.job_pause import JobPause, PauseState


def _make(tmp_path):
    return JobPause(str(tmp_path / "pause"))


def test_pause_creates_state(tmp_path):
    jp = _make(tmp_path)
    state = jp.pause("backup")
    assert state.job_name == "backup"
    assert isinstance(state.paused_at, float)


def test_is_paused_true_after_pause(tmp_path):
    jp = _make(tmp_path)
    jp.pause("backup")
    assert jp.is_paused("backup") is True


def test_is_paused_false_before_pause(tmp_path):
    jp = _make(tmp_path)
    assert jp.is_paused("backup") is False


def test_resume_clears_pause(tmp_path):
    jp = _make(tmp_path)
    jp.pause("backup")
    jp.resume("backup")
    assert jp.is_paused("backup") is False


def test_resume_nonexistent_is_noop(tmp_path):
    jp = _make(tmp_path)
    jp.resume("ghost")  # should not raise


def test_pause_with_reason(tmp_path):
    jp = _make(tmp_path)
    jp.pause("sync", reason="maintenance")
    state = jp.get_state("sync")
    assert state is not None
    assert state.reason == "maintenance"


def test_pause_auto_resume_expired(tmp_path):
    jp = _make(tmp_path)
    jp.pause("sync", resume_after=time.time() - 1)  # already expired
    assert jp.is_paused("sync") is False


def test_pause_auto_resume_not_yet(tmp_path):
    jp = _make(tmp_path)
    jp.pause("sync", resume_after=time.time() + 3600)
    assert jp.is_paused("sync") is True


def test_list_paused(tmp_path):
    jp = _make(tmp_path)
    jp.pause("alpha")
    jp.pause("beta")
    paused = jp.list_paused()
    assert "alpha" in paused
    assert "beta" in paused


def test_list_paused_excludes_resumed(tmp_path):
    jp = _make(tmp_path)
    jp.pause("alpha")
    jp.pause("beta")
    jp.resume("alpha")
    assert jp.list_paused() == ["beta"]


def test_state_roundtrip():
    s = PauseState(job_name="test", paused_at=1000.0, reason="x", resume_after=2000.0)
    s2 = PauseState.from_dict(s.to_dict())
    assert s2.job_name == "test"
    assert s2.reason == "x"
    assert s2.resume_after == 2000.0


def test_get_state_none_when_not_paused(tmp_path):
    jp = _make(tmp_path)
    assert jp.get_state("missing") is None
