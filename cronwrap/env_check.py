"""Check that required environment variables are present before running a job."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class EnvCheckResult:
    missing: List[str] = field(default_factory=list)
    present: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.missing) == 0

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"EnvCheckResult(ok={self.ok}, "
            f"present={self.present}, missing={self.missing})"
        )


def check_env(required: List[str]) -> EnvCheckResult:
    """Return an EnvCheckResult indicating which variables are present/missing."""
    import os

    result = EnvCheckResult()
    for var in required:
        if os.environ.get(var) is not None:
            result.present.append(var)
        else:
            result.missing.append(var)
    return result


def assert_env(required: List[str]) -> None:
    """Raise EnvironmentError listing all missing variables, if any."""
    result = check_env(required)
    if not result.ok:
        raise EnvironmentError(
            "Required environment variables not set: "
            + ", ".join(result.missing)
        )
