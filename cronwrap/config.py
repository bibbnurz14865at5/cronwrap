"""Configuration model for cronwrap."""

import json
import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CronwrapConfig:
    # Slack
    slack_webhook_url: Optional[str] = None

    # Email / SMTP
    email_recipients: List[str] = field(default_factory=list)
    email_sender: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: Optional[bool] = True

    # General
    timeout_seconds: Optional[int] = None
    notify_on_success: bool = False
    log_output: bool = True


KNOWN_FIELDS = {f.name for f in CronwrapConfig.__dataclass_fields__.values()}  # type: ignore[attr-defined]


def from_dict(data: dict) -> CronwrapConfig:
    """Build a CronwrapConfig from a plain dictionary, ignoring unknown keys."""
    filtered = {k: v for k, v in data.items() if k in KNOWN_FIELDS}
    return CronwrapConfig(**filtered)


def from_json_file(path: str) -> CronwrapConfig:
    """Load configuration from a JSON file."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return from_dict(data)


def from_env() -> CronwrapConfig:
    """Build a CronwrapConfig from environment variables (prefixed with CRONWRAP_)."""
    mapping = {
        "slack_webhook_url": os.getenv("CRONWRAP_SLACK_WEBHOOK_URL"),
        "email_recipients": [
            r.strip()
            for r in os.getenv("CRONWRAP_EMAIL_RECIPIENTS", "").split(",")
            if r.strip()
        ],
        "email_sender": os.getenv("CRONWRAP_EMAIL_SENDER"),
        "smtp_host": os.getenv("CRONWRAP_SMTP_HOST"),
        "smtp_port": int(os.getenv("CRONWRAP_SMTP_PORT", "587")),
        "smtp_username": os.getenv("CRONWRAP_SMTP_USERNAME"),
        "smtp_password": os.getenv("CRONWRAP_SMTP_PASSWORD"),
        "smtp_use_tls": os.getenv("CRONWRAP_SMTP_USE_TLS", "true").lower() != "false",
        "timeout_seconds": int(t) if (t := os.getenv("CRONWRAP_TIMEOUT_SECONDS")) else None,
        "notify_on_success": os.getenv("CRONWRAP_NOTIFY_ON_SUCCESS", "false").lower() == "true",
        "log_output": os.getenv("CRONWRAP_LOG_OUTPUT", "true").lower() != "false",
    }
    return from_dict(mapping)
