"""CLI for managing job notification suppression."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone, timedelta

from cronwrap.job_suppression import JobSuppression


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-suppression",
        description="Manage job notification suppression",
    )
    sub = parser.add_subparsers(dest="command")

    sup = sub.add_parser("suppress", help="Suppress notifications for a job")
    sup.add_argument("job_name")
    sup.add_argument("--minutes", type=int, default=60, help="Duration in minutes (default: 60)")
    sup.add_argument("--reason", default=None)
    sup.add_argument("--state-dir", default="/tmp/cronwrap/suppression")

    res = sub.add_parser("resume", help="Resume notifications for a job")
    res.add_argument("job_name")
    res.add_argument("--state-dir", default="/tmp/cronwrap/suppression")

    chk = sub.add_parser("check", help="Check if a job is suppressed")
    chk.add_argument("job_name")
    chk.add_argument("--state-dir", default="/tmp/cronwrap/suppression")

    lst = sub.add_parser("list", help="List all active suppressions")
    lst.add_argument("--state-dir", default="/tmp/cronwrap/suppression")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    js = JobSuppression(state_dir=args.state_dir)

    if args.command == "suppress":
        until = datetime.now(timezone.utc) + timedelta(minutes=args.minutes)
        state = js.suppress(args.job_name, until=until, reason=args.reason)
        print(f"Suppressed '{args.job_name}' until {state.suppressed_until.isoformat()}")
        return 0

    if args.command == "resume":
        js.resume(args.job_name)
        print(f"Resumed notifications for '{args.job_name}'")
        return 0

    if args.command == "check":
        suppressed = js.is_suppressed(args.job_name)
        status = "suppressed" if suppressed else "active"
        print(f"{args.job_name}: {status}")
        return 0 if not suppressed else 2

    if args.command == "list":
        states = js.list_suppressed()
        if not states:
            print("No active suppressions.")
        for s in states:
            reason = f" ({s.reason})" if s.reason else ""
            print(f"{s.job_name}: until {s.suppressed_until.isoformat()}{reason}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
