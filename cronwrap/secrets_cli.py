"""CLI for managing job secret definitions."""
from __future__ import annotations

import argparse
import json
import sys

from cronwrap.job_secrets import JobSecrets, SecretsRegistry

DEFAULT_REGISTRY = "/var/lib/cronwrap/secrets.json"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Manage job secret references")
    p.add_argument("--registry", default=DEFAULT_REGISTRY, help="Path to secrets registry JSON")
    sub = p.add_subparsers(dest="command")

    reg = sub.add_parser("register", help="Register secret env-var names for a job")
    reg.add_argument("job_name")
    reg.add_argument("--required", nargs="*", default=[], metavar="VAR")
    reg.add_argument("--optional", nargs="*", default=[], metavar="VAR")

    chk = sub.add_parser("check", help="Check that required secrets are present")
    chk.add_argument("job_name")

    sub.add_parser("list", help="List all jobs with registered secrets")

    rm = sub.add_parser("remove", help="Remove secret definition for a job")
    rm.add_argument("job_name")

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    reg = SecretsRegistry(args.registry)

    if args.command == "register":
        reg.register(JobSecrets(args.job_name, args.required, args.optional))
        print(f"Registered secrets for '{args.job_name}'")
        return 0

    if args.command == "check":
        s = reg.get(args.job_name)
        if s is None:
            print(f"No secrets registered for '{args.job_name}'")
            return 1
        result = s.check()
        if result.ok:
            print("All required secrets present")
            return 0
        print(f"Missing: {', '.join(result.missing)}", file=sys.stderr)
        return 2

    if args.command == "list":
        jobs = reg.all_jobs()
        if not jobs:
            print("No jobs registered")
        else:
            print("\n".join(jobs))
        return 0

    if args.command == "remove":
        removed = reg.remove(args.job_name)
        if removed:
            print(f"Removed '{args.job_name}'")
            return 0
        print(f"Not found: '{args.job_name}'")
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
