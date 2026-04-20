"""Tests for cronwrap.job_secrets and cronwrap.secrets_cli."""
from __future__ import annotations

import os
import json
import pytest

from cronwrap.job_secrets import JobSecrets, SecretsCheckResult, SecretsRegistry
from cronwrap.secrets_cli import build_parser, main


# --- JobSecrets unit tests ---

def test_to_dict_keys():
    s = JobSecrets("myjob", required=["A"], optional=["B"])
    d = s.to_dict()
    assert set(d) == {"job_name", "required", "optional"}


def test_roundtrip():
    s = JobSecrets("myjob", required=["A", "B"], optional=["C"])
    assert JobSecrets.from_dict(s.to_dict()) == s


def test_from_dict_defaults():
    s = JobSecrets.from_dict({"job_name": "x"})
    assert s.required == []
    assert s.optional == []


def test_missing_required_all_absent(monkeypatch):
    monkeypatch.delenv("SECRET_X", raising=False)
    monkeypatch.delenv("SECRET_Y", raising=False)
    s = JobSecrets("j", required=["SECRET_X", "SECRET_Y"])
    assert s.missing_required() == ["SECRET_X", "SECRET_Y"]


def test_missing_required_some_present(monkeypatch):
    monkeypatch.setenv("SECRET_X", "val")
    monkeypatch.delenv("SECRET_Y", raising=False)
    s = JobSecrets("j", required=["SECRET_X", "SECRET_Y"])
    assert s.missing_required() == ["SECRET_Y"]


def test_check_ok(monkeypatch):
    monkeypatch.setenv("MY_KEY", "abc")
    s = JobSecrets("j", required=["MY_KEY"])
    r = s.check()
    assert r.ok is True
    assert r.missing == []


def test_check_not_ok(monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    s = JobSecrets("j", required=["MISSING_KEY"])
    r = s.check()
    assert r.ok is False
    assert "MISSING_KEY" in r.missing


# --- SecretsRegistry tests ---

def _make_registry(tmp_path):
    return SecretsRegistry(str(tmp_path / "secrets.json"))


def test_register_and_get(tmp_path):
    reg = _make_registry(tmp_path)
    s = JobSecrets("backup", required=["K"], optional=["O"])
    reg.register(s)
    got = reg.get("backup")
    assert got == s


def test_get_missing_returns_none(tmp_path):
    reg = _make_registry(tmp_path)
    assert reg.get("nope") is None


def test_all_jobs_sorted(tmp_path):
    reg = _make_registry(tmp_path)
    reg.register(JobSecrets("z"))
    reg.register(JobSecrets("a"))
    assert reg.all_jobs() == ["a", "z"]


def test_remove_existing(tmp_path):
    reg = _make_registry(tmp_path)
    reg.register(JobSecrets("j"))
    assert reg.remove("j") is True
    assert reg.get("j") is None


def test_remove_nonexistent(tmp_path):
    reg = _make_registry(tmp_path)
    assert reg.remove("ghost") is False


# --- CLI tests ---

def _run(argv, tmp_path):
    registry = str(tmp_path / "secrets.json")
    return main(["--registry", registry] + argv)


def test_build_parser_returns_parser():
    assert build_parser() is not None


def test_cli_register_and_list(tmp_path):
    assert _run(["register", "myjob", "--required", "A", "B"], tmp_path) == 0
    assert _run(["list"], tmp_path) == 0


def test_cli_check_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("SECRET_Z", raising=False)
    _run(["register", "j", "--required", "SECRET_Z"], tmp_path)
    rc = _run(["check", "j"], tmp_path)
    assert rc == 2


def test_cli_check_not_registered(tmp_path):
    assert _run(["check", "unknown"], tmp_path) == 1


def test_cli_remove(tmp_path):
    _run(["register", "j"], tmp_path)
    assert _run(["remove", "j"], tmp_path) == 0
    assert _run(["remove", "j"], tmp_path) == 1
