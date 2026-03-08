"""OpenAI-compatible LLM provider implementation."""

import json
import logging
from typing import Any

from openai import OpenAI, OpenAIError

from core.exceptions import LLMFeedbackError
from core.interfaces.llm import LLMProvider
from core.models.diff import DiffResult

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a professional English pronunciation coach.
You will receive a sentence the student was supposed to say and a word-by-word
comparison of what they actually said.

Respond ONLY with a JSON object that matches this exact schema:
{
  "score": <integer 0-100>,
  "errors": [
    {
      "word": "<expected word>",
      "issue": "<mispronounced|missing|inserted>",
      "suggestion": "<short, actionable tip>"
    }
  ],
  "suggestions": ["<tip 1>", "<tip 2>"]
}

Rules:
- score must be an integer between 0 and 100.
- errors must be a list (empty list if none).
- suggestions must be a list of 1 to 3 overall improvement tips.
- Do not include any text outside the JSON object.
"""


def _build_user_prompt(expected_text: str, diff_result: DiffResult) -> str:
    lines = [f'Expected sentence: "{expected_text}"', "", "Word-level analysis:"]
    for entry in diff_result.entries:
        parts = [
            f"  expected={entry.expected_word!r}",
            f"spoken={entry.spoken_word!r}",
            f"status={entry.status}",
        ]
        if entry.confidence is not None:
            parts.append(f"confidence={entry.confidence:.2f}")
        if entry.phoneme_scores:
            phoneme_summary = ", ".join(
                f"{ps.phoneme}:{ps.score:.0f}" for ps in entry.phoneme_scores
            )
            parts.append(f"phonemes=[{phoneme_summary}]")
        lines.append(" ".join(parts))
    return "\n".join(lines)


def _validate_schema(data: dict[str, Any]) -> None:
    """Raise LLMFeedbackError if the feedback dict does not match the expected schema."""
    if "score" not in data:
        raise LLMFeedbackError("LLM response missing required field: 'score'")
    if not isinstance(data["score"], int):
        # Accept float that is a whole number (e.g. 85.0 → coerce)
        if isinstance(data["score"], float) and data["score"].is_integer():
            data["score"] = int(data["score"])
        else:
            raise LLMFeedbackError(
                f"LLM response 'score' must be an integer, got {type(data['score']).__name__}"
            )
    if not (0 <= data["score"] <= 100):
        raise LLMFeedbackError(f"LLM response 'score' out of range [0, 100]: {data['score']}")
    if "errors" not in data or not isinstance(data["errors"], list):
        raise LLMFeedbackError("LLM response missing or invalid field: 'errors' (must be a list)")
    if "suggestions" not in data or not isinstance(data["suggestions"], list):
        raise LLMFeedbackError(
            "LLM response missing or invalid field: 'suggestions' (must be a list)"
        )


class OpenAILLMProvider(LLMProvider):
    """LLM feedback provider backed by any OpenAI-compatible Chat Completions API.

    Works with OpenAI, Gemini (via OpenAI compatibility layer), Groq, and local
    Ollama — just set the appropriate model and base_url.

    Examples:
        # OpenAI
        OpenAILLMProvider(api_key=..., model="gpt-4o-mini")

        # Gemini (free tier)
        OpenAILLMProvider(
            api_key=GEMINI_API_KEY,
            model="gemini-2.0-flash",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )

        # Groq (free tier)
        OpenAILLMProvider(
            api_key=GROQ_API_KEY,
            model="llama-3.3-70b-versatile",
            base_url="https://api.groq.com/openai/v1",
        )

        # Ollama (local, no API key needed)
        OpenAILLMProvider(
            api_key="ollama",
            model="llama3.2:8b",
            base_url="http://localhost:11434/v1",
        )
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
    ) -> None:
        """Initialize the LLM provider.

        Args:
            api_key: API key. Must be non-empty (use "ollama" for local Ollama).
            model: Chat model identifier. Defaults to "gpt-4o-mini".
            base_url: Optional base URL override for non-OpenAI providers
                (Gemini, Groq, Ollama, etc.). If None, uses the OpenAI default.

        Raises:
            ValueError: If api_key is empty or whitespace.
        """
        if not api_key or not api_key.strip():
            raise ValueError("LLM API key must be set and non-empty")
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        logger.debug(
            "OpenAILLMProvider initialised: model=%s base_url=%s",
            model,
            base_url or "(openai default)",
        )

    def generate_feedback(self, expected_text: str, diff_result: DiffResult) -> dict[str, Any]:
        """Generate structured pronunciation feedback via OpenAI.

        Args:
            expected_text: The sentence the user was supposed to pronounce.
            diff_result: Word-level comparison result from TextComparisonEngine.

        Returns:
            dict with keys: score (int), errors (list[dict]), suggestions (list[str]).

        Raises:
            LLMFeedbackError: If the API call fails, the response is not valid
                JSON, or the returned structure does not match the schema.
        """
        user_prompt = _build_user_prompt(expected_text, diff_result)
        n_words = len(diff_result.entries)
        logger.debug("generate_feedback: model=%s expected_text=%r n_words=%d", self._model, expected_text, n_words)

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except OpenAIError as exc:
            logger.error("LLM API call failed: model=%s error=%s", self._model, exc)
            raise LLMFeedbackError(f"OpenAI API call failed: {exc}") from exc

        raw = response.choices[0].message.content or ""
        logger.debug("LLM raw response (first 200 chars): %s", raw[:200])

        try:
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error("LLM returned non-JSON response: %s", raw[:200])
            raise LLMFeedbackError(f"OpenAI returned non-JSON response: {raw[:200]}") from exc

        _validate_schema(data)
        logger.debug("generate_feedback result: score=%s n_errors=%d", data.get("score"), len(data.get("errors", [])))
        return data
