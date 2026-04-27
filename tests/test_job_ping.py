"""Tests for cronwrap.job_ping."""
from __future__ import annotations

import json
import pytest
from unittest.mock import patch, MagicMock

from cronwrap.job_ping import PingConfig, PingError, send_ping, ping_for_result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg(**kwargs) -> PingConfig:
    base = {"job_name": "backup", "success_url": "https://hc.io/ok",
            "failure_url": "https://hc.io/fail", "start_url": "https://hc.io/start"}
    base.update(kwargs)
    return PingConfig.from_dict(base)


# ---------------------------------------------------------------------------
# PingConfig serialisation
# ---------------------------------------------------------------------------

def test_from_dict_required_only():
    cfg = PingConfig.from_dict({"job_name": "myjob"})
    assert cfg.job_name == "myjob"
    assert cfg.success_url is None
    assert cfg.failure_url is None
    assert cfg.start_url is None
    assert cfg.timeout == 10


def test_from_dict_full():
    cfg = _cfg(timeout=5)
    assert cfg.success_url == "https://hc.io/ok"
    assert cfg.failure_url == "https://hc.io/fail"
    assert cfg.start_url == "https://hc.io/start"
    assert cfg.timeout == 5


def test_from_dict_missing_job_name_raises():
    with pytest.raises(ValueError, match="job_name"):
        PingConfig.from_dict({"success_url": "https://hc.io/ok"})


def test_to_dict_roundtrip():
    cfg = _cfg()
    assert PingConfig.from_dict(cfg.to_dict()).to_dict() == cfg.to_dict()


def test_to_dict_omits_none_urls():
    cfg = PingConfig.from_dict({"job_name": "x"})
    d = cfg.to_dict()
    assert "success_url" not in d
    assert "failure_url" not in d
    assert "start_url" not in d


def test_from_json_file(tmp_path):
    p = tmp_path / "ping.json"
    p.write_text(json.dumps({"job_name": "nightly", "success_url": "https://x.io/ok"}))
    cfg = PingConfig.from_json_file(str(p))
    assert cfg.job_name == "nightly"


def test_from_json_file_not_found():
    with pytest.raises(FileNotFoundError):
        PingConfig.from_json_file("/nonexistent/ping.json")


# ---------------------------------------------------------------------------
# send_ping
# ---------------------------------------------------------------------------

def _mock_urlopen(status: int = 200):
    cm = MagicMock()
    cm.__enter__ = lambda s: MagicMock(status=status)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def test_send_ping_success():
    with patch("cronwrap.job_ping.urllib.request.urlopen", return_value=_mock_urlopen(200)):
        code = send_ping("https://hc.io/ok")
    assert code == 200


def test_send_ping_http_error_raises():
    import urllib.error
    with patch("cronwrap.job_ping.urllib.request.urlopen",
               side_effect=urllib.error.HTTPError(None, 500, "err", {}, None)):
        with pytest.raises(PingError, match="HTTP 500"):
            send_ping("https://hc.io/ok")


def test_send_ping_network_error_raises():
    with patch("cronwrap.job_ping.urllib.request.urlopen",
               side_effect=OSError("timeout")):
        with pytest.raises(PingError, match="Failed to ping"):
            send_ping("https://hc.io/ok")


# ---------------------------------------------------------------------------
# ping_for_result
# ---------------------------------------------------------------------------

def test_ping_for_result_success_calls_success_url():
    cfg = _cfg()
    with patch("cronwrap.job_ping.send_ping", return_value=200) as mock_send:
        result = ping_for_result(cfg, success=True)
    mock_send.assert_called_once_with(cfg.success_url, timeout=cfg.timeout)
    assert result == 200


def test_ping_for_result_failure_calls_failure_url():
    cfg = _cfg()
    with patch("cronwrap.job_ping.send_ping", return_value=200) as mock_send:
        ping_for_result(cfg, success=False)
    mock_send.assert_called_once_with(cfg.failure_url, timeout=cfg.timeout)


def test_ping_for_result_start_calls_start_url():
    cfg = _cfg()
    with patch("cronwrap.job_ping.send_ping", return_value=200) as mock_send:
        ping_for_result(cfg, success=True, start=True)
    mock_send.assert_called_once_with(cfg.start_url, timeout=cfg.timeout)


def test_ping_for_result_returns_none_when_no_url():
    cfg = PingConfig.from_dict({"job_name": "x"})
    result = ping_for_result(cfg, success=True)
    assert result is None
