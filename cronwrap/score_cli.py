"""CLI for job health scoring."""
from __future__ import annotations

import argparse
import sys

from cronwrap.job_score import ScoringError, compute_score


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-score",
        description="Compute a health score for a cron job.",
    )
    sub = p.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Show score for a job")
    show.add_argument("job_name", help="Name of the job")
    show.add_argument(
        "--history-dir",
        default=".cronwrap/history",
        help="Directory containing history files",
    )
    show.add_argument(
        "--window",
        type=int,
        default=30,
        help="Number of recent runs to consider (default: 30)",
    )
    show.add_argument(
        "--threshold",
        type=float,
        default=60.0,
        help="Duration penalty threshold in seconds (default: 60)",
    )
    show.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "show":
        try:
            result = compute_score(
                job_name=args.job_name,
                history_dir=args.history_dir,
                window=args.window,
                duration_penalty_threshold=args.threshold,
            )
        except ScoringError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

        if args.json:
            print(result.to_json())
        else:
            print(
                f"Job:          {result.job_name}\n"
                f"Score:        {result.score:.1f} / 100  (Grade: {result.grade})\n"
                f"Success rate: {result.success_rate * 100:.1f}%\n"
                f"Avg duration: {result.avg_duration:.1f}s\n"
                f"Sample size:  {result.sample_size} runs"
            )
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
