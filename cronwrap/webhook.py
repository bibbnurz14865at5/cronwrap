"""Webhook notification channel for cronwrap."""
from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

from cronwrap.runner import JobResult


class WebhookError(Exception):
    """Raised when a webhook delivery fails."""


def build_payload(job_name: str, result: JobResult, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build a JSON-serialisable payload describing the job result."""
    payload: Dict[str, Any] = {
        "job": job_name,
        "success": result.success,
        "exit_code": result.exit_code,
        "duration": round(result.duration, 3),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "timed_out": result.timed_out,
    }
    if extra:
        payload.update(extra)
    return payload


def send_webhook(
    url: str,
    payload: Dict[str, Any],
    *,
    timeout: int = 10,
    secret_header: Optional[str] = None,
) -> None:
    """POST *payload* as JSON to *url*.

    Args:
        url: Destination URL.
        payload: Dict that will be JSON-encoded.
        timeout: HTTP timeout in seconds.
        secret_header: Optional value for the ``X-Cronwrap-Secret`` header.

    Raises:
        WebhookError: On any HTTP or network error.
    """
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if secret_header:
        req.add_header("X-Cronwrap-Secret", secret_header)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            status = resp.status
    except urllib.error.HTTPError as exc:
        raise WebhookError(f"HTTP {exc.code} from {url}") from exc
    except urllib.error.URLError as exc:
        raise WebhookError(f"Network error posting to {url}: {exc.reason}") from exc
    if status >= 400:
        raise WebhookError(f"HTTP {status} from {url}")
