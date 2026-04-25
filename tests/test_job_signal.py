"""Tests for cronwrap.job_signal and cronwrap.signal_cli."""
from __future__ import annotations

import json
import os
import signal
from unittest.mock import patch

import pytest

from cronwrap.job_signal import JobSignal, SignalError, SignalRecord


def _make(tmp_path) -> JobSignal:
    return JobSignal(state_dir=str(tmp_path / "signals"))


# ---------------------------------------------------------------------------
# SignalRecord
# ---------------------------------------------------------------------------

def test_record_to_dict_required_keys():
    r = SignalRecord(job_name="backup", pid=1234, signal_name="SIGTERM", sent_at="2024-01-01T00:00:00+00:00")
    d = r.to_dict()
    assert set(d.keys()) == {"job_name", "pid", "signal_name", "sent_at"}


def test_record_to_dict_includes_extra_when_set():
    r = SignalRecord(job_name="j", pid=9, signal_name="SIGHUP", sent_at="ts", extra={"reason": "reload"})
    d = r.to_dict()
    assert d["extra"] == {"reason": "reload"}


def test_record_roundtrip():
    r = SignalRecord(job_name="j", pid=42, signal_name="SIGUSR1", sent_at="2024-06-01T12:00:00+00:00", extra={"k": "v"})
    assert SignalRecord.from_dict(r.to_dict()).to_dict() == r.to_dict()


# ---------------------------------------------------------------------------
# JobSignal.send
# ---------------------------------------------------------------------------

def test_send_disallowed_signal_raises(tmp_path):
    store = _make(tmp_path)
    with pytest.raises(SignalError, match="not allowed"):
        store.send("job", os.getpid(), "SIGSTOP")


def test_send_unknown_pid_raises(tmp_path):
    store = _make(tmp_path)
    # PID 0 is not a valid target for os.kill in this context on Linux but
    # we simulate ProcessLookupError via a nonexistent PID.
    with patch("os.kill", side_effect=ProcessLookupError):
        with pytest.raises(SignalError, match="No process"):
            store.send("job", 99999999, "SIGTERM")


def test_send_permission_error_raises(tmp_path):
    store = _make(tmp_path)
    with patch("os.kill", side_effect=PermissionError):
        with pytest.raises(SignalError, match="Permission denied"):
            store.send("job", 1, "SIGTERM")


def test_send_records_to_log(tmp_path):
    store = _make(tmp_path)
    with patch("os.kill"):
        record = store.send("myjob", 1234, "SIGHUP", extra={"env": "prod"})
    assert record.job_name == "myjob"
    assert record.pid == 1234
    assert record.signal_name == "SIGHUP"
    assert record.extra == {"env": "prod"}


def test_send_appends_multiple_records(tmp_path):
    store = _make(tmp_path)
    with patch("os.kill"):
        store.send("j", 10, "SIGTERM")
        store.send("j", 10, "SIGUSR1")
    assert len(store.history("j")) == 2


# ---------------------------------------------------------------------------
# JobSignal.history / clear_history
# ---------------------------------------------------------------------------

def test_history_empty_for_unknown_job(tmp_path):
    store = _make(tmp_path)
    assert store.history("nope") == []


def test_clear_history_returns_count(tmp_path):
    store = _make(tmp_path)
    with patch("os.kill"):
        store.send("j", 5, "SIGTERM")
        store.send("j", 5, "SIGHUP")
    removed = store.clear_history("j")
    assert removed == 2
    assert store.history("j") == []


def test_clear_history_nonexistent_returns_zero(tmp_path):
    store = _make(tmp_path)
    assert store.clear_history("ghost") == 0


# ---------------------------------------------------------------------------
# signal_cli
# ---------------------------------------------------------------------------

def _run(args, tmp_path):
    from cronwrap.signal_cli import main
    return main(["--state-dir", str(tmp_path / "signals")] + args)


def test_cli_no_command_returns_1(tmp_path):
    assert _run([], tmp_path) == 1


def test_cli_send_bad_signal_returns_3(tmp_path):
    rc = _run(["send", "job", str(os.getpid()), "SIGSTOP"], tmp_path)
    assert rc == 3


def test_cli_send_bad_extra_returns_2(tmp_path):
    rc = _run(["send", "job", str(os.getpid()), "SIGTERM", "--extra", "not-json"], tmp_path)
    assert rc == 2


def test_cli_history_empty(tmp_path, capsys):
    rc = _run(["history", "myjob"], tmp_path)
    assert rc == 0
    out = capsys.readouterr().out
    assert "No signal history" in out


def test_cli_history_json(tmp_path, capsys):
    store = JobSignal(state_dir=str(tmp_path / "signals"))
    with patch("os.kill"):
        store.send("j", 7, "SIGTERM")
    rc = _run(["history", "j", "--json"], tmp_path)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    assert data[0]["signal_name"] == "SIGTERM"


def test_cli_clear(tmp_path, capsys):
    store = JobSignal(state_dir=str(tmp_path / "signals"))
    with patch("os.kill"):
        store.send("j", 7, "SIGHUP")
    rc = _run(["clear", "j"], tmp_path)
    assert rc == 0
    assert "1 record" in capsys.readouterr().out
