"""CLI for pausing and resuming cron jobs."""
from __future__ import annotations

import argparse
import sys
import time

from cronwrap.job_pause import JobPause


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cronwrap-pause", description="Pause or resume cron jobs")
    p.add_argument("--state-dir", default="/tmp/cronwrap/pause", help="Directory for pause state files")
    sub = p.add_subparsers(dest="command")

    pause_p = sub.add_parser("pause", help="Pause a job")
    pause_p.add_argument("job", help="Job name")
    pause_p.add_argument("--reason", default=None)
    pause_p.add_argument("--minutes", type=float, default=None, help="Auto-resume after N minutes")

    resume_p = sub.add_parser("resume", help="Resume a job")
    resume_p.add_argument("job", help="Job name")

    check_p = sub.add_parser("check", help="Check if a job is paused")
    check_p.add_argument("job", help="Job name")

    sub.add_parser("list", help="List all paused jobs")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    jp = JobPause(args.state_dir)

    if args.command == "pause":
        resume_after = time.time() + args.minutes * 60 if args.minutes else None
        state = jp.pause(args.job, reason=args.reason, resume_after=resume_after)
        print(f"Paused {args.job!r}" + (f" — {args.reason}" if args.reason else ""))
        return 0

    if args.command == "resume":
        jp.resume(args.job)
        print(f"Resumed {args.job!r}")
        return 0

    if args.command == "check":
        if jp.is_paused(args.job):
            state = jp.get_state(args.job)
            print(f"PAUSED: {args.job}" + (f" ({state.reason})" if state and state.reason else ""))
            return 1
        print(f"ACTIVE: {args.job}")
        return 0

    if args.command == "list":
        paused = jp.list_paused()
        if not paused:
            print("No jobs paused.")
        else:
            for name in paused:
                print(name)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
