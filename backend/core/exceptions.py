"""Domain exceptions for the Read & Improve application."""


class TranscriptionError(Exception):
    """Raised when audio transcription fails."""

    pass


class PronunciationError(Exception):
    """Raised when pronunciation assessment fails."""

    pass
