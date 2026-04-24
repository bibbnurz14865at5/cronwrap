"""CLI for inspecting and managing job retry state."""
from __future__ import annotations

import argparse
import sys

from cronwrap.job_retry import RetryPolicy


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-retry",
        description="Inspect and manage job retry state.",
    )
    p.add_argument("--state-dir", default="/tmp/cronwrap/retry", metavar="DIR")
    sub = p.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Show retry state for a job")
    show.add_argument("job_name")

    reset = sub.add_parser("reset", help="Reset retry state for a job")
    reset.add_argument("job_name")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    policy = RetryPolicy(
        job_name=args.job_name,
        state_dir=args.state_dir,
    )

    if args.command == "show":
        attempts = policy.attempts()
        exhausted = policy.exhausted()
        print(f"job:       {args.job_name}")
        print(f"attempts:  {attempts} / {policy.max_retries}")
        print(f"exhausted: {exhausted}")
        return 0

    if args.command == "reset":
        policy.reset()
        print(f"Retry state cleared for '{args.job_name}'.")
        return 0

    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
