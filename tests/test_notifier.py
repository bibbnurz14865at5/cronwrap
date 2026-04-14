"""Tests for cronwrap.notifier module."""

import json
import smtplib
from unittest.mock import MagicMock, patch

import pytest

from cronwrap.config import CronwrapConfig
from cronwrap.notifier import (
    NotificationError,
    dispatch,
    notify_email,
    notify_slack,
)


# ---------------------------------------------------------------------------
# notify_slack
# ---------------------------------------------------------------------------

class _FakeResponse:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *_): pass


def test_notify_slack_success():
    with patch("urllib.request.urlopen", return_value=_FakeResponse()) as mock_open:
        notify_slack("https://hooks.slack.com/fake", "something broke", job_name="backup")
    mock_open.assert_called_once()
    req = mock_open.call_args[0][0]
    body = json.loads(req.data.decode())
    assert "backup" in body["text"]
    assert "something broke" in body["text"]


def test_notify_slack_http_error():
    bad_resp = _FakeResponse()
    bad_resp.status = 500
    with patch("urllib.request.urlopen", return_value=bad_resp):
        with pytest.raises(NotificationError, match="HTTP 500"):
            notify_slack("https://hooks.slack.com/fake", "msg")


def test_notify_slack_network_error():
    import urllib.error
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
        with pytest.raises(NotificationError, match="Failed to reach"):
            notify_slack("https://hooks.slack.com/fake", "msg")


# ---------------------------------------------------------------------------
# notify_email
# ---------------------------------------------------------------------------

def test_notify_email_success():
    mock_server = MagicMock()
    with patch("smtplib.SMTP") as MockSMTP:
        MockSMTP.return_value.__enter__ = lambda s: mock_server
        MockSMTP.return_value.__exit__ = MagicMock(return_value=False)
        notify_email(
            smtp_host="smtp.example.com",
            smtp_port=587,
            sender="alerts@example.com",
            recipients=["ops@example.com"],
            message="disk full",
            job_name="cleanup",
        )
    mock_server.starttls.assert_called_once()
    mock_server.sendmail.assert_called_once()


def test_notify_email_smtp_exception():
    with patch("smtplib.SMTP") as MockSMTP:
        MockSMTP.return_value.__enter__ = MagicMock(side_effect=smtplib.SMTPException("conn refused"))
        MockSMTP.return_value.__exit__ = MagicMock(return_value=False)
        with pytest.raises(NotificationError, match="Failed to send email"):
            notify_email(
                smtp_host="smtp.example.com",
                smtp_port=587,
                sender="a@b.com",
                recipients=["c@d.com"],
                message="err",
            )


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------

def test_dispatch_calls_slack_and_email():
    cfg = CronwrapConfig(
        slack_webhook_url="https://hooks.slack.com/fake",
        smtp_host="smtp.example.com",
        email_recipients=["ops@example.com"],
        email_sender="bot@example.com",
    )
    with patch("cronwrap.notifier.notify_slack") as mock_slack, \
         patch("cronwrap.notifier.notify_email") as mock_email:
        dispatch(cfg, "failure output", job_name="etl")
    mock_slack.assert_called_once()
    mock_email.assert_called_once()


def test_dispatch_skips_email_when_no_smtp_host():
    cfg = CronwrapConfig(
        slack_webhook_url="https://hooks.slack.com/fake",
        email_recipients=["ops@example.com"],
    )
    with patch("cronwrap.notifier.notify_slack") as mock_slack, \
         patch("cronwrap.notifier.notify_email") as mock_email:
        dispatch(cfg, "msg")
    mock_slack.assert_called_once()
    mock_email.assert_not_called()


def test_dispatch_swallows_slack_error(caplog):
    cfg = CronwrapConfig(slack_webhook_url="https://hooks.slack.com/fake")
    with patch("cronwrap.notifier.notify_slack", side_effect=NotificationError("boom")):
        dispatch(cfg, "msg")  # should not raise
    assert "Slack notification failed" in caplog.text
