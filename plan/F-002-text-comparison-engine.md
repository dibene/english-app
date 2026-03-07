# Plan: Text Comparison Engine (F-002)

## Goal
Implement a pure Python module that diffs expected text against a TranscriptionResult and classifies each word as ok, missing, inserted, or mispronounced.

## Scope
**In scope:**
- `DiffEntry` and `DiffResult` dataclasses in `backend/core/models/diff.py`
- `TextComparisonEngine` class in `backend/core/services/text_comparison.py`
- Full unit tests in `backend/tests/test_text_comparison.py`

**Out of scope (this PR):**
- HTTP API exposure of comparison results
- Integration with STT or LLM
- Phoneme-level analysis

## Files to Create or Modify
- `backend/core/models/diff.py` - create (DiffEntry, DiffResult dataclasses)
- `backend/core/services/text_comparison.py` - create (TextComparisonEngine)
- `backend/tests/test_text_comparison.py` - create (unit tests)

## Interfaces and Data Models

```python
@dataclass
class DiffEntry:
    expected_word: str | None
    spoken_word: str | None
    status: str             # "ok" | "missing" | "inserted" | "mispronounced"
    confidence: float | None

@dataclass
class DiffResult:
    entries: list[DiffEntry]
```

```python
class TextComparisonEngine:
    def __init__(self, mispronounced_threshold: float = 0.7) -> None: ...

    def compare(
        self,
        expected_text: str,
        transcription_result: TranscriptionResult,
    ) -> DiffResult: ...
```

## Implementation Steps
1. Create `DiffEntry` and `DiffResult` dataclasses in `core/models/diff.py`
2. Implement `TextComparisonEngine.compare()` in `core/services/text_comparison.py`:
   a. Normalise `expected_text` (lowercase, strip punctuation) -> list of words
   b. Build a list of `(word, confidence)` from `transcription_result.words`, normalised the same way
   c. Use `difflib.SequenceMatcher` to align the two word sequences
   d. Iterate opcodes and create `DiffEntry` objects:
      - `equal` -> status `ok`
      - `delete` (expected word absent in spoken) -> status `missing`, spoken_word=None
      - `insert` (spoken word not in expected) -> status `inserted`, expected_word=None
      - `replace` -> if spoken word confidence < threshold: `mispronounced`, else `inserted`+`missing`
   e. Return `DiffResult(entries=[...])`
3. Write unit tests covering all classify cases plus edge cases

## Test Cases
- `test_all_words_ok` — perfect match, all entries are `ok`
- `test_missing_word` — expected word absent from spoken output
- `test_inserted_word` — spoken word not in expected text
- `test_mispronounced_word_low_confidence` — word present but confidence < 0.7
- `test_word_above_threshold_not_mispronounced` — confidence >= 0.7, classified ok
- `test_empty_transcription_result` — TranscriptionResult with no words
- `test_expected_text_empty_after_normalization` — expected text is only punctuation
- `test_normalization_strips_punctuation` — "Hello, world!" matches "hello world"
- `test_configurable_threshold` — custom threshold passed to engine

## Definition of Done
- [ ] All planned test cases pass (`uv run pytest`)
- [ ] No domain layer imports provider code
- [ ] Typing is complete (no untyped functions)
- [ ] Plan steps are all implemented
