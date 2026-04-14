"""Tests for cronwrap.runner."""

import sys
import pytest
from cronwrap.runner import run_job, JobResult


# ---------------------------------------------------------------------------
# JobResult helpers
# ---------------------------------------------------------------------------

def _make_result(**kwargs) -> JobResult:
    defaults = dict(
        command=["echo", "hi"],
        returncode=0,
        stdout="hi\n",
        stderr="",
        duration_seconds=0.01,
        timed_out=False,
    )
    defaults.update(kwargs)
    return JobResult(**defaults)


def test_job_result_success():
    r = _make_result(returncode=0)
    assert r.success is True


def test_job_result_failure_nonzero():
    r = _make_result(returncode=1)
    assert r.success is False


def test_job_result_failure_timeout():
    r = _make_result(returncode=0, timed_out=True)
    assert r.success is False


def test_job_result_summary_ok():
    r = _make_result(stdout="done\n", stderr="")
    summary = r.summary()
    assert "[OK]" in summary
    assert "done" in summary


def test_job_result_summary_failed():
    r = _make_result(returncode=2, stderr="bad things")
    summary = r.summary()
    assert "FAILED" in summary
    assert "exit 2" in summary


def test_job_result_summary_timeout():
    r = _make_result(returncode=-1, timed_out=True)
    assert "TIMEOUT" in r.summary()


# ---------------------------------------------------------------------------
# run_job integration (uses real subprocess)
# ---------------------------------------------------------------------------

def test_run_job_success():
    result = run_job([sys.executable, "-c", "print('hello')"])
    assert result.success is True
    assert "hello" in result.stdout
    assert result.returncode == 0
    assert result.duration_seconds >= 0


def test_run_job_failure():
    result = run_job([sys.executable, "-c", "import sys; sys.exit(3)"])
    assert result.success is False
    assert result.returncode == 3


def test_run_job_stderr_captured():
    result = run_job([sys.executable, "-c", "import sys; sys.stderr.write('err msg')"])
    assert "err msg" in result.stderr


def test_run_job_timeout():
    result = run_job([sys.executable, "-c", "import time; time.sleep(10)"], timeout=1)
    assert result.timed_out is True
    assert result.success is False


def test_run_job_duration_recorded():
    result = run_job([sys.executable, "-c", "pass"])
    assert isinstance(result.duration_seconds, float)
    assert result.duration_seconds >= 0
