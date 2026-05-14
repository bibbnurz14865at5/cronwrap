"""CLI for evaluating quota alert thresholds."""
from __future__ import annotations

import argparse
import json
import sys

from cronwrap.job_quota_alert import QuotaAlertError, QuotaAlertPolicy


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-quota-alert",
        description="Evaluate quota usage against alert thresholds.",
    )
    sub = p.add_subparsers(dest="command")

    ev = sub.add_parser("check", help="Check quota usage level")
    ev.add_argument("--config", required=True, help="Path to quota alert JSON config")
    ev.add_argument("--used", type=int, required=True, help="Current usage count")
    ev.add_argument("--limit", type=int, required=True, help="Maximum allowed count")
    ev.add_argument("--format", choices=["text", "json"], default="text")

    sh = sub.add_parser("show", help="Show alert policy configuration")
    sh.add_argument("--config", required=True, help="Path to quota alert JSON config")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    try:
        policy = QuotaAlertPolicy.from_json_file(args.config)
    except QuotaAlertError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.command == "show":
        print(json.dumps(policy.to_dict(), indent=2))
        return 0

    # check
    try:
        result = policy.evaluate(args.used, args.limit)
    except QuotaAlertError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(result.to_json())
    else:
        print(f"job={result.job_name} used={result.used}/{result.limit} ({result.pct}%) level={result.level}")

    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
