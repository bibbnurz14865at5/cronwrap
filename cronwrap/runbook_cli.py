"""CLI sub-commands for managing job runbooks."""
from __future__ import annotations

import argparse
import sys

from cronwrap.job_runbook import JobRunbook, RunbookEntry

_DEFAULT_STATE_DIR = "/var/lib/cronwrap"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-runbook",
        description="Manage runbook entries for cron jobs.",
    )
    parser.add_argument("--state-dir", default=_DEFAULT_STATE_DIR, help="State directory")
    sub = parser.add_subparsers(dest="command")

    # set
    p_set = sub.add_parser("set", help="Attach a runbook to a job")
    p_set.add_argument("job_name")
    p_set.add_argument("--url", default=None)
    p_set.add_argument("--notes", default=None)
    p_set.add_argument("--tags", nargs="*", default=[])

    # get
    p_get = sub.add_parser("get", help="Show runbook for a job")
    p_get.add_argument("job_name")

    # remove
    p_rm = sub.add_parser("remove", help="Remove runbook for a job")
    p_rm.add_argument("job_name")

    # list
    sub.add_parser("list", help="List all runbook entries")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    rb = JobRunbook(args.state_dir)

    if args.command == "set":
        entry = RunbookEntry(
            job_name=args.job_name,
            url=args.url,
            notes=args.notes,
            tags=args.tags or [],
        )
        rb.set(entry)
        print(f"Runbook set for '{args.job_name}'.")
        return 0

    if args.command == "get":
        entry = rb.get(args.job_name)
        if entry is None:
            print(f"No runbook found for '{args.job_name}'.", file=sys.stderr)
            return 1
        print(f"job:   {entry.job_name}")
        print(f"url:   {entry.url or '(none)'}")
        print(f"notes: {entry.notes or '(none)'}")
        print(f"tags:  {', '.join(entry.tags) or '(none)'}")
        return 0

    if args.command == "remove":
        removed = rb.remove(args.job_name)
        if not removed:
            print(f"No runbook found for '{args.job_name}'.", file=sys.stderr)
            return 1
        print(f"Runbook removed for '{args.job_name}'.")
        return 0

    if args.command == "list":
        entries = rb.all_entries()
        if not entries:
            print("No runbook entries found.")
            return 0
        for e in entries:
            url_part = f"  url={e.url}" if e.url else ""
            print(f"{e.job_name}{url_part}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
