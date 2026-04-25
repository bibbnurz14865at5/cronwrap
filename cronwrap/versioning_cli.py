"""CLI for inspecting job version history."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from cronwrap.job_versioning import JobVersioning, VersionRecord, VersioningError


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-version",
        description="Manage cron job version records.",
    )
    p.add_argument("--state-dir", default="/var/lib/cronwrap/versions", metavar="DIR")
    sub = p.add_subparsers(dest="command")

    rec = sub.add_parser("record", help="Record a new deployment version.")
    rec.add_argument("job_name")
    rec.add_argument("version")
    rec.add_argument("--by", dest="deployed_by", default=None)
    rec.add_argument("--notes", default=None)

    cur = sub.add_parser("current", help="Show the current version of a job.")
    cur.add_argument("job_name")

    hist = sub.add_parser("history", help="Show full version history for a job.")
    hist.add_argument("job_name")

    rb = sub.add_parser("rollback-target", help="Show the previous version (rollback candidate).")
    rb.add_argument("job_name")

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    store = JobVersioning(args.state_dir)

    if args.command == "record":
        now = datetime.now(timezone.utc).isoformat()
        rec = VersionRecord(
            job_name=args.job_name,
            version=args.version,
            deployed_at=now,
            deployed_by=args.deployed_by,
            notes=args.notes,
        )
        store.record(rec)
        print(json.dumps(rec.to_dict(), indent=2))
        return 0

    if args.command == "current":
        rec = store.current(args.job_name)
        if rec is None:
            print(f"No version recorded for '{args.job_name}'.")
            return 2
        print(json.dumps(rec.to_dict(), indent=2))
        return 0

    if args.command == "history":
        records = store.history(args.job_name)
        print(json.dumps([r.to_dict() for r in records], indent=2))
        return 0

    if args.command == "rollback-target":
        rec = store.rollback_target(args.job_name)
        if rec is None:
            print(f"No rollback target available for '{args.job_name}'.")
            return 2
        print(json.dumps(rec.to_dict(), indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
