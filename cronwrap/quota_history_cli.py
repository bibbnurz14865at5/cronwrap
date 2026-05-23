"""CLI for inspecting job quota usage history."""
from __future__ import annotations

import argparse
import json
import sys

from cronwrap.job_quota_history import QuotaHistory


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-quota-history",
        description="Inspect quota usage history for a job.",
    )
    sub = p.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Show quota usage history")
    show.add_argument("job_name", help="Job name")
    show.add_argument("--state-dir", default="/var/lib/cronwrap/quota", help="State directory")
    show.add_argument("--format", choices=["text", "json"], default="text")
    show.add_argument("--last", type=int, default=0, help="Show last N entries (0 = all)")

    clear = sub.add_parser("clear", help="Clear quota usage history")
    clear.add_argument("job_name", help="Job name")
    clear.add_argument("--state-dir", default="/var/lib/cronwrap/quota", help="State directory")

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    qh = QuotaHistory(job_name=args.job_name, state_dir=args.state_dir)

    if args.command == "show":
        snaps = qh.snapshots()
        if args.last > 0:
            snaps = snaps[-args.last:]
        if args.format == "json":
            print(json.dumps([s.to_dict() for s in snaps], indent=2))
        else:
            if not snaps:
                print(f"No quota history for job '{args.job_name}'.")
            for s in snaps:
                print(f"{s.timestamp}  used={s.used}/{s.limit}  ({s.pct_used}%)")
        return 0

    if args.command == "clear":
        qh.clear()
        print(f"Cleared quota history for '{args.job_name}'.")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
