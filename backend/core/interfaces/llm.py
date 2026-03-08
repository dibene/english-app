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
    def generate_feedback(self, expected_text: str, diff_result: DiffResult) -> dict[str, Any]:
        """Generate structured pronunciation feedback.

        Args:
            expected_text: The sentence the user was supposed to pronounce.
            diff_result: Word-level comparison result from TextComparisonEngine.

        Returns:
            dict with keys:
                score (int): Overall pronunciation score 0-100.
                errors (list[dict]): Per-word issues, each with "word", "issue",
                    and "suggestion" keys.
                suggestions (list[str]): 1-3 overall improvement tips.

        Raises:
            LLMFeedbackError: If the API call fails, the response is not valid
                JSON, or the returned structure does not match the schema.
        """
        ...
