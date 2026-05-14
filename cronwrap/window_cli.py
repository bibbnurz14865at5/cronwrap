"""CLI for inspecting execution window policies."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from cronwrap.job_window import WindowError, WindowPolicy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-window",
        description="Inspect job execution window policies.",
    )
    sub = parser.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Show policy details")
    show.add_argument("config", help="Path to window policy JSON file")
    show.add_argument("--format", choices=["text", "json"], default="text")

    check = sub.add_parser("check", help="Check if a job is allowed to run now")
    check.add_argument("config", help="Path to window policy JSON file")
    check.add_argument("--at", help="ISO datetime to check (default: now)")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    try:
        policy = WindowPolicy.from_json_file(args.config)
    except WindowError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.command == "show":
        if args.format == "json":
            print(json.dumps(policy.to_dict(), indent=2))
        else:
            print(f"Job      : {policy.job_name}")
            print(f"Timezone : {policy.timezone}")
            print(f"Windows  : {len(policy.windows)}")
            for i, w in enumerate(policy.windows, 1):
                days = w.get("weekdays", "all")
                print(f"  [{i}] {w.get('start')} – {w.get('end')}  weekdays={days}")
        return 0

    if args.command == "check":
        dt = None
        if args.at:
            try:
                dt = datetime.fromisoformat(args.at)
            except ValueError as exc:
                print(f"Invalid --at value: {exc}", file=sys.stderr)
                return 2
        allowed = policy.is_allowed(dt)
        status = "ALLOWED" if allowed else "BLOCKED"
        print(f"{policy.job_name}: {status}")
        return 0 if allowed else 3

    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
