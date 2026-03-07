"""Domain models for speech transcription results."""

from dataclasses import dataclass, field


@dataclass
class PhonemeScore:
    """Accuracy score for a single phoneme."""

    phoneme: str  # e.g. "W", "ER1", "L", "D"
    score: float  # 0.0 - 100.0 (Azure HundredMark scale)


@dataclass
class WordResult:
    """A single transcribed word with optional pronunciation detail.

    Basic STT providers (e.g. Deepgram) populate only word/confidence/timing.
    Pronunciation assessment providers (e.g. Azure) also populate error_type
    and phoneme_scores in the same object.
    """

    word: str
    confidence: float | None  # 0.0 - 1.0; None if provider does not supply it
    start_time: float | None
    end_time: float | None
    error_type: str | None = None  # "None" | "Mispronunciation" | "Omission" | "Insertion"
    phoneme_scores: list[PhonemeScore] | None = None  # populated by PA providers


@dataclass
class TranscriptionResult:
    """Full transcription result from a speech-to-text provider."""

    transcript: str
    confidence: float = 0.0  # overall transcript confidence, 0.0 - 1.0
    words: list[WordResult] = field(default_factory=list)
