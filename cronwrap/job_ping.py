"""job_ping.py — Dead-man's-switch / healthcheck ping support.

Each job can register a ping URL (e.g. healthchecks.io) that is called
on success, failure, or both.  The result of the HTTP request is returned
so callers can decide whether to surface errors.
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class PingError(Exception):
    """Raised when a ping HTTP request fails."""


@dataclass
class PingConfig:
    job_name: str
    success_url: Optional[str] = None
    failure_url: Optional[str] = None
    start_url: Optional[str] = None
    timeout: int = 10

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        d: dict = {"job_name": self.job_name, "timeout": self.timeout}
        if self.success_url:
            d["success_url"] = self.success_url
        if self.failure_url:
            d["failure_url"] = self.failure_url
        if self.start_url:
            d["start_url"] = self.start_url
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "PingConfig":
        if "job_name" not in data:
            raise ValueError("PingConfig requires 'job_name'")
        return cls(
            job_name=data["job_name"],
            success_url=data.get("success_url"),
            failure_url=data.get("failure_url"),
            start_url=data.get("start_url"),
            timeout=int(data.get("timeout", 10)),
        )

    @classmethod
    def from_json_file(cls, path: str) -> "PingConfig":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Ping config not found: {path}")
        return cls.from_dict(json.loads(p.read_text()))


def send_ping(url: str, timeout: int = 10) -> int:
    """Send a GET request to *url*.  Returns the HTTP status code.

    Raises :class:`PingError` on network / HTTP errors.
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return resp.status
    except urllib.error.HTTPError as exc:
        raise PingError(f"HTTP {exc.code} pinging {url}") from exc
    except Exception as exc:
        raise PingError(f"Failed to ping {url}: {exc}") from exc


def ping_for_result(config: PingConfig, *, success: bool, start: bool = False) -> Optional[int]:
    """Send the appropriate ping URL based on *success*.

    If *start* is True and a ``start_url`` is configured, that URL is used
    regardless of *success*.  Returns the HTTP status code, or ``None`` when
    no URL is configured for the given outcome.
    """
    if start:
        url = config.start_url
    elif success:
        url = config.success_url
    else:
        url = config.failure_url

    if not url:
        return None
    return send_ping(url, timeout=config.timeout)
