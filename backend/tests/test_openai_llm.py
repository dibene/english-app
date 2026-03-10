"""Unit tests for OpenAILLMProvider — all API calls are mocked."""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from core.exceptions import LLMFeedbackError
from core.models.diff import DiffEntry, DiffResult
from core.models.transcription import PhonemeScore
from providers.openai_llm import OpenAILLMProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_FEEDBACK = {
    "suggestions": ["Practice the 'w' sound", "Record yourself and listen back"],
}


def _make_mock_response(content: str) -> MagicMock:
    message = MagicMock()
    message.content = content

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    return response


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
                confidence=0.55,
            ),
        ]
    )


@pytest.fixture
def provider() -> OpenAILLMProvider:
    with patch("providers.openai_llm.OpenAI"):
        return OpenAILLMProvider(api_key="test-key")


# ---------------------------------------------------------------------------
# Init validation
# ---------------------------------------------------------------------------


def test_missing_api_key_raises_value_error() -> None:
    with pytest.raises(ValueError, match="API key"):
        OpenAILLMProvider(api_key="")


def test_whitespace_api_key_raises_value_error() -> None:
    with pytest.raises(ValueError, match="API key"):
        OpenAILLMProvider(api_key="   ")


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_generate_feedback_returns_valid_schema(provider: OpenAILLMProvider) -> None:
    provider._client.chat.completions.create.return_value = _make_mock_response(
        json.dumps(_VALID_FEEDBACK)
    )
    result = provider.generate_feedback("hello world", _make_diff_result())
    assert result == _VALID_FEEDBACK
    assert isinstance(result["suggestions"], list)


def test_generate_feedback_includes_diff_context(provider: OpenAILLMProvider) -> None:
    """The user prompt sent to OpenAI must contain the expected_text."""
    provider._client.chat.completions.create.return_value = _make_mock_response(
        json.dumps(_VALID_FEEDBACK)
    )
    provider.generate_feedback("hello world", _make_diff_result())

    call_kwargs = provider._client.chat.completions.create.call_args
    messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0]
    # Find the user message content
    user_content = next(m["content"] for m in messages if m["role"] == "user")
    assert "hello world" in user_content


def test_generate_feedback_phoneme_scores_included_in_prompt(
    provider: OpenAILLMProvider,
) -> None:
    """When phoneme_scores are present they must appear in the user prompt."""
    diff = DiffResult(
        entries=[
            DiffEntry(
                expected_word="world",
                spoken_word="word",
                status="mispronounced",
                confidence=0.55,
                phoneme_scores=[PhonemeScore(phoneme="W", score=45.0)],
            )
        ]
    )
    provider._client.chat.completions.create.return_value = _make_mock_response(
        json.dumps(_VALID_FEEDBACK)
    )
    provider.generate_feedback("world", diff)

    call_kwargs = provider._client.chat.completions.create.call_args
    messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0]
    user_content = next(m["content"] for m in messages if m["role"] == "user")
    assert "W:" in user_content


def test_generate_feedback_score_float_whole_number_is_coerced(
    provider: OpenAILLMProvider,
) -> None:
    """The LLM no longer returns score — coercion test is removed; kept as a no-op placeholder."""
    # Score coercion was removed when LLM contract changed to suggestions-only.
    pass


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_openai_api_error_raises_llm_feedback_error(provider: OpenAILLMProvider) -> None:
    from openai import OpenAIError

    provider._client.chat.completions.create.side_effect = OpenAIError("timeout")
    with pytest.raises(LLMFeedbackError, match="OpenAI API call failed"):
        provider.generate_feedback("hello world", _make_diff_result())


def test_invalid_json_response_raises_llm_feedback_error(provider: OpenAILLMProvider) -> None:
    provider._client.chat.completions.create.return_value = _make_mock_response("this is not json")
    with pytest.raises(LLMFeedbackError, match="non-JSON"):
        provider.generate_feedback("hello world", _make_diff_result())


def test_missing_suggestions_field_raises_llm_feedback_error(
    provider: OpenAILLMProvider,
) -> None:
    feedback: dict[str, Any] = {}
    provider._client.chat.completions.create.return_value = _make_mock_response(
        json.dumps(feedback)
    )
    with pytest.raises(LLMFeedbackError, match="'suggestions'"):
        provider.generate_feedback("hello world", _make_diff_result())
