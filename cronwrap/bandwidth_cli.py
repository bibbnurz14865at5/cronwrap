"""CLI for inspecting job bandwidth records."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwrap.job_bandwidth import BandwidthPolicy, BandwidthError


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-bandwidth",
        description="Inspect job bandwidth usage records.",
    )
    sub = p.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Show last bandwidth record for a job")
    show.add_argument("job_name")
    show.add_argument("--state-dir", default="/tmp/cronwrap/bandwidth")
    show.add_argument("--format", choices=["text", "json"], default="text")

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "show":
        try:
            policy = BandwidthPolicy(
                job_name=args.job_name,
                max_bytes_per_run=0,
                state_dir=args.state_dir,
            )
            record = policy.last_record()
        except BandwidthError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

        if record is None:
            print(f"No bandwidth record found for job '{args.job_name}'.")
            return 0

        if args.format == "json":
            print(json.dumps(record, indent=2))
        else:
            print(f"job:       {record['job_name']}")
            print(f"bytes:     {record['bytes_used']}")
            print(f"limit:     {record['max_bytes_per_run']}")
            print(f"exceeded:  {record['exceeded']}")
            print(f"warn:      {record['warn']}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
