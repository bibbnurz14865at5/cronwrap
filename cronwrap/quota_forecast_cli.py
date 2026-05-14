"""CLI for quota usage forecasting."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwrap.job_quota_forecast import QuotaForecastError, forecast_quota


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-quota-forecast",
        description="Forecast when a job will exhaust its quota.",
    )
    sub = p.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Print forecast for a job")
    show.add_argument("--job", required=True, help="Job name")
    show.add_argument("--limit", type=int, required=True, help="Quota limit")
    show.add_argument("--current", type=int, default=0, help="Current period usage")
    show.add_argument(
        "--history",
        default="",
        help="Comma-separated per-period usage history (e.g. 10,12,9)",
    )
    show.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    history: list[int] = []
    if args.history.strip():
        try:
            history = [int(x.strip()) for x in args.history.split(",") if x.strip()]
        except ValueError:
            print("error: --history must be comma-separated integers", file=sys.stderr)
            return 2

    try:
        result = forecast_quota(
            job_name=args.job,
            quota_limit=args.limit,
            usage_history=history,
            current_usage=args.current,
        )
    except QuotaForecastError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(result.to_json())
    else:
        pr = result.periods_remaining
        pr_str = f"{pr:.2f}" if pr is not None else "N/A"
        status = "WILL EXHAUST" if result.will_exhaust else "OK"
        print(f"job            : {result.job_name}")
        print(f"quota limit    : {result.quota_limit}")
        print(f"current usage  : {result.current_usage}")
        print(f"avg/period     : {result.avg_usage_per_period:.4f}")
        print(f"periods left   : {pr_str}")
        print(f"status         : {status}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
