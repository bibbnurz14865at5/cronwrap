"""CLI interface for job profiler: view and clear duration profiles."""
from __future__ import annotations

import argparse
import json
import sys

from cronwrap.job_profiler import JobProfiler, ProfilerError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-profiler",
        description="Inspect job duration profiles and detect regressions.",
    )
    sub = parser.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Show profile for a job")
    show.add_argument("job_name", help="Name of the job")
    show.add_argument("--state-dir", default="/tmp/cronwrap/profiles", metavar="DIR")

    list_p = sub.add_parser("list", help="List all profiled jobs")
    list_p.add_argument("--state-dir", default="/tmp/cronwrap/profiles", metavar="DIR")
    list_p.add_argument("--json", dest="as_json", action="store_true")

    check = sub.add_parser("check", help="Check if a duration is a regression")
    check.add_argument("job_name")
    check.add_argument("duration", type=float, help="Observed duration in seconds")
    check.add_argument("--threshold", type=float, default=2.0)
    check.add_argument("--state-dir", default="/tmp/cronwrap/profiles", metavar="DIR")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "show":
            profiler = JobProfiler(args.state_dir)
            snap = profiler.load(args.job_name)
            print(json.dumps(snap.to_dict(), indent=2))
            return 0

        if args.command == "list":
            profiler = JobProfiler(args.state_dir)
            snapshots = profiler.all_snapshots()
            if args.as_json:
                print(json.dumps({k: v.to_dict() for k, v in snapshots.items()}, indent=2))
            else:
                if not snapshots:
                    print("No profiles found.")
                else:
                    for name, snap in snapshots.items():
                        print(f"{name}: p50={snap.p50():.2f}s p95={snap.p95()}s samples={len(snap.durations)}")
            return 0

        if args.command == "check":
            profiler = JobProfiler(args.state_dir)
            snap = profiler.load(args.job_name)
            if snap.is_regression(args.duration, threshold=args.threshold):
                print(f"REGRESSION: {args.duration}s exceeds {args.threshold}x p95 ({snap.p95()}s)")
                return 2
            print(f"OK: {args.duration}s within normal range (p95={snap.p95()}s)")
            return 0

    except ProfilerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
