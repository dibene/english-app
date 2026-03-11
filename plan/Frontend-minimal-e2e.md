# Plan: Minimal End-to-End Flow (F-006)

## Goal

A single Next.js page where the user types a sentence, records audio, submits to
`POST /analyze`, and sees the raw JSON response — confirming the full pipeline works
end-to-end.

## Scope

**In scope:**
- Typed API client in `lib/api.ts`: `analyze(audio: Blob, sentence: string) → AnalyzeResponse`
- `app/page.tsx`: single-page UI with textarea, record button, and raw JSON output
- Record button state machine: idle → recording → processing → done
- `NEXT_PUBLIC_API_URL` env var consumed in `lib/api.ts`; `frontend/.env.local.example` updated
- Graceful error display for: mic permission denied, unsupported browser, backend unreachable, CORS failure

**Out of scope (this PR):**
- Sentence splitting (F-007)
- Styled feedback panel (F-007)
- Any backend changes

## Audio Recording Decision: Native MediaRecorder (no RecordRTC)

Native `MediaRecorder` is sufficient for the MVP:
- Supported in all modern browsers (Chrome, Firefox, Safari 14.1+, Edge)
- Produces `audio/webm` by default in Chromium/Firefox — the backend already accepts `audio/webm`
- Zero extra dependencies
- RecordRTC would add ~300 KB to the bundle with no benefit at this stage

The only edge case is Safari on iOS 14.0 and below — out of scope for MVP.

## Files to Create or Modify

- `frontend/lib/api.ts` — implement `analyze()` client, typed `AnalyzeResponse`
- `frontend/app/page.tsx` — replace static heading with full UI
- `frontend/.env.local.example` — add `NEXT_PUBLIC_API_URL=http://localhost:8000`

No new package dependencies required (native MediaRecorder, native fetch).

## Interfaces and Data Models

Types to define in `lib/api.ts`, matching the backend's `AnalyzeResponse` exactly:

```typescript
export interface PhonemeScore {
  phoneme: string;
  score: number;
}

export interface WordOut {
  expected_word: string | null;
  spoken_word: string | null;
  status: string;
  confidence: number | null;
  expected_phonemes: string[] | null;
  phoneme_scores: PhonemeScore[] | null;
}

export interface AnalyzeResponse {
  score: number;
  words: WordOut[];
  suggestions: string[];
}

export async function analyze(
  audio: Blob,
  sentence: string,
): Promise<AnalyzeResponse>
```

The function builds a `FormData` with fields `audio_file` (Blob) and `expected_text`
(string), POSTs to `${API_URL}/analyze`, and throws a descriptive `Error` on non-2xx.

## Implementation Steps

1. **`lib/api.ts`**: export types + implement `analyze()` — replaces the placeholder.
2. **`app/page.tsx`**: implement `RecorderPage` component:
   - `useRef<MediaRecorder>` + `useRef<Blob[]>` to collect chunks
   - `useState` for `status: 'idle' | 'recording' | 'processing' | 'done' | 'error'`
   - `useState` for `result: AnalyzeResponse | null` and `errorMsg: string | null`
   - `startRecording()`: `navigator.mediaDevices.getUserMedia({ audio: true })` →
     `new MediaRecorder(stream)` → push chunks on `ondataavailable` → set status
   - `stopRecording()`: calls `recorder.stop()`, in `onstop` assembles `Blob`,
     calls `analyze()`, sets result or errorMsg
   - Render: textarea, record/stop button, status indicator, raw JSON pre-block or error
3. **`.env.local.example`**: add `NEXT_PUBLIC_API_URL=http://localhost:8000`

## Error Handling

| Scenario | Behavior |
|----------|----------|
| `getUserMedia` permission denied | Catch `NotAllowedError`, set errorMsg |
| `getUserMedia` not available | Catch `NotFoundError` / `TypeError`, set errorMsg |
| `analyze()` throws (network/CORS/4xx/5xx) | Catch in `onstop`, set errorMsg |
| Backend returns non-200 | `analyze()` throws with status + body detail |

## Definition of Done

- [ ] `analyze()` is typed and sends correct multipart/form-data to backend
- [ ] Record → stop → submit flow works against the real local backend
- [ ] Raw JSON response (or clear error message) is displayed
- [ ] Mic permission denied shows a helpful message (not a crash)
- [ ] `NEXT_PUBLIC_API_URL` is consumed from env; `.env.local.example` documents it
- [ ] `npm run build` passes without TypeScript errors
