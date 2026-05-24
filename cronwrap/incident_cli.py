"""CLI for managing job incidents."""
from __future__ import annotations

import argparse
import json
import sys

from cronwrap.job_incident import IncidentError, JobIncident

_DEFAULT_STATE_DIR = "/var/lib/cronwrap/incidents"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-incident",
        description="Manage cron job incidents",
    )
    p.add_argument("--state-dir", default=_DEFAULT_STATE_DIR, help="Incident state directory")
    sub = p.add_subparsers(dest="command")

    op = sub.add_parser("open", help="Open a new incident")
    op.add_argument("job_name")
    op.add_argument("--reason", default=None)

    rp = sub.add_parser("resolve", help="Resolve an open incident")
    rp.add_argument("job_name")
    rp.add_argument("incident_id")

    lp = sub.add_parser("list", help="List incidents for a job")
    lp.add_argument("job_name")
    lp.add_argument("--open-only", action="store_true", default=False)
    lp.add_argument("--format", choices=["text", "json"], default="text")

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    store = JobIncident(args.state_dir)

    if args.command == "open":
        rec = store.open(args.job_name, reason=args.reason)
        print(f"Opened incident {rec.incident_id} for job {rec.job_name!r}")
        return 0

    if args.command == "resolve":
        try:
            rec = store.resolve(args.job_name, args.incident_id)
            print(f"Resolved incident {rec.incident_id} (resolved_at={rec.resolved_at})")
            return 0
        except IncidentError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2

    if args.command == "list":
        records = (
            store.list_open(args.job_name)
            if args.open_only
            else store.list_all(args.job_name)
        )
        if args.format == "json":
            print(json.dumps([r.to_dict() for r in records], indent=2))
        else:
            if not records:
                print("No incidents found.")
            for r in records:
                line = f"[{r.status.upper()}] {r.incident_id}  opened={r.opened_at}"
                if r.reason:
                    line += f"  reason={r.reason}"
                print(line)
        return 0

    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
