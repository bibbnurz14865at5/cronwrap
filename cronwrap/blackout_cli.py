"""CLI for inspecting and testing blackout windows."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from cronwrap.job_blackout import BlackoutPolicy, BlackoutError


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-blackout",
        description="Inspect blackout windows for a job.",
    )
    sub = p.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Show blackout policy from a JSON file")
    show.add_argument("config", help="Path to blackout JSON config")

    check = sub.add_parser("check", help="Check whether the job is currently blacked out")
    check.add_argument("config", help="Path to blackout JSON config")
    check.add_argument(
        "--at",
        default=None,
        metavar="YYYY-MM-DDTHH:MM",
        help="Check at a specific datetime instead of now",
    )

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    try:
        policy = BlackoutPolicy.from_json_file(args.config)
    except BlackoutError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.command == "show":
        print(json.dumps(policy.to_dict(), indent=2))
        return 0

    if args.command == "check":
        dt = None
        if args.at:
            try:
                dt = datetime.strptime(args.at, "%Y-%m-%dT%H:%M")
            except ValueError:
                print("error: --at must be YYYY-MM-DDTHH:MM", file=sys.stderr)
                return 2
        blacked_out = policy.is_blacked_out(dt)
        status = "BLACKED OUT" if blacked_out else "active"
        print(f"{policy.job_name}: {status}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
