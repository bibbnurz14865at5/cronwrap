"""Tests for cronwrap.annotations_cli."""
import json
import pytest
from cronwrap.annotations_cli import build_parser, main


def _run(tmp_path, *args):
    return main(["--storage-dir", str(tmp_path), "--job", "testjob"] + list(args))


def test_build_parser_returns_parser(tmp_path):
    p = build_parser()
    assert p is not None


def test_set_and_get(tmp_path, capsys):
    assert _run(tmp_path, "set", "owner", "alice") == 0
    assert _run(tmp_path, "get", "owner") == 0
    assert capsys.readouterr().out.strip() == "alice"


def test_get_missing_returns_1(tmp_path, capsys):
    rc = _run(tmp_path, "get", "ghost")
    assert rc == 1


def test_list_empty(tmp_path, capsys):
    _run(tmp_path, "list")
    out = capsys.readouterr().out
    assert json.loads(out) == {}


def test_list_with_entries(tmp_path, capsys):
    _run(tmp_path, "set", "a", "1")
    _run(tmp_path, "set", "b", "2")
    _run(tmp_path, "list")
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data == {"a": "1", "b": "2"}


def test_remove_existing(tmp_path, capsys):
    _run(tmp_path, "set", "k", "v")
    rc = _run(tmp_path, "remove", "k")
    assert rc == 0


def test_remove_missing_returns_1(tmp_path):
    rc = _run(tmp_path, "remove", "ghost")
    assert rc == 1


def test_clear(tmp_path, capsys):
    _run(tmp_path, "set", "x", "1")
    _run(tmp_path, "clear")
    _run(tmp_path, "list")
    out = capsys.readouterr().out
    assert json.loads(out) == {}
