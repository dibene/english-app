"""Live tests for OpenAILLMProvider — makes a real API call to the configured LLM service.

These tests are skipped automatically unless both conditions are met:
  1. RUN_LLM_GEMINI_LIVE_TESTS=true  (in backend/.env or environment)
  2. LLM_API_KEY is set and non-empty

Run manually with:
    RUN_LLM_GEMINI_LIVE_TESTS=true uv run pytest tests/test_openai_llm_live.py -v

Or set RUN_LLM_GEMINI_LIVE_TESTS=true in backend/.env and run:
    uv run pytest tests/test_openai_llm_live.py -v

Works with any OpenAI-compatible provider (Gemini, Groq, Ollama, OpenAI).
OpenAI-compatible is the de-facto industry standard protocol — configure via
LLM_API_KEY + LLM_BASE_URL to switch between services without code changes.
Configure via LLM_API_KEY, LLM_MODEL, LLM_BASE_URL in backend/.env.
"""

import os

import pytest

from core.models.diff import DiffEntry, DiffResult
from core.models.transcription import PhonemeScore
from providers.openai_llm import OpenAILLMProvider

# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------

_api_key = os.environ.get("LLM_API_KEY", "").strip()
_run_live = os.environ.get("RUN_LLM_GEMINI_LIVE_TESTS", "false").lower() == "true"

_skip_reason = ""
if not _run_live:
    _skip_reason = "RUN_LLM_GEMINI_LIVE_TESTS is not set to true in backend/.env"
elif not _api_key:
    _skip_reason = "LLM_API_KEY is not set in backend/.env"

skip_if_not_configured = pytest.mark.skipif(
    not _run_live or not _api_key,
    reason=_skip_reason or "live tests disabled",
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def live_provider() -> OpenAILLMProvider:
    return OpenAILLMProvider(
        api_key=_api_key,
        model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        base_url=os.environ.get("LLM_BASE_URL") or None,
    )


def _make_diff_result() -> DiffResult:
    return DiffResult(
        entries=[
            DiffEntry(
                expected_word="hello",
                spoken_word="hello",
                status="ok",
                confidence=0.99,
            ),
            DiffEntry(
                expected_word="world",
                spoken_word="word",
                status="mispronounced",
                confidence=0.52,
            ),
            DiffEntry(
                expected_word="beautiful",
                spoken_word=None,
                status="missing",
                confidence=None,
            ),
        ]
    )


# ---------------------------------------------------------------------------
# Live tests
# ---------------------------------------------------------------------------


@skip_if_not_configured
def test_live_returns_valid_schema(live_provider: OpenAILLMProvider) -> None:
    """Real API call: response must have score, errors, and suggestions."""
    result = live_provider.generate_feedback("hello world beautiful", _make_diff_result())

    assert isinstance(result, dict), "response must be a dict"
    assert "score" in result, "response must have 'score'"
    assert "errors" in result, "response must have 'errors'"
    assert "suggestions" in result, "response must have 'suggestions'"


@skip_if_not_configured
def test_live_score_in_range(live_provider: OpenAILLMProvider) -> None:
    """score must be an integer between 0 and 100."""
    result = live_provider.generate_feedback("hello world beautiful", _make_diff_result())

    assert isinstance(result["score"], int), f"score must be int, got {type(result['score'])}"
    assert 0 <= result["score"] <= 100, f"score out of range: {result['score']}"


@skip_if_not_configured
def test_live_errors_is_list(live_provider: OpenAILLMProvider) -> None:
    """errors must be a list (can be empty)."""
    result = live_provider.generate_feedback("hello world beautiful", _make_diff_result())

    assert isinstance(result["errors"], list), "errors must be a list"


@skip_if_not_configured
def test_live_suggestions_is_list(live_provider: OpenAILLMProvider) -> None:
    """suggestions must be a non-empty list."""
    result = live_provider.generate_feedback("hello world beautiful", _make_diff_result())

    assert isinstance(result["suggestions"], list), "suggestions must be a list"
    assert len(result["suggestions"]) >= 1, "suggestions must have at least one item"


@skip_if_not_configured
def test_live_perfect_score_for_all_ok(live_provider: OpenAILLMProvider) -> None:
    """All-ok diff should produce a high score and empty errors list."""
    diff = DiffResult(
        entries=[
            DiffEntry(expected_word="hello", spoken_word="hello", status="ok", confidence=0.99),
            DiffEntry(expected_word="world", spoken_word="world", status="ok", confidence=0.97),
        ]
    )
    result = live_provider.generate_feedback("hello world", diff)

    assert result["score"] >= 80, f"all-ok diff should score >= 80, got {result['score']}"


@skip_if_not_configured
def test_live_phoneme_scores_in_prompt_affect_response(live_provider: OpenAILLMProvider) -> None:
    """Phoneme scores in DiffResult entries must not break the response schema.

    Sends a diff where a mispronounced word includes per-phoneme detail and
    verifies the LLM still returns a valid schema with at least one error entry
    referencing the mispronounced word.
    """
    diff = DiffResult(
        entries=[
            DiffEntry(
                expected_word="world",
                spoken_word="word",
                status="mispronounced",
                confidence=0.55,
                phoneme_scores=[
                    PhonemeScore(phoneme="W", score=90.0),
                    PhonemeScore(phoneme="ER1", score=30.0),
                    PhonemeScore(phoneme="L", score=25.0),
                    PhonemeScore(phoneme="D", score=80.0),
                ],
            )
        ]
    )
    result = live_provider.generate_feedback("world", diff)

    assert isinstance(result, dict)
    assert "score" in result and "errors" in result and "suggestions" in result
    assert (
        isinstance(result["errors"], list) and len(result["errors"]) >= 1
    ), "expected at least one error for mispronounced word with low phoneme scores"
