"""Tests for cronwrap.quota_forecast_cli."""
import json
import sys

import pytest

from cronwrap.quota_forecast_cli import build_parser, main


def _run(*args):
    return main(list(args))


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1():
    assert _run() == 1


def test_show_command_text_ok(capsys):
    rc = _run("show", "--job", "backup", "--limit", "100",
              "--current", "30", "--history", "10,10,10")
    assert rc == 0
    out = capsys.readouterr().out
    assert "backup" in out
    assert "OK" in out


def test_show_command_will_exhaust(capsys):
    rc = _run("show", "--job", "backup", "--limit", "100",
              "--current", "95", "--history", "10,10,10")
    assert rc == 0
    out = capsys.readouterr().out
    assert "WILL EXHAUST" in out


def test_show_command_json_format(capsys):
    rc = _run("show", "--job", "myjob", "--limit", "200",
              "--current", "50", "--history", "20,25",
              "--format", "json")
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["job_name"] == "myjob"
    assert "will_exhaust" in data


def test_show_no_history(capsys):
    rc = _run("show", "--job", "j", "--limit", "100")
    assert rc == 0
    out = capsys.readouterr().out
    assert "N/A" in out


def test_show_invalid_history_returns_2(capsys):
    rc = _run("show", "--job", "j", "--limit", "100", "--history", "a,b")
    assert rc == 2


def test_show_invalid_limit_returns_2(capsys):
    rc = _run("show", "--job", "j", "--limit", "0")
    assert rc == 2
