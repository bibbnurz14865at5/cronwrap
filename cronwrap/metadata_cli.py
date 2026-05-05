"""CLI for managing per-job metadata."""
from __future__ import annotations

import argparse
import json
import sys

from cronwrap.job_metadata import JobMetadata, MetadataError


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-metadata",
        description="Manage arbitrary metadata for a cron job.",
    )
    p.add_argument("--state-dir", default=".cronwrap/metadata", help="Metadata storage directory")
    sub = p.add_subparsers(dest="command")

    s = sub.add_parser("set", help="Set a metadata key")
    s.add_argument("job", help="Job name")
    s.add_argument("key", help="Metadata key")
    s.add_argument("value", help="Metadata value (stored as string)")

    g = sub.add_parser("get", help="Get a metadata key")
    g.add_argument("job", help="Job name")
    g.add_argument("key", help="Metadata key")

    r = sub.add_parser("remove", help="Remove a metadata key")
    r.add_argument("job", help="Job name")
    r.add_argument("key", help="Metadata key")

    ls = sub.add_parser("list", help="List all metadata for a job")
    ls.add_argument("job", help="Job name")

    cl = sub.add_parser("clear", help="Clear all metadata for a job")
    cl.add_argument("job", help="Job name")

    return p


def main(argv: list[str] | None = None) -> int:  # noqa: UP006
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    try:
        meta = JobMetadata(job_name=args.job, state_dir=args.state_dir)

        if args.command == "set":
            meta.set(args.key, args.value)
            print(f"Set {args.key}={args.value!r} for job '{args.job}'")

        elif args.command == "get":
            val = meta.get(args.key)
            if val is None:
                print(f"Key '{args.key}' not found for job '{args.job}'", file=sys.stderr)
                return 2
            print(val)

        elif args.command == "remove":
            meta.remove(args.key)
            print(f"Removed '{args.key}' from job '{args.job}'")

        elif args.command == "list":
            data = meta.all()
            print(json.dumps(data, indent=2))

        elif args.command == "clear":
            meta.clear()
            print(f"Cleared all metadata for job '{args.job}'")

    except MetadataError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
