"""CLI entry-point for the job-summary feature."""
from __future__ import annotations

import argparse
import sys

from cronwrap.job_summary import build_summary, summary_to_json


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-summary",
        description="Print a summary of all jobs in a history directory.",
    )
    sub = p.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Print summary table")
    show.add_argument("--history-dir", default=".cronwrap/history", metavar="DIR")
    show.add_argument("--json", dest="as_json", action="store_true",
                      help="Output raw JSON instead of table")

    return p


def _render_table(entries) -> str:
    if not entries:
        return "(no jobs found)"
    header = f"{'JOB':<30} {'RUNS':>6} {'SUCCESS%':>9} {'AVG_DUR':>9} {'LAST':>8}"
    sep = "-" * len(header)
    rows = [header, sep]
    for e in entries:
        rows.append(
            f"{e.job_name:<30} {e.total_runs:>6} "
            f"{e.success_rate * 100:>8.1f}% "
            f"{e.avg_duration:>8.2f}s "
            f"{e.last_status:>8}"
        )
    return "\n".join(rows)


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "show":
        if args.as_json:
            print(summary_to_json(args.history_dir))
        else:
            entries = build_summary(args.history_dir)
            print(_render_table(entries))
        return 0

    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
