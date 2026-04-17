"""Tests for cronwrap.output_capture."""
import pytest
from cronwrap.output_capture import (
    CapturedOutput,
    capture,
    tail_lines,
    DEFAULT_MAX_BYTES,
)


def test_capture_no_truncation():
    result = capture("hello", "world")
    assert result.stdout == "hello"
    assert result.stderr == "world"
    assert result.truncated is False


def test_capture_truncates_stdout():
    big = "x" * (DEFAULT_MAX_BYTES + 100)
    result = capture(big, "")
    assert result.truncated is True
    assert "[truncated]" in result.stdout
    assert len(result.stdout.encode()) < DEFAULT_MAX_BYTES + 200


def test_capture_truncates_stderr():
    big = "e" * (DEFAULT_MAX_BYTES + 50)
    result = capture("", big)
    assert result.truncated is True
    assert "[truncated]" in result.stderr


def test_capture_custom_max_bytes():
    result = capture("abcdef", "", max_bytes=3)
    assert result.truncated is True
    assert result.stdout.startswith("abc")


def test_combined_both():
    result = CapturedOutput(stdout="out", stderr="err")
    combined = result.combined()
    assert "[stdout]" in combined
    assert "[stderr]" in combined
    assert "out" in combined
    assert "err" in combined


def test_combined_only_stdout():
    result = CapturedOutput(stdout="only", stderr="")
    assert "[stderr]" not in result.combined()


def test_to_dict_roundtrip():
    original = CapturedOutput(stdout="a", stderr="b", truncated=True)
    restored = CapturedOutput.from_dict(original.to_dict())
    assert restored.stdout == "a"
    assert restored.stderr == "b"
    assert restored.truncated is True


def test_from_dict_defaults():
    result = CapturedOutput.from_dict({})
    assert result.stdout == ""
    assert result.stderr == ""
    assert result.truncated is False


def test_tail_lines_fewer_than_n():
    text = "line1\nline2\nline3"
    assert tail_lines(text, 10) == text


def test_tail_lines_more_than_n():
    text = "\n".join(str(i) for i in range(50))
    result = tail_lines(text, 5)
    assert result == "45\n46\n47\n48\n49"


def test_tail_lines_empty():
    assert tail_lines("", 10) == ""
