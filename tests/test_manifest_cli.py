"""Tests for cronwrap.manifest_cli."""
import json
import pytest

from cronwrap.manifest_cli import build_parser, main


def _run(tmp_path, *args):
    manifest_path = str(tmp_path / "manifest.json")
    return main(["--manifest", manifest_path, *args])


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1(tmp_path):
    assert _run(tmp_path) == 1


def test_register_returns_0(tmp_path):
    assert _run(tmp_path, "register", "myjob", "run.sh") == 0


def test_register_persists_entry(tmp_path):
    _run(tmp_path, "register", "myjob", "run.sh", "--schedule", "0 * * * *")
    manifest_path = str(tmp_path / "manifest.json")
    with open(manifest_path) as fh:
        data = json.load(fh)
    assert "myjob" in data
    assert data["myjob"]["schedule"] == "0 * * * *"


def test_register_with_tags(tmp_path):
    _run(tmp_path, "register", "myjob", "run.sh", "--tags", "infra,db")
    manifest_path = str(tmp_path / "manifest.json")
    with open(manifest_path) as fh:
        data = json.load(fh)
    assert data["myjob"]["tags"] == ["infra", "db"]


def test_show_existing_job(tmp_path, capsys):
    _run(tmp_path, "register", "myjob", "run.sh")
    rc = _run(tmp_path, "show", "myjob")
    assert rc == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["job_name"] == "myjob"


def test_show_missing_job_returns_2(tmp_path):
    assert _run(tmp_path, "show", "ghost") == 2


def test_remove_existing_returns_0(tmp_path):
    _run(tmp_path, "register", "myjob", "run.sh")
    assert _run(tmp_path, "remove", "myjob") == 0


def test_remove_missing_returns_2(tmp_path):
    assert _run(tmp_path, "remove", "ghost") == 2


def test_list_empty(tmp_path, capsys):
    rc = _run(tmp_path, "list")
    assert rc == 0
    assert "No jobs" in capsys.readouterr().out


def test_list_shows_registered_jobs(tmp_path, capsys):
    _run(tmp_path, "register", "alpha", "a.sh")
    _run(tmp_path, "register", "beta", "b.sh")
    rc = _run(tmp_path, "list")
    assert rc == 0
    out = capsys.readouterr().out
    assert "alpha" in out
    assert "beta" in out
