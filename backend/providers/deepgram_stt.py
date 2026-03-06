"""Deepgram implementation of the SpeechToTextProvider interface."""

from deepgram import DeepgramClient, ListenV1Response

from core.exceptions import TranscriptionError
from core.interfaces.stt import SpeechToTextProvider
from core.models.transcription import TranscriptionResult, WordResult


class DeepgramSTTProvider(SpeechToTextProvider):
    """Speech-to-text provider backed by the Deepgram pre-recorded audio API."""

    def __init__(self, api_key: str) -> None:
        """Initialize the Deepgram STT provider.

        Args:
            api_key: Deepgram API key. Must be non-empty.

        Raises:
            ValueError: If api_key is empty or whitespace.
        """
        if not api_key or not api_key.strip():
            raise ValueError("DEEPGRAM_API_KEY must be set and non-empty")
        self._client = DeepgramClient(api_key=api_key)

    def transcribe(self, audio_bytes: bytes) -> TranscriptionResult:
        """Transcribe audio bytes using the Deepgram pre-recorded API.

        Args:
            audio_bytes: Raw audio file content (WAV, WebM, MP3, etc.)

        Returns:
            TranscriptionResult with full transcript and word-level confidence.

        Raises:
            TranscriptionError: If the Deepgram API call fails for any reason.
        """
        try:
            response: ListenV1Response = self._client.listen.v1.media.transcribe_file(
                request=audio_bytes,
                model="nova-3",
                smart_format=True,
            )
        except Exception as exc:
            raise TranscriptionError(f"Deepgram transcription failed: {exc}") from exc

        return self._map_response(response)

    def _map_response(self, response: ListenV1Response) -> TranscriptionResult:
        """Map a Deepgram API response to our domain TranscriptionResult."""
        try:
            alternative = response.results.channels[0].alternatives[0]
        except (AttributeError, IndexError, TypeError):
            return TranscriptionResult(transcript="", words=[])

        transcript = alternative.transcript or ""
        confidence: float = float(alternative.confidence or 0.0)

        words: list[WordResult] = []
        if alternative.words:
            for w in alternative.words:
                words.append(
                    WordResult(
                        word=w.word,
                        confidence=w.confidence,
                        start_time=w.start,
                        end_time=w.end,
                    )
                )

        return TranscriptionResult(transcript=transcript, confidence=confidence, words=words)
