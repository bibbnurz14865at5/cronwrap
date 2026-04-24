"""CLI sub-commands for managing job mutes."""

from __future__ import annotations

import argparse
import sys
import time

from cronwrap.job_mute import JobMute, MuteError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-mute",
        description="Mute or unmute alerting for a cron job.",
    )
    sub = parser.add_subparsers(dest="command")

    # mute
    p_mute = sub.add_parser("mute", help="Mute a job for a duration")
    p_mute.add_argument("job_name", help="Name of the job")
    p_mute.add_argument("duration", type=int, help="Duration in seconds")
    p_mute.add_argument("--reason", default=None, help="Optional reason")
    p_mute.add_argument("--state-dir", default="/tmp/cronwrap/mute")

    # unmute
    p_unmute = sub.add_parser("unmute", help="Remove a mute")
    p_unmute.add_argument("job_name")
    p_unmute.add_argument("--state-dir", default="/tmp/cronwrap/mute")

    # status
    p_status = sub.add_parser("status", help="Show mute status for a job")
    p_status.add_argument("job_name")
    p_status.add_argument("--state-dir", default="/tmp/cronwrap/mute")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    jm = JobMute(state_dir=args.state_dir)

    if args.command == "mute":
        try:
            state = jm.mute(args.job_name, args.duration, reason=args.reason)
        except MuteError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        until = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(state.muted_until))
        print(f"Muted '{args.job_name}' until {until}")
        return 0

    if args.command == "unmute":
        jm.unmute(args.job_name)
        print(f"Unmuted '{args.job_name}'")
        return 0

    if args.command == "status":
        state = jm.get(args.job_name)
        if state is None or not state.is_active():
            print(f"'{args.job_name}' is NOT muted")
            return 0
        until = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(state.muted_until))
        reason_str = f" ({state.reason})" if state.reason else ""
        print(f"'{args.job_name}' is MUTED until {until}{reason_str}")
        return 0

    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
