"""Tests for cronwrap.quota_audit_cli."""
import json
import pytest
from cronwrap.quota_audit_cli import build_parser, main
from cronwrap.job_quota_audit import QuotaAuditLog, QuotaAuditEvent


def _run(argv, tmp_path):
    return main(["--log-dir", str(tmp_path / "audit")] + argv)


def _write_event(tmp_path, **kwargs):
    log = QuotaAuditLog(str(tmp_path / "audit"))
    defaults = dict(job_name="myjob", action="allowed", quota_used=2, quota_limit=5)
    defaults.update(kwargs)
    log.record(QuotaAuditEvent(**defaults))
    return log


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1(tmp_path):
    assert _run([], tmp_path) == 1


def test_show_empty_returns_0(tmp_path):
    assert _run(["show", "myjob"], tmp_path) == 0


def test_show_text_format(tmp_path, capsys):
    _write_event(tmp_path, action="denied", reason="cap")
    rc = _run(["show", "myjob"], tmp_path)
    assert rc == 0
    out = capsys.readouterr().out
    assert "DENIED" in out
    assert "cap" in out


def test_show_json_format(tmp_path, capsys):
    _write_event(tmp_path, action="allowed")
    rc = _run(["show", "myjob", "--format", "json"], tmp_path)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list)
    assert data[0]["action"] == "allowed"


def test_clear_returns_0(tmp_path):
    _write_event(tmp_path)
    rc = _run(["clear", "myjob"], tmp_path)
    assert rc == 0


def test_clear_removes_events(tmp_path):
    _write_event(tmp_path)
    _run(["clear", "myjob"], tmp_path)
    log = QuotaAuditLog(str(tmp_path / "audit"))
    assert log.events("myjob") == []
