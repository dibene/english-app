"""Domain models for pronunciation assessment results."""

from dataclasses import dataclass, field

from core.models.transcription import WordResult


@dataclass
class PronunciationResult:
    """Full pronunciation assessment result for an utterance."""

    accuracy_score: float
    fluency_score: float
    completeness_score: float
    prosody_score: float | None
    words: list[WordResult] = field(default_factory=list)
