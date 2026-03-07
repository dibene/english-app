"""Domain models for text comparison / diff results."""

from dataclasses import dataclass, field

from core.models.transcription import PhonemeScore


@dataclass
class DiffEntry:
    """A single word-level comparison entry between expected and spoken text."""

    expected_word: str | None
    spoken_word: str | None
    status: str  # "ok" | "missing" | "inserted" | "mispronounced"
    confidence: float | None
    expected_phonemes: list[str] | None = None  # e.g. ["W", "ER1", "L", "D"] from cmudict
    phoneme_scores: list[PhonemeScore] | None = None  # actual scores from PA provider


@dataclass
class DiffResult:
    """Full diff result comparing expected text against a TranscriptionResult."""

    entries: list[DiffEntry] = field(default_factory=list)
