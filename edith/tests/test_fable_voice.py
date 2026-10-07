"""Unit tests for Fable-inspired voice transcript streaming helpers."""

from edith.voice.transcript_stream import (
    merge_speech_transcript,
    normalize_speech_transcript,
    should_commit_interim_transcript,
)


def test_normalize_speech_transcript():
    assert normalize_speech_transcript("  hello    edith   ") == "hello edith"
    assert normalize_speech_transcript(None) == ""


def test_merge_speech_transcript():
    assert merge_speech_transcript("open chrome", "open chrome") == "open chrome"
    assert merge_speech_transcript("hello", None) == "hello"
    assert merge_speech_transcript(None, "world") == "world"


def test_should_commit_interim_transcript():
    # Trigger command with fast stable time >= 180ms
    assert should_commit_interim_transcript("edith", 200.0) is True
    assert should_commit_interim_transcript("edith", 100.0) is False

    # Long sentence with stable time >= 450ms
    assert should_commit_interim_transcript("please open my chrome browser", 500.0) is True
    assert should_commit_interim_transcript("please open my chrome browser", 300.0) is False
