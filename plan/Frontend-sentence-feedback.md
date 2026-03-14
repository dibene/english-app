# Plan: Sentence Splitter + Feedback Display UI (F-007)

## Goal
Upgrade the minimal E2E flow with sentence splitting on text input and a styled
feedback panel that replaces the raw JSON dump — showing score, word-level highlighting,
per-phoneme breakdown, suggestions, and a re-record flow.

## Scope

**In scope:**
- Textarea with 500 character limit and live counter
- Sentence splitter: detect sentence boundaries (`.`, `?`, `!`) and show as clickable list
- Sentence list: click to select; selected sentence is highlighted and fed into the recording flow
- Feedback panel replacing raw JSON:
  - Overall score with colour coding (green ≥ 80, yellow 50–79, red < 50)
  - Word row: each word coloured by its `status` (ok / mispronounced / missing / inserted)
  - Per-phoneme row below each word (hidden when both `phoneme_scores` and `expected_phonemes` are absent)
  - Suggestions list
  - Re-record button that resets to idle state for the selected sentence
  - Explicit success state when score is 100 / no errors
- Graceful degradation: phoneme score colouring hidden when `phoneme_scores` is absent (Deepgram fallback)
- Audio preview before sending: after stopping the recorder the audio is held in state; the user can listen, discard and re-record, or confirm and send — using the native `<audio>` element, no extra library

**Out of scope (this PR):**
- Backend changes of any kind
- Multi-sentence batch submission (F-008)
- Keyboard shortcuts, animations, accessibility audit beyond semantic HTML
- Any feature not listed above

## Files to Create or Modify

| File | Action |
|------|--------|
| `frontend/app/page.tsx` | Modify — integrate SentenceList + FeedbackPanel, add 500-char limit |
| `frontend/components/SentenceList.tsx` | Create — sentence splitter + selectable list |
| `frontend/components/FeedbackPanel.tsx` | Create — score, word row, phoneme chips, suggestions |

No new dependencies required — Tailwind provides all needed styling primitives.

## Interfaces and Data Models

These are already defined in `frontend/lib/api.ts` (F-006) and do not change:
```typescript
interface PhonemeScore { phoneme: string; score: number; }
interface WordOut {
  expected_word: string | null;
  spoken_word: string | null;
  status: string;               // "ok" | "mispronounced" | "missing" | "inserted"
  confidence: number | null;
  expected_phonemes: string[] | null;
  phoneme_scores: PhonemeScore[] | null;
}
interface AnalyzeResponse { score: number; words: WordOut[]; suggestions: string[]; }
```

## Sentence Splitting Logic

```typescript
// Split on . ? ! followed by whitespace or end-of-string; trim and drop empties
function splitSentences(text: string): string[] {
  return text
    .split(/(?<=[.?!])\s+/)
    .map(s => s.trim())
    .filter(Boolean);
}
```

Edge cases:
- Single sentence (no punctuation at boundary): return the whole trimmed text as one sentence
- Only whitespace after split: filtered out
- Empty input: return `[]`

## Phoneme Normalisation

```typescript
// Strip ARPAbet stress digits ("ER1" → "er", "AH0" → "ah")
function normalisePhoneme(p: string): string {
  return p.replace(/\d+$/, "").toLowerCase();
}

// Returns true if spoken differs from expected (case-insensitive, stress stripped)
function phonemeDiffers(expected: string, spoken: string): boolean {
  return normalisePhoneme(expected) !== spoken.toLowerCase();
}
```

## Component Design

### `SentenceList`

```
Props:
  text: string              — full textarea content
  selected: number | null   — index of selected sentence
  onChange: (i: number) => void

Renders:
  - If splitSentences(text).length === 0: nothing (parent controls empty state)
  - A list of sentence items; selected one has distinct background + ring
  - Clicking a sentence calls onChange(i)
```

### `FeedbackPanel`

```
Props:
  result: AnalyzeResponse
  onReRecord: () => void    — called when Re-record button is clicked

Renders:
  1. Score badge — number + colour by threshold (green/yellow/red)
     - When score === 100 or no errors: success banner ("Perfect pronunciation!")
  2. Word row — one pill per WordOut:
     - Colour by status: ok=green, mispronounced=yellow, missing=red (greyed out), inserted=blue
     - Below each word: phoneme chips (see below)
  3. Suggestions — bulleted list (hidden if empty)
  4. Re-record button

Phoneme chips (per WordOut):
  - Iterate expected_phonemes[i] in parallel with phoneme_scores[i]
  - Chip label: expected_phonemes[i] (stripped of stress digit)
  - Chip colour: green if score≥80, yellow if 50–79, red if <50
    - If phoneme_scores absent but expected_phonemes present: neutral grey chip, no score colour
    - If both absent: render nothing
  - Below chip (inline, small grey text): phoneme_scores[i].phoneme — only if it differs from expected
```

## Implementation Steps

1. Create `frontend/components/SentenceList.tsx`
   - Pure component; accepts `text`, `selected`, `onChange`
   - Uses `splitSentences()` helper defined in component file
   - Tailwind styling: unselected = `bg-white hover:bg-gray-50`, selected = `bg-blue-50 ring-2 ring-blue-400`

2. Create `frontend/components/FeedbackPanel.tsx`
   - `scoreColour(n)` helper: returns Tailwind class
   - `wordColour(status)` helper
   - `normalisePhoneme()` and `phonemeDiffers()` helpers
   - PhonemeChip is an inline sub-component (not a separate file — it's only used here)
   - Re-record button calls `onReRecord` prop

3. Modify `frontend/app/page.tsx`
   - Add `selectedSentenceIdx` state (`number | null`, default `null`)
   - Add `audioBlob` state (`Blob | null`, default `null`) — holds recorded audio in preview
   - Add `audioUrl` state (`string | null`) — `URL.createObjectURL(blob)`, revoked on cleanup
   - Add `charCount` derived value from textarea value
   - Enforce 500-char limit in `onChange` handler (or show counter + disable submit)
   - Show `SentenceList` below textarea when `sentence.trim()` is non-empty
   - `canRecord` now also requires `selectedSentenceIdx !== null`
   - **Updated state machine:** `idle → recording → preview → processing → done`
     - `recorder.onstop`: save blob + create object URL → set status `"preview"` (do NOT call `analyze()` yet)
     - Preview UI: `<audio controls src={audioUrl} />` + "Send" button + "Re-record" button
     - "Send" → calls `analyze(blob, sentence)` → `"processing"` → `"done"`
     - "Re-record" → revokes object URL, clears `audioBlob`/`audioUrl` → back to `"idle"`
   - Pass `sentences[selectedSentenceIdx]` as `expected_text` to `analyze()`
   - Replace raw JSON block with `<FeedbackPanel result={result} onReRecord={resetToIdle} />`
   - `resetToIdle`: sets `status → "idle"`, clears `result`, `errorMsg`, `audioBlob`, `audioUrl`

## Definition of Done

- [ ] Textarea shows character counter; input beyond 500 chars is rejected
- [ ] Sentences are split and rendered as a clickable list
- [ ] Selecting a sentence highlights it and enables the record button
- [ ] Feedback panel shows score with correct colour coding
- [ ] Word pills render with correct colour per status
- [ ] Phoneme chips render (with score colouring) when Azure data is present
- [ ] Phoneme chips render in neutral grey when `phoneme_scores` is absent
- [ ] "Spoken" phoneme label shown only when it differs from expected
- [ ] Success state shown when score === 100 or no errors
- [ ] After stopping, audio is held in preview state (not auto-sent)
- [ ] Preview shows native `<audio>` player, a "Send" button, and a "Re-record" button
- [ ] "Send" triggers the analyze call and transitions to processing
- [ ] "Re-record" discards the blob and returns to idle
- [ ] Object URL is revoked when no longer needed (no memory leak)
- [ ] Re-record resets to idle for the selected sentence
- [ ] No TypeScript errors (`next build` or `tsc --noEmit` passes)
- [ ] App runs locally and displays correctly in browser
