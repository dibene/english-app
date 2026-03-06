"""Unit tests for TextComparisonEngine — no external API calls needed."""

import pytest

from core.models.diff import DiffEntry, DiffResult
from core.models.transcription import TranscriptionResult, WordResult
from core.services.text_comparison import TextComparisonEngine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_transcription(words: list[tuple[str, float]]) -> TranscriptionResult:
    """Build a TranscriptionResult from (word, confidence) tuples."""
    word_results = [
        WordResult(word=w, confidence=c, start_time=None, end_time=None) for w, c in words
    ]
    transcript = " ".join(w for w, _ in words)
    return TranscriptionResult(transcript=transcript, words=word_results)


def _statuses(result: DiffResult) -> list[str]:
    return [e.status for e in result.entries]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_all_words_ok() -> None:
    engine = TextComparisonEngine()
    transcription = _make_transcription([("hello", 0.99), ("world", 0.95)])
    result = engine.compare("hello world", transcription)

    assert _statuses(result) == ["ok", "ok"]
    assert result.entries[0].expected_word == "hello"
    assert result.entries[0].spoken_word == "hello"
    assert result.entries[1].expected_word == "world"
    assert result.entries[1].spoken_word == "world"


def test_missing_word() -> None:
    engine = TextComparisonEngine()
    # User said only "hello", skipped "world"
    transcription = _make_transcription([("hello", 0.99)])
    result = engine.compare("hello world", transcription)

    assert "missing" in _statuses(result)
    missing = [e for e in result.entries if e.status == "missing"]
    assert len(missing) == 1
    assert missing[0].expected_word == "world"
    assert missing[0].spoken_word is None
    assert missing[0].confidence is None


def test_inserted_word() -> None:
    engine = TextComparisonEngine()
    # User said "hello world extra word"
    transcription = _make_transcription(
        [("hello", 0.99), ("world", 0.95), ("extra", 0.92), ("word", 0.90)]
    )
    result = engine.compare("hello world", transcription)

    inserted = [e for e in result.entries if e.status == "inserted"]
    assert len(inserted) >= 1
    inserted_words = {e.spoken_word for e in inserted}
    assert inserted_words & {"extra", "word"}


def test_mispronounced_word_low_confidence() -> None:
    engine = TextComparisonEngine()  # default threshold 0.7
    transcription = _make_transcription([("hello", 0.99), ("world", 0.5)])
    result = engine.compare("hello world", transcription)

    assert _statuses(result) == ["ok", "mispronounced"]
    mispronounced = result.entries[1]
    assert mispronounced.expected_word == "world"
    assert mispronounced.spoken_word == "world"
    assert mispronounced.confidence == 0.5


def test_word_exactly_at_threshold_is_ok() -> None:
    engine = TextComparisonEngine(mispronounced_threshold=0.7)
    transcription = _make_transcription([("hello", 0.99), ("world", 0.7)])
    result = engine.compare("hello world", transcription)

    assert _statuses(result) == ["ok", "ok"]


def test_word_above_threshold_not_mispronounced() -> None:
    engine = TextComparisonEngine(mispronounced_threshold=0.7)
    transcription = _make_transcription([("hello", 0.99), ("world", 0.85)])
    result = engine.compare("hello world", transcription)

    assert all(e.status == "ok" for e in result.entries)


def test_empty_transcription_result() -> None:
    engine = TextComparisonEngine()
    transcription = TranscriptionResult(transcript="", words=[])
    result = engine.compare("hello world", transcription)

    assert len(result.entries) == 2
    assert all(e.status == "missing" for e in result.entries)


def test_expected_text_empty_after_normalization() -> None:
    engine = TextComparisonEngine()
    transcription = _make_transcription([("hello", 0.99)])
    # Only punctuation — normalizes to empty word list
    result = engine.compare("..., !!!", transcription)

    assert len(result.entries) == 1
    assert result.entries[0].status == "inserted"
    assert result.entries[0].spoken_word == "hello"


def test_normalization_strips_punctuation() -> None:
    engine = TextComparisonEngine()
    transcription = _make_transcription([("hello", 0.99), ("world", 0.95)])
    result = engine.compare("Hello, world!", transcription)

    assert _statuses(result) == ["ok", "ok"]


def test_configurable_threshold() -> None:
    engine = TextComparisonEngine(mispronounced_threshold=0.9)
    # confidence 0.8 is below 0.9 threshold -> mispronounced
    transcription = _make_transcription([("hello", 0.99), ("world", 0.8)])
    result = engine.compare("hello world", transcription)

    assert result.entries[1].status == "mispronounced"


def test_configurable_threshold_low() -> None:
    engine = TextComparisonEngine(mispronounced_threshold=0.3)
    # confidence 0.5 is above 0.3 threshold -> ok
    transcription = _make_transcription([("hello", 0.99), ("world", 0.5)])
    result = engine.compare("hello world", transcription)

    assert _statuses(result) == ["ok", "ok"]


def test_replace_with_high_confidence_word() -> None:
    engine = TextComparisonEngine()
    # User said "cat" instead of "dog" with high confidence -> missing + inserted
    transcription = _make_transcription([("cat", 0.99)])
    result = engine.compare("dog", transcription)

    statuses = _statuses(result)
    assert "missing" in statuses
    assert "inserted" in statuses


def test_replace_with_low_confidence_word() -> None:
    engine = TextComparisonEngine()
    # User said "cat" instead of "dog" with low confidence -> mispronounced
    transcription = _make_transcription([("cat", 0.4)])
    result = engine.compare("dog", transcription)

    assert _statuses(result) == ["mispronounced"]
    assert result.entries[0].expected_word == "dog"
    assert result.entries[0].spoken_word == "cat"


def test_multiword_sentence() -> None:
    engine = TextComparisonEngine()
    transcription = _make_transcription(
        [("the", 0.99), ("cat", 0.3), ("sat", 0.95), ("on", 0.99), ("the", 0.99), ("mat", 0.99)]
    )
    result = engine.compare("The cat sat on the mat", transcription)

    ok_entries = [e for e in result.entries if e.status == "ok"]
    mispronounced = [e for e in result.entries if e.status == "mispronounced"]
    assert len(ok_entries) == 5
    assert len(mispronounced) == 1
    assert mispronounced[0].expected_word == "cat"


def test_diff_result_is_dataclass() -> None:
    result = DiffResult()
    assert result.entries == []


def test_diff_entry_fields() -> None:
    entry = DiffEntry(
        expected_word="hello",
        spoken_word="hello",
        status="ok",
        confidence=0.99,
    )
    assert entry.expected_word == "hello"
    assert entry.spoken_word == "hello"
    assert entry.status == "ok"
    assert entry.confidence == 0.99
    assert entry.expected_phonemes is None  # not set by default


def test_expected_phonemes_populated_for_ok_word() -> None:
    engine = TextComparisonEngine()
    transcription = _make_transcription([("hello", 0.99), ("world", 0.95)])
    result = engine.compare("hello world", transcription)

    # Both words are in cmudict so phonemes must be populated
    assert result.entries[0].expected_phonemes is not None
    assert isinstance(result.entries[0].expected_phonemes, list)
    assert len(result.entries[0].expected_phonemes) > 0
    assert result.entries[1].expected_phonemes is not None
    # "world" ARPAbet: W ER1 L D
    assert "W" in result.entries[1].expected_phonemes


def test_expected_phonemes_populated_for_mispronounced() -> None:
    engine = TextComparisonEngine()
    transcription = _make_transcription([("hello", 0.99), ("world", 0.4)])
    result = engine.compare("hello world", transcription)

    mispronounced = [e for e in result.entries if e.status == "mispronounced"]
    assert len(mispronounced) == 1
    assert mispronounced[0].expected_phonemes is not None
    assert "W" in mispronounced[0].expected_phonemes


def test_expected_phonemes_populated_for_missing_word() -> None:
    engine = TextComparisonEngine()
    transcription = _make_transcription([("hello", 0.99)])
    result = engine.compare("hello world", transcription)

    missing = [e for e in result.entries if e.status == "missing"]
    assert len(missing) == 1
    assert missing[0].expected_phonemes is not None
    assert "W" in missing[0].expected_phonemes


def test_expected_phonemes_none_for_inserted_entry() -> None:
    engine = TextComparisonEngine()
    # extra word has no expected_word -> no expected phonemes
    transcription = _make_transcription([("hello", 0.99), ("world", 0.95), ("extra", 0.92)])
    result = engine.compare("hello world", transcription)

    inserted = [e for e in result.entries if e.status == "inserted"]
    assert len(inserted) >= 1
    for entry in inserted:
        assert entry.expected_phonemes is None


def test_expected_phonemes_none_for_unknown_word() -> None:
    engine = TextComparisonEngine()
    # "zxqwerty" is not in cmudict
    transcription = _make_transcription([("zxqwerty", 0.99)])
    result = engine.compare("zxqwerty", transcription)

    assert result.entries[0].expected_phonemes is None
