"""CLI for cronwrap job signal management."""
from __future__ import annotations

import argparse
import json
import sys

from cronwrap.job_signal import JobSignal, SignalError


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-signal",
        description="Send OS signals to running cron jobs and inspect signal history.",
    )
    p.add_argument("--state-dir", default="/tmp/cronwrap/signals", help="Directory for signal logs")
    sub = p.add_subparsers(dest="command")

    # send
    send_p = sub.add_parser("send", help="Send a signal to a job PID")
    send_p.add_argument("job_name", help="Job name")
    send_p.add_argument("pid", type=int, help="Target process PID")
    send_p.add_argument("signal", help="Signal name (e.g. SIGTERM, SIGHUP)")
    send_p.add_argument("--extra", default="{}", help="JSON extra metadata")

    # history
    hist_p = sub.add_parser("history", help="Show signal history for a job")
    hist_p.add_argument("job_name", help="Job name")
    hist_p.add_argument("--json", dest="as_json", action="store_true", help="Output as JSON")

    # clear
    clear_p = sub.add_parser("clear", help="Clear signal history for a job")
    clear_p.add_argument("job_name", help="Job name")

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    store = JobSignal(state_dir=args.state_dir)

    if args.command == "send":
        try:
            extra = json.loads(args.extra)
        except json.JSONDecodeError as exc:
            print(f"error: --extra is not valid JSON: {exc}", file=sys.stderr)
            return 2
        try:
            record = store.send(args.job_name, args.pid, args.signal, extra=extra)
        except SignalError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 3
        print(f"Sent {record.signal_name} to PID {record.pid} at {record.sent_at}")
        return 0

    if args.command == "history":
        records = store.history(args.job_name)
        if args.as_json:
            print(json.dumps([r.to_dict() for r in records], indent=2))
        else:
            if not records:
                print(f"No signal history for '{args.job_name}'.")
            for r in records:
                print(f"{r.sent_at}  {r.signal_name}  pid={r.pid}")
        return 0

    if args.command == "clear":
        removed = store.clear_history(args.job_name)
        print(f"Cleared {removed} record(s) for '{args.job_name}'.")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
