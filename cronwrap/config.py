"""Configuration loader for cronwrap."""

import os
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CronwrapConfig:
    """Holds configuration for a cronwrap job."""

    command: str
    job_name: str = "unnamed-job"
    timeout: Optional[int] = None  # seconds
    slack_webhook_url: Optional[str] = None
    email_recipients: list = field(default_factory=list)
    notify_on_success: bool = False
    notify_on_failure: bool = True
    env_file: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "CronwrapConfig":
        """Create a CronwrapConfig from a dictionary."""
        allowed = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in allowed}
        return cls(**filtered)

    @classmethod
    def from_json_file(cls, path: str) -> "CronwrapConfig":
        """Load config from a JSON file."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_env(cls, command: str) -> "CronwrapConfig":
        """Build a minimal config from environment variables."""
        return cls(
            command=command,
            job_name=os.environ.get("CRONWRAP_JOB_NAME", "unnamed-job"),
            timeout=int(os.environ["CRONWRAP_TIMEOUT"]) if os.environ.get("CRONWRAP_TIMEOUT") else None,
            slack_webhook_url=os.environ.get("CRONWRAP_SLACK_WEBHOOK"),
            email_recipients=[
                e.strip()
                for e in os.environ.get("CRONWRAP_EMAIL_RECIPIENTS", "").split(",")
                if e.strip()
            ],
            notify_on_success=os.environ.get("CRONWRAP_NOTIFY_SUCCESS", "false").lower() == "true",
            notify_on_failure=os.environ.get("CRONWRAP_NOTIFY_FAILURE", "true").lower() == "true",
        )
