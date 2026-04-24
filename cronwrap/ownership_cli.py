"""CLI for managing job ownership records."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronwrap.job_ownership import JobOwnership, OwnerRecord, OwnershipError

_DEFAULT_PATH = Path(".cronwrap/ownership.json")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-ownership",
        description="Manage job ownership records.",
    )
    p.add_argument("--store", default=str(_DEFAULT_PATH), metavar="FILE")
    sub = p.add_subparsers(dest="command")

    s = sub.add_parser("set", help="Set owner for a job")
    s.add_argument("job_name")
    s.add_argument("owner")
    s.add_argument("--team", default=None)
    s.add_argument("--email", default=None)

    g = sub.add_parser("get", help="Show owner for a job")
    g.add_argument("job_name")

    r = sub.add_parser("remove", help="Remove ownership record")
    r.add_argument("job_name")

    t = sub.add_parser("team", help="List jobs for a team")
    t.add_argument("team_name")

    sub.add_parser("list", help="List all ownership records")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    store = JobOwnership(Path(args.store))

    if args.command == "set":
        store.set(
            OwnerRecord(
                job_name=args.job_name,
                owner=args.owner,
                team=args.team,
                email=args.email,
            )
        )
        print(f"Owner for '{args.job_name}' set to '{args.owner}'.")
        return 0

    if args.command == "get":
        rec = store.get(args.job_name)
        if rec is None:
            print(f"No ownership record for '{args.job_name}'.", file=sys.stderr)
            return 1
        print(f"job={rec.job_name}  owner={rec.owner}  team={rec.team}  email={rec.email}")
        return 0

    if args.command == "remove":
        try:
            store.remove(args.job_name)
            print(f"Removed ownership record for '{args.job_name}'.")
            return 0
        except OwnershipError as exc:
            print(str(exc), file=sys.stderr)
            return 1

    if args.command == "team":
        jobs = store.jobs_for_team(args.team_name)
        if not jobs:
            print(f"No jobs found for team '{args.team_name}'.")
        for j in jobs:
            print(j)
        return 0

    if args.command == "list":
        records = store.all_records()
        if not records:
            print("No ownership records.")
        for r in records:
            print(f"{r.job_name}: owner={r.owner}  team={r.team}  email={r.email}")
        return 0

    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
