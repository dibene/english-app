# Plan: Core Pipeline Service (F-004)

## Goal

Wire `PronunciationAssessmentProvider` (or Deepgram fallback) + `TextComparisonEngine` + `LLMProvider`
into a single `PronunciationService.analyze(audio_bytes, expected_text) -> dict` orchestration,
and clean up `TextComparisonEngine.compare()` to accept a single `PronunciationResult`.

---

## Scope

**In scope:**
- Create `PronunciationService` in `backend/core/services/pronunciation_service.py`
- Update `TextComparisonEngine.compare()`: replace `(transcription_result, pronunciation_result=None)` with `(result: PronunciationResult)`
- Remove `_merge_phoneme_scores()` from `text_comparison.py` — phoneme_scores come directly from `WordResult`
- Add `_transcription_to_pronunciation_result()` adapter in the new service module
- Update all tests in `test_text_comparison.py` to match new `compare()` signature
- Create `backend/tests/test_pipeline_integration.py` with mocked-providers CI test and `@pytest.mark.live` path

**Out of scope (this PR):**
- FastAPI endpoint (F-005)
- Provider instantiation / dependency injection wiring in `main.py` (done in F-005)
- New domain exceptions beyond what already exists in `exceptions.py`

---

## Files to Create or Modify

| File | Action |
|------|--------|
| `backend/core/services/text_comparison.py` | Update `compare()` signature; delete `_merge_phoneme_scores` |
| `backend/core/services/pronunciation_service.py` | Create |
| `backend/tests/test_text_comparison.py` | Update all calls to `compare()` |
| `backend/tests/test_pipeline_integration.py` | Create |

---

## Interfaces and Data Models

No new models or interfaces. All types already exist.

**`compare()` — new signature:**
```python
def compare(self, expected_text: str, result: PronunciationResult) -> DiffResult: ...
```

**`_transcription_to_pronunciation_result()` — helper in service module:**
```python
def _transcription_to_pronunciation_result(t: TranscriptionResult) -> PronunciationResult:
    return PronunciationResult(
        accuracy_score=t.confidence * 100,
        fluency_score=t.confidence * 100,
        completeness_score=100.0,
        prosody_score=None,
        words=t.words,  # phoneme_scores=None (Deepgram doesn't populate them)
    )
```

**`PronunciationService`:**
```python
class PronunciationService:
    def __init__(
        self,
        pronunciation_provider: PronunciationAssessmentProvider | None,
        stt_provider: SpeechToTextProvider | None,
        comparison_engine: TextComparisonEngine,
        llm_provider: LLMProvider,
    ) -> None: ...

    def analyze(self, audio_bytes: bytes, expected_text: str) -> dict[str, Any]:
        """Orchestrate: provider → compare → feedback."""
        ...
```

Constructor asserts at least one of `pronunciation_provider` or `stt_provider` is provided (runtime guard).

---

## Implementation Steps

### Step 1 — Update `TextComparisonEngine.compare()`

1. Remove `transcription_result: TranscriptionResult` and `pronunciation_result: PronunciationResult | None = None` params.
2. Add `result: PronunciationResult` param.
3. Build `spoken_words`, `confidences`, and `phoneme_scores_by_index` from `result.words` in a single loop.
4. When creating `DiffEntry` for any spoken word at index `j`, set `phoneme_scores=phoneme_scores_by_index[j]` directly.
5. Remove the `_merge_phoneme_scores()` call and the function itself.
6. Remove the `TranscriptionResult` import (no longer needed in this module).

**Key internal change:** replace
```python
spoken_words: list[str] = []
confidences: list[float] = []
for wr in transcription_result.words:
    ...
```
with
```python
spoken_words: list[str] = []
confidences: list[float | None] = []
phoneme_scores_by_index: list[list[PhonemeScore] | None] = []
for wr in result.words:
    normalised = _normalize(wr.word)
    if not normalised:
        continue
    spoken_words.append(normalised[0])
    confidences.append(wr.confidence)
    phoneme_scores_by_index.append(wr.phoneme_scores)
```
Then pass `phoneme_scores=phoneme_scores_by_index[j + offset]` when building DiffEntry for spoken words (equal, insert, replace tags).

### Step 2 — Create `PronunciationService`

File: `backend/core/services/pronunciation_service.py`

```python
"""Application service that orchestrates the pronunciation analysis pipeline."""

from typing import Any

from core.interfaces.llm import LLMProvider
from core.interfaces.pronunciation import PronunciationAssessmentProvider
from core.interfaces.stt import SpeechToTextProvider
from core.models.pronunciation import PronunciationResult
from core.models.transcription import TranscriptionResult
from core.services.text_comparison import TextComparisonEngine


def _transcription_to_pronunciation_result(t: TranscriptionResult) -> PronunciationResult:
    return PronunciationResult(
        accuracy_score=t.confidence * 100,
        fluency_score=t.confidence * 100,
        completeness_score=100.0,
        prosody_score=None,
        words=t.words,
    )


class PronunciationService:
    def __init__(
        self,
        comparison_engine: TextComparisonEngine,
        llm_provider: LLMProvider,
        pronunciation_provider: PronunciationAssessmentProvider | None = None,
        stt_provider: SpeechToTextProvider | None = None,
    ) -> None:
        if pronunciation_provider is None and stt_provider is None:
            raise ValueError("At least one of pronunciation_provider or stt_provider must be set.")
        self._pronunciation_provider = pronunciation_provider
        self._stt_provider = stt_provider
        self._comparison_engine = comparison_engine
        self._llm_provider = llm_provider

    def analyze(self, audio_bytes: bytes, expected_text: str) -> dict[str, Any]:
        if self._pronunciation_provider is not None:
            result = self._pronunciation_provider.assess(audio_bytes, expected_text)
        else:
            transcription = self._stt_provider.transcribe(audio_bytes)  # type: ignore[union-attr]
            result = _transcription_to_pronunciation_result(transcription)

        diff_result = self._comparison_engine.compare(expected_text, result)
        return self._llm_provider.generate_feedback(expected_text, diff_result)
```

### Step 3 — Update `test_text_comparison.py`

- Replace `_make_transcription()` helper with `_make_pronunciation()` that returns a `PronunciationResult`:
  ```python
  def _make_pronunciation(words: list[tuple[str, float]]) -> PronunciationResult:
      word_results = [
          WordResult(word=w, confidence=c, start_time=None, end_time=None)
          for w, c in words
      ]
      return PronunciationResult(
          accuracy_score=90.0,
          fluency_score=88.0,
          completeness_score=100.0,
          prosody_score=None,
          words=word_results,
      )
  ```
- Update all `engine.compare("...", transcription)` calls to `engine.compare("...", pronunciation)`.
- Remove the `TranscriptionResult` import if unused.
- Simplify phoneme-score tests: since phoneme_scores are already on WordResult, there is no second argument to `compare()`. Update `_make_pronunciation_result()` or fold it into `_make_pronunciation()` by accepting optional phoneme data.

### Step 4 — Create `test_pipeline_integration.py`

Tests:
1. `test_analyze_returns_feedback_dict_with_azure_provider()` — mock `PronunciationAssessmentProvider`, `TextComparisonEngine`, `LLMProvider`; assert returned dict has `score`, `errors`, `suggestions`.
2. `test_analyze_uses_deepgram_fallback_when_no_azure()` — mock `SpeechToTextProvider`; assert adapter converts `TranscriptionResult` → `PronunciationResult` correctly and pipeline completes.
3. `test_analyze_propagates_pronunciation_error()` — mock provider raises `PronunciationError`; assert it propagates.
4. `test_analyze_propagates_llm_error()` — mock LLM raises `LLMFeedbackError`; assert it propagates.
5. `test_service_requires_at_least_one_provider()` — both `None` raises `ValueError`.
6. `@pytest.mark.live` `test_analyze_live_azure()` — uses real providers + real `.wav` fixture.

---

## Test Cases Summary

### `test_text_comparison.py` (updated, not new)
All existing tests remain but with updated `compare()` signature. No test logic is removed.

### `test_pipeline_integration.py` (new)
- `test_analyze_returns_feedback_dict_with_azure_provider`
- `test_analyze_uses_deepgram_fallback_when_no_azure`
- `test_analyze_propagates_pronunciation_error`
- `test_analyze_propagates_llm_error`
- `test_service_requires_at_least_one_provider`
- `test_analyze_live_azure` *(live)*

---

## Definition of Done

- [ ] `TextComparisonEngine.compare()` accepts `PronunciationResult` only; old params removed
- [ ] `_merge_phoneme_scores()` deleted; phoneme_scores read directly from `WordResult`
- [ ] `PronunciationService.analyze()` orchestrates provider → compare → LLM
- [ ] Deepgram fallback adapter `_transcription_to_pronunciation_result()` in service module
- [ ] All existing `test_text_comparison.py` tests pass with new signature
- [ ] New `test_pipeline_integration.py` CI tests pass (`uv run pytest`)
- [ ] No domain layer imports provider code
- [ ] All functions are fully typed (no untyped functions)
