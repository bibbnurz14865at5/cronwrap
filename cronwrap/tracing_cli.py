"""CLI for inspecting job trace records."""
from __future__ import annotations

import argparse
import json
import sys

from cronwrap.job_tracing import JobTracing, TracingError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-tracing",
        description="Inspect job distributed trace records.",
    )
    sub = parser.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Show the current trace for a job.")
    show.add_argument("job_name", help="Job name")
    show.add_argument(
        "--state-dir",
        default="/var/lib/cronwrap/traces",
        help="Directory where trace files are stored.",
    )

    clear = sub.add_parser("clear", help="Clear the trace record for a job.")
    clear.add_argument("job_name", help="Job name")
    clear.add_argument(
        "--state-dir",
        default="/var/lib/cronwrap/traces",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    tracing = JobTracing(args.state_dir)

    if args.command == "show":
        record = tracing.get(args.job_name)
        if record is None:
            print(f"No trace found for job '{args.job_name}'.", file=sys.stderr)
            return 2
        print(json.dumps(record.to_dict(), indent=2))
        return 0

    if args.command == "clear":
        try:
            tracing.clear(args.job_name)
            print(f"Trace cleared for job '{args.job_name}'.")
        except TracingError as exc:
            print(str(exc), file=sys.stderr)
            return 3
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
