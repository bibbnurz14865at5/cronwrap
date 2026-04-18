"""CLI for managing job annotations."""
from __future__ import annotations

import argparse
import json
import sys

from cronwrap.job_annotations import JobAnnotations


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-annotations",
        description="Manage per-job annotations",
    )
    p.add_argument("--storage-dir", default="/var/lib/cronwrap/annotations", metavar="DIR")
    p.add_argument("--job", required=True, metavar="NAME")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("set", help="Set an annotation")
    s.add_argument("key")
    s.add_argument("value")

    g = sub.add_parser("get", help="Get an annotation")
    g.add_argument("key")

    sub.add_parser("list", help="List all annotations")

    r = sub.add_parser("remove", help="Remove an annotation")
    r.add_argument("key")

    sub.add_parser("clear", help="Clear all annotations")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    ann = JobAnnotations(args.storage_dir, args.job)

    if args.cmd == "set":
        ann.set(args.key, args.value)
        print(f"Set {args.key}={args.value}")
    elif args.cmd == "get":
        val = ann.get(args.key)
        if val is None:
            print(f"Key '{args.key}' not found", file=sys.stderr)
            return 1
        print(val)
    elif args.cmd == "list":
        print(json.dumps(ann.all(), indent=2))
    elif args.cmd == "remove":
        found = ann.remove(args.key)
        if not found:
            print(f"Key '{args.key}' not found", file=sys.stderr)
            return 1
        print(f"Removed {args.key}")
    elif args.cmd == "clear":
        ann.clear()
        print("Cleared all annotations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
