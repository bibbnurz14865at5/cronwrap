"""Load and validate webhook configuration for cronwrap."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class WebhookConfig:
    url: str
    timeout: int = 10
    secret_header: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "timeout": self.timeout,
            "secret_header": self.secret_header,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WebhookConfig":
        return cls(
            url=data["url"],
            timeout=int(data.get("timeout", 10)),
            secret_header=data.get("secret_header"),
        )

    @classmethod
    def from_json_file(cls, path: str) -> "WebhookConfig":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Webhook config not found: {path}")
        with p.open() as fh:
            return cls.from_dict(json.load(fh))
