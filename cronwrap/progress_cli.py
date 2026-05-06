"""CLI for inspecting job progress records."""
from __future__ import annotations

import argparse
import json
import sys

from cronwrap.job_progress import JobProgress, ProgressError


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-progress",
        description="Inspect or clear job progress records.",
    )
    sub = p.add_subparsers(dest="command")

    show_p = sub.add_parser("show", help="Show progress for a job")
    show_p.add_argument("job_name")
    show_p.add_argument("--state-dir", default="/tmp/cronwrap/progress")

    clear_p = sub.add_parser("clear", help="Clear progress record for a job")
    clear_p.add_argument("job_name")
    clear_p.add_argument("--state-dir", default="/tmp/cronwrap/progress")

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    tracker = JobProgress(state_dir=args.state_dir)

    if args.command == "show":
        record = tracker.get(args.job_name)
        if record is None:
            print(f"No progress record found for '{args.job_name}'.", file=sys.stderr)
            return 2
        print(json.dumps(record.to_dict(), indent=2))
        return 0

    if args.command == "clear":
        tracker.clear(args.job_name)
        print(f"Progress record cleared for '{args.job_name}'.")
        return 0

    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
