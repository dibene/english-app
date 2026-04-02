"""OpenAI-compatible LLM provider implementation."""

import json
import logging
from collections import Counter
from typing import Any

from openai import OpenAI, OpenAIError

from core.exceptions import LLMFeedbackError
from core.interfaces.llm import LLMProvider
from core.models.diff import DiffResult

logger = logging.getLogger(__name__)

# Words per entry threshold above which we switch to the aggregated phoneme
# summary prompt instead of listing every word individually.
_AGGREGATE_ENTRIES_THRESHOLD = 40

_SYSTEM_PROMPT_TEMPLATE = """\
You are a professional English pronunciation coach specializing in American English.

Your students are Spanish speakers (native Spanish) with English levels between A2 and B2.
Your main goal is to help them improve pronunciation. Focus especially on the pronunciation
challenges that Spanish speakers commonly have when speaking American English.

You will receive a word-by-word or aggregated analysis of the student's pronunciation,
including per-phoneme scores when available (scale 0-100; lower means more difficulty).

Your task is to provide {min_s} to {max_s} short, actionable improvement tips focused on
pronunciation.

Guidelines:
- Focus only on pronunciation, not grammar or vocabulary.
- Prioritize the phonemes that are most difficult for Spanish speakers.
- Keep explanations simple and practical for A2-B2 learners.
- When relevant, explain the sound using simple phonetic hints (e.g. /\u026a/ vs /i\u02d0/, /b/ vs /v/).
- Give clear tips on how to move the mouth, tongue, or lips.
- Prioritize these common Spanish-speaker challenges:
    /\u026a/ vs /i\u02d0/ (ship vs sheep), /\u00e6/ (cat), /\u028c/ (cup),
    /b/ vs /v/, /\u0283/ (sh), /t\u0283/ (ch), /d\u0292/ (j),
    word stress, consonant endings.

Respond ONLY with a JSON object that matches this exact schema:
{{
  "suggestions": ["<tip 1>", "<tip 2>"]
}}

Rules:
- suggestions must be a list of {min_s} to {max_s} overall improvement tips.
- Do not include any text outside the JSON object.
"""


def _build_user_prompt(expected_text: str, diff_result: DiffResult) -> str:
    """Build the user prompt for a small/single-sentence analysis.

    Only includes entries that carry a coaching signal (errors or low-scoring
    phonemes). OK words with all phoneme scores \u2265 60 are omitted to keep the
    prompt compact.
    """
    lines = [
        f'Expected sentence: "{expected_text}"',
        "",
        "Word-level analysis (errors and weak phonemes only):",
    ]
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
    if len(lines) == 3:  # nothing was added
        lines.append("  (all words pronounced correctly)")
    return "\n".join(lines)


_PHONEME_WEAK_THRESHOLD = 70  # scores below this are considered weak


def _build_aggregate_prompt(expected_text: str, diff_result: DiffResult) -> str:
    """Build a compact aggregated prompt for large sessions (many sentences).

    Instead of listing every word, we summarise:
    - Phonemes that appeared with score < 70, ranked by frequency.
    - Error summary (missing/inserted/mispronounced word counts).
    This keeps the prompt to ~15-30 lines regardless of session length.
    """
    phoneme_counts: Counter[str] = Counter()
    phoneme_words: dict[str, list[str]] = {}
    mispronounced = 0
    missing = 0
    inserted = 0

    for entry in diff_result.entries:
        if entry.status == "missing":
            missing += 1
        elif entry.status == "inserted":
            inserted += 1
        elif entry.status == "mispronounced":
            mispronounced += 1

        for ps in entry.phoneme_scores or []:
            if ps.score < _PHONEME_WEAK_THRESHOLD:
                phoneme_counts[ps.phoneme] += 1
                word = entry.expected_word or entry.spoken_word or "?"
                phoneme_words.setdefault(ps.phoneme, []).append(word)

    lines = [f"Session: {expected_text}", ""]

    # Error summary
    error_parts = []
    if mispronounced:
        error_parts.append(f"{mispronounced} mispronounced")
    if missing:
        error_parts.append(f"{missing} missing")
    if inserted:
        error_parts.append(f"{inserted} inserted")
    if error_parts:
        lines.append("Error summary: " + ", ".join(error_parts))
    else:
        lines.append("Error summary: no pronunciation errors detected")

    # Weak phoneme summary (top 10 by frequency)
    lines.append("")
    if phoneme_counts:
        lines.append(f"Weak phonemes (score < {_PHONEME_WEAK_THRESHOLD}, by frequency):")
        for phoneme, count in phoneme_counts.most_common(10):
            example_words = ", ".join(list(dict.fromkeys(phoneme_words[phoneme]))[:5])
            lines.append(f"  /{phoneme}/: {count}\u00d7  (e.g. {example_words})")
    else:
        lines.append("Weak phonemes: none — phoneme scores were all strong.")

    return "\n".join(lines)


def _validate_schema(data: dict[str, Any]) -> None:
    """Raise LLMFeedbackError if the feedback dict does not match the expected schema."""
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

    def generate_feedback(
        self,
        expected_text: str,
        diff_result: DiffResult,
        n_suggestions_range: tuple[int, int] = (1, 3),
    ) -> dict[str, Any]:
        """Generate pronunciation improvement suggestions via OpenAI.

        Args:
            expected_text: The sentence(s) the user was supposed to pronounce.
            diff_result: Pre-filtered word-level comparison result.
            n_suggestions_range: (min, max) suggestions to request from the LLM.

        Returns:
            dict with key: suggestions (list[str]).

        Raises:
            LLMFeedbackError: If the API call fails, the response is not valid
                JSON, or the returned structure does not match the schema.
        """
        min_s, max_s = n_suggestions_range
        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(min_s=min_s, max_s=max_s)

        # Use aggregate prompt for large sessions to keep token count low
        if len(diff_result.entries) >= _AGGREGATE_ENTRIES_THRESHOLD:
            user_prompt = _build_aggregate_prompt(expected_text, diff_result)
        else:
            user_prompt = _build_user_prompt(expected_text, diff_result)

        n_words = len(diff_result.entries)
        logger.debug(
            "generate_feedback: model=%s expected_text=%r n_words=%d",
            self._model,
            expected_text,
            n_words,
        )

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
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
        logger.debug(
            "generate_feedback result: n_suggestions=%d",
            len(data.get("suggestions", [])),
        )
        return data
