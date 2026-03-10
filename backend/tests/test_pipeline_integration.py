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
from core.models.pronunciation import PronunciationResult
from core.models.transcription import WordResult
from core.services.pronunciation_service import PronunciationService
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
    feedback: dict[str, Any] | None = None,
    enable_llm: bool = True,
) -> PronunciationService:
    """Build a PronunciationService with mocked providers."""
    pronunciation_provider = MagicMock()
    pronunciation_provider.assess.return_value = pronunciation_result or _make_pronunciation_result(
        [("hello", 0.99)]
    )

    llm_provider = MagicMock()
    llm_provider.generate_feedback.return_value = feedback or _MOCK_FEEDBACK

    return PronunciationService(
        comparison_engine=TextComparisonEngine(),
        llm_provider=llm_provider,
        pronunciation_provider=pronunciation_provider,
        enable_llm=enable_llm,
    )


# ---------------------------------------------------------------------------
# CI tests (no real providers)
# ---------------------------------------------------------------------------


def test_analyze_returns_feedback_dict() -> None:
    """Full pipeline returns feedback dict with expected keys."""
    pa_result = _make_pronunciation_result([("hello", 0.99), ("world", 0.95)])
    service = _build_service(pronunciation_result=pa_result)

    feedback = service.analyze(b"fake-audio", "hello world")

    assert isinstance(feedback, dict)
    assert "score" in feedback
    assert "errors" in feedback
    assert "suggestions" in feedback
    assert isinstance(feedback["errors"], list)
    assert isinstance(feedback["suggestions"], list)


def test_analyze_with_llm_disabled_skips_llm_call() -> None:
    """When enable_llm=False, LLM provider is never called and suggestions is empty."""
    pa_result = _make_pronunciation_result([("hello", 0.99), ("world", 0.95)])
    service = _build_service(pronunciation_result=pa_result, enable_llm=False)

    feedback = service.analyze(b"fake-audio", "hello world")

    assert "score" in feedback
    assert feedback["suggestions"] == []
    # LLM should NOT have been called
    service._llm_provider.generate_feedback.assert_not_called()  # type: ignore[attr-defined]


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


def test_service_requires_pronunciation_provider() -> None:
    """PronunciationService requires a pronunciation_provider (no longer optional)."""
    # TypeError is raised by Python when the required positional arg is missing.
    with pytest.raises(TypeError):
        PronunciationService(  # type: ignore[call-arg]
            comparison_engine=TextComparisonEngine(),
            llm_provider=MagicMock(),
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
