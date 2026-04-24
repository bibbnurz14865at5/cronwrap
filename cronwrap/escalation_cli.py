"""CLI helper for inspecting and resetting escalation state."""
from __future__ import annotations

import argparse
import json
import sys

from cronwrap.job_escalation import EscalationError, EscalationPolicy


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-escalation",
        description="Inspect or reset job escalation state.",
    )
    p.add_argument("--config", required=True, help="Path to escalation JSON config")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("show", help="Show current consecutive failure count")
    sub.add_parser("reset", help="Reset consecutive failure counter to zero")
    sub.add_parser("check", help="Exit 0 if NOT escalated, 1 if escalated")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    try:
        policy = EscalationPolicy.from_json_file(args.config)
    except EscalationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.command == "show":
        count = policy.consecutive_failures()
        print(json.dumps({"job_name": policy.job_name, "consecutive_failures": count}))
        return 0

    if args.command == "reset":
        policy.record_success()
        print(f"Reset escalation state for '{policy.job_name}'.")
        return 0

    if args.command == "check":
        if policy.should_escalate():
            print(
                f"ESCALATED: '{policy.job_name}' has "
                f"{policy.consecutive_failures()} consecutive failures "
                f"(threshold={policy.failure_threshold})"
            )
            return 1
        print(f"OK: '{policy.job_name}' is not escalated.")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
