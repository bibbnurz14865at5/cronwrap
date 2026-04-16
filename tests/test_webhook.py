"""Tests for cronwrap.webhook."""
from __future__ import annotations

import json
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from cronwrap.runner import JobResult
from cronwrap.webhook import WebhookError, build_payload, send_webhook


def _make_result(success=True, exit_code=0, duration=1.5, stdout="ok", stderr="", timed_out=False):
    r = JobResult.__new__(JobResult)
    r.success = success
    r.exit_code = exit_code
    r.duration = duration
    r.stdout = stdout
    r.stderr = stderr
    r.timed_out = timed_out
    return r


def test_build_payload_keys():
    result = _make_result()
    payload = build_payload("myjob", result)
    assert payload["job"] == "myjob"
    assert payload["success"] is True
    assert payload["exit_code"] == 0
    assert payload["duration"] == 1.5
    assert payload["stdout"] == "ok"
    assert payload["stderr"] == ""
    assert payload["timed_out"] is False


def test_build_payload_extra_merged():
    result = _make_result()
    payload = build_payload("myjob", result, extra={"env": "prod"})
    assert payload["env"] == "prod"


def test_build_payload_duration_rounded():
    result = _make_result(duration=1.23456789)
    payload = build_payload("j", result)
    assert payload["duration"] == 1.235


class _FakeResponse:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_send_webhook_success():
    with patch("urllib.request.urlopen", return_value=_FakeResponse(200)):
        send_webhook("http://example.com/hook", {"job": "test"})


def test_send_webhook_sends_json():
    captured = {}

    def fake_urlopen(req, timeout):
        captured["data"] = req.data
        captured["content_type"] = req.get_header("Content-type")
        return _FakeResponse(200)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        send_webhook("http://example.com/hook", {"key": "value"})

    assert json.loads(captured["data"]) == {"key": "value"}
    assert captured["content_type"] == "application/json"


def test_send_webhook_secret_header():
    captured = {}

    def fake_urlopen(req, timeout):
        captured["secret"] = req.get_header("X-cronwrap-secret")
        return _FakeResponse(200)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        send_webhook("http://example.com/hook", {}, secret_header="tok123")

    assert captured["secret"] == "tok123"


def test_send_webhook_http_error_raises():
    exc = urllib.error.HTTPError("http://x.com", 500, "Server Error", {}, None)
    with patch("urllib.request.urlopen", side_effect=exc):
        with pytest.raises(WebhookError, match="HTTP 500"):
            send_webhook("http://x.com", {})


def test_send_webhook_url_error_raises():
    exc = urllib.error.URLError("connection refused")
    with patch("urllib.request.urlopen", side_effect=exc):
        with pytest.raises(WebhookError, match="Network error"):
            send_webhook("http://x.com", {})
