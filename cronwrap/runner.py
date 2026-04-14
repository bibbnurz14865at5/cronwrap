"""Job runner: executes a shell command and captures result metadata."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class JobResult:
    """Holds the outcome of a single cron job execution."""

    command: List[str]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    def summary(self) -> str:
        status = "OK" if self.success else ("TIMEOUT" if self.timed_out else f"FAILED (exit {self.returncode})")
        cmd_str = " ".join(self.command)
        return (
            f"[{status}] `{cmd_str}` finished in {self.duration_seconds:.2f}s\n"
            f"stdout: {self.stdout.strip() or '(empty)'}\n"
            f"stderr: {self.stderr.strip() or '(empty)'}"
        )


def run_job(
    command: List[str],
    timeout: Optional[int] = None,
    env: Optional[dict] = None,
) -> JobResult:
    """Run *command* as a subprocess and return a :class:`JobResult`.

    Args:
        command: Argument list passed to ``subprocess.run``.
        timeout: Optional wall-clock timeout in seconds.
        env:     Optional mapping of environment variables for the child process.

    Returns:
        A :class:`JobResult` describing what happened.
    """
    start = time.monotonic()
    timed_out = False

    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        returncode = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = -1
        stdout = (exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = (exc.stderr or b"").decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")

    duration = time.monotonic() - start

    return JobResult(
        command=command,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=round(duration, 4),
        timed_out=timed_out,
    )
