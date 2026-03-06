"""Domain models for text comparison / diff results."""

from dataclasses import dataclass, field


@dataclass
class DiffEntry:
    """A single word-level comparison entry between expected and spoken text."""

    expected_word: str | None
    spoken_word: str | None
    status: str  # "ok" | "missing" | "inserted" | "mispronounced"
    confidence: float | None


@dataclass
class DiffResult:
    """Full diff result comparing expected text against a TranscriptionResult."""

    entries: list[DiffEntry] = field(default_factory=list)
