"""Integration tests for POST /analyze endpoint."""

import asyncio
import io
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_pronunciation_service
from api.main import app
from core.exceptions import LLMFeedbackError, PronunciationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_WAV = (
    # 44-byte WAV header for a silent 1-sample PCM 16kHz mono file
    b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
    b"\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00"
    b"\x02\x00\x10\x00data\x02\x00\x00\x00\x00\x00"
)

_MOCK_ANALYZE_RESULT: dict[str, Any] = {
    "score": 85,
    "words": [
        {
            "expected_word": "hello",
            "spoken_word": "hello",
            "status": "ok",
            "confidence": 0.99,
            "expected_phonemes": ["HH", "AH0", "L", "OW1"],
            "phoneme_scores": None,
        },
        {
            "expected_word": "world",
            "spoken_word": "world",
            "status": "mispronounced",
            "confidence": 0.55,
            "expected_phonemes": ["W", "ER1", "L", "D"],
            "phoneme_scores": [
                {"phoneme": "W", "score": 0.95},
                {"phoneme": "ER1", "score": 0.42},
                {"phoneme": "L", "score": 0.88},
                {"phoneme": "D", "score": 0.71},
            ],
        },
    ],
    "suggestions": ["Focus on the 'ER' vowel sound in 'world'"],
}


def _make_client(analyze_side_effect: Any = None, analyze_return: Any = None) -> TestClient:
    """Build a TestClient with a mocked PronunciationService."""
    mock_service = MagicMock()
    if analyze_side_effect is not None:
        mock_service.analyze.side_effect = analyze_side_effect
    else:
        mock_service.analyze.return_value = analyze_return or _MOCK_ANALYZE_RESULT

    app.dependency_overrides[get_pronunciation_service] = lambda: mock_service
    client = TestClient(app, raise_server_exceptions=False)
    return client


def _reset_overrides() -> None:
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAnalyzeHappyPath:
    def test_analyze_happy_path(self) -> None:
        """200 with valid WAV + text; response has score, words, suggestions."""
        client = _make_client()
        try:
            response = client.post(
                "/analyze",
                data={"expected_text": "hello world"},
                files={"audio_file": ("test.wav", io.BytesIO(_MINIMAL_WAV), "audio/wav")},
            )
            assert response.status_code == 200
            body = response.json()
            assert "score" in body
            assert "words" in body
            assert "suggestions" in body
            assert isinstance(body["score"], int)
            assert isinstance(body["words"], list)
            assert isinstance(body["suggestions"], list)
        finally:
            _reset_overrides()

    def test_analyze_response_schema(self) -> None:
        """Response words contain expected schema fields."""
        client = _make_client()
        try:
            response = client.post(
                "/analyze",
                data={"expected_text": "hello world"},
                files={"audio_file": ("test.wav", io.BytesIO(_MINIMAL_WAV), "audio/wav")},
            )
            assert response.status_code == 200
            body = response.json()
            word = body["words"][0]
            assert "expected_word" in word
            assert "spoken_word" in word
            assert "status" in word
            assert "confidence" in word
            assert "expected_phonemes" in word
            assert "phoneme_scores" in word
        finally:
            _reset_overrides()


class TestValidationErrors:
    def test_analyze_missing_text(self) -> None:
        """400 when expected_text is empty."""
        client = _make_client()
        try:
            response = client.post(
                "/analyze",
                data={"expected_text": ""},
                files={"audio_file": ("test.wav", io.BytesIO(_MINIMAL_WAV), "audio/wav")},
            )
            assert response.status_code == 400
        finally:
            _reset_overrides()

    def test_analyze_whitespace_only_text(self) -> None:
        """400 when expected_text is whitespace only."""
        client = _make_client()
        try:
            response = client.post(
                "/analyze",
                data={"expected_text": "   "},
                files={"audio_file": ("test.wav", io.BytesIO(_MINIMAL_WAV), "audio/wav")},
            )
            assert response.status_code == 400
        finally:
            _reset_overrides()

    def test_analyze_text_too_long(self) -> None:
        """400 when expected_text exceeds 500 characters."""
        client = _make_client()
        try:
            response = client.post(
                "/analyze",
                data={"expected_text": "a" * 501},
                files={"audio_file": ("test.wav", io.BytesIO(_MINIMAL_WAV), "audio/wav")},
            )
            assert response.status_code == 400
        finally:
            _reset_overrides()

    def test_analyze_wrong_content_type(self) -> None:
        """400 for unsupported content type like image/png."""
        client = _make_client()
        try:
            response = client.post(
                "/analyze",
                data={"expected_text": "hello world"},
                files={"audio_file": ("test.png", io.BytesIO(b"\x89PNG"), "image/png")},
            )
            assert response.status_code == 400
        finally:
            _reset_overrides()

    def test_analyze_audio_too_large(self) -> None:
        """400 when audio file exceeds 10 MB."""
        client = _make_client()
        try:
            big_audio = b"\x00" * (10 * 1024 * 1024 + 1)
            response = client.post(
                "/analyze",
                data={"expected_text": "hello world"},
                files={"audio_file": ("big.wav", io.BytesIO(big_audio), "audio/wav")},
            )
            assert response.status_code == 400
        finally:
            _reset_overrides()


class TestPipelineFailures:
    def test_analyze_pipeline_failure(self) -> None:
        """422 when service raises PronunciationError."""
        client = _make_client(analyze_side_effect=PronunciationError("Azure failed"))
        try:
            response = client.post(
                "/analyze",
                data={"expected_text": "hello world"},
                files={"audio_file": ("test.wav", io.BytesIO(_MINIMAL_WAV), "audio/wav")},
            )
            assert response.status_code == 422
        finally:
            _reset_overrides()

    def test_analyze_llm_failure(self) -> None:
        """422 when service raises LLMFeedbackError."""
        client = _make_client(analyze_side_effect=LLMFeedbackError("LLM failed"))
        try:
            response = client.post(
                "/analyze",
                data={"expected_text": "hello world"},
                files={"audio_file": ("test.wav", io.BytesIO(_MINIMAL_WAV), "audio/wav")},
            )
            assert response.status_code == 422
        finally:
            _reset_overrides()

    def test_analyze_timeout(self) -> None:
        """504 when service exceeds timeout."""

        def _slow(*_args: Any, **_kwargs: Any) -> None:
            raise asyncio.TimeoutError()

        client = _make_client(analyze_side_effect=_slow)
        try:
            # Patch wait_for so it raises TimeoutError immediately (avoid real sleeping)
            with patch("api.analyze.asyncio.wait_for", side_effect=asyncio.TimeoutError()):
                response = client.post(
                    "/analyze",
                    data={"expected_text": "hello world"},
                    files={"audio_file": ("test.wav", io.BytesIO(_MINIMAL_WAV), "audio/wav")},
                )
            assert response.status_code == 504
        finally:
            _reset_overrides()
