"""Tests for cronwrap.digest_sender.send_digest."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from cronwrap.config import CronwrapConfig
from cronwrap.digest_sender import send_digest
from cronwrap.history import JobHistory, HistoryEntry


def _cfg(**kwargs) -> CronwrapConfig:
    defaults = dict(
        slack_webhook_url=None,
        email_to=None,
        email_from=None,
        smtp_host="localhost",
        smtp_port=25,
    )
    defaults.update(kwargs)
    return CronwrapConfig(**defaults)


def _write_job(tmp_path: Path, job: str) -> None:
    jh = JobHistory(job, tmp_path)
    jh.record(HistoryEntry(
        job_name=job, success=True, exit_code=0,
        duration=1.5, stdout="", stderr="",
    ))


def test_send_digest_returns_none_when_empty(tmp_path):
    result = send_digest(_cfg(), tmp_path)
    assert result is None


def test_send_digest_returns_body_text(tmp_path):
    _write_job(tmp_path, "backup")
    with patch("cronwrap.digest_sender.dispatch") as mock_dispatch:
        result = send_digest(_cfg(), tmp_path)
    assert result is not None
    assert "backup" in result
    mock_dispatch.assert_called_once()


def test_send_digest_json_format(tmp_path):
    _write_job(tmp_path, "sync")
    with patch("cronwrap.digest_sender.dispatch") as mock_dispatch:
        result = send_digest(_cfg(), tmp_path, fmt="json")
    assert result is not None
    import json
    parsed = json.loads(result)
    assert "entries" in parsed


def test_send_digest_passes_subject(tmp_path):
    _write_job(tmp_path, "myjob")
    with patch("cronwrap.digest_sender.dispatch") as mock_dispatch:
        send_digest(_cfg(), tmp_path, subject="Weekly Report")
    _, kwargs = mock_dispatch.call_args
    assert kwargs.get("subject") == "Weekly Report" or \
        mock_dispatch.call_args[0][1] == "Weekly Report" or \
        "Weekly Report" in str(mock_dispatch.call_args)


def test_send_digest_dispatch_called_with_config(tmp_path):
    _write_job(tmp_path, "etl")
    cfg = _cfg(slack_webhook_url="https://hooks.example.com/x")
    with patch("cronwrap.digest_sender.dispatch") as mock_dispatch:
        send_digest(cfg, tmp_path)
    call_kwargs = mock_dispatch.call_args[1]
    assert call_kwargs["config"] is cfg
