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
| `backend/pyproject.toml` | modify — add `deepgram-sdk` and `gTTS` (dev) dependencies |
| `backend/core/models/transcription.py` | create — `WordResult`, `TranscriptionResult` |
| `backend/core/exceptions.py` | create — `TranscriptionError` |
| `backend/core/interfaces/stt.py` | create — abstract `SpeechToTextProvider` |
| `backend/providers/deepgram_stt.py` | create — `DeepgramSTTProvider` |
| `backend/tests/test_deepgram_stt.py` | create — unit tests (mocked SDK) |
| `backend/tests/test_deepgram_stt_live.py` | create — live tests with real API (marked `live`) |
| `backend/tests/fixtures/generate_fixtures.py` | create — script to generate `.wav` fixtures via gTTS |
| `backend/tests/fixtures/README.md` | create — explains fixtures and how to regenerate |

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

1. **Add `deepgram-sdk` to `pyproject.toml`** and `gTTS` to dev deps, run `uv sync`
2. **Create `core/models/transcription.py`** with `WordResult` and `TranscriptionResult`
3. **Create `core/exceptions.py`** with `TranscriptionError`
4. **Create `core/interfaces/stt.py`** with abstract `SpeechToTextProvider`
5. **Create `providers/deepgram_stt.py`** with `DeepgramSTTProvider`:
   - `__init__` validates `api_key` is non-empty, raises `ValueError` if missing
   - `transcribe` calls Deepgram async REST API via SDK
   - Maps Deepgram response to `TranscriptionResult`
   - Wraps SDK exceptions in `TranscriptionError`
6. **Configure `pytest.mark.live`** in `pyproject.toml` so the marker is recognized
7. **Create `tests/fixtures/generate_fixtures.py`** — generates `hello_how_are_you.wav`, `missing_word.wav`, `silence.wav` using `gTTS`
8. **Run `generate_fixtures.py`** to produce the `.wav` files
9. **Create `tests/test_deepgram_stt.py`** — 5 unit tests with mocked SDK
10. **Create `tests/test_deepgram_stt_live.py`** — 3 live tests using real API + fixtures
11. **Run `uv run pytest`** (unit only) — all tests must pass
12. **Run `uv run pytest -m live`** — all live tests must pass against real Deepgram

---

## Test Cases

### Unit tests — `tests/test_deepgram_stt.py` (mocked SDK, no API calls)

```python
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

### Live tests — `tests/test_deepgram_stt_live.py` (real Deepgram API, `@pytest.mark.live`)

Run only explicitly: `uv run pytest -m live` — never in CI or `uv run pytest` default.

**Audio fixtures** (`tests/fixtures/`) — generated by `generate_fixtures.py` using `gTTS` (Google Text-to-Speech, free, no API key):

| Fixture | Text spoken | What it tests |
|---------|------------|---------------|
| `hello_how_are_you.wav` | "Hello, how are you today?" | Full correct transcript, word timestamps, confidence scores |
| `missing_word.wav` | "Hello, how today?" | Fewer words, Deepgram still returns valid word list |
| `silence.wav` | *(empty audio)* | Empty transcript edge case |

> User can also drop a real microphone recording as `tests/fixtures/my_voice.wav` — live test will pick it up if present.

```python
@pytest.mark.live
async def test_live_transcribes_hello_audio():
    # Reads hello_how_are_you.wav, calls real Deepgram API
    # Asserts: transcript contains "hello", words > 0, confidence in [0, 1]

@pytest.mark.live
async def test_live_transcribes_missing_word_audio():
    # Reads missing_word.wav
    # Asserts: transcript does NOT contain "are you", word count < full sentence

@pytest.mark.live
async def test_live_silence_returns_empty_transcript():
    # Reads silence.wav
    # Asserts: transcript == "" or words == []
```

---

## Definition of Done

- [ ] `deepgram-sdk` listed in `pyproject.toml` dependencies
- [ ] `WordResult` and `TranscriptionResult` dataclasses defined and typed
- [ ] `TranscriptionError` domain exception exists in `core/exceptions.py`
- [ ] `SpeechToTextProvider` ABC defined with `transcribe(audio_bytes: bytes) -> TranscriptionResult`
- [ ] `DeepgramSTTProvider` implements the interface
- [ ] No Deepgram imports anywhere in `core/` (domain layer stays clean)
- [ ] All 5 unit tests pass with mocked SDK (no real API calls)
- [ ] `pytest.mark.live` registered in `pyproject.toml`
- [ ] `tests/fixtures/generate_fixtures.py` generates valid `.wav` files
- [ ] All 3 live tests pass against real Deepgram API (`uv run pytest -m live`)
- [ ] Pre-existing `test_health.py` still passes
- [ ] mypy strict: no type errors
- [ ] `uv run pytest` (default, no live) exits 0
