# Plan: Phoneme Preview Before Recording (D-008)

## Goal

Show expected IPA phonemes under each sentence **before** the user records, so they
know how to pronounce each word. Controlled by a "Show phonemes" toggle. Also adds a
persistent IPA reference guide (vowels + consonants with examples).

---

## Scope

**In scope:**
- `POST /phonemes` backend endpoint: accepts a list of words, returns `{ word → IPA[] }` for each word found in CMUdict
- "Show phonemes" toggle in the UI (off by default)
- When enabled: frontend fetches phonemes on load/text-change and renders neutral-grey IPA chips under each sentence row in both `SentenceList` and `BilingualSentenceList`
- New `IPAReference` component: a collapsible/modal IPA guide with vowels and consonants, their IPA symbols, descriptions, and example words

**Out of scope (this PR):**
- Phoneme score colouring during preview (preview is always neutral grey — scoring happens after recording)
- Persisting the toggle preference beyond the page session
- IPA for languages other than English

---

## Files to Create or Modify

| File | Action |
|------|--------|
| `backend/core/services/text_comparison.py` | Add public `get_phonemes_for_words()` helper |
| `backend/api/analyze.py` | Add `PhonemeRequest`, `PhonemeResponse` models + `POST /phonemes` route |
| `backend/tests/test_phonemes_endpoint.py` | Create — unit tests for new endpoint |
| `frontend/lib/api.ts` | Add `getPhonemes()` typed client function |
| `frontend/app/page.tsx` | Add `showPhonemes` toggle, `previewPhonemes` state, `useEffect` for fetch, pass props |
| `frontend/components/SentenceList.tsx` | Accept + render `previewPhonemes` chips |
| `frontend/components/BilingualSentenceList.tsx` | Accept + render `previewPhonemes` chips (English side) |
| `frontend/components/IPAReference.tsx` | Create — full IPA reference guide component |

---

## Interfaces and Data Models

### Backend

```python
# New models in backend/api/analyze.py
class PhonemeRequest(BaseModel):
    words: list[str]      # raw words; endpoint normalises to lowercase

class PhonemeResponse(BaseModel):
    phonemes: dict[str, list[str]]   # word → IPA list; words not in CMUdict omitted
```

### New backend helper in `text_comparison.py`

```python
def get_phonemes_for_words(words: list[str]) -> dict[str, list[str] | None]:
    """Return IPA phonemes for each word; None when not found in CMUdict."""
    return {w: _get_phonemes(w) for w in words}
```

### Frontend

```typescript
// lib/api.ts addition
export async function getPhonemes(
  words: string[]
): Promise<Record<string, string[]>> { ... }

// PhonemeChips props (inline in SentenceList / BilingualSentenceList)
// previewPhonemes: Record<string, string[]>
//   key = lowercase word (no punctuation)
//   value = IPA phoneme array, e.g. ["w", "ɝ", "l", "d"]
```

---

## Implementation Steps

### Step 1 — Backend: expose helper + add route

1. In `backend/core/services/text_comparison.py`:
   - Add `get_phonemes_for_words(words: list[str]) -> dict[str, list[str] | None]` (public)
   - Normalise each word with `_normalize()` before the CMUdict lookup (consistent with existing logic)

2. In `backend/api/analyze.py`:
   - Add `PhonemeRequest` and `PhonemeResponse` Pydantic models
   - Add `POST /phonemes` route:
     - Import `get_phonemes_for_words` from `core.services.text_comparison`
     - Deduplicate incoming words before lookup
     - Return only words that have an entry (omit `None` values)
     - No auth or rate limiting required for MVP (phoneme lookup is a pure dictionary call)

### Step 2 — Backend tests

In `backend/tests/test_phonemes_endpoint.py`:
- `test_phonemes_known_word`: `["world"]` → response contains `"world"` with non-empty IPA list
- `test_phonemes_unknown_word`: `["xyzzy"]` → response `phonemes` is empty `{}`
- `test_phonemes_deduplication`: `["the", "the"]` → only one entry in response
- `test_phonemes_empty_list`: `[]` → `{"phonemes": {}}`
- `test_phonemes_mixed`: `["hello", "xyzzy"]` → only `"hello"` present in response

### Step 3 — Frontend API client

Add to `frontend/lib/api.ts`:
```typescript
export async function getPhonemes(
  words: string[]
): Promise<Record<string, string[]>> {
  const res = await fetch(`${API_URL}/phonemes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ words }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.phonemes as Record<string, string[]>;
}
```

### Step 4 — Frontend page state + fetch

In `frontend/app/page.tsx`:
- Add `showPhonemes` (`boolean`, default `false`) and `previewPhonemes` (`Record<string, string[]>`, default `{}`) states
- Add a `useEffect` that runs when `showPhonemes` is `true` and the sentence list changes:
  - Collect all unique words from all sentences (normalise: lowercase, strip punctuation)
  - Call `getPhonemes(words)` and set `previewPhonemes`
  - When `showPhonemes` flips to `false`, clear `previewPhonemes` to `{}`
- Add a "Show phonemes" toggle button in the toolbar (near the LLM mode selector)
- Pass `showPhonemes` and `previewPhonemes` as props to `SentenceList` and `BilingualSentenceList`

### Step 5 — SentenceList phoneme chips

In `frontend/components/SentenceList.tsx`:
- Add `previewPhonemes?: Record<string, string[]>` prop
- Below each sentence text (before the record button row), if `previewPhonemes` is non-empty:
  - Tokenise the sentence into words (same simple normalise: lowercase, strip common punctuation)
  - For each word that has an entry in `previewPhonemes`, render the IPA phoneme chips inline
  - Each chip: small, neutral grey, rounded — example: `<span class="...">ɝ</span>`
  - Words with no entry render nothing
  - Chips are only shown when `showPhonemes` is truthy (passed in from parent)

### Step 6 — BilingualSentenceList phoneme chips

Same as Step 5 but applied to the English sentence column only.

### Step 7 — IPAReference component

Create `frontend/components/IPAReference.tsx`:
- Renders a button "IPA guide 📖" that toggles a collapsible panel (no modal — simpler, no focus
  trapping needed)
- Panel contains two sections: **Vowels** and **Consonants**
- Each row: IPA symbol | ARPAbet code | description (pronunciation hint) | example word
- Data is static — embedded in the component file
- Full coverage of all 39 ARPAbet phonemes (15 vowels + 24 consonants) using the same
  mapping already in `text_comparison.py`

#### Vowel data (15 entries):

| IPA | ARPAbet | Description | Example |
|-----|---------|-------------|---------|
| ɑ | AA | "ah" open back | *father* |
| æ | AE | short "a" | *cat* |
| ʌ | AH | short "u" | *cup* |
| ə | AH0 | schwa (unstressed) | *about* |
| ɔ | AO | "aw" sound | *law* |
| aʊ | AW | "ow" diphthong | *cow* |
| aɪ | AY | "eye" diphthong | *fly* |
| ɛ | EH | short "e" | *bed* |
| ɝ | ER | "er" r-colored | *bird* |
| eɪ | EY | long "a" | *say* |
| ɪ | IH | short "i" | *bit* |
| i | IY | long "ee" | *beat* |
| oʊ | OW | long "o" | *go* |
| ɔɪ | OY | "oy" diphthong | *boy* |
| ʊ | UH | short "oo" | *book* |
| u | UW | long "oo" | *food* |

#### Consonant data (24 entries):

| IPA | ARPAbet | Description | Example |
|-----|---------|-------------|---------|
| b | B | voiced bilabial stop | *bed* |
| tʃ | CH | affricate | *choose* |
| d | D | voiced alveolar stop | *day* |
| ð | DH | voiced dental fricative | *the* |
| f | F | labiodental fricative | *fat* |
| ɡ | G | voiced velar stop | *get* |
| h | HH | glottal fricative | *he* |
| dʒ | JH | voiced affricate | *judge* |
| k | K | voiceless velar stop | *key* |
| l | L | lateral liquid | *leg* |
| m | M | bilabial nasal | *me* |
| n | N | alveolar nasal | *no* |
| ŋ | NG | velar nasal | *sing* |
| p | P | voiceless bilabial stop | *pet* |
| r | R | approximant | *red* |
| s | S | voiceless alveolar fricative | *sit* |
| ʃ | SH | voiceless palatal fricative | *she* |
| t | T | voiceless alveolar stop | *top* |
| θ | TH | voiceless dental fricative | *thin* |
| v | V | voiced labiodental fricative | *van* |
| w | W | labio-velar approximant | *wet* |
| j | Y | palatal approximant | *yet* |
| z | Z | voiced alveolar fricative | *zip* |
| ʒ | ZH | voiced palatal fricative | *measure* |

---

## Test Cases

### Backend (`test_phonemes_endpoint.py`)
- `test_phonemes_known_word` — `["world"]` → `phonemes["world"]` is a non-empty list
- `test_phonemes_unknown_word` — `["xyzzy"]` → `phonemes` is `{}`
- `test_phonemes_deduplication` — `["the", "the"]` → exactly one key in `phonemes`
- `test_phonemes_empty_list` — `[]` → `phonemes` is `{}`
- `test_phonemes_mixed` — `["hello", "xyzzy"]` → only `"hello"` in `phonemes`

---

## Definition of Done

- [ ] `POST /phonemes` endpoint returns correct IPA for known words, omits unknown words
- [ ] All 5 backend test cases pass
- [ ] No domain layer imports provider code (clean architecture preserved)
- [ ] `getPhonemes()` added to `lib/api.ts` with correct typing
- [ ] "Show phonemes" toggle in page.tsx; off by default
- [ ] IPA chips rendered as neutral grey under sentences in both list components
- [ ] `IPAReference` component renders complete vowel + consonant table
- [ ] No TypeScript errors (`tsc --noEmit`)
- [ ] Frontend builds without errors (`npm run build`)
