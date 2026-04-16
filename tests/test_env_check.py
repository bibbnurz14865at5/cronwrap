"""Tests for cronwrap.env_check."""
import os
import pytest

from cronwrap.env_check import EnvCheckResult, check_env, assert_env


def test_env_check_result_ok_when_no_missing():
    r = EnvCheckResult(present=["A"], missing=[])
    assert r.ok is True


def test_env_check_result_not_ok_when_missing():
    r = EnvCheckResult(present=[], missing=["B"])
    assert r.ok is False


def test_check_env_all_present(monkeypatch):
    monkeypatch.setenv("CW_TEST_A", "1")
    monkeypatch.setenv("CW_TEST_B", "2")
    result = check_env(["CW_TEST_A", "CW_TEST_B"])
    assert result.ok is True
    assert set(result.present) == {"CW_TEST_A", "CW_TEST_B"}
    assert result.missing == []


def test_check_env_some_missing(monkeypatch):
    monkeypatch.setenv("CW_TEST_A", "yes")
    monkeypatch.delenv("CW_TEST_MISSING", raising=False)
    result = check_env(["CW_TEST_A", "CW_TEST_MISSING"])
    assert result.ok is False
    assert "CW_TEST_MISSING" in result.missing
    assert "CW_TEST_A" in result.present


def test_check_env_empty_list():
    result = check_env([])
    assert result.ok is True
    assert result.present == []
    assert result.missing == []


def test_assert_env_passes_when_all_set(monkeypatch):
    monkeypatch.setenv("CW_X", "val")
    assert_env(["CW_X"])  # should not raise


def test_assert_env_raises_on_missing(monkeypatch):
    monkeypatch.delenv("CW_NOPE", raising=False)
    monkeypatch.delenv("CW_ALSO_NOPE", raising=False)
    with pytest.raises(EnvironmentError) as exc_info:
        assert_env(["CW_NOPE", "CW_ALSO_NOPE"])
    msg = str(exc_info.value)
    assert "CW_NOPE" in msg
    assert "CW_ALSO_NOPE" in msg


def test_assert_env_message_lists_only_missing(monkeypatch):
    monkeypatch.setenv("CW_PRESENT", "ok")
    monkeypatch.delenv("CW_ABSENT", raising=False)
    with pytest.raises(EnvironmentError) as exc_info:
        assert_env(["CW_PRESENT", "CW_ABSENT"])
    assert "CW_PRESENT" not in str(exc_info.value)
    assert "CW_ABSENT" in str(exc_info.value)
