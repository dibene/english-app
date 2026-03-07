"""Unit tests for AzurePronunciationProvider — all Azure SDK calls are mocked."""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import azure.cognitiveservices.speech as speechsdk
import pytest

from core.exceptions import PronunciationError
from providers.azure_pronunciation import AzurePronunciationProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPECTED_TEXT = "hello world"


def _make_phoneme(phoneme: str, score: float) -> dict[str, Any]:
    return {"Phoneme": phoneme, "PronunciationAssessment": {"AccuracyScore": score}}


def _make_word(
    word: str, accuracy: float, error_type: str, phonemes: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "Word": word,
        "PronunciationAssessment": {"AccuracyScore": accuracy, "ErrorType": error_type},
        "Phonemes": phonemes,
    }


def _make_json_result(words: list[dict[str, Any]]) -> str:
    return json.dumps({"NBest": [{"Words": words}]})


def _make_sdk_result(
    reason: speechsdk.ResultReason = speechsdk.ResultReason.RecognizedSpeech,
    json_str: str = "",
) -> MagicMock:
    result = MagicMock(spec=speechsdk.SpeechRecognitionResult)
    result.reason = reason
    result.properties.get.return_value = json_str
    return result


def _make_pa_result(
    accuracy: float = 85.0,
    fluency: float = 90.0,
    completeness: float = 100.0,
    prosody: float | None = 78.0,
) -> MagicMock:
    pa = MagicMock(spec=speechsdk.PronunciationAssessmentResult)
    pa.accuracy_score = accuracy
    pa.fluency_score = fluency
    pa.completeness_score = completeness
    pa.prosody_score = prosody
    return pa


@pytest.fixture
def provider() -> AzurePronunciationProvider:
    return AzurePronunciationProvider(key="test-key", region="brazilsouth")


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


def test_missing_key_raises_value_error() -> None:
    with pytest.raises(ValueError, match="AZURE_SPEECH_KEY"):
        AzurePronunciationProvider(key="", region="brazilsouth")


def test_whitespace_key_raises_value_error() -> None:
    with pytest.raises(ValueError, match="AZURE_SPEECH_KEY"):
        AzurePronunciationProvider(key="   ", region="brazilsouth")


def test_missing_region_raises_value_error() -> None:
    with pytest.raises(ValueError, match="AZURE_SPEECH_REGION"):
        AzurePronunciationProvider(key="test-key", region="")


def test_whitespace_region_raises_value_error() -> None:
    with pytest.raises(ValueError, match="AZURE_SPEECH_REGION"):
        AzurePronunciationProvider(key="test-key", region="   ")


# ---------------------------------------------------------------------------
# Happy path tests
# ---------------------------------------------------------------------------


def _run_assess(
    provider: AzurePronunciationProvider,
    pa_result: MagicMock,
    sdk_result: MagicMock,
) -> Any:
    """Patch per-call Azure SDK entry points and call provider.assess()."""
    with (
        patch("providers.azure_pronunciation.speechsdk.PronunciationAssessmentConfig"),
        patch("providers.azure_pronunciation.speechsdk.audio.PushAudioInputStream"),
        patch("providers.azure_pronunciation.speechsdk.audio.AudioConfig"),
        patch("providers.azure_pronunciation.speechsdk.SpeechRecognizer") as mock_recognizer_cls,
        patch(
            "providers.azure_pronunciation.speechsdk.PronunciationAssessmentResult",
            return_value=pa_result,
        ),
    ):
        mock_recognizer = MagicMock()
        mock_recognizer.recognize_once.return_value = sdk_result
        mock_recognizer_cls.return_value = mock_recognizer
        return provider.assess(b"fake-audio", EXPECTED_TEXT)


def test_assess_returns_pronunciation_result(provider: AzurePronunciationProvider) -> None:
    words = [
        _make_word("hello", 95.0, "None", [_make_phoneme("hh", 98.0), _make_phoneme("ah", 92.0)]),
        _make_word("world", 72.0, "None", [_make_phoneme("w", 80.0), _make_phoneme("er", 60.0)]),
    ]
    sdk_result = _make_sdk_result(json_str=_make_json_result(words))
    pa_result = _make_pa_result(accuracy=85.0, fluency=90.0, completeness=100.0, prosody=78.0)

    result = _run_assess(provider, pa_result, sdk_result)

    assert result.accuracy_score == 85.0
    assert result.fluency_score == 90.0
    assert result.completeness_score == 100.0
    assert result.prosody_score == 78.0


def test_assess_returns_word_list(provider: AzurePronunciationProvider) -> None:
    words = [
        _make_word("hello", 95.0, "None", []),
        _make_word("world", 60.0, "Mispronunciation", []),
    ]
    sdk_result = _make_sdk_result(json_str=_make_json_result(words))
    result = _run_assess(provider, _make_pa_result(), sdk_result)

    assert len(result.words) == 2
    assert result.words[0].word == "hello"
    assert result.words[1].word == "world"


def test_assess_word_has_confidence(provider: AzurePronunciationProvider) -> None:
    words = [_make_word("hello", 95.0, "None", [])]
    sdk_result = _make_sdk_result(json_str=_make_json_result(words))
    result = _run_assess(provider, _make_pa_result(), sdk_result)

    assert result.words[0].confidence == pytest.approx(0.95)


def test_assess_word_has_error_type(provider: AzurePronunciationProvider) -> None:
    words = [_make_word("world", 55.0, "Mispronunciation", [])]
    sdk_result = _make_sdk_result(json_str=_make_json_result(words))
    result = _run_assess(provider, _make_pa_result(), sdk_result)

    assert result.words[0].error_type == "Mispronunciation"


def test_assess_word_has_phoneme_scores(provider: AzurePronunciationProvider) -> None:
    phonemes = [_make_phoneme("w", 80.0), _make_phoneme("er", 45.0), _make_phoneme("l", 90.0)]
    words = [_make_word("world", 70.0, "Mispronunciation", phonemes)]
    sdk_result = _make_sdk_result(json_str=_make_json_result(words))
    result = _run_assess(provider, _make_pa_result(), sdk_result)

    ph = result.words[0].phoneme_scores
    assert len(ph) == 3
    assert ph[0].phoneme == "w"
    assert ph[0].score == 80.0
    assert ph[1].phoneme == "er"
    assert ph[1].score == 45.0


def test_assess_prosody_score_can_be_none(provider: AzurePronunciationProvider) -> None:
    sdk_result = _make_sdk_result(json_str=_make_json_result([]))
    pa_result = _make_pa_result(prosody=None)
    result = _run_assess(provider, pa_result, sdk_result)

    assert result.prosody_score is None


# ---------------------------------------------------------------------------
# Error path tests
# ---------------------------------------------------------------------------


def test_assess_raises_on_no_match(provider: AzurePronunciationProvider) -> None:
    sdk_result = _make_sdk_result(reason=speechsdk.ResultReason.NoMatch)

    with pytest.raises(PronunciationError, match="NoMatch"):
        with (
            patch("providers.azure_pronunciation.speechsdk.PronunciationAssessmentConfig"),
            patch("providers.azure_pronunciation.speechsdk.audio.PushAudioInputStream"),
            patch("providers.azure_pronunciation.speechsdk.audio.AudioConfig"),
            patch(
                "providers.azure_pronunciation.speechsdk.SpeechRecognizer"
            ) as mock_recognizer_cls,
        ):
            mock_recognizer = MagicMock()
            mock_recognizer.recognize_once.return_value = sdk_result
            mock_recognizer_cls.return_value = mock_recognizer
            provider.assess(b"fake-audio", EXPECTED_TEXT)


def test_assess_raises_on_canceled(provider: AzurePronunciationProvider) -> None:
    sdk_result = _make_sdk_result(reason=speechsdk.ResultReason.Canceled)

    with pytest.raises(PronunciationError, match="canceled"):
        with (
            patch("providers.azure_pronunciation.speechsdk.PronunciationAssessmentConfig"),
            patch("providers.azure_pronunciation.speechsdk.audio.PushAudioInputStream"),
            patch("providers.azure_pronunciation.speechsdk.audio.AudioConfig"),
            patch(
                "providers.azure_pronunciation.speechsdk.SpeechRecognizer"
            ) as mock_recognizer_cls,
            patch(
                "providers.azure_pronunciation.speechsdk.CancellationDetails",
                return_value=MagicMock(reason="Error", error_details="auth failed"),
            ),
        ):
            mock_recognizer = MagicMock()
            mock_recognizer.recognize_once.return_value = sdk_result
            mock_recognizer_cls.return_value = mock_recognizer
            provider.assess(b"fake-audio", EXPECTED_TEXT)


def test_assess_raises_on_sdk_exception(provider: AzurePronunciationProvider) -> None:
    with pytest.raises(PronunciationError, match="Azure Speech SDK error"):
        with (
            patch("providers.azure_pronunciation.speechsdk.PronunciationAssessmentConfig"),
            patch("providers.azure_pronunciation.speechsdk.audio.PushAudioInputStream"),
            patch("providers.azure_pronunciation.speechsdk.audio.AudioConfig"),
            patch(
                "providers.azure_pronunciation.speechsdk.SpeechRecognizer"
            ) as mock_recognizer_cls,
        ):
            mock_recognizer = MagicMock()
            mock_recognizer.recognize_once.side_effect = RuntimeError("network timeout")
            mock_recognizer_cls.return_value = mock_recognizer
            provider.assess(b"fake-audio", EXPECTED_TEXT)
