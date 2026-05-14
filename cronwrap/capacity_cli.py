"""CLI for inspecting job capacity state."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwrap.job_capacity import CapacityError, CapacityPolicy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-capacity",
        description="Inspect job capacity slot usage.",
    )
    sub = parser.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Show capacity status for a job")
    show.add_argument("job_name", help="Job name")
    show.add_argument("--max-slots", type=int, default=1, help="Max concurrent slots")
    show.add_argument("--state-dir", default="/tmp/cronwrap/capacity", help="State directory")
    show.add_argument("--format", choices=["text", "json"], default="text")

    release = sub.add_parser("release", help="Release current PID slot for a job")
    release.add_argument("job_name", help="Job name")
    release.add_argument("--max-slots", type=int, default=1)
    release.add_argument("--state-dir", default="/tmp/cronwrap/capacity")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    policy = CapacityPolicy(
        job_name=args.job_name,
        max_slots=args.max_slots,
        state_dir=args.state_dir,
    )

    if args.command == "show":
        used = policy.used_slots()
        available = policy.available_slots()
        if getattr(args, "format", "text") == "json":
            print(json.dumps({"job_name": policy.job_name, "used": used, "available": available, "max_slots": policy.max_slots}))
        else:
            print(f"Job:       {policy.job_name}")
            print(f"Max slots: {policy.max_slots}")
            print(f"Used:      {used}")
            print(f"Available: {available}")
        return 0

    if args.command == "release":
        policy.release()
        print(f"Released slot for job '{policy.job_name}'")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
