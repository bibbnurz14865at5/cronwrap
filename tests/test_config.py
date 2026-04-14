"""Tests for cronwrap.config module."""

import json
import os
import pytest
from cronwrap.config import CronwrapConfig


def test_from_dict_basic():
    cfg = CronwrapConfig.from_dict({"command": "echo hello", "job_name": "test-job"})
    assert cfg.command == "echo hello"
    assert cfg.job_name == "test-job"
    assert cfg.timeout is None
    assert cfg.notify_on_failure is True


def test_from_dict_ignores_unknown_keys():
    cfg = CronwrapConfig.from_dict({"command": "ls", "unknown_key": "value"})
    assert cfg.command == "ls"
    assert not hasattr(cfg, "unknown_key")


def test_from_json_file(tmp_path):
    config_data = {
        "command": "backup.sh",
        "job_name": "nightly-backup",
        "timeout": 300,
        "notify_on_success": True,
    }
    config_file = tmp_path / "cronwrap.json"
    config_file.write_text(json.dumps(config_data))

    cfg = CronwrapConfig.from_json_file(str(config_file))
    assert cfg.command == "backup.sh"
    assert cfg.job_name == "nightly-backup"
    assert cfg.timeout == 300
    assert cfg.notify_on_success is True


def test_from_json_file_not_found():
    with pytest.raises(FileNotFoundError):
        CronwrapConfig.from_json_file("/nonexistent/path/config.json")


def test_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_JOB_NAME", "env-job")
    monkeypatch.setenv("CRONWRAP_TIMEOUT", "60")
    monkeypatch.setenv("CRONWRAP_SLACK_WEBHOOK", "https://hooks.slack.com/test")
    monkeypatch.setenv("CRONWRAP_EMAIL_RECIPIENTS", "a@example.com, b@example.com")
    monkeypatch.setenv("CRONWRAP_NOTIFY_SUCCESS", "true")

    cfg = CronwrapConfig.from_env("my-command")
    assert cfg.command == "my-command"
    assert cfg.job_name == "env-job"
    assert cfg.timeout == 60
    assert cfg.slack_webhook_url == "https://hooks.slack.com/test"
    assert cfg.email_recipients == ["a@example.com", "b@example.com"]
    assert cfg.notify_on_success is True


def test_from_env_defaults(monkeypatch):
    for key in ["CRONWRAP_JOB_NAME", "CRONWRAP_TIMEOUT", "CRONWRAP_SLACK_WEBHOOK",
                "CRONWRAP_EMAIL_RECIPIENTS", "CRONWRAP_NOTIFY_SUCCESS", "CRONWRAP_NOTIFY_FAILURE"]:
        monkeypatch.delenv(key, raising=False)

    cfg = CronwrapConfig.from_env("default-cmd")
    assert cfg.job_name == "unnamed-job"
    assert cfg.timeout is None
    assert cfg.email_recipients == []
    assert cfg.notify_on_failure is True
