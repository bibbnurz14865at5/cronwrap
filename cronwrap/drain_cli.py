"""drain_cli.py – CLI for managing job drain state."""
from __future__ import annotations

import argparse
import sys

from cronwrap.job_drain import DrainError, JobDrain

_DEFAULT_STATE_DIR = "/var/lib/cronwrap/drain"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-drain",
        description="Manage graceful drain state for cron jobs.",
    )
    p.add_argument(
        "--state-dir",
        default=_DEFAULT_STATE_DIR,
        help="Directory to store drain state files (default: %(default)s)",
    )
    sub = p.add_subparsers(dest="command")

    # drain
    dr = sub.add_parser("drain", help="Mark a job as draining.")
    dr.add_argument("job_name")
    dr.add_argument("--reason", default=None, help="Optional reason for draining.")

    # undrain
    ud = sub.add_parser("undrain", help="Remove the drain marker for a job.")
    ud.add_argument("job_name")

    # status
    st = sub.add_parser("status", help="Show drain status for a job.")
    st.add_argument("job_name")

    # list
    sub.add_parser("list", help="List all currently draining jobs.")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    jd = JobDrain(state_dir=args.state_dir)

    try:
        if args.command == "drain":
            state = jd.drain(args.job_name, reason=args.reason)
            print(f"Job '{args.job_name}' marked as draining at {state.drained_at}.")
            return 0

        if args.command == "undrain":
            jd.undrain(args.job_name)
            print(f"Job '{args.job_name}' drain marker removed.")
            return 0

        if args.command == "status":
            state = jd.get(args.job_name)
            if state is None:
                print(f"Job '{args.job_name}' is NOT draining.")
            else:
                print(f"Job '{args.job_name}' is DRAINING since {state.drained_at}.")
                if state.reason:
                    print(f"  Reason: {state.reason}")
            return 0

        if args.command == "list":
            jobs = jd.list_draining()
            if not jobs:
                print("No jobs are currently draining.")
            else:
                for name in jobs:
                    print(name)
            return 0

    except DrainError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 0  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
