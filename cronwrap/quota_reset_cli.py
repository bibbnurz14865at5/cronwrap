"""CLI for managing quota reset policies in cronwrap."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwrap.job_quota_reset import QuotaResetError, QuotaResetPolicy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-quota-reset",
        description="Manage quota reset windows for cron jobs.",
    )
    sub = parser.add_subparsers(dest="command")

    # check
    chk = sub.add_parser("check", help="Check whether a quota reset is due.")
    chk.add_argument("--config", required=True, help="Path to reset policy JSON file.")

    # reset
    rst = sub.add_parser("reset", help="Record a quota reset for a job.")
    rst.add_argument("--config", required=True, help="Path to reset policy JSON file.")

    # show
    shw = sub.add_parser("show", help="Show last reset time for a job.")
    shw.add_argument("--config", required=True, help="Path to reset policy JSON file.")

    return parser


def _load_policy(config_path: str) -> QuotaResetPolicy:
    p = Path(config_path)
    if not p.exists():
        print(f"Config file not found: {config_path}", file=sys.stderr)
        sys.exit(2)
    data = json.loads(p.read_text())
    return QuotaResetPolicy.from_dict(data)


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    try:
        policy = _load_policy(args.config)
    except QuotaResetError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.command == "check":
        due = policy.needs_reset()
        status = "DUE" if due else "OK"
        print(f"quota_reset_check job={policy.job_name} period={policy.period} status={status}")
        return 0 if not due else 3

    if args.command == "reset":
        ts = policy.reset()
        print(f"quota reset recorded job={policy.job_name} at={ts}")
        return 0

    if args.command == "show":
        last = policy.last_reset_time()
        if last:
            print(f"last_reset job={policy.job_name} at={last}")
        else:
            print(f"no reset recorded for job={policy.job_name}")
        return 0

    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
