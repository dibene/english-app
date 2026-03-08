# Plan: LLM Feedback Generator (F-003)

## Goal
Define an abstract `LLMProvider` interface and implement it with OpenAI `gpt-4o-mini` to
generate structured pronunciation feedback (score, errors, suggestions) from an expected
text and a `DiffResult`.

## Scope

**In scope:**
- Abstract `LLMProvider` in `backend/core/interfaces/llm.py`
- `OpenAILLMProvider` in `backend/providers/openai_llm.py`
- `LLMFeedbackError` domain exception in `backend/core/exceptions.py`
- `openai` added as a project dependency (`uv add openai`)
- Provider selected via env var `LLM_PROVIDER=openai`
- Prompt includes: expected text, per-word diff status, confidence, and phoneme scores when available
- Validate response is JSON and matches feedback schema before returning
- Unit tests in `backend/tests/test_openai_llm.py` (mock OpenAI, no real API call)

**Out of scope (this PR):**
- Wiring into `PronunciationService` (that belongs to F-004)
- Other LLM providers (local Ollama, etc. — deferred per feature list)
- Streaming responses
- Prompt engineering beyond the required fields

## Files to Create or Modify

| File | Action |
|------|--------|
| `backend/core/interfaces/llm.py` | create |
| `backend/providers/openai_llm.py` | create |
| `backend/core/exceptions.py` | modify — add `LLMFeedbackError` |
| `backend/tests/test_openai_llm.py` | create |
| `backend/pyproject.toml` | modify — add `openai` dependency |

## Interfaces and Data Models

### LLMProvider (abstract interface)

```python
class LLMProvider(ABC):
    @abstractmethod
    def generate_feedback(self, expected_text: str, diff_result: DiffResult) -> dict:
        """Generate pronunciation feedback JSON.

        Args:
            expected_text: The sentence the user was supposed to pronounce.
            diff_result: Word-level comparison result from TextComparisonEngine.

        Returns:
            dict with keys: score (int 0-100), errors (list[dict]), suggestions (list[str])

        Raises:
            LLMFeedbackError: If the LLM call fails or returns invalid JSON.
        """
```

### Feedback schema (returned dict)

```python
{
    "score": int,           # 0-100
    "errors": [
        {
            "word": str,
            "issue": str,   # e.g. "mispronounced", "missing", "inserted"
            "suggestion": str
        }
    ],
    "suggestions": [str]    # 1-3 overall improvement tips
}
```

### New domain exception

```python
class LLMFeedbackError(Exception):
    """Raised when LLM feedback generation fails."""
```

## Implementation Steps

1. Add `openai` to `backend/pyproject.toml` dependencies and `uv sync`
2. Add `LLMFeedbackError` to `backend/core/exceptions.py`
3. Create `backend/core/interfaces/llm.py` with abstract `LLMProvider`
4. Create `backend/providers/openai_llm.py`:
   - `__init__(self, api_key: str, model: str = "gpt-4o-mini")`
   - Validate `api_key` non-empty in `__init__`
   - Build a structured system prompt (role: pronunciation coach)
   - Build user prompt from `expected_text` + serialised `DiffResult` entries
     (word, status, confidence, phoneme_scores if present)
   - Call `openai.OpenAI(api_key=...).chat.completions.create(...)` with
     `response_format={"type": "json_object"}`
   - Parse JSON, validate schema: `score` is int 0-100, `errors` is list, `suggestions` is list
   - Raise `LLMFeedbackError` on API error, JSON parse error, or schema violation
5. Create `backend/tests/test_openai_llm.py` (see test cases below)

## Test Cases

| Test | What it validates |
|------|------------------|
| `test_missing_api_key_raises_value_error` | Empty `api_key` → `ValueError` |
| `test_whitespace_api_key_raises_value_error` | Whitespace `api_key` → `ValueError` |
| `test_generate_feedback_returns_valid_schema` | Happy path: mock returns valid JSON → correct dict |
| `test_generate_feedback_score_is_int` | `score` field is `int` |
| `test_generate_feedback_errors_is_list` | `errors` field is a `list` |
| `test_generate_feedback_suggestions_is_list` | `suggestions` field is a `list` |
| `test_generate_feedback_includes_diff_context` | Prompt sent to OpenAI contains expected_text |
| `test_openai_api_error_raises_llm_feedback_error` | SDK raises → `LLMFeedbackError` |
| `test_invalid_json_response_raises_llm_feedback_error` | Non-JSON response → `LLMFeedbackError` |
| `test_missing_score_field_raises_llm_feedback_error` | JSON missing `score` → `LLMFeedbackError` |
| `test_score_out_of_range_raises_llm_feedback_error` | `score=150` → `LLMFeedbackError` |

## Definition of Done

- [ ] All planned test cases pass (`uv run pytest tests/test_openai_llm.py -v`)
- [ ] No domain layer imports provider code
- [ ] `LLMProvider` and `OpenAILLMProvider` are fully type-annotated
- [ ] Research was not needed — pattern follows existing STT and PA providers exactly
- [ ] Plan steps are all implemented
