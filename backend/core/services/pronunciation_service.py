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

# Phoneme score below which an otherwise-ok word is still sent to the LLM.
_PHONEME_WEAK_THRESHOLD = 60

# Suggestion count ranges keyed by number of sentences in the session.
_SUGGESTION_RANGES: list[tuple[int, tuple[int, int]]] = [
    (16, (4, 7)),  # 16+ sentences → 4-7 suggestions
    (6, (3, 5)),  # 6–15 sentences → 3-5 suggestions
    (2, (2, 4)),  # 2–5 sentences  → 2-4 suggestions
    (0, (1, 3)),  # 1 sentence     → 1-3 suggestions
]


def _suggestion_range(n_sentences: int) -> tuple[int, int]:
    """Return (min, max) suggestion count for a session of n_sentences."""
    for threshold, range_ in _SUGGESTION_RANGES:
        if n_sentences >= threshold:
            return range_
    return (1, 3)


def _filter_entries_for_llm(entries: list[DiffEntry]) -> list[DiffEntry]:
    """Keep only entries that carry a useful coaching signal.

    Included:
    - Any word with status != 'ok'  (missing, inserted, mispronounced)
    - 'ok' words where at least one phoneme score is below the weak threshold

    Excluded:
    - 'ok' words where all phoneme scores are >= threshold, or no phoneme data

    This typically reduces a 25-sentence session from ~400 tokens of word data
    to ~50-100 tokens, focusing the LLM entirely on problem areas.
    """
    filtered: list[DiffEntry] = []
    for entry in entries:
        if entry.status != "ok":
            filtered.append(entry)
            continue
        if entry.phoneme_scores and any(
            ps.score < _PHONEME_WEAK_THRESHOLD for ps in entry.phoneme_scores
        ):
            filtered.append(entry)
    return filtered


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

        filtered_diff = DiffResult(entries=_filter_entries_for_llm(diff_result.entries))
        feedback = self._llm_provider.generate_feedback(
            expected_text, filtered_diff, n_suggestions_range=(1, 3)
        )
        return {
            "score": int(result.accuracy_score),
            "words": words,
            "suggestions": feedback.get("suggestions", []),
        }

    def generate_feedback_for_session(
        self, sentences: list[Any], max_suggestions: int | None = None
    ) -> list[str]:
        """Generate LLM suggestions from a list of pre-computed sentence results.

        The prompt is automatically optimised:
        - Only error words and words with weak phonemes (< 60) are sent to the LLM.
        - For large sessions (>= 40 filtered entries) an aggregated phoneme-frequency
          summary replaces the word-by-word listing to stay under token limits.
        - The suggestion count range scales with session size unless overridden.

        Args:
            sentences: List of FeedbackSentenceIn-compatible objects.
            max_suggestions: When set, caps the upper bound of the suggestion count.

        Returns:
            list[str]: coaching suggestions covering the full session.

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
        filtered_entries = _filter_entries_for_llm(all_entries)
        combined_diff = DiffResult(entries=filtered_entries)
        min_s, max_s = _suggestion_range(len(sentences))
        if max_suggestions is not None:
            max_s = max(min_s, max_suggestions)
        feedback = self._llm_provider.generate_feedback(
            combined_text, combined_diff, n_suggestions_range=(min_s, max_s)
        )
        suggestions: list[str] = feedback.get("suggestions", [])
        return suggestions
