"""CLI for inspecting and managing the dead-letter queue."""
from __future__ import annotations

import argparse
import json
import sys

from cronwrap.job_deadletter import DeadLetterQueue

_DEFAULT_DIR = "/var/lib/cronwrap/deadletter"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-deadletter",
        description="Manage the cronwrap dead-letter queue.",
    )
    p.add_argument("--queue-dir", default=_DEFAULT_DIR, help="Dead-letter queue directory")
    sub = p.add_subparsers(dest="command")

    show = sub.add_parser("show", help="List dead-letter events for a job")
    show.add_argument("job_name")

    purge = sub.add_parser("purge", help="Purge dead-letter events for a job")
    purge.add_argument("job_name")

    sub.add_parser("list", help="List all jobs with dead-letter events")
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    q = DeadLetterQueue(args.queue_dir)

    if args.command == "list":
        names = q.all_job_names()
        if not names:
            print("No dead-letter events found.")
        else:
            for name in names:
                print(name)
        return 0

    if args.command == "show":
        events = q.list_events(args.job_name)
        if not events:
            print(f"No dead-letter events for job '{args.job_name}'.")
            return 0
        print(json.dumps([e.to_dict() for e in events], indent=2))
        return 0

    if args.command == "purge":
        count = q.purge(args.job_name)
        print(f"Purged {count} event(s) for job '{args.job_name}'.")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
