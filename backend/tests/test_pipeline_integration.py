"""Integration tests for PronunciationService pipeline."""

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

_FIXTURES_DIR = Path(__file__).parent / "fixtures"

_run_live = os.environ.get("RUN_PIPELINE_LIVE_TESTS", "false").lower() == "true"
_speech_key = os.environ.get("AZURE_SPEECH_KEY", "")
_speech_region = os.environ.get("AZURE_SPEECH_REGION", "")
_openai_key = os.environ.get("OPENAI_API_KEY", "")
_live_skip_reason = (
    None
    if (_run_live and _speech_key and _speech_region and _openai_key)
    else "live tests disabled (set RUN_PIPELINE_LIVE_TESTS=true and provide API keys)"
)

from core.exceptions import LLMFeedbackError, PronunciationError
from core.models.diff import DiffResult
from core.models.pronunciation import PronunciationResult
from core.models.transcription import TranscriptionResult, WordResult
from core.services.pronunciation_service import (
    PronunciationService,
    _transcription_to_pronunciation_result,
)
from core.services.text_comparison import TextComparisonEngine

# ---------------------------------------------------------------------------

_MOCK_FEEDBACK: dict[str, Any] = {
    "score": 85,
    "errors": [{"word": "world", "issue": "mispronounced", "suggestion": "Focus on ER vowel"}],
    "suggestions": ["Practice the R-colored vowel"],
}


def _make_pronunciation_result(words: list[tuple[str, float]]) -> PronunciationResult:
    word_results = [
        WordResult(word=w, confidence=c, start_time=None, end_time=None) for w, c in words
    ]
    return PronunciationResult(
        accuracy_score=85.0,
        fluency_score=80.0,
        completeness_score=100.0,
        prosody_score=None,
        words=word_results,
    )


def _build_service(
    pronunciation_result: PronunciationResult | None = None,
    transcription_result: TranscriptionResult | None = None,
    feedback: dict[str, Any] | None = None,
) -> PronunciationService:
    """Build a PronunciationService with mocked providers."""
    pronunciation_provider = None
    stt_provider = None

    if pronunciation_result is not None:
        pronunciation_provider = MagicMock()
        pronunciation_provider.assess.return_value = pronunciation_result

    if transcription_result is not None:
        stt_provider = MagicMock()
        stt_provider.transcribe.return_value = transcription_result

    llm_provider = MagicMock()
    llm_provider.generate_feedback.return_value = feedback or _MOCK_FEEDBACK

    return PronunciationService(
        comparison_engine=TextComparisonEngine(),
        llm_provider=llm_provider,
        pronunciation_provider=pronunciation_provider,
        stt_provider=stt_provider,
    )


# ---------------------------------------------------------------------------
# CI tests (no real providers)
# ---------------------------------------------------------------------------


def test_analyze_returns_feedback_dict_with_azure_provider() -> None:
    """Full pipeline via Azure path returns feedback dict with expected keys."""
    pa_result = _make_pronunciation_result([("hello", 0.99), ("world", 0.95)])
    service = _build_service(pronunciation_result=pa_result)

    feedback = service.analyze(b"fake-audio", "hello world")

    assert isinstance(feedback, dict)
    assert "score" in feedback
    assert "errors" in feedback
    assert "suggestions" in feedback
    assert isinstance(feedback["errors"], list)
    assert isinstance(feedback["suggestions"], list)


def test_analyze_uses_deepgram_fallback_when_no_azure() -> None:
    """Pipeline falls back to STT provider and adapts TranscriptionResult correctly."""
    words = [
        WordResult(word="hello", confidence=0.9, start_time=0.0, end_time=0.5),
        WordResult(word="world", confidence=0.8, start_time=0.6, end_time=1.0),
    ]
    transcription = TranscriptionResult(transcript="hello world", confidence=0.85, words=words)
    service = _build_service(transcription_result=transcription)

    feedback = service.analyze(b"fake-audio", "hello world")

    assert "score" in feedback
    assert "errors" in feedback
    assert "suggestions" in feedback


def test_adapter_converts_transcription_to_pronunciation_result() -> None:
    """_transcription_to_pronunciation_result maps confidence correctly."""
    words = [WordResult(word="hello", confidence=0.9, start_time=None, end_time=None)]
    t = TranscriptionResult(transcript="hello", confidence=0.75, words=words)

    result = _transcription_to_pronunciation_result(t)

    assert result.accuracy_score == pytest.approx(75.0)
    assert result.fluency_score == pytest.approx(75.0)
    assert result.completeness_score == 100.0
    assert result.prosody_score is None
    assert result.words is words  # same list, not copied


def test_analyze_propagates_pronunciation_error() -> None:
    """PronunciationError raised by provider propagates out of analyze()."""
    pronunciation_provider = MagicMock()
    pronunciation_provider.assess.side_effect = PronunciationError("API failure")

    llm_provider = MagicMock()
    service = PronunciationService(
        comparison_engine=TextComparisonEngine(),
        llm_provider=llm_provider,
        pronunciation_provider=pronunciation_provider,
    )

    with pytest.raises(PronunciationError, match="API failure"):
        service.analyze(b"audio", "hello world")


def test_analyze_propagates_llm_error() -> None:
    """LLMFeedbackError raised by LLM provider propagates out of analyze()."""
    pa_result = _make_pronunciation_result([("hello", 0.99)])
    llm_provider = MagicMock()
    llm_provider.generate_feedback.side_effect = LLMFeedbackError("LLM timeout")

    pronunciation_provider = MagicMock()
    pronunciation_provider.assess.return_value = pa_result

    service = PronunciationService(
        comparison_engine=TextComparisonEngine(),
        llm_provider=llm_provider,
        pronunciation_provider=pronunciation_provider,
    )

    with pytest.raises(LLMFeedbackError, match="LLM timeout"):
        service.analyze(b"audio", "hello")


def test_service_requires_at_least_one_provider() -> None:
    """Constructing PronunciationService with both providers None raises ValueError."""
    with pytest.raises(ValueError, match="At least one"):
        PronunciationService(
            comparison_engine=TextComparisonEngine(),
            llm_provider=MagicMock(),
            pronunciation_provider=None,
            stt_provider=None,
        )


# ---------------------------------------------------------------------------
# Live tests (real providers — skipped in CI)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(bool(_live_skip_reason), reason=_live_skip_reason or "")
def test_analyze_live_azure() -> None:
    """Full pipeline with real Azure + OpenAI providers."""
    from providers.azure_pronunciation import AzurePronunciationProvider
    from providers.openai_llm import OpenAILLMProvider

    fixture = _FIXTURES_DIR / "hello_how_are_you.wav"
    if not fixture.exists():
        pytest.skip(f"Fixture not found: {fixture}. Run tests/fixtures/generate_fixtures.py")

    pronunciation_provider = AzurePronunciationProvider(
        key=_speech_key,
        region=_speech_region,
    )
    llm_provider = OpenAILLMProvider(api_key=_openai_key)

    service = PronunciationService(
        comparison_engine=TextComparisonEngine(),
        llm_provider=llm_provider,
        pronunciation_provider=pronunciation_provider,
    )

    feedback = service.analyze(fixture.read_bytes(), "hello how are you")

    assert isinstance(feedback.get("score"), int)
    assert 0 <= feedback["score"] <= 100
    assert isinstance(feedback.get("errors"), list)
    assert isinstance(feedback.get("suggestions"), list)
