"""Azure Cognitive Services implementation of PronunciationAssessmentProvider."""

import json

import azure.cognitiveservices.speech as speechsdk

from core.exceptions import PronunciationError
from core.interfaces.pronunciation import PronunciationAssessmentProvider
from core.models.pronunciation import PhonemeScore, PronunciationResult, WordPronunciationResult


class AzurePronunciationProvider(PronunciationAssessmentProvider):
    """Pronunciation assessment provider backed by Azure Cognitive Services Speech SDK."""

    def __init__(self, key: str, region: str) -> None:
        """Initialize the Azure Pronunciation Assessment provider.

        Args:
            key: Azure Speech resource key (KEY 1 or KEY 2).
            region: Azure region, e.g. "brazilsouth", "eastus".

        Raises:
            ValueError: If key or region is empty or whitespace.
        """
        if not key or not key.strip():
            raise ValueError("AZURE_SPEECH_KEY must be set and non-empty")
        if not region or not region.strip():
            raise ValueError("AZURE_SPEECH_REGION must be set and non-empty")
        self._speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        self._audio_format = speechsdk.audio.AudioStreamFormat(
            samples_per_second=16000,
            bits_per_sample=16,
            channels=1,
        )

    def assess(self, audio_bytes: bytes, expected_text: str) -> PronunciationResult:
        """Assess pronunciation of audio against the expected text.

        Args:
            audio_bytes: Raw WAV PCM audio (16kHz, 16-bit, mono).
            expected_text: The sentence the user was supposed to pronounce.

        Returns:
            PronunciationResult with overall and per-word/phoneme scores.

        Raises:
            PronunciationError: If the Azure SDK call fails or returns no result.
        """
        pa_config = speechsdk.PronunciationAssessmentConfig(
            reference_text=expected_text,
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
            enable_miscue=True,
        )
        pa_config.enable_prosody_assessment()

        push_stream = speechsdk.audio.PushAudioInputStream(stream_format=self._audio_format)
        push_stream.write(audio_bytes)
        push_stream.close()

        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=self._speech_config, audio_config=audio_config
        )
        pa_config.apply_to(recognizer)

        try:
            result = recognizer.recognize_once()
        except Exception as exc:
            raise PronunciationError(f"Azure Speech SDK error: {exc}") from exc

        if result.reason == speechsdk.ResultReason.NoMatch:
            raise PronunciationError("Azure could not recognize speech in the audio (NoMatch)")

        if result.reason == speechsdk.ResultReason.Canceled:
            cancellation = speechsdk.CancellationDetails(result)
            raise PronunciationError(
                f"Azure recognition canceled: {cancellation.reason} — {cancellation.error_details}"
            )

        pa_result = speechsdk.PronunciationAssessmentResult(result)
        return self._map_result(pa_result, result)

    def _map_result(
        self,
        pa_result: speechsdk.PronunciationAssessmentResult,
        raw_result: speechsdk.SpeechRecognitionResult,
    ) -> PronunciationResult:
        """Map Azure SDK result objects to domain PronunciationResult."""
        words = self._parse_words(raw_result)
        return PronunciationResult(
            accuracy_score=pa_result.accuracy_score,
            fluency_score=pa_result.fluency_score,
            completeness_score=pa_result.completeness_score,
            prosody_score=pa_result.prosody_score,
            words=words,
        )

    def _parse_words(
        self, raw_result: speechsdk.SpeechRecognitionResult
    ) -> list[WordPronunciationResult]:
        """Parse per-word and per-phoneme detail from the raw JSON result."""
        try:
            detail = json.loads(
                raw_result.properties.get(
                    speechsdk.PropertyId.SpeechServiceResponse_JsonResult, "{}"
                )
            )
        except (json.JSONDecodeError, AttributeError):
            return []

        nbes = detail.get("NBest", [])
        if not nbes:
            return []

        words_data = nbes[0].get("Words", [])
        words: list[WordPronunciationResult] = []

        for w in words_data:
            pa = w.get("PronunciationAssessment", {})
            phonemes_data = w.get("Phonemes", [])

            phoneme_scores: list[PhonemeScore] = [
                PhonemeScore(
                    phoneme=p.get("Phoneme", ""),
                    score=p.get("PronunciationAssessment", {}).get("AccuracyScore", 0.0),
                )
                for p in phonemes_data
            ]

            words.append(
                WordPronunciationResult(
                    word=w.get("Word", ""),
                    accuracy_score=pa.get("AccuracyScore", 0.0),
                    error_type=pa.get("ErrorType", "None"),
                    phoneme_scores=phoneme_scores,
                )
            )

        return words
