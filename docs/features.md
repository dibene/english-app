---
name: Feature List - Read & Improve MVP
description: >
  Prioritized atomic feature backlog. Each feature follows the agent workflow
  defined in AGENTS.md: Research (optional) -> Plan -> Implement -> Review.
related:
  - docs/mvp_prd.md
  - AGENTS.md
---

# Feature List - Read & Improve MVP

Each feature follows the lifecycle: **Research (optional) -> Plan -> Implement -> Review**.
See [AGENTS.md](../AGENTS.md) for the full workflow definition.

---

## Priority Levels
- **P0** - Core pipeline, must work before anything else
- **P1** - Required for a usable end-to-end product
- **P2** - Developer experience, nice to have for MVP

---

## Backend Features

> **Implementation status:**
> ✅ F-000 · ✅ F-001 · ✅ F-011 · ✅ F-002 · ✅ F-003 · 🔜 F-004 (next) · ⬜ F-005

---

### F-000 - Backend Project Setup ✅ Done
**Priority:** P0 - must exist before any other backend feature
**Slug:** Backend-setup

Bootstrap the Python backend project: uv, FastAPI skeleton, folder structure per Clean
Architecture, and a minimal health check endpoint. No domain logic yet. This is the
foundation every other backend feature builds on.

**Scope:**
- Initialize uv project in backend/ (pyproject.toml, .python-version)
- Install: fastapi, uvicorn, pytest, httpx (for test client), python-dotenv
- Create folder structure: core/interfaces/, core/services/, core/models/, providers/, api/, tests/
- Minimal FastAPI app with GET /health -> { "status": "ok" }
- pytest test confirming /health returns 200
- backend/.env.example with placeholder keys

**High-level error/failure modes:**
- Missing .env file (clear startup error required)
- Port conflict on default port 8000

---

### F-001 - Deepgram STT Provider ✅ Done
**Priority:** P0
**Slug:** deepgram-stt-provider

Define the SpeechToTextProvider abstract interface and implement it with Deepgram.
In the final pipeline Deepgram acts as a **fallback adapter** when Azure is not
configured — it returns word-level confidence but no phoneme scores.
Returns a TranscriptionResult with full transcript and word-level confidence.

**Scope:**
- Define abstract SpeechToTextProvider in backend/core/interfaces/stt.py
- Define TranscriptionResult, WordResult, PhonemeScore models in backend/core/models/transcription.py
- Implement DeepgramSTTProvider in backend/providers/deepgram_stt.py
- Unit tests: mock Deepgram SDK response, assert TranscriptionResult fields
- Interface contract: `transcribe(audio_bytes: bytes) -> TranscriptionResult`

**Implemented models:**
```python
@dataclass
class PhonemeScore:
    phoneme: str            # ARPAbet symbol, e.g. "W"
    score: float            # 0.0 - 1.0

@dataclass
class WordResult:
    word: str
    confidence: float       # 0.0 - 1.0
    start_time: float | None
    end_time: float | None
    error_type: str | None  # "None" | "Mispronunciation" | "Omission" | "Insertion" (Azure only)
    phoneme_scores: list[PhonemeScore] | None  # per-phoneme scores (Azure); None for Deepgram

@dataclass
class TranscriptionResult:
    transcript: str
    words: list[WordResult]
```

**High-level error/failure modes:**
- Invalid or missing DEEPGRAM_API_KEY
- Request timeout
- Unsupported audio format
- No speech detected in audio (empty transcript)

---

### F-011 - Azure Pronunciation Assessment Provider ✅ Done
**Priority:** P0 — chosen as primary provider
**Slug:** pronunciation-assessment-provider

Define the `PronunciationAssessmentProvider` abstract interface and implement with
Azure Cognitive Services Pronunciation Assessment. Receives audio + expected text and
returns per-word and per-phoneme scores. This is the **primary analysis path**: Azure
replaces the need for a separate STT call — it returns transcription, word accuracy,
and phoneme-level detail in a single pass.

**Why Azure over Deepgram as primary:**
Deepgram returns only word-level confidence. Azure returns word accuracy + phoneme-level
scores, which are required to show the user _which phoneme_ they mispronounced — the core
value of the product. The `phoneme_scores` data in `WordResult` is what drives the
per-word phoneme diff display in the frontend. Deepgram remains available as a fallback
adapter (no phoneme data) when Azure is not configured.

This is NOT a type of STT. STT converts audio → text. Pronunciation Assessment scores
how accurately the user pronounced the expected text.

**Scope:**
- Define abstract `PronunciationAssessmentProvider` in `backend/core/interfaces/pronunciation.py`
- Define `PronunciationResult` in `backend/core/models/pronunciation.py`
- Implement `AzurePronunciationProvider` in `backend/providers/azure_pronunciation.py`
- Provider selected via `PRONUNCIATION_PROVIDER=azure` env var (`deepgram` as fallback)
- Unit tests: mock Azure SDK response, assert PronunciationResult fields
- Live test: `test_azure_pronunciation_live.py` with real `.wav` fixture

**Implemented models:**
```python
@dataclass
class PronunciationResult:
    accuracy_score: float       # 0.0 - 100.0
    fluency_score: float        # 0.0 - 100.0
    completeness_score: float   # 0.0 - 100.0
    prosody_score: float | None # 0.0 - 100.0
    words: list[WordResult]     # WordResult.phoneme_scores populated by Azure
```

**Interface contract:**
```python
def assess(self, audio_bytes: bytes, expected_text: str) -> PronunciationResult: ...
```

**High-level error/failure modes:**
- Invalid or missing AZURE_SPEECH_KEY / AZURE_SPEECH_REGION
- Audio format not supported (WAV PCM 16kHz 16-bit mono required)
- Provider returns empty or malformed response

---

### F-002 - Text Comparison Engine ✅ Done
**Priority:** P0
**Slug:** text-comparison-engine

Pure Python module that diffs the expected sentence against a PronunciationResult.
Uses word-level confidence and phoneme scores alongside sequence diff to classify
each word as: ok, missing, inserted, or mispronounced. Returns a structured DiffResult.
No external API calls — fully deterministic and unit-testable.

Note: the current `compare()` signature still accepts `(expected_text, transcription_result,
pronunciation_result=None)`. F-004 simplifies this to a single `result: PronunciationResult`
parameter — the Deepgram adapter lives in the service layer.

**Scope:**
- Input: expected_text (str) + transcription_result (TranscriptionResult) + optional PronunciationResult
- Normalize both sides (lowercase, strip punctuation) before comparison
- Use sequence diff (difflib.SequenceMatcher) to align word sequences
- Classify each diff entry: ok / missing / inserted / mispronounced
- Mispronounced = word present but confidence below configurable threshold (default 0.7)
- Merge per-word phoneme_scores from PronunciationResult into each matching DiffEntry
- Return DiffResult (list of DiffEntry)
- Full unit test coverage with synthetic input

**Implemented models:**
```python
@dataclass
class DiffEntry:
    expected_word: str | None
    spoken_word: str | None
    status: str             # "ok" | "missing" | "inserted" | "mispronounced"
    confidence: float | None
    expected_phonemes: list[str] | None  # ARPAbet from cmudict, e.g. ["W", "ER1", "L", "D"]
    phoneme_scores: list[PhonemeScore] | None  # actual per-phoneme scores from Azure PA

@dataclass
class DiffResult:
    entries: list[DiffEntry]
```

**High-level error/failure modes:**
- Empty PronunciationResult (no words)
- Expected text has no recognizable words after normalization
- All words classified as mispronounced (likely wrong language)

---

### F-003 - LLM Feedback Generator ✅ Done
**Priority:** P0
**Slug:** llm-feedback-generator

Define the LLMProvider abstract interface and implement it with OpenAI gpt-4o-mini.
Receives the full context: expected_text + DiffResult (including phoneme scores when
available from Azure). Produces the feedback JSON (score, errors[], suggestions[]).
Provider is swappable via config — domain logic must not reference OpenAI directly.

**Scope:**
- Define abstract LLMProvider in backend/core/interfaces/llm.py
- Implement OpenAILLMProvider in backend/providers/openai_llm.py
- Provider selected via env var (LLM_PROVIDER=openai)
- Prompt includes: expected text, per-word diff status, confidence, and phoneme scores when available
- Validate response is JSON and matches feedback schema before returning
- Unit tests: mock OpenAI response, assert feedback JSON structure
- Interface contract: `generate_feedback(expected_text, diff_result) -> dict`

**High-level error/failure modes:**
- Invalid or missing OPENAI_API_KEY
- OpenAI timeout
- Response is not valid JSON
- Score outside 0-100 range

---

### F-004 - Core Pipeline Service 🔜 Next
**Priority:** P0 - built after F-001, F-011, F-002, F-003 are individually done
**Slug:** core-pipeline-service

Application service that wires Azure PA (or Deepgram fallback) + ComparisonEngine + LLM
into a single `PronunciationService.analyze(audio_bytes, expected_text) -> feedback_json`
call. The pipeline uses `PronunciationResult` as the single shared structure throughout.

Note: `DiffEntry.phoneme_scores` and `_merge_phoneme_scores()` already exist (done as
part of F-002 implementation). This feature focuses on the service layer and cleaning
up the `compare()` signature.

---

**Provider strategy: Azure primary, Deepgram as fallback adapter**

**Option A — Azure (default, `PRONUNCIATION_PROVIDER=azure`):**
```
audio -> AzurePronunciationProvider.assess() -> PronunciationResult
  (WordResult has confidence + error_type + phoneme_scores)
```

**Option B — Deepgram fallback (`PRONUNCIATION_PROVIDER=deepgram`):**
```
audio -> DeepgramSTTProvider.transcribe() -> TranscriptionResult
  -> _transcription_to_pronunciation_result() -> PronunciationResult
  (WordResult has confidence only, phoneme_scores=None)
```

The adapter `_transcription_to_pronunciation_result()` lives in the service layer:
```python
def _transcription_to_pronunciation_result(t: TranscriptionResult) -> PronunciationResult:
    return PronunciationResult(
        accuracy_score=t.confidence * 100,
        fluency_score=t.confidence * 100,
        completeness_score=100.0,
        prosody_score=None,
        words=t.words,  # phoneme_scores=None
    )
```

---

**Scope:**
- `PronunciationService` in `backend/core/services/pronunciation_service.py`
- Update `TextComparisonEngine.compare()` signature: remove `transcription_result` and
  `pronunciation_result` params, replace with single `result: PronunciationResult`
- Delete `_merge_phoneme_scores()` — `phoneme_scores` is already on `WordResult` from Azure
- Implement `_transcription_to_pronunciation_result()` adapter in service layer
- `PronunciationService.analyze(audio_bytes, expected_text) -> dict` orchestrates:
  1. Call active provider → `PronunciationResult`
  2. `TextComparisonEngine.compare(expected_text, result)` → `DiffResult`
  3. `LLMProvider.generate_feedback(expected_text, diff_result)` → `dict`
- Integration test in `backend/tests/test_pipeline_integration.py`
  - Mocked providers for CI; real `.wav` fixture for `@pytest.mark.live`
  - Asserts: `feedback_json` has `score` (int), `errors` (list), `suggestions` (list)
- Update all existing unit tests that call `compare()` with the old signature

**Files to create or modify:**
- `backend/core/services/pronunciation_service.py` — create
- `backend/core/services/text_comparison.py` — update `compare()` signature, delete `_merge_phoneme_scores`
- `backend/tests/test_pipeline_integration.py` — create
- `backend/tests/test_text_comparison.py` — update tests to new signature

**High-level error/failure modes:**
- Provider returns empty words (no speech in audio)
- DiffResult is empty (expected and spoken match perfectly — valid, score 100)
- LLM returns malformed JSON
- Any provider raises — service propagates as domain exception

---

### F-005 - FastAPI Pronunciation Endpoint
**Priority:** P1 - needed for frontend integration
**Slug:** Backend-api-endpoint

HTTP POST endpoint that accepts multipart/form-data (audio file + expected_text string),
calls PronunciationService, and returns feedback JSON. Includes input validation and
structured error responses. This is the integration point between frontend and backend.
The response includes per-word `phoneme_scores` so the frontend can highlight individual
phonemes (expected vs spoken).

**Scope:**
- POST /analyze: audio_file (WAV/WebM) + expected_text (string, max 500 chars)
- Response includes per-word diff entries with `phoneme_scores` when available (Azure path)
- 400 for validation errors, 422 for pipeline failures, 504 for timeout
- CORS configured for local frontend dev (localhost:3000)
- Integration test using httpx TestClient

**Response schema (example with Azure phoneme data):**
```json
{
  "score": 85,
  "errors": [
    {
      "word": "world",
      "status": "mispronounced",
      "phoneme_scores": [
        {"phoneme": "W",   "score": 0.95},
        {"phoneme": "ER1", "score": 0.42},
        {"phoneme": "L",   "score": 0.88},
        {"phoneme": "D",   "score": 0.71}
      ]
    }
  ],
  "suggestions": ["Focus on the 'ER' vowel sound in 'world'"]
}
```

**High-level error/failure modes:**
- Missing required fields
- Audio file too large or wrong format
- Pipeline failure surfaced as structured HTTP error
- Request timeout (> 10 seconds)

---

## Frontend Features

### F-006 - Text Input and Sentence Splitter UI
**Priority:** P1
**Slug:** Frontend-text-input

Next.js page where the user pastes English text. System splits into sentences and
displays them as a numbered list. User selects one sentence to record.

**Scope:**
- Textarea with 500 char limit and counter
- Sentence splitting (period/question/exclamation detection)
- Sentence list with click-to-select
- Selected sentence highlighted

**High-level error/failure modes:**
- Text exceeds 500 characters
- No sentences detected
- Text contains no recognizable English words

---

### F-007 - Audio Recording UI
**Priority:** P1
**Slug:** Frontend-audio-recording

Browser-based audio recording per selected sentence (Web Audio API).
Shows recording state (idle / recording / processing).
Submits audio to backend POST /analyze on stop.

**Scope:**
- Record button with state machine: idle -> recording -> processing -> done
- Max recording duration: 45 seconds (auto-stop)
- Visual recording indicator (timer or waveform)
- Sends (audio_blob, expected_text) as multipart/form-data to backend

**High-level error/failure modes:**
- Microphone permission denied by user
- Browser does not support MediaRecorder API
- Audio too short (< 1 second)
- Recording exceeds 45 seconds

---

### F-008 - Feedback Display UI
**Priority:** P1
**Slug:** Frontend-feedback-display

Displays the feedback JSON returned by the backend:
- Overall score (0-100) with visual indicator
- Sentence with problematic words highlighted inline
- Per-word phoneme breakdown: expected phonemes vs actual scores
- 1-3 improvement suggestions as a list

**Scope:**
- Score display (number + color coding: green >= 80, yellow 50-79, red < 50)
- Word-level highlighting in the original sentence (color per error type)
- On hover/tap of a highlighted word: show phoneme breakdown — which phonemes
  were ok and which were below threshold (uses `phoneme_scores` from API response).
  When Azure data is unavailable (Deepgram fallback), phoneme breakdown is hidden.
- Suggestions list
- Re-record button to try the same sentence again
- Success state when score is 100 / no errors

**High-level error/failure modes:**
- Backend returns error response
- feedback JSON has missing or unexpected fields
- No errors in response (score 100) - explicit success state required
- `phoneme_scores` absent (Deepgram fallback) — phoneme panel hidden gracefully

---

### F-009 - Frontend to Backend Integration
**Priority:** P1 - ties F-005 + F-006/007/008 together
**Slug:** Frontend-backend-integration

Wire the full frontend flow to the live backend API.
End-to-end browser test: paste text -> select sentence -> record -> see feedback.

**Scope:**
- Typed API client module in frontend (fetch-based)
- Error state handling in UI (backend down, timeout, validation error)
- NEXT_PUBLIC_API_URL env var for backend URL
- Verify CORS works end-to-end (local backend + local frontend)

**High-level error/failure modes:**
- CORS policy blocking requests
- Backend not running (connection refused)
- Network timeout
- Response parsing error

---

## Infrastructure Features

### F-010 - Local Dev Setup and README
**Priority:** P2
**Slug:** local-dev-setup

README with setup instructions for both backend (uv, env vars, run server) and
frontend (npm install, env vars, run dev). .env.example files for both.

**Scope:**
- Root README.md with project overview and quick start
- backend/.env.example (DEEPGRAM_API_KEY, OPENAI_API_KEY, STT_PROVIDER, LLM_PROVIDER)
- frontend/.env.local.example (NEXT_PUBLIC_API_URL)
- Step-by-step local setup instructions
- Document default ports (backend: 8000, frontend: 3000)

**High-level error/failure modes:**
- Missing .env file (clear error message required)
- Port conflicts (document how to change default ports)

---

## Deferred (Post-MVP)

| ID    | Feature                        | Reason deferred                              |
|-------|--------------------------------|----------------------------------------------|
| D-001 | Local STT (faster-whisper)     | STT interface ready; implementation deferred |
| D-002 | Local LLM (Ollama / Deepseek)  | LLM interface ready; implementation deferred |
| D-003 | User authentication            | Out of MVP scope                             |
| D-004 | Audio history / replay         | Out of MVP scope                             |
| D-005 | Mobile native app              | Out of MVP scope                             |
| D-006 | Streaming feedback             | Out of MVP scope                             |
| D-007 | Phoneme-level display          | Phoneme data flows through pipeline (Azure); display promoted to F-008 scope |
