"""CLI entry-point: check job dependencies then exec the wrapped command."""
from __future__ import annotations

import argparse
import subprocess
import sys

from cronwrap.job_dependencies import DependencyConfig, DependencyError, assert_dependencies


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run a command only if job dependencies are satisfied."
    )
    p.add_argument("--config", required=True, help="Path to dependency config JSON")
    p.add_argument("--history-dir", required=True, help="Path to cronwrap history directory")
    p.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to run (after --)")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    cmd = [a for a in args.cmd if a != "--"]
    if not cmd:
        print("cronwrap-deps: no command provided", file=sys.stderr)
        return 2

    try:
        cfg = DependencyConfig.from_json_file(args.config)
    except FileNotFoundError as exc:
        print(f"cronwrap-deps: {exc}", file=sys.stderr)
        return 2

    try:
        assert_dependencies(cfg, args.history_dir)
    except DependencyError as exc:
        print(f"cronwrap-deps: {exc}", file=sys.stderr)
        return 1

    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
