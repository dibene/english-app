"""Abstract interface for speech-to-text providers."""

from abc import ABC, abstractmethod

from core.models.transcription import TranscriptionResult


class SpeechToTextProvider(ABC):
    """Abstract base class for speech-to-text providers.

    The Deepgram SDK and similar providers are synchronous.
    FastAPI endpoints that call this should be defined as `def` (not `async def`)
    so FastAPI runs them in a threadpool automatically.
    """

    @abstractmethod
    def transcribe(self, audio_bytes: bytes) -> TranscriptionResult:
        """Transcribe audio bytes to text with word-level confidence.

        Args:
            audio_bytes: Raw audio file content (WAV, WebM, MP3, etc.)

        Returns:
            TranscriptionResult with full transcript and word-level data.

        Raises:
            TranscriptionError: If the transcription request fails.
        """
        ...
