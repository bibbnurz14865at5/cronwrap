"""CLI entry-point for the job-snapshot command."""
from __future__ import annotations

import argparse
import sys

from cronwrap.job_snapshot import build_snapshot, save_snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-snapshot",
        description="Snapshot the current state of all tracked cron jobs.",
    )
    parser.add_argument(
        "--history-dir",
        default=".cronwrap/history",
        help="Directory containing per-job history JSON files (default: .cronwrap/history).",
    )
    parser.add_argument(
        "--output",
        default="-",
        help="Output file path. Use '-' to print to stdout (default).",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=True,
        help="Pretty-print JSON output (default: true).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:  # pragma: no cover – thin wrapper
    parser = build_parser()
    args = parser.parse_args(argv)

    report = build_snapshot(args.history_dir)

    if args.output == "-":
        print(report.to_json())
    else:
        save_snapshot(report, args.output)
        print(f"Snapshot written to {args.output}", file=sys.stderr)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
