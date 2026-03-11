# Plan: FastAPI Pronunciation Endpoint (F-005)

## Goal

Expose `PronunciationService.analyze()` as `POST /analyze` — a multipart/form-data
endpoint that accepts raw audio + expected text and returns structured pronunciation
feedback JSON.

## Research

Not needed. FastAPI file uploads are standard, the service layer is fully implemented
(F-004), and the response schema is defined in the PRD. No external APIs or new
patterns are introduced.

---

## Scope

**In scope:**
- `POST /analyze` accepting `audio_file` (WAV/WebM) + `expected_text` (string ≤ 500 chars)
- Input validation: file content-type, file size (max 10 MB), expected_text length
- Provider wiring via environment variables in `api/dependencies.py`
- Structured error responses: 400 (validation), 422 (pipeline failure), 504 (timeout)
- 10-second timeout using `asyncio.wait_for` + `asyncio.to_thread`
- Integration test using `httpx.AsyncClient` / `TestClient`
- Add `python-multipart` dependency (required by FastAPI for UploadFile)

**Out of scope (this PR):**
- Frontend wiring (F-009)
- Authentication / rate limiting
- WebM → WAV conversion (WAV input only for MVP; WebM noted as future work)
- Streaming responses

---

## Response Schema

The `PronunciationService.analyze()` already returns a `words` list containing **all**
diff entries (ok, mispronounced, missing, inserted). The features.md schema example
uses `"errors"` but that was illustrative. We expose **all** `words` so the frontend
(F-008) can reconstruct and highlight the full sentence — returning only errors would
not give the frontend enough context to render the sentence correctly.

```json
{
  "score": 85,
  "words": [
    {
      "expected_word": "hello",
      "spoken_word": "hello",
      "status": "ok",
      "confidence": 0.99,
      "expected_phonemes": ["HH", "AH0", "L", "OW1"],
      "phoneme_scores": null
    },
    {
      "expected_word": "world",
      "spoken_word": "world",
      "status": "mispronounced",
      "confidence": 0.55,
      "expected_phonemes": ["W", "ER1", "L", "D"],
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

---

## Files to Create or Modify

| File | Action |
|------|--------|
| `backend/pyproject.toml` | Add `python-multipart` dependency |
| `backend/api/dependencies.py` | Create — provider wiring + `get_pronunciation_service()` |
| `backend/api/analyze.py` | Create — POST /analyze route |
| `backend/api/main.py` | Modify — include the analyze router |
| `backend/tests/test_analyze_endpoint.py` | Create — integration tests |

---

## Interfaces and Data Models

No new domain interfaces or models.

### Pydantic response model (`api/analyze.py`)

```python
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
```

---

## Implementation Steps

### Step 1 — Add `python-multipart` dependency

```
uv add python-multipart
```

Update `pyproject.toml` and lock file.

### Step 2 — `api/dependencies.py`

- `_build_pronunciation_provider()` — reads `PRONUNCIATION_PROVIDER`, `AZURE_SPEECH_KEY`,
  `AZURE_SPEECH_REGION` env vars; returns `AzurePronunciationProvider` (only Azure
  supported for now; raise `RuntimeError` if vars missing).
- `_build_llm_provider()` — reads `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`,
  `LLM_BASE_URL`, `ENABLE_LLM`; returns `OpenAILLMProvider` or a no-op stub
  (raise `RuntimeError` if key missing when enabled).
- `get_pronunciation_service()` — cached singleton factory (via `functools.lru_cache`),
  returns a `PronunciationService` wired from the above.
- Exposed as FastAPI `Depends(get_pronunciation_service)` on the endpoint.

### Step 3 — `api/analyze.py`

```python
router = APIRouter()

MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_TEXT_CHARS = 500
ALLOWED_CONTENT_TYPES = {"audio/wav", "audio/wave", "audio/webm", "audio/x-wav"}
ANALYZE_TIMEOUT_SECONDS = 10.0

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    audio_file: UploadFile,
    expected_text: Annotated[str, Form()],
    service: Annotated[PronunciationService, Depends(get_pronunciation_service)],
) -> AnalyzeResponse:
    ...
```

Validation:
- `expected_text` empty or > 500 chars → `HTTPException(400)`
- `audio_file` content_type not in allowed set → `HTTPException(400)`
- Audio bytes > 10 MB → `HTTPException(400)`

Pipeline call wrapped in `asyncio.wait_for(asyncio.to_thread(...), timeout=10.0)`:
- `asyncio.TimeoutError` → `HTTPException(504)`
- `PronunciationError` or `LLMFeedbackError` → `HTTPException(422)`

### Step 4 — `api/main.py`

Include the analyze router:
```python
from api.analyze import router as analyze_router
app.include_router(analyze_router)
```

### Step 5 — `tests/test_analyze_endpoint.py`

Tests (all use `TestClient` with fully mocked `PronunciationService`):

| Test | What it checks |
|------|----------------|
| `test_analyze_happy_path` | 200 with valid WAV + text, asserts score/words/suggestions keys |
| `test_analyze_missing_text` | 400 when expected_text is empty |
| `test_analyze_text_too_long` | 400 when expected_text > 500 chars |
| `test_analyze_wrong_content_type` | 400 for `image/png` content-type |
| `test_analyze_audio_too_large` | 400 when file > 10 MB |
| `test_analyze_pipeline_failure` | 422 when service raises PronunciationError |
| `test_analyze_timeout` | 504 when service exceeds 10 s |
| `test_analyze_llm_failure` | 422 when service raises LLMFeedbackError |

---

## Definition of Done

- [ ] All 8 planned test cases pass (`uv run pytest`)
- [ ] No domain layer imports from `api/` or `providers/`
- [ ] Typing is complete (no untyped functions)
- [ ] `python-multipart` added to `pyproject.toml`
- [ ] `uv run pytest` passes (all existing tests still green)
- [ ] Plan steps are all implemented
