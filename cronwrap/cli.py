"""Entry-point CLI for cronwrap.

Usage example::

    cronwrap --config /etc/cronwrap.json -- /usr/bin/backup.sh --full
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from cronwrap.config import CronwrapConfig, from_env, from_json_file
from cronwrap.notifier import dispatch
from cronwrap.runner import JobResult, run_job


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap",
        description="Wrap a cron command and alert on failure.",
    )
    parser.add_argument(
        "--config", "-c",
        metavar="FILE",
        help="Path to a JSON config file (falls back to environment variables).",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=None,
        metavar="SECONDS",
        help="Kill the job after this many seconds.",
    )
    parser.add_argument(
        "--notify-on-success",
        action="store_true",
        default=False,
        help="Send a notification even when the job succeeds.",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to run (use -- to separate from cronwrap flags).",
    )
    return parser


def _load_config(config_path: Optional[str]) -> CronwrapConfig:
    if config_path:
        return from_json_file(config_path)
    return from_env()


def _strip_double_dash(args: List[str]) -> List[str]:
    """Remove a leading '--' separator that argparse leaves in REMAINDER."""
    if args and args[0] == "--":
        return args[1:]
    return args


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)

    command = _strip_double_dash(ns.command)
    if not command:
        parser.error("No command specified.")

    cfg = _load_config(ns.config)
    result: JobResult = run_job(command, timeout=ns.timeout)

    if not result.success or ns.notify_on_success:
        try:
            dispatch(cfg, result.summary())
        except Exception as exc:  # noqa: BLE001
            print(f"[cronwrap] notification error: {exc}", file=sys.stderr)

    return 0 if result.success else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
