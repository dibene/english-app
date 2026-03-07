# Plan: Pronunciation Assessment Provider (F-011)

## Goal
Define the `PronunciationAssessmentProvider` abstract interface and implement it with
Azure Cognitive Services Speech SDK to return per-word and per-phoneme pronunciation scores.

## Scope
**In scope:**
- `PronunciationError` domain exception in `core/exceptions.py`
- `PhonemeScore`, `WordPronunciationResult`, `PronunciationResult` models in `core/models/pronunciation.py`
- Abstract `PronunciationAssessmentProvider` interface in `core/interfaces/pronunciation.py`
- `AzurePronunciationProvider` in `providers/azure_pronunciation.py`
- Unit tests (mocked Azure SDK) in `tests/test_azure_pronunciation.py`
- Live test (real API) in `tests/test_azure_pronunciation_live.py`

**Out of scope (this PR):**
- Merging PA results into DiffResult (F-012)
- HTTP endpoint exposure
- Speechace provider

## Files to Create or Modify
- `backend/core/exceptions.py` - add `PronunciationError`
- `backend/core/models/pronunciation.py` - create
- `backend/core/interfaces/pronunciation.py` - create
- `backend/providers/azure_pronunciation.py` - create
- `backend/tests/test_azure_pronunciation.py` - create (unit, mocked)
- `backend/tests/test_azure_pronunciation_live.py` - create (live, marked `@pytest.mark.live`)
- `backend/pyproject.toml` - add `azure-cognitiveservices-speech` dependency

## Interfaces and Data Models

```python
@dataclass
class PhonemeScore:
    phoneme: str      # e.g. "w", "er", "l", "d"
    score: float      # 0.0 - 100.0 (Azure native scale)

@dataclass
class WordPronunciationResult:
    word: str
    accuracy_score: float        # 0.0 - 100.0
    error_type: str              # "None" | "Mispronunciation" | "Omission" | "Insertion"
    phoneme_scores: list[PhonemeScore]

@dataclass
class PronunciationResult:
    accuracy_score: float
    fluency_score: float
    completeness_score: float
    prosody_score: float | None  # Only available with PronunciationAssessmentGranularity.FullText
    words: list[WordPronunciationResult]
```

```python
class PronunciationAssessmentProvider(ABC):
    @abstractmethod
    def assess(self, audio_bytes: bytes, expected_text: str) -> PronunciationResult: ...
```

## Implementation Notes — Azure SDK

The Azure Speech SDK works differently from REST APIs: it uses an audio stream and
a callback-based recognizer. Key steps:

1. Create `speechsdk.SpeechConfig(subscription=key, region=region)`
2. Create `speechsdk.PronunciationAssessmentConfig(reference_text=expected_text, ...)`
   with `GradingSystem.HundredMark`, `Granularity.Phoneme`, `enable_prosody_assessment=True`
3. Push audio via `speechsdk.audio.PushAudioInputStream` → `AudioConfig`
4. Create `SpeechRecognizer` + call `.recognize_once_sync()`
5. Parse `PronunciationAssessmentResult.from_result(result)` to extract scores
6. Map to domain models — no Azure types in return value

**Audio requirement:** Azure SDK expects WAV PCM 16kHz 16-bit mono by default.
The provider will accept raw bytes and push them into a `PushAudioInputStream`
with `AudioStreamFormat.get_wave_format_pcm(16000, 16, 1)`.

## Implementation Steps
1. Add `PronunciationError` to `core/exceptions.py`
2. Create `core/models/pronunciation.py` with the three dataclasses
3. Create `core/interfaces/pronunciation.py` with abstract `PronunciationAssessmentProvider`
4. Add `azure-cognitiveservices-speech` to `pyproject.toml` via `uv add`
5. Implement `AzurePronunciationProvider` in `providers/azure_pronunciation.py`
6. Write unit tests with fully mocked Azure SDK objects
7. Write live test using existing WAV fixture

## Test Cases (unit)
- `test_missing_key_raises_value_error`
- `test_missing_region_raises_value_error`
- `test_assess_returns_pronunciation_result`
- `test_assess_returns_correct_accuracy_score`
- `test_assess_returns_word_list`
- `test_assess_word_has_error_type`
- `test_assess_word_has_phoneme_scores`
- `test_assess_raises_pronunciation_error_on_sdk_failure`
- `test_assess_raises_pronunciation_error_on_no_match`

## Definition of Done
- [ ] All unit tests pass (`uv run pytest`)
- [ ] Live test exists and is marked `@pytest.mark.live`
- [ ] No `azure` imports in `core/` layer
- [ ] Typing complete (no untyped functions)
- [ ] Plan steps all implemented
