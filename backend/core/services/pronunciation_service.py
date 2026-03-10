"""Application service that orchestrates the pronunciation analysis pipeline."""

# NOTE: STT-only path (DeepgramSTTProvider without phoneme analysis)
# If needed in the future, adapt TranscriptionResult → PronunciationResult in an
# intermediate service or adapter before passing the result into PronunciationService.
# See removed _transcription_to_pronunciation_result for reference.

from typing import Any

from core.interfaces.llm import LLMProvider
from core.interfaces.pronunciation import PronunciationAssessmentProvider
from core.services.text_comparison import TextComparisonEngine

# LLM skip thresholds (future use):
# Skip LLM feedback when accuracy_score >= this value AND no phoneme has a low score.
_LLM_SKIP_ACCURACY_THRESHOLD = 80


class PronunciationService:
    """Orchestrates pronunciation assessment, text comparison, and LLM feedback.

    Args:
        comparison_engine: Text comparison engine.
        llm_provider: LLM provider for generating feedback.
        pronunciation_provider: Pronunciation assessment provider (required).
        enable_llm: When False the LLM call is skipped and suggestions are empty.
            Useful to stay within daily LLM request limits.
            Future: auto-skip when accuracy_score >= 80 and no low-scoring phonemes.
    """

    def __init__(
        self,
        comparison_engine: TextComparisonEngine,
        llm_provider: LLMProvider,
        pronunciation_provider: PronunciationAssessmentProvider,
        enable_llm: bool = True,
    ) -> None:
        self._pronunciation_provider = pronunciation_provider
        self._comparison_engine = comparison_engine
        self._llm_provider = llm_provider
        self._enable_llm = enable_llm

    def analyze(self, audio_bytes: bytes, expected_text: str) -> dict[str, Any]:
        """Analyze pronunciation and return structured feedback.

        Args:
            audio_bytes: Raw WAV audio bytes.
            expected_text: The sentence the user was supposed to pronounce.

        Returns:
            dict with keys: score (int), errors (list), suggestions (list).
            When enable_llm=False, suggestions is always an empty list.

        Raises:
            PronunciationError: If the pronunciation provider fails.
            LLMFeedbackError: If the LLM provider fails (only when enable_llm=True).
        """
        result = self._pronunciation_provider.assess(audio_bytes, expected_text)
        diff_result = self._comparison_engine.compare(expected_text, result)

        if not self._enable_llm:
            return {
                "score": int(result.accuracy_score),
                "errors": [
                    {"word": e.spoken_word or e.expected_word, "status": e.status}
                    for e in diff_result.entries
                    if e.status != "ok"
                ],
                "suggestions": [],
            }

        return self._llm_provider.generate_feedback(expected_text, diff_result)
