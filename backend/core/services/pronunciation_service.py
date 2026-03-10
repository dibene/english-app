"""Application service that orchestrates the pronunciation analysis pipeline."""

from typing import Any

from core.interfaces.llm import LLMProvider
from core.interfaces.pronunciation import PronunciationAssessmentProvider
from core.interfaces.stt import SpeechToTextProvider
from core.models.pronunciation import PronunciationResult
from core.models.transcription import TranscriptionResult
from core.services.text_comparison import TextComparisonEngine


def _transcription_to_pronunciation_result(t: TranscriptionResult) -> PronunciationResult:
    """Adapt a TranscriptionResult (Deepgram) to PronunciationResult for the pipeline.

    WordResult.phoneme_scores will be None — Deepgram does not provide phoneme data.
    """
    return PronunciationResult(
        accuracy_score=t.confidence * 100,
        fluency_score=t.confidence * 100,
        completeness_score=100.0,
        prosody_score=None,
        words=t.words,
    )


class PronunciationService:
    """Orchestrates pronunciation assessment, text comparison, and LLM feedback.

    Uses Azure PronunciationAssessmentProvider as the primary path. When
    pronunciation_provider is None, falls back to DeepgramSTTProvider and
    adapts its TranscriptionResult to a PronunciationResult.
    """

    def __init__(
        self,
        comparison_engine: TextComparisonEngine,
        llm_provider: LLMProvider,
        pronunciation_provider: PronunciationAssessmentProvider | None = None,
        stt_provider: SpeechToTextProvider | None = None,
    ) -> None:
        if pronunciation_provider is None and stt_provider is None:
            raise ValueError(
                "At least one of pronunciation_provider or stt_provider must be provided."
            )
        self._pronunciation_provider = pronunciation_provider
        self._stt_provider = stt_provider
        self._comparison_engine = comparison_engine
        self._llm_provider = llm_provider

    def analyze(self, audio_bytes: bytes, expected_text: str) -> dict[str, Any]:
        """Analyze pronunciation and return structured feedback.

        Args:
            audio_bytes: Raw WAV audio bytes.
            expected_text: The sentence the user was supposed to pronounce.

        Returns:
            dict with keys: score (int), errors (list), suggestions (list).

        Raises:
            PronunciationError: If the pronunciation/STT provider fails.
            LLMFeedbackError: If the LLM provider fails.
        """
        if self._pronunciation_provider is not None:
            result = self._pronunciation_provider.assess(audio_bytes, expected_text)
        else:
            transcription = self._stt_provider.transcribe(audio_bytes)  # type: ignore[union-attr]
            result = _transcription_to_pronunciation_result(transcription)

        diff_result = self._comparison_engine.compare(expected_text, result)
        return self._llm_provider.generate_feedback(expected_text, diff_result)
