"""CLI for job run-time forecasting."""
from __future__ import annotations

import argparse
import sys

from cronwrap.job_forecast import ForecastError, forecast_job


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-forecast",
        description="Forecast next run duration for a cron job.",
    )
    sub = p.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Show forecast for a job")
    show.add_argument("job_name", help="Name of the job")
    show.add_argument(
        "--history-dir",
        default=".cronwrap/history",
        help="Path to history directory",
    )
    show.add_argument(
        "--multiplier",
        type=float,
        default=1.5,
        help="Std-dev multiplier for bounds (default: 1.5)",
    )
    show.add_argument(
        "--json",
        dest="as_json",
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

    try:
        result = forecast_job(
            args.job_name,
            args.history_dir,
            stddev_multiplier=args.multiplier,
        )
    except ForecastError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.as_json:
        print(result.to_json())
    else:
        print(f"Job:              {result.job_name}")
        print(f"Sample size:      {result.sample_size}")
        print(f"Predicted:        {result.predicted_duration:.2f}s")
        print(f"Range:            {result.lower_bound:.2f}s – {result.upper_bound:.2f}s")
        print(f"Confidence:       {result.confidence}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
