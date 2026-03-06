"""Unit tests for DeepgramSTTProvider — all SDK calls are mocked."""

from unittest.mock import MagicMock, patch

import pytest

from core.exceptions import TranscriptionError
from providers.deepgram_stt import DeepgramSTTProvider


def _make_word(word: str, confidence: float, start: float, end: float) -> MagicMock:
    w = MagicMock()
    w.word = word
    w.confidence = confidence
    w.start = start
    w.end = end
    return w


def _make_response(transcript: str, words: list[MagicMock], confidence: float = 0.97) -> MagicMock:
    alternative = MagicMock()
    alternative.transcript = transcript
    alternative.confidence = confidence
    alternative.words = words

    channel = MagicMock()
    channel.alternatives = [alternative]

    response = MagicMock()
    response.results.channels = [channel]
    return response


@pytest.fixture
def provider() -> DeepgramSTTProvider:
    with patch("providers.deepgram_stt.DeepgramClient"):
        return DeepgramSTTProvider(api_key="test-key")


def test_missing_api_key_raises_value_error() -> None:
    with pytest.raises(ValueError, match="DEEPGRAM_API_KEY"):
        DeepgramSTTProvider(api_key="")


def test_whitespace_api_key_raises_value_error() -> None:
    with pytest.raises(ValueError, match="DEEPGRAM_API_KEY"):
        DeepgramSTTProvider(api_key="   ")


def test_transcribe_returns_transcript_text(provider: DeepgramSTTProvider) -> None:
    response = _make_response(
        transcript="hello world",
        words=[_make_word("hello", 0.99, 0.0, 0.5), _make_word("world", 0.95, 0.6, 1.0)],
    )
    provider._client.listen.v1.media.transcribe_file.return_value = response

    result = provider.transcribe(b"fake-audio")

    assert result.transcript == "hello world"


def test_transcribe_returns_transcript_confidence(provider: DeepgramSTTProvider) -> None:
    response = _make_response(transcript="hello world", words=[], confidence=0.92)
    provider._client.listen.v1.media.transcribe_file.return_value = response

    result = provider.transcribe(b"fake-audio")

    assert result.confidence == 0.92


def test_transcribe_returns_word_list_with_correct_fields(
    provider: DeepgramSTTProvider,
) -> None:
    words = [
        _make_word("hello", 0.99, 0.0, 0.5),
        _make_word("world", 0.95, 0.6, 1.0),
    ]
    response = _make_response(transcript="hello world", words=words)
    provider._client.listen.v1.media.transcribe_file.return_value = response

    result = provider.transcribe(b"fake-audio")

    assert len(result.words) == 2
    assert result.words[0].word == "hello"
    assert result.words[0].confidence == 0.99
    assert result.words[0].start_time == 0.0
    assert result.words[0].end_time == 0.5
    assert result.words[1].word == "world"
    assert result.words[1].confidence == 0.95


def test_transcribe_empty_audio_returns_empty_result(provider: DeepgramSTTProvider) -> None:
    response = _make_response(transcript="", words=[])
    provider._client.listen.v1.media.transcribe_file.return_value = response

    result = provider.transcribe(b"")

    assert result.transcript == ""
    assert result.words == []


def test_transcribe_raises_transcription_error_on_sdk_failure(
    provider: DeepgramSTTProvider,
) -> None:
    provider._client.listen.v1.media.transcribe_file.side_effect = RuntimeError("API down")

    with pytest.raises(TranscriptionError, match="Deepgram transcription failed"):
        provider.transcribe(b"fake-audio")
