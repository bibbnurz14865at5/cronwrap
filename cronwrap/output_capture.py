"""Capture and truncate job stdout/stderr for storage or alerting."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

DEFAULT_MAX_BYTES = 4096


@dataclass
class CapturedOutput:
    stdout: str = ""
    stderr: str = ""
    truncated: bool = False

    def combined(self) -> str:
        parts = []
        if self.stdout:
            parts.append(f"[stdout]\n{self.stdout}")
        if self.stderr:
            parts.append(f"[stderr]\n{self.stderr}")
        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "truncated": self.truncated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CapturedOutput":
        return cls(
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
            truncated=data.get("truncated", False),
        )


def capture(stdout: str, stderr: str, max_bytes: int = DEFAULT_MAX_BYTES) -> CapturedOutput:
    """Truncate stdout/stderr to max_bytes each and return a CapturedOutput."""
    truncated = False

    if len(stdout.encode()) > max_bytes:
        stdout = stdout.encode()[:max_bytes].decode(errors="replace") + "\n...[truncated]"
        truncated = True

    if len(stderr.encode()) > max_bytes:
        stderr = stderr.encode()[:max_bytes].decode(errors="replace") + "\n...[truncated]"
        truncated = True

    return CapturedOutput(stdout=stdout, stderr=stderr, truncated=truncated)


def tail_lines(text: str, n: int = 20) -> str:
    """Return the last n lines of text."""
    lines = text.splitlines()
    return "\n".join(lines[-n:]) if lines else ""
