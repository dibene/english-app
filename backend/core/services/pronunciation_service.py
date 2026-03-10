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
            dict with keys:
                score (int): Overall accuracy score 0-100 from the PA provider.
                words (list[dict]): Per-word detail for every entry in the diff,
                    including expected_phonemes and phoneme_scores so the frontend
                    can render expected vs. spoken phoneme comparisons.
                suggestions (list[str]): 1-3 LLM-generated improvement tips.
                    Empty list when enable_llm=False.

        Raises:
            PronunciationError: If the pronunciation provider fails.
            LLMFeedbackError: If the LLM provider fails (only when enable_llm=True).
        """
        result = self._pronunciation_provider.assess(audio_bytes, expected_text)
        diff_result = self._comparison_engine.compare(expected_text, result)

        words = [
            {
                "expected_word": e.expected_word,
                "spoken_word": e.spoken_word,
                "status": e.status,
                "confidence": e.confidence,
                "expected_phonemes": e.expected_phonemes,
                "phoneme_scores": (
                    [{"phoneme": ps.phoneme, "score": ps.score} for ps in e.phoneme_scores]
                    if e.phoneme_scores
                    else None
                ),
            }
            for e in diff_result.entries
        ]

        if not self._enable_llm:
            return {
                "score": int(result.accuracy_score),
                "words": words,
                "suggestions": [],
            }

        feedback = self._llm_provider.generate_feedback(expected_text, diff_result)
        return {
            "score": int(result.accuracy_score),
            "words": words,
            "suggestions": feedback.get("suggestions", []),
        }
