"""Abstract interface for LLM-based feedback providers."""

from abc import ABC, abstractmethod
from typing import Any

from core.models.diff import DiffResult


class LLMProvider(ABC):
    """Abstract base class for LLM feedback providers.

    Receives the expected text and a word-level diff result, and produces
    structured pronunciation feedback (score, errors, suggestions).

    The concrete implementation is selected via the LLM_PROVIDER env var.
    Current implementation (OpenAILLMProvider) supports any OpenAI-compatible
    API: Gemini, Groq, Ollama (local), or OpenAI — no OpenAI account required.
    Domain logic must never reference a concrete provider directly.
    """

    @abstractmethod
    def generate_feedback(
        self,
        expected_text: str,
        diff_result: DiffResult,
        n_suggestions_range: tuple[int, int] = (1, 3),
    ) -> dict[str, Any]:
        """Generate pronunciation improvement suggestions via LLM.

        The LLM is responsible only for suggestions. Score and per-word phoneme
        data are derived directly from the pronunciation assessment provider and
        assembled by PronunciationService.

        Args:
            expected_text: The sentence(s) the user was supposed to pronounce.
            diff_result: Word-level comparison result from TextComparisonEngine.
                For session feedback this is a pre-filtered, aggregated DiffResult.
            n_suggestions_range: (min, max) number of suggestions to request.
                Scaled by the caller based on session size.

        Returns:
            dict with key:
                suggestions (list[str]): actionable improvement tips.

        Raises:
            LLMFeedbackError: If the API call fails, the response is not valid
                JSON, or the returned structure does not match the schema.
        """
        ...
