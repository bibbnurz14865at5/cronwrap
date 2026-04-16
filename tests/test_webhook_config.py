"""Tests for cronwrap.webhook_config."""
from __future__ import annotations

import json
import pytest

from cronwrap.webhook_config import WebhookConfig


def test_from_dict_required_only():
    cfg = WebhookConfig.from_dict({"url": "http://example.com"})
    assert cfg.url == "http://example.com"
    assert cfg.timeout == 10
    assert cfg.secret_header is None


def test_from_dict_all_fields():
    cfg = WebhookConfig.from_dict({
        "url": "http://example.com/hook",
        "timeout": 5,
        "secret_header": "abc",
    })
    assert cfg.timeout == 5
    assert cfg.secret_header == "abc"


def test_from_dict_missing_url_raises():
    with pytest.raises(KeyError):
        WebhookConfig.from_dict({"timeout": 3})


def test_to_dict_roundtrip():
    original = WebhookConfig(url="http://x.com", timeout=7, secret_header="s")
    restored = WebhookConfig.from_dict(original.to_dict())
    assert restored.url == original.url
    assert restored.timeout == original.timeout
    assert restored.secret_header == original.secret_header


def test_from_json_file(tmp_path):
    cfg_file = tmp_path / "webhook.json"
    cfg_file.write_text(json.dumps({"url": "http://hook.io", "timeout": 8}))
    cfg = WebhookConfig.from_json_file(str(cfg_file))
    assert cfg.url == "http://hook.io"
    assert cfg.timeout == 8


def test_from_json_file_not_found():
    with pytest.raises(FileNotFoundError):
        WebhookConfig.from_json_file("/nonexistent/webhook.json")
