"""Application service that orchestrates the pronunciation analysis pipeline."""

# NOTE: STT-only path (DeepgramSTTProvider without phoneme analysis)
# If needed in the future, adapt TranscriptionResult → PronunciationResult in an
# intermediate service or adapter before passing the result into PronunciationService.
# See removed _transcription_to_pronunciation_result for reference.

from typing import Any

from core.exceptions import LLMFeedbackError
from core.interfaces.llm import LLMProvider
from core.interfaces.pronunciation import PronunciationAssessmentProvider
from core.models.diff import DiffEntry, DiffResult
from core.models.transcription import PhonemeScore as PhonemeScoreModel
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

    def analyze(
        self, audio_bytes: bytes, expected_text: str, enable_llm_override: bool | None = None
    ) -> dict[str, Any]:
        """Analyze pronunciation and return structured feedback.

        Args:
            audio_bytes: Raw WAV audio bytes.
            expected_text: The sentence the user was supposed to pronounce.
            enable_llm_override: When provided, overrides the server-level enable_llm
                setting for this single request. Useful for the frontend to request
                fast (no-LLM) analysis most of the time and only trigger LLM via
                POST /feedback after accumulating results.

        Returns:
            dict with keys:
                score (int): Overall accuracy score 0-100 from the PA provider.
                words (list[dict]): Per-word detail for every entry in the diff,
                    including expected_phonemes and phoneme_scores so the frontend
                    can render expected vs. spoken phoneme comparisons.
                suggestions (list[str]): 1-3 LLM-generated improvement tips.
                    Empty list when LLM is disabled.

        Raises:
            PronunciationError: If the pronunciation provider fails.
            LLMFeedbackError: If the LLM provider fails (only when LLM is enabled).
        """
        use_llm = enable_llm_override if enable_llm_override is not None else self._enable_llm

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
                    if e.phoneme_scores is not None
                    else None
                ),
            }
            for e in diff_result.entries
        ]

        if not use_llm:
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

    def generate_feedback_for_session(self, sentences: list[Any]) -> list[str]:
        """Generate LLM suggestions from a list of pre-computed sentence results.

        The frontend accumulates per-sentence AnalyzeResponse results (fast, no-LLM
        calls) and then calls this once to get coaching tips across the whole session.
        All sentence context is sent to the LLM in a single request.

        Args:
            sentences: List of FeedbackSentenceIn-compatible objects with fields:
                expected_text (str), score (int), words (list with status/phoneme_scores).

        Returns:
            list[str]: 1-5 coaching suggestions covering the full session.

        Raises:
            RuntimeError: If LLM is disabled server-side.
            LLMFeedbackError: If the LLM call fails.
        """
        if not self._enable_llm:
            raise RuntimeError(
                "LLM is disabled on this server (ENABLE_LLM=false). "
                "Cannot generate session feedback."
            )

        # Reconstruct a DiffResult-like structure from the raw sentence data
        # so we can reuse the existing LLM provider interface.
        all_entries: list[DiffEntry] = []
        expected_texts: list[str] = []

        for sentence in sentences:
            expected_texts.append(sentence.expected_text)
            for w in sentence.words:
                ph_scores = None
                if w.phoneme_scores is not None:
                    ph_scores = [
                        PhonemeScoreModel(phoneme=ps.phoneme, score=ps.score)
                        for ps in w.phoneme_scores
                    ]
                all_entries.append(
                    DiffEntry(
                        expected_word=w.expected_word,
                        spoken_word=w.spoken_word,
                        status=w.status,
                        confidence=w.confidence,
                        expected_phonemes=w.expected_phonemes,
                        phoneme_scores=ph_scores,
                    )
                )

        combined_text = " / ".join(expected_texts)
        combined_diff = DiffResult(entries=all_entries)
        feedback = self._llm_provider.generate_feedback(combined_text, combined_diff)
        suggestions: list[str] = feedback.get("suggestions", [])
        return suggestions
