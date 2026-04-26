"""CLI for inspecting job staleness."""
from __future__ import annotations

import argparse
import json
import sys

from cronwrap.job_stale import StaleError, StalePolicy, check_stale


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-stale",
        description="Check whether a cron job is stale (hasn't run recently enough).",
    )
    sub = parser.add_subparsers(dest="command")

    chk = sub.add_parser("check", help="Check staleness for a job")
    chk.add_argument("--config", required=True, help="Path to stale policy JSON file")
    chk.add_argument(
        "--json", dest="as_json", action="store_true", help="Output result as JSON"
    )

    return parser


def main(argv: list[str] | None = None) -> int:  # pragma: no branch
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "check":
        try:
            policy = StalePolicy.from_json_file(args.config)
        except StaleError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

        result = check_stale(policy)

        if args.as_json:
            print(
                json.dumps(
                    {
                        "job_name": result.job_name,
                        "is_stale": result.is_stale,
                        "last_run": result.last_run.isoformat() if result.last_run else None,
                        "age_seconds": result.age_seconds,
                        "max_age_seconds": result.max_age_seconds,
                        "reason": result.reason,
                    },
                    indent=2,
                )
            )
        else:
            status = "STALE" if result.is_stale else "OK"
            print(f"[{status}] {result.job_name}: {result.reason}")

        return 1 if result.is_stale else 0

    return 0  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
