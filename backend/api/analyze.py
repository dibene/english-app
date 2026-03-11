"""POST /analyze endpoint — pronunciation analysis."""

import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from pydantic import BaseModel

from api.dependencies import get_pronunciation_service
from core.exceptions import LLMFeedbackError, PronunciationError
from core.services.pronunciation_service import PronunciationService

router = APIRouter()

_MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB
_MAX_TEXT_CHARS = 500
_ANALYZE_TIMEOUT_SECONDS = 30.0
_ALLOWED_CONTENT_TYPES = {
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/webm",
}


class PhonemeScoreOut(BaseModel):
    phoneme: str
    score: float


class WordOut(BaseModel):
    expected_word: str | None
    spoken_word: str | None
    status: str
    confidence: float | None
    expected_phonemes: list[str] | None
    phoneme_scores: list[PhonemeScoreOut] | None


class AnalyzeResponse(BaseModel):
    score: int
    words: list[WordOut]
    suggestions: list[str]


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    audio_file: UploadFile,
    expected_text: Annotated[str, Form()] = "",
    service: PronunciationService = Depends(get_pronunciation_service),
) -> AnalyzeResponse:
    """Analyze pronunciation of uploaded audio against the expected sentence.

    Args:
        audio_file: WAV or WebM audio file (max 10 MB).
        expected_text: The sentence the user was supposed to pronounce (max 500 chars).
        service: Injected PronunciationService.

    Returns:
        AnalyzeResponse with overall score, per-word detail, and suggestions.

    Raises:
        HTTPException 400: Validation error (bad input).
        HTTPException 422: Pipeline failure (provider or LLM error).
        HTTPException 504: Request timed out after 10 seconds.
    """
    # --- input validation ---
    if not expected_text or not expected_text.strip():
        raise HTTPException(status_code=400, detail="expected_text must not be empty")
    if len(expected_text) > _MAX_TEXT_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"expected_text must not exceed {_MAX_TEXT_CHARS} characters",
        )

    content_type = (audio_file.content_type or "").lower().split(";")[0].strip()
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported audio content type '{content_type}'. "
                f"Allowed: {sorted(_ALLOWED_CONTENT_TYPES)}"
            ),
        )

    audio_bytes = await audio_file.read()
    if len(audio_bytes) > _MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Audio file must not exceed {_MAX_AUDIO_BYTES // (1024 * 1024)} MB",
        )
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Audio file must not be empty")

    # --- pipeline call with timeout ---
    try:
        result: dict[str, Any] = await asyncio.wait_for(
            asyncio.to_thread(service.analyze, audio_bytes, expected_text),
            timeout=_ANALYZE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Pronunciation analysis timed out. Please try again.",
        )
    except (PronunciationError, LLMFeedbackError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return AnalyzeResponse(
        score=result["score"],
        words=[WordOut(**w) for w in result["words"]],
        suggestions=result["suggestions"],
    )
