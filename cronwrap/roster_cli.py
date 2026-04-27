"""CLI interface for job roster management."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from cronwrap.job_roster import JobRoster, RosterEntry, RosterError

_DEFAULT_ROSTER = "roster.json"
_DEFAULT_HISTORY = "history"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-roster",
        description="Manage the expected-job roster.",
    )
    p.add_argument("--roster", default=_DEFAULT_ROSTER, help="Path to roster JSON file")
    p.add_argument("--history-dir", default=_DEFAULT_HISTORY, help="History directory")
    sub = p.add_subparsers(dest="command")

    reg = sub.add_parser("register", help="Register a job on the roster")
    reg.add_argument("job_name")
    reg.add_argument("--interval", type=int, required=True, help="Expected interval (seconds)")
    reg.add_argument("--description", default=None)

    rm = sub.add_parser("unregister", help="Remove a job from the roster")
    rm.add_argument("job_name")

    sub.add_parser("list", help="List all registered jobs")
    sub.add_parser("check", help="Report missing/overdue jobs")
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    roster = JobRoster(roster_path=args.roster, history_dir=args.history_dir)

    if args.command == "register":
        entry = RosterEntry(
            job_name=args.job_name,
            expected_interval_seconds=args.interval,
            description=args.description,
        )
        roster.register(entry)
        print(f"Registered {args.job_name!r} (interval={args.interval}s)")
        return 0

    if args.command == "unregister":
        try:
            roster.unregister(args.job_name)
            print(f"Unregistered {args.job_name!r}")
            return 0
        except RosterError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2

    if args.command == "list":
        entries = roster.list_entries()
        if not entries:
            print("No jobs registered.")
        else:
            print(json.dumps([e.to_dict() for e in entries], indent=2))
        return 0

    if args.command == "check":
        now = datetime.now(timezone.utc)
        missing = roster.check_missing(now=now)
        if not missing:
            print("All jobs are on schedule.")
            return 0
        for m in missing:
            last = m.last_seen.isoformat() if m.last_seen else "never"
            print(
                f"OVERDUE  {m.job_name}  last_seen={last}  "
                f"overdue_by={m.seconds_overdue:.1f}s"
            )
        return 3

    parser.print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
