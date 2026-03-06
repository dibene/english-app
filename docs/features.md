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

### F-000 - Backend Project Setup
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

### F-001 - Deepgram STT Provider
**Priority:** P0
**Slug:** deepgram-stt-provider

Define the SpeechToTextProvider abstract interface and implement it with Deepgram (free tier).
Unit-tested with a mocked Deepgram response - no real API call required in tests.
Returns a TranscriptionResult with full transcript and word-level confidence.

**Scope:**
- Define abstract SpeechToTextProvider in backend/core/interfaces/stt.py
- Define TranscriptionResult and WordResult data models in backend/core/models/
- Implement DeepgramSTTProvider in backend/providers/deepgram_stt.py
- Provider selected via env var (STT_PROVIDER=deepgram)
- Unit tests: mock Deepgram SDK response, assert TranscriptionResult fields
- Interface contract: transcribe(audio_bytes: bytes) -> TranscriptionResult

**Data models (to implement):**
`python
@dataclass
class WordResult:
    word: str
    confidence: float       # 0.0 - 1.0
    start_time: float | None
    end_time: float | None

@dataclass
class TranscriptionResult:
    transcript: str
    words: list[WordResult]
`

**High-level error/failure modes:**
- Invalid or missing DEEPGRAM_API_KEY
- Request timeout
- Unsupported audio format
- No speech detected in audio (empty transcript)
- Deepgram quota exceeded

---

### F-002 - Text Comparison Engine
**Priority:** P0
**Slug:** text-comparison-engine

Pure Python module that diffs the expected sentence against a TranscriptionResult.
Uses word-level confidence from TranscriptionResult alongside sequence diff to classify
each word as: ok, missing, inserted, or mispronounced (wrong word or confidence below threshold).
Returns a structured DiffResult. No external API calls - fully deterministic and unit-testable.

**Scope:**
- Input: expected_text (str) + transcription_result (TranscriptionResult)
- Normalize both sides (lowercase, strip punctuation) before comparison
- Use sequence diff (difflib.SequenceMatcher) to align word sequences
- Classify each diff entry: ok / missing / inserted / mispronounced
- Mispronounced = word present but confidence below configurable threshold (default 0.7)
- Return DiffResult (list of DiffEntry)
- Full unit test coverage with synthetic input (no API needed)

**Data models (to implement):**
`python
@dataclass
class DiffEntry:
    expected_word: str | None
    spoken_word: str | None
    status: str             # "ok" | "missing" | "inserted" | "mispronounced"
    confidence: float | None
    expected_phonemes: list[str] | None  # ARPAbet from cmudict, e.g. ["W", "ER1", "L", "D"]

@dataclass
class DiffResult:
    entries: list[DiffEntry]
`

**High-level error/failure modes:**
- Empty TranscriptionResult (no words)
- Expected text has no recognizable words after normalization
- All words classified as mispronounced (likely wrong language)

---

### F-003 - LLM Feedback Generator
**Priority:** P0
**Slug:** llm-feedback-generator

Define the LLMProvider abstract interface and implement it with OpenAI gpt-4o-mini.
Receives the full context: expected_text + TranscriptionResult + DiffResult.
Produces the feedback JSON (score, errors[], suggestions[]).
Provider is swappable via config - domain logic must not reference OpenAI directly.

**Scope:**
- Define abstract LLMProvider in backend/core/interfaces/llm.py
- Implement OpenAILLMProvider in backend/providers/openai_llm.py
- Provider selected via env var (LLM_PROVIDER=openai)
- Prompt: provides expected text, spoken transcript with per-word confidence, and diff classification
- Validate response is JSON and matches feedback schema before returning
- Unit tests: mock OpenAI response, assert feedback JSON structure
- Interface contract: generate_feedback(expected_text, transcription_result, diff_result) -> dict

**High-level error/failure modes:**
- Invalid or missing OPENAI_API_KEY
- OpenAI timeout
- Response is not valid JSON
- Score outside 0-100 range
- Suggestions list is empty or None

---

### F-004 - Core Pipeline Service (Integration Test)
**Priority:** P0 - built after F-001, F-002, F-003 are individually tested
**Slug:** core-pipeline-service

Application service that wires together STT + ComparisonEngine + LLM into a single
PronunciationService.analyze(audio_bytes, expected_text) -> feedback_json call.
Validated by an integration test using a real .wav file and real API calls (or
wired mocks for CI). This is the first end-to-end proof that all pieces work together.

**Scope:**
- PronunciationService in backend/core/services/pronunciation_service.py
- Orchestrates: SpeechToTextProvider -> ComparisonEngine -> LLMProvider
- Integration test in backend/tests/test_pipeline_integration.py
- Test uses a real .wav audio sample committed to tests/fixtures/
- Test asserts: feedback_json has score (int), errors (list), suggestions (list)
- No HTTP layer needed - direct service call in pytest

**High-level error/failure modes:**
- STT returns empty transcript (no speech in audio)
- DiffResult is empty (expected and spoken match perfectly - valid case, score 100)
- LLM returns malformed JSON
- Any provider raises - service propagates as domain exception

---

### F-005 - FastAPI Pronunciation Endpoint
**Priority:** P1 - needed for frontend integration
**Slug:** Backend-api-endpoint

HTTP POST endpoint that accepts multipart/form-data (audio file + expected_text string),
calls PronunciationService, and returns feedback JSON. Includes input validation and
structured error responses. This is the integration point between frontend and backend.

**Scope:**
- POST /analyze: audio_file (WAV/WebM) + expected_text (string, max 500 chars)
- Response: feedback JSON (schema from PRD section 6)
- 400 for validation errors, 422 for pipeline failures, 504 for timeout
- CORS configured for local frontend dev (localhost:3000)
- Integration test using httpx TestClient

**High-level error/failure modes:**
- Missing required fields
- Audio file too large or wrong format
- STT or LLM downstream failure surfaced as structured HTTP error
- Request timeout (> 10 seconds)

---

### F-011 - Pronunciation Assessment Provider
**Priority:** P1
**Slug:** pronunciation-assessment-provider

Define a `PronunciationAssessmentProvider` abstract interface — parallel to but separate from
`SpeechToTextProvider`. Receives audio + expected text and returns per-word and per-phoneme
pronunciation scores. Implements with Speechace (2.5 hrs/month free) as primary and
Azure Pronunciation Assessment (5 hrs/month free) as alternative.

This is NOT a type of STT. STT converts audio → text. Pronunciation Assessment
scores how accurately the user pronounced the expected text.

**Scope:**
- Define abstract `PronunciationAssessmentProvider` in `backend/core/interfaces/pronunciation.py`
- Define `PhonemeScore`, `WordPronunciationResult`, `PronunciationResult` in `backend/core/models/`
- Implement `SpeechacePronunciationProvider` in `backend/providers/speechace_pronunciation.py`
- Implement `AzurePronunciationProvider` in `backend/providers/azure_pronunciation.py`
- Provider selected via `PRONUNCIATION_PROVIDER=speechace|azure` env var
- Unit tests: mock API responses, assert PronunciationResult fields

**Data models (to implement):**
`python
@dataclass
class PhonemeScore:
    phoneme: str        # ARPAbet symbol, e.g. "W"
    score: float        # 0.0 - 1.0

@dataclass
class WordPronunciationResult:
    word: str
    score: float            # 0.0 - 1.0
    phoneme_scores: list[PhonemeScore]

@dataclass
class PronunciationResult:
    overall_score: float
    fluency_score: float | None
    words: list[WordPronunciationResult]
`

**Interface contract:**
`python
def assess(self, audio_bytes: bytes, expected_text: str) -> PronunciationResult: ...
`

**Free tier comparison:**
| Provider | Free tier | Phoneme scores | Notes |
|----------|-----------|---------------|-------|
| Speechace | 2.5 hrs/month | ✅ | Language-learning oriented |
| Azure PA | 5 hrs/month | ✅ | Also gives stress, prosody, syllable |

**High-level error/failure modes:**
- Invalid or missing API key
- Audio format not supported
- Expected text too long for provider limits
- Provider returns empty or malformed response

---

### F-012 - Pronunciation Pipeline Integration
**Priority:** P1
**Slug:** pronunciation-pipeline-integration

Enrich `DiffResult` with real per-phoneme scores from `PronunciationAssessmentProvider`
by merging `PronunciationResult` into the comparison engine output. Update
`PronunciationService` to optionally call the PA provider alongside STT.

**Scope:**
- Update `DiffEntry` to hold `phoneme_scores: list[PhonemeScore] | None` (actual scores from PA)
- Update `TextComparisonEngine.compare()` to accept optional `PronunciationResult` and
  merge per-word phoneme scores into the matching `DiffEntry`
- Update `PronunciationService` to call `PronunciationAssessmentProvider` when configured
- Update LLM prompt to include phoneme-level detail when available
- Integration tests with mocked PA provider

**High-level error/failure modes:**
- PA provider word list doesn't align with DiffResult (handle gracefully, best-effort merge)
- PA provider disabled/not configured (pipeline continues with phonemes=None)

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
- 1-3 improvement suggestions as a list

**Scope:**
- Score display (number + color coding: green >= 80, yellow 50-79, red < 50)
- Word-level highlighting in the original sentence (color per error type)
- Suggestions list
- Re-record button to try the same sentence again
- Success state when score is 100 / no errors

**High-level error/failure modes:**
- Backend returns error response
- feedback JSON has missing or unexpected fields
- No errors in response (score 100) - explicit success state required

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
| D-007 | Phoneme-level analysis         | Out of MVP scope                             |
