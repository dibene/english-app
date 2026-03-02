# Plan: Deepgram STT Provider (F-001)

## Goal

Define the `SpeechToTextProvider` abstract interface and implement it with Deepgram (pre-recorded audio, free tier). Returns a `TranscriptionResult` with full transcript and word-level confidence. Unit-tested with mocked Deepgram SDK responses.

---

## Audio Architecture Decision

**No file storage.** Audio bytes flow from the HTTP request directly to Deepgram in memory:

```
Frontend records audio
        ↓
POST /analyze (multipart/form-data) — F-005
        ↓
FastAPI reads bytes into memory (UploadFile.read())
        ↓
DeepgramSTTProvider.transcribe(audio_bytes: bytes)
        ↓
Deepgram pre-recorded API → full transcript + word-level data
        ↓
TranscriptionResult returned to service layer
```

**Pre-recorded (not streaming):** The full audio is sent after recording stops. Simpler, more accurate word timestamps, no WebSockets needed. Streaming would be for real-time feedback (post-MVP).

---

## Scope

**In scope:**
- `WordResult` and `TranscriptionResult` dataclasses in `core/models/`
- `SpeechToTextProvider` abstract interface in `core/interfaces/stt.py`
- `DeepgramSTTProvider` in `providers/deepgram_stt.py`
- `TranscriptionError` domain exception
- `deepgram-sdk` added as dependency
- Unit tests: mocked Deepgram SDK, assert all TranscriptionResult fields

**Out of scope (this PR):**
- HTTP endpoint wiring (F-005)
- Provider factory / dependency injection into FastAPI (F-005)
- Streaming transcription
- Audio format validation
- File storage (filesystem or S3)

---

## Files to Create or Modify

| File | Action |
|------|--------|
| `backend/pyproject.toml` | modify — add `deepgram-sdk` dependency |
| `backend/core/models/transcription.py` | create — `WordResult`, `TranscriptionResult` |
| `backend/core/exceptions.py` | create — `TranscriptionError` |
| `backend/core/interfaces/stt.py` | create — abstract `SpeechToTextProvider` |
| `backend/providers/deepgram_stt.py` | create — `DeepgramSTTProvider` |
| `backend/tests/test_deepgram_stt.py` | create — unit tests (mocked SDK) |

---

## Interfaces and Data Models

### Domain Models (`core/models/transcription.py`)

```python
from dataclasses import dataclass

@dataclass
class WordResult:
    word: str
    confidence: float        # 0.0 - 1.0
    start_time: float | None
    end_time: float | None

@dataclass
class TranscriptionResult:
    transcript: str
    words: list[WordResult]
```

### Domain Exception (`core/exceptions.py`)

```python
class TranscriptionError(Exception):
    """Raised when audio transcription fails."""
    pass
```

### Abstract Interface (`core/interfaces/stt.py`)

```python
from abc import ABC, abstractmethod
from core.models.transcription import TranscriptionResult

class SpeechToTextProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes) -> TranscriptionResult:
        """Transcribe audio bytes to text with word-level confidence."""
        ...
```

### Deepgram Implementation (`providers/deepgram_stt.py`)

```python
class DeepgramSTTProvider(SpeechToTextProvider):
    def __init__(self, api_key: str) -> None:
        # Validates key is non-empty, initializes DeepgramClient
        ...

    async def transcribe(self, audio_bytes: bytes) -> TranscriptionResult:
        # Calls deepgram SDK, maps response to TranscriptionResult
        # Raises TranscriptionError on SDK/API failure
        ...
```

**Deepgram SDK response mapping:**
- `response.results.channels[0].alternatives[0].transcript` → `TranscriptionResult.transcript`
- `response.results.channels[0].alternatives[0].words[]` → `TranscriptionResult.words`
  - `word.word` → `WordResult.word`
  - `word.confidence` → `WordResult.confidence`
  - `word.start` → `WordResult.start_time`
  - `word.end` → `WordResult.end_time`

---

## Implementation Steps

1. **Add `deepgram-sdk` to `pyproject.toml`** and run `uv sync`
2. **Create `core/models/transcription.py`** with `WordResult` and `TranscriptionResult`
3. **Create `core/exceptions.py`** with `TranscriptionError`
4. **Create `core/interfaces/stt.py`** with abstract `SpeechToTextProvider`
5. **Create `providers/deepgram_stt.py`** with `DeepgramSTTProvider`:
   - `__init__` validates `api_key` is non-empty, raises `ValueError` if missing
   - `transcribe` calls `client.listen.asyncrest.v("1").transcribe_file()`
   - Maps Deepgram response to `TranscriptionResult`
   - Wraps SDK exceptions in `TranscriptionError`
6. **Create `tests/test_deepgram_stt.py`** with mocked SDK tests
7. **Run full test suite** — all tests must pass including pre-existing health tests

---

## Test Cases

```python
# test_deepgram_stt.py
test_transcribe_returns_transcript_text()
    # Mock SDK response with single word, assert transcript field

test_transcribe_returns_word_list_with_correct_fields()
    # Mock SDK response with 2 words, assert word, confidence, start_time, end_time

test_transcribe_empty_audio_returns_empty_result()
    # Mock SDK response with empty words[], assert words=[] and transcript=""

test_transcribe_raises_transcription_error_on_sdk_failure()
    # Mock SDK raises Exception, assert TranscriptionError is raised

test_missing_api_key_raises_value_error()
    # Instantiate DeepgramSTTProvider(""), assert ValueError
```

---

## Definition of Done

- [ ] `deepgram-sdk` listed in `pyproject.toml` dependencies
- [ ] `WordResult` and `TranscriptionResult` dataclasses defined and typed
- [ ] `TranscriptionError` domain exception exists in `core/exceptions.py`
- [ ] `SpeechToTextProvider` ABC defined with `transcribe(audio_bytes: bytes) -> TranscriptionResult`
- [ ] `DeepgramSTTProvider` implements the interface
- [ ] No Deepgram imports anywhere in `core/` (domain layer stays clean)
- [ ] All 5+ test cases pass with mocked SDK (no real API calls in tests)
- [ ] Pre-existing test `test_health.py` still passes
- [ ] mypy strict: no type errors
- [ ] `uv run pytest` exits 0
