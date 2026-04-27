"""CLI for inspecting quota audit logs."""
from __future__ import annotations

import argparse
import json
import sys

from cronwrap.job_quota_audit import QuotaAuditLog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-quota-audit",
        description="Inspect quota audit events for cron jobs.",
    )
    parser.add_argument("--log-dir", default="/var/lib/cronwrap/quota_audit", help="Audit log directory")
    sub = parser.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Show audit events for a job")
    show.add_argument("job_name", help="Job name")
    show.add_argument("--format", choices=["text", "json"], default="text")

    clear = sub.add_parser("clear", help="Clear audit log for a job")
    clear.add_argument("job_name", help="Job name")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    log = QuotaAuditLog(args.log_dir)

    if args.command == "show":
        events = log.events(args.job_name)
        if not events:
            print(f"No audit events found for '{args.job_name}'.")
            return 0
        if args.format == "json":
            print(json.dumps([e.to_dict() for e in events], indent=2))
        else:
            for e in events:
                reason = f" ({e.reason})" if e.reason else ""
                print(f"[{e.timestamp}] {e.action.upper()} used={e.quota_used}/{e.quota_limit}{reason}")
        return 0

    if args.command == "clear":
        log.clear(args.job_name)
        print(f"Cleared quota audit log for '{args.job_name}'.")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
