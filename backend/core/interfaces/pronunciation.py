"""Abstract interface for pronunciation assessment providers."""

from abc import ABC, abstractmethod

from core.models.pronunciation import PronunciationResult


class PronunciationAssessmentProvider(ABC):
    """Abstract base class for pronunciation assessment providers.

    Receives audio and the expected text the user was supposed to say,
    and returns per-word and per-phoneme pronunciation scores.

    This is distinct from SpeechToTextProvider: STT converts audio to text,
    while PronunciationAssessmentProvider scores how accurately the user
    pronounced the expected text.

    The Azure Speech SDK is synchronous. FastAPI endpoints that call this
    should be defined as `def` (not `async def`) so FastAPI runs them in
    a threadpool automatically.
    """

    @abstractmethod
    def assess(self, audio_bytes: bytes, expected_text: str) -> PronunciationResult:
        """Assess pronunciation of audio against the expected text.

        Args:
            audio_bytes: Raw WAV PCM audio (16kHz, 16-bit, mono).
            expected_text: The sentence the user was supposed to pronounce.

        Returns:
            PronunciationResult with overall scores and per-word/phoneme detail.

        Raises:
            PronunciationError: If the assessment request fails.
        """
        ...
