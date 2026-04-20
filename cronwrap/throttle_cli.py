"""CLI for inspecting and resetting job throttle state."""
from __future__ import annotations

import argparse
import sys

from cronwrap.job_throttle import ThrottlePolicy


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-throttle",
        description="Inspect or reset job throttle state.",
    )
    p.add_argument("job_name", help="Name of the job")
    p.add_argument(
        "--min-interval",
        type=int,
        default=3600,
        metavar="SECONDS",
        help="Minimum interval between runs (default: 3600)",
    )
    p.add_argument(
        "--state-dir",
        default="/tmp/cronwrap/throttle",
        metavar="DIR",
        help="Directory where throttle state is stored",
    )
    sub = p.add_subparsers(dest="command")
    sub.add_parser("check", help="Show remaining throttle time")
    sub.add_parser("reset", help="Clear throttle state for the job")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    policy = ThrottlePolicy(
        job_name=args.job_name,
        min_interval_seconds=args.min_interval,
        state_dir=args.state_dir,
    )

    if args.command == "reset":
        policy.reset()
        print(f"Throttle state cleared for '{args.job_name}'.")
        return 0

    # default: check
    remaining = policy.check()
    if remaining > 0:
        print(f"THROTTLED  {remaining:.1f}s remaining for '{args.job_name}'.")
        return 1
    print(f"OK  '{args.job_name}' may run now.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
