"""CLI for inspecting job execution heatmaps."""

from __future__ import annotations

import argparse
import json
import sys

from cronwrap.job_heatmap import JobHeatmap


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Inspect job execution heatmaps")
    sub = p.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Show heatmap for a job")
    show.add_argument("job_name")
    show.add_argument("--state-dir", default="/var/lib/cronwrap/heatmaps")
    show.add_argument("--json", dest="as_json", action="store_true")

    ls = sub.add_parser("list", help="List all jobs with heatmap data")
    ls.add_argument("--state-dir", default="/var/lib/cronwrap/heatmaps")

    rst = sub.add_parser("reset", help="Reset heatmap for a job")
    rst.add_argument("job_name")
    rst.add_argument("--state-dir", default="/var/lib/cronwrap/heatmaps")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    hm = JobHeatmap(args.state_dir)

    if args.command == "show":
        rec = hm.get(args.job_name)
        if args.as_json:
            print(json.dumps(rec.to_dict(), indent=2))
        else:
            print(f"Job: {rec.job_name}  total={rec.total_runs()}  peak_hour={rec.peak_hour()}")
            for h, count in enumerate(rec.buckets):
                bar = "#" * count
                print(f"  {h:02d}:00  {count:4d}  {bar}")
        return 0

    if args.command == "list":
        jobs = hm.all_jobs()
        for name in jobs:
            print(name)
        return 0

    if args.command == "reset":
        hm.reset(args.job_name)
        print(f"Heatmap reset for {args.job_name}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
