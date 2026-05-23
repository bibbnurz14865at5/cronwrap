"""CLI for managing job grace periods."""
from __future__ import annotations

import argparse
import json
import sys

from cronwrap.job_grace_period import GracePeriodError, GracePeriodPolicy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-grace",
        description="Manage grace periods for cron jobs.",
    )
    sub = parser.add_subparsers(dest="command")

    act = sub.add_parser("activate", help="Activate a grace period for a job")
    act.add_argument("--job", required=True, help="Job name")
    act.add_argument("--duration", type=int, required=True, help="Duration in seconds")
    act.add_argument("--state-dir", default="/tmp/cronwrap/grace", dest="state_dir")
    act.add_argument("--reason", default=None)

    chk = sub.add_parser("check", help="Check whether a grace period is active")
    chk.add_argument("--job", required=True, help="Job name")
    chk.add_argument("--state-dir", default="/tmp/cronwrap/grace", dest="state_dir")
    chk.add_argument("--format", choices=["text", "json"], default="text", dest="fmt")

    deact = sub.add_parser("deactivate", help="Deactivate a grace period for a job")
    deact.add_argument("--job", required=True, help="Job name")
    deact.add_argument("--state-dir", default="/tmp/cronwrap/grace", dest="state_dir")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "activate":
            policy = GracePeriodPolicy(
                job_name=args.job,
                duration_seconds=args.duration,
                state_dir=args.state_dir,
                reason=args.reason,
            )
            policy.activate()
            print(f"Grace period activated for '{args.job}' ({args.duration}s).")
            return 0

        if args.command == "check":
            policy = GracePeriodPolicy(
                job_name=args.job,
                duration_seconds=0,
                state_dir=args.state_dir,
            )
            active = policy.is_active()
            if args.fmt == "json":
                print(json.dumps({"job_name": args.job, "grace_active": active}))
            else:
                status = "ACTIVE" if active else "INACTIVE"
                print(f"Grace period for '{args.job}': {status}")
            return 0

        if args.command == "deactivate":
            policy = GracePeriodPolicy(
                job_name=args.job,
                duration_seconds=0,
                state_dir=args.state_dir,
            )
            policy.deactivate()
            print(f"Grace period deactivated for '{args.job}'.")
            return 0

    except GracePeriodError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
