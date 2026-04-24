"""CLI sub-tool for inspecting job SLA policies."""
from __future__ import annotations

import argparse
import json
import sys

from cronwrap.job_sla import SLAError, SLAPolicy, check_sla


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-sla",
        description="Inspect and evaluate job SLA policies.",
    )
    sub = parser.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Print the SLA policy as JSON.")
    show.add_argument("config", help="Path to SLA JSON config file.")

    check = sub.add_parser("check", help="Evaluate whether a run breached the SLA.")
    check.add_argument("config", help="Path to SLA JSON config file.")
    check.add_argument("--duration", type=float, required=True, help="Job duration in seconds.")
    check.add_argument("--run-time", default=None, help="Completion time as HH:MM.")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    try:
        policy = SLAPolicy.from_json_file(args.config)
    except SLAError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.command == "show":
        print(json.dumps(policy.to_dict(), indent=2))
        return 0

    if args.command == "check":
        result = check_sla(policy, args.duration, run_time=args.run_time)
        status = "BREACHED" if result.breached else "OK"
        print(f"SLA {status}: {result.reason or 'within limits'}")
        return 1 if result.breached else 0

    return 0  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
