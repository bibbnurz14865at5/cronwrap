"""Send a cronwrap digest via the configured notifier channel."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from cronwrap.config import CronwrapConfig
from cronwrap.digest import Digest, build_digest
from cronwrap.notifier import dispatch


def send_digest(
    config: CronwrapConfig,
    history_dir: Path,
    *,
    fmt: str = "text",
    subject: str = "Cronwrap Digest",
) -> Optional[str]:
    """Build and dispatch a digest report.

    Parameters
    ----------
    config:
        CronwrapConfig with notifier settings.
    history_dir:
        Directory containing per-job history JSON files.
    fmt:
        Output format — ``"text"`` or ``"json"``.
    subject:
        Subject line used for email notifications.

    Returns
    -------
    The rendered digest string, or ``None`` if nothing was sent because
    the digest contained no entries.
    """
    digest: Digest = build_digest(history_dir)
    if not digest.entries:
        return None

    body = digest.to_json() if fmt == "json" else digest.to_text()

    dispatch(
        config=config,
        subject=subject,
        body=body,
        job_name="__digest__",
    )
    return body
