"""Tests for cronwrap.job_score and cronwrap.score_cli."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.history import HistoryEntry, JobHistory
from cronwrap.job_score import ScoreResult, ScoringError, compute_score
from cronwrap.score_cli import build_parser, main


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_history(tmp_path: Path, job_name: str, entries: list[dict]) -> str:
    hist = JobHistory(job_name=job_name, history_dir=str(tmp_path))
    for e in entries:
        hist.record(
            HistoryEntry(
                success=e.get("success", True),
                duration=e.get("duration", 5.0),
                exit_code=e.get("exit_code", 0),
            )
        )
    return str(tmp_path)


# ---------------------------------------------------------------------------
# ScoreResult
# ---------------------------------------------------------------------------

def test_score_result_grade_a():
    r = ScoreResult(job_name="j", score=95.0, success_rate=1.0, avg_duration=1.0, sample_size=10)
    assert r.grade == "A"


def test_score_result_grade_f():
    r = ScoreResult(job_name="j", score=20.0, success_rate=0.2, avg_duration=200.0, sample_size=5)
    assert r.grade == "F"


def test_score_result_to_dict_keys():
    r = ScoreResult(job_name="j", score=80.0, success_rate=0.9, avg_duration=10.0, sample_size=20)
    d = r.to_dict()
    for key in ("job_name", "score", "grade", "success_rate", "avg_duration", "sample_size"):
        assert key in d


def test_score_result_to_dict_omits_extra_when_empty():
    r = ScoreResult(job_name="j", score=80.0, success_rate=0.9, avg_duration=10.0, sample_size=5)
    assert "extra" not in r.to_dict()


def test_score_result_to_json_valid():
    r = ScoreResult(job_name="j", score=75.0, success_rate=0.8, avg_duration=5.0, sample_size=3)
    parsed = json.loads(r.to_json())
    assert parsed["job_name"] == "j"


# ---------------------------------------------------------------------------
# compute_score
# ---------------------------------------------------------------------------

def test_compute_score_all_success(tmp_path):
    hdir = _write_history(tmp_path, "myjob", [{"success": True, "duration": 5.0}] * 10)
    result = compute_score("myjob", hdir)
    assert result.success_rate == pytest.approx(1.0)
    assert result.score == pytest.approx(100.0)
    assert result.grade == "A"


def test_compute_score_all_failure(tmp_path):
    hdir = _write_history(tmp_path, "badjob", [{"success": False, "duration": 2.0, "exit_code": 1}] * 5)
    result = compute_score("badjob", hdir)
    assert result.success_rate == pytest.approx(0.0)
    assert result.score < 40


def test_compute_score_no_history_raises(tmp_path):
    with pytest.raises(ScoringError):
        compute_score("ghost", str(tmp_path))


def test_compute_score_duration_penalty(tmp_path):
    # avg_duration = 120s, threshold = 60s → dur_score = 0.0
    hdir = _write_history(tmp_path, "slowjob", [{"success": True, "duration": 120.0}] * 5)
    result = compute_score("slowjob", hdir, duration_penalty_threshold=60.0)
    assert result.score == pytest.approx(70.0)  # 100% SR * 70 + 0 * 30


def test_compute_score_respects_window(tmp_path):
    entries = [{"success": False, "duration": 1.0, "exit_code": 1}] * 5
    entries += [{"success": True, "duration": 1.0}] * 5
    hdir = _write_history(tmp_path, "winjob", entries)
    result = compute_score("winjob", hdir, window=5)
    assert result.success_rate == pytest.approx(1.0)
    assert result.sample_size == 5


# ---------------------------------------------------------------------------
# score_cli
# ---------------------------------------------------------------------------

def _run(argv):
    return main(argv)


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1():
    assert _run([]) == 1


def test_show_missing_history_returns_2(tmp_path):
    assert _run(["show", "ghost", "--history-dir", str(tmp_path)]) == 2


def test_show_command_text_output(tmp_path, capsys):
    hdir = _write_history(tmp_path, "ok", [{"success": True, "duration": 3.0}] * 4)
    rc = _run(["show", "ok", "--history-dir", hdir])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Score:" in out
    assert "Grade:" in out


def test_show_command_json_output(tmp_path, capsys):
    hdir = _write_history(tmp_path, "ok", [{"success": True, "duration": 3.0}] * 4)
    rc = _run(["show", "ok", "--history-dir", hdir, "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["job_name"] == "ok"
    assert "grade" in data
