"""Domain models for pronunciation assessment results."""

from dataclasses import dataclass, field


@dataclass
class PhonemeScore:
    """Accuracy score for a single phoneme."""

    phoneme: str  # e.g. "w", "er", "l", "d"
    score: float  # 0.0 - 100.0 (Azure HundredMark scale)


@dataclass
class WordPronunciationResult:
    """Pronunciation assessment result for a single word."""

    word: str
    accuracy_score: float  # 0.0 - 100.0
    error_type: str  # "None" | "Mispronunciation" | "Omission" | "Insertion"
    phoneme_scores: list[PhonemeScore] = field(default_factory=list)


@dataclass
class PronunciationResult:
    """Full pronunciation assessment result for an utterance."""

    accuracy_score: float
    fluency_score: float
    completeness_score: float
    prosody_score: float | None
    words: list[WordPronunciationResult] = field(default_factory=list)
