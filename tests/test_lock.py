"""Tests for cronwrap.lock."""

import os
import threading
import pytest

from cronwrap.lock import JobLock, LockError


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_lock(job_name: str, tmp_path, **kwargs) -> JobLock:
    """Create a JobLock rooted in *tmp_path* with optional keyword overrides."""
    return JobLock(job_name, lock_dir=str(tmp_path), **kwargs)


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def test_acquire_creates_lock_file(tmp_path):
    lock = _make_lock("test-job", tmp_path)
    lock.acquire()
    assert lock.is_locked
    lock.release()


def test_release_removes_lock_file(tmp_path):
    lock = _make_lock("test-job", tmp_path)
    lock.acquire()
    lock.release()
    assert not lock.is_locked


def test_context_manager_acquires_and_releases(tmp_path):
    lock = _make_lock("ctx-job", tmp_path)
    with lock:
        assert lock.is_locked
    assert not lock.is_locked


def test_lock_file_contains_pid(tmp_path):
    lock = _make_lock("pid-job", tmp_path)
    with lock:
        content = open(lock.lock_path).read()
    assert content == str(os.getpid())


def test_second_acquire_raises_lock_error(tmp_path):
    lock1 = _make_lock("dup-job", tmp_path, timeout=0)
    lock2 = _make_lock("dup-job", tmp_path, timeout=0)
    lock1.acquire()
    try:
        with pytest.raises(LockError):
            lock2.acquire()
    finally:
        lock1.release()


def test_safe_name_replaces_slashes_and_spaces(tmp_path):
    lock = _make_lock("my job/task", tmp_path)
    assert "my_job_task" in lock.lock_path


def test_release_is_idempotent(tmp_path):
    lock = _make_lock("idem-job", tmp_path)
    lock.acquire()
    lock.release()
    lock.release()  # should not raise


def test_lock_released_after_exception_in_context(tmp_path):
    lock = _make_lock("exc-job", tmp_path)
    with pytest.raises(ValueError):
        with lock:
            raise ValueError("boom")
    assert not lock.is_locked


def test_concurrent_jobs_only_one_acquires(tmp_path):
    """Only one of two racing threads should acquire the lock."""
    results = []
    barrier = threading.Barrier(2)

    def try_acquire():
        lock = _make_lock("race-job", tmp_path, timeout=0)
        barrier.wait()
        try:
            lock.acquire()
            results.append("ok")
            lock.release()
        except LockError:
            results.append("blocked")

    threads = [threading.Thread(target=try_acquire) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count("ok") == 1
    assert results.count("blocked") == 1
