"""File-based locking to prevent overlapping cron job executions."""

import os
import time
import errno
from typing import Optional


class LockError(Exception):
    """Raised when a lock cannot be acquired."""


class JobLock:
    """A simple file-based lock for a named cron job.

    Usage::

        with JobLock("my-job", lock_dir="/tmp") as lock:
            # job runs here
            ...
    """

    def __init__(self, job_name: str, lock_dir: str = "/tmp", timeout: int = 0):
        safe_name = job_name.replace("/", "_").replace(" ", "_")
        self.lock_path = os.path.join(lock_dir, f"cronwrap_{safe_name}.lock")
        self.timeout = timeout
        self._fd: Optional[int] = None

    def acquire(self) -> None:
        """Acquire the lock, optionally waiting up to *timeout* seconds."""
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                self._fd = os.open(
                    self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                )
                os.write(self._fd, str(os.getpid()).encode())
                return
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                if time.monotonic() >= deadline:
                    raise LockError(
                        f"Could not acquire lock for job; lock file: {self.lock_path}"
                    ) from exc
                time.sleep(0.5)

    def release(self) -> None:
        """Release the lock and remove the lock file."""
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        try:
            os.unlink(self.lock_path)
        except OSError:
            pass

    def __enter__(self) -> "JobLock":
        self.acquire()
        return self

    def __exit__(self, *_) -> None:
        self.release()

    @property
    def is_locked(self) -> bool:
        """Return True if the lock file currently exists."""
        return os.path.exists(self.lock_path)
