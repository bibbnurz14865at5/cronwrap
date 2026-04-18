"""CLI entry-point for cronwrap."""

import argparse
import sys
from typing import List, Optional

from cronwrap.config import CronwrapConfig, from_env, from_json_file
from cronwrap.lock import JobLock, LockError
from cronwrap.notifier import dispatch
from cronwrap.runner import run_job


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap",
        description="Wrap a cron command with failure alerting.",
    )
    parser.add_argument("--config", metavar="FILE", help="Path to JSON config file.")
    parser.add_argument("--job", metavar="NAME", help="Human-readable job name.", default="cron-job")
    parser.add_argument("--timeout", metavar="SECS", type=int, default=0, help="Kill job after N seconds.")
    parser.add_argument("--lock", action="store_true", help="Prevent overlapping executions via file lock.")
    parser.add_argument("--lock-dir", metavar="DIR", default="/tmp", help="Directory for lock files.")
    parser.add_argument("--lock-timeout", metavar="SECS", type=int, default=0, help="Seconds to wait for lock.")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run (after --)")
    return parser


def _load_config(path: Optional[str]) -> CronwrapConfig:
    if path:
        try:
            return from_json_file(path)
        except FileNotFoundError:
            print(f"[cronwrap] config file not found: {path}", file=sys.stderr)
            sys.exit(1)
        except Exception as exc:
            print(f"[cronwrap] failed to load config: {exc}", file=sys.stderr)
            sys.exit(1)
    return from_env()


def _strip_double_dash(args: List[str]) -> List[str]:
    """Remove a leading '--' separator from the command list if present."""
    if args and args[0] == "--":
        return args[1:]
    return args


def main(argv: Optional[List[str]] = None) -> int:  # noqa: C901
    parser = build_parser()
    ns = parser.parse_args(argv)

    command = _strip_double_dash(ns.command)
    if not command:
        parser.error("No command specified.")

    cfg = _load_config(ns.config)

    # ------------------------------------------------------------------ lock
    lock: Optional[JobLock] = None
    if ns.lock:
        lock = JobLock(ns.job, lock_dir=ns.lock_dir, timeout=ns.lock_timeout)
        try:
            lock.acquire()
        except LockError as exc:
            print(f"[cronwrap] {exc}", file=sys.stderr)
            return 1

    # ------------------------------------------------------------------ run
    try:
        result = run_job(command, timeout=ns.timeout or None)
    finally:
        if lock is not None:
            lock.release()

    print(result.summary(ns.job))

    if not result.success:
        try:
            dispatch(cfg, ns.job, result)
        except Exception as exc:  # pragma: no cover
            print(f"[cronwrap] notification failed: {exc}", file=sys.stderr)

    return 0 if result.success else result.returncode or 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
