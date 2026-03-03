"""Domain models for speech transcription results."""

from dataclasses import dataclass, field


@dataclass
class WordResult:
    """A single transcribed word with timing and confidence data."""

    word: str
    confidence: float  # 0.0 - 1.0
    start_time: float | None
    end_time: float | None


@dataclass
class TranscriptionResult:
    """Full transcription result from a speech-to-text provider."""

    transcript: str
    words: list[WordResult] = field(default_factory=list)
