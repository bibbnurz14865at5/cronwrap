"""CLI for managing the cronwrap job manifest."""
from __future__ import annotations

import argparse
import json
import sys

from cronwrap.job_manifest import JobManifest, ManifestEntry, ManifestError

_DEFAULT_PATH = "cronwrap_manifest.json"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-manifest",
        description="Manage the cronwrap job manifest",
    )
    p.add_argument("--manifest", default=_DEFAULT_PATH, help="Path to manifest file")
    sub = p.add_subparsers(dest="command")

    reg = sub.add_parser("register", help="Register or update a job")
    reg.add_argument("job_name")
    reg.add_argument("command")
    reg.add_argument("--schedule", default=None)
    reg.add_argument("--owner", default=None)
    reg.add_argument("--tags", default="", help="Comma-separated tags")
    reg.add_argument("--description", default=None)

    rm = sub.add_parser("remove", help="Remove a job from the manifest")
    rm.add_argument("job_name")

    show = sub.add_parser("show", help="Show a single job entry")
    show.add_argument("job_name")

    sub.add_parser("list", help="List all registered jobs")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    manifest = JobManifest(args.manifest)

    if args.command == "register":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        entry = ManifestEntry(
            job_name=args.job_name,
            command=args.command,
            schedule=args.schedule,
            owner=args.owner,
            tags=tags,
            description=args.description,
        )
        manifest.register(entry)
        print(f"Registered job '{args.job_name}'.")
        return 0

    if args.command == "remove":
        try:
            manifest.remove(args.job_name)
            print(f"Removed job '{args.job_name}'.")
            return 0
        except ManifestError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2

    if args.command == "show":
        entry = manifest.get(args.job_name)
        if entry is None:
            print(f"Job '{args.job_name}' not found.", file=sys.stderr)
            return 2
        print(json.dumps(entry.to_dict(), indent=2))
        return 0

    if args.command == "list":
        entries = manifest.all_entries()
        if not entries:
            print("No jobs registered.")
            return 0
        for e in entries:
            schedule = e.schedule or "(none)"
            print(f"{e.job_name}  schedule={schedule}  owner={e.owner or '(none)'}")
        return 0

    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
