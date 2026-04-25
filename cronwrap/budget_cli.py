"""CLI for inspecting and managing job execution budgets."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwrap.job_budget import BudgetPolicy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-budget",
        description="Inspect and manage job execution budgets.",
    )
    sub = parser.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Show current budget usage for a job.")
    show.add_argument("--config", required=True, help="Path to budget policy JSON file.")

    reset = sub.add_parser("reset", help="Reset the run counter for a job.")
    reset.add_argument("--config", required=True, help="Path to budget policy JSON file.")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        return 2

    try:
        data = json.loads(config_path.read_text())
        policy = BudgetPolicy.from_dict(data)
    except (ValueError, KeyError) as exc:
        print(f"Error loading config: {exc}", file=sys.stderr)
        return 3

    if args.command == "show":
        count = policy.current_count()
        remaining = policy.max_runs - count
        print(f"Job:       {policy.job_name}")
        print(f"Window:    {policy.window_seconds}s")
        print(f"Max runs:  {policy.max_runs}")
        print(f"Used:      {count}")
        print(f"Remaining: {max(remaining, 0)}")
        return 0

    if args.command == "reset":
        policy.reset()
        print(f"Budget reset for job '{policy.job_name}'.")
        return 0

    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
