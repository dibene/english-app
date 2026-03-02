---
name: PRD - Read & Improve - AI Pronunciation Feedback
description: >
  Product Requirements Document for Read & Improve: a web application for English
  learners (A2-B2) to paste text, record audio sentence by sentence, and receive
  automated pronunciation feedback. MVP goal is to validate perceived value of
  instant, personalized feedback on user-provided text.
version: "0.1.0"
status: MVP - in definition
stack:
  frontend: Next.js (App Router)
  backend: Python 3.11+ / FastAPI / uv
  stt_primary: Deepgram (free tier)
  stt_local: faster-whisper (defined, not implemented in MVP)
  llm_primary: OpenAI gpt-4o-mini (free tier / credits)
  llm_local: Ollama / Deepseek (defined, not implemented in MVP)
related:
  - docs/features.md
  - AGENTS.md
---

# Read & Improve - AI Pronunciation Feedback (MVP)

## 1. Executive Summary

Read & Improve is a web-based MVP that allows users to paste any English text,
read it aloud sentence by sentence, and receive automated pronunciation feedback.
The goal is to validate whether instant feedback on user-provided text creates
enough value to justify further development into a scalable pronunciation training product.

This MVP focuses strictly on:
- Text-based reading (user-provided)
- Audio transcription (STT)
- Pronunciation comparison (diff engine)
- Structured JSON feedback (score + errors + suggestions)

No conversation mode, no gamification, no authentication.

## 2. Problem Statement

Self-learners of English lack real-time pronunciation feedback when reading texts
they are personally interested in. Most existing tools:
- Use fixed exercises
- Restrict content input
- Do not allow free text input

This product enables users to practice with any text they choose.

## 3. Target User

- English learners (A2-B2 level)
- Self-directed learners
- Users who read books, articles, or study materials in English
- Users preparing for remote work or interviews

## 4. Product Goal (MVP)

Validate that users perceive meaningful value from immediate pronunciation feedback
when reading arbitrary text.

**Success is defined as:**
- Feedback delivered in < 10 seconds end-to-end
- Clear identification of pronunciation issues
- Actionable improvement suggestions
- System stable under 20 tests/day

## 5. Core User Flow

1. User pastes English text (up to 500 characters).
2. System splits text into sentences.
3. User selects a sentence and records audio.
4. System transcribes audio using STT provider.
5. System compares expected vs. transcription result.
6. System generates structured pronunciation feedback via LLM using the full context.
7. UI displays: overall score, highlighted problematic words, 1-3 suggestions.

## 6. High-Level Data Flow

`
[User] -> pastes text -> [Frontend]
[Frontend] -> selects sentence + records audio
           -> sends (audio_file, expected_text) -> [Backend API]

[Backend] -> SpeechToTextProvider.transcribe(audio) -> TranscriptionResult
             TranscriptionResult: { transcript: str, words: [{ word, confidence, start, end }] }

[Backend] -> ComparisonEngine.compare(expected_text, transcription_result) -> DiffResult
             DiffResult: [{ word, status: missing|inserted|mispronounced|ok, confidence }]

[Backend] -> LLMProvider.generate_feedback(expected_text, transcription_result, diff_result) -> feedback_json
             LLM receives full context: what was expected, what was said (with confidence),
             and the word-level diff - enabling accurate, grounded feedback.

[Backend] -> returns feedback_json -> [Frontend]
[Frontend] -> renders score + highlighted words + suggestions -> [User]
`

**Data Models:**

`python
@dataclass
class WordResult:
    word: str
    confidence: float       # 0.0 - 1.0 (if provided by STT)
    start_time: float | None
    end_time: float | None

@dataclass
class TranscriptionResult:
    transcript: str         # full spoken text
    words: list[WordResult] # word-level detail

@dataclass
class DiffEntry:
    expected_word: str | None
    spoken_word: str | None
    status: str             # "ok" | "missing" | "inserted" | "mispronounced"
    confidence: float | None

@dataclass
class DiffResult:
    entries: list[DiffEntry]
`

**Feedback JSON contract (output schema):**
`json
{
  "score": 82,
  "errors": [
    { "word": "pronunciation", "type": "mispronounced", "spoken_as": "prononciation" },
    { "word": "arbitrary", "type": "missing" }
  ],
  "suggestions": [
    "Focus on the 'tion' ending - it sounds like /shen/.",
    "Try saying each syllable of 'arbitrary' slowly: ar-bi-trar-y."
  ]
}
`

## 7. Functional Requirements

### FR-1: Text Input
- User can paste text up to 500 characters.
- Text is split into sentences for individual recording.
- Input accepts English text including punctuation and numbers.

### FR-2: Audio Recording
- Browser-based recording (Web Audio API).
- Maximum duration: 45 seconds per sentence.
- Audio format: WAV or WebM.

### FR-3: Speech-to-Text (STT)
- Audio transcribed via pluggable STT provider interface (SpeechToTextProvider).
- Primary provider: Deepgram free tier.
- Interface contract: transcribe(audio_bytes) -> TranscriptionResult
- TranscriptionResult includes: full transcript text + word-level confidence per word.
- System must be STT-provider agnostic - local options (faster-whisper) are defined but deferred.

### FR-4: Pronunciation Analysis
- Compare expected text vs. TranscriptionResult using ComparisonEngine -> DiffResult.
- Detect: missing words, inserted words, mispronounced words (wrong word or confidence below threshold).
- LLMProvider receives: expected_text + TranscriptionResult + DiffResult.
- LLM has full context to generate grounded, accurate feedback.
- LLMProvider is provider-agnostic - local LLM (Ollama/Deepseek) deferred to post-MVP.
- Output: feedback JSON schema defined in section 6.

### FR-5: Response Time
- Total processing time must not exceed 10 seconds.

## 8. Out of Scope (MVP)

- Free conversation mode
- Persistent user accounts / auth
- Audio history or replay
- Payments or subscriptions
- Mobile native app
- SEO optimization
- Real-time streaming feedback
- Phoneme-level acoustic analysis
- Local STT / local LLM (interfaces defined; implementations deferred)

## 9. Non-Functional Requirements

- Must run fully locally for MVP (no cloud infrastructure beyond free-tier APIs).
- Cost must remain near zero (free tiers only).
- STT provider must be swappable without touching domain logic.
- LLM provider must be swappable without touching domain logic.
- Codebase uses Clean Architecture: domain layer has zero provider dependencies.

## 10. Technical Stack

| Layer        | Choice                          | Notes                                        |
|--------------|---------------------------------|----------------------------------------------|
| Frontend     | Next.js (App Router)            | TypeScript, React                            |
| Backend      | Python 3.11+ / FastAPI / uv     | Clean Architecture                           |
| Testing      | pytest                          | Backend unit + integration tests             |
| STT          | Deepgram (free tier)            | Primary - abstracted via interface           |
| STT (future) | faster-whisper                  | Local fallback, not in MVP                   |
| LLM          | OpenAI gpt-4o-mini (free tier)  | Primary - abstracted via interface           |
| LLM (future) | Ollama / Deepseek               | Local fallback, not in MVP                   |
| Repo         | Monorepo (backend/ + frontend/) | Single repo, no build tooling needed for MVP |

## 11. Tech Decision Rationale

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend language | Python | Best ecosystem for AI/ML/data libs; deepgram-sdk, openai, ollama SDKs are first-class Python. Avoids JS complexity for an AI-heavy backend. |
| Backend framework | FastAPI | Lightweight, async-native, auto-generates OpenAPI docs. Clean fit with Python dataclasses/Pydantic for the data models in section 6. |
| Package manager | uv | Significantly faster than pip/poetry, zero-config, handles venv + lockfile. |
| Frontend framework | Next.js (App Router) | Preferred over Vite/plain React for scalability: built-in routing, SSR, API routes if needed. More future-proof for a growing product. Vite would be lighter but Next.js costs nothing extra at MVP scale. |
| Repo structure | Monorepo (single repo) | MVP simplicity - no cross-repo linking overhead. backend/ and frontend/ are co-located. Can be split later if needed. No Turborepo/pnpm workspaces - that complexity is deferred. |
| Cost strategy | Free tiers + zero infra | MVP goal is functional validation, not production scale. Deepgram free tier + OpenAI credits covers all testing. Local alternatives (faster-whisper, Ollama) are designed-in but not implemented until free tiers become a constraint. |
| Provider abstraction | Interface-based (Clean Arch) | STT and LLM providers are behind interfaces. Swapping Deepgram for faster-whisper, or OpenAI for Ollama, requires only a new provider class - zero domain changes. |

## 12. Repository Structure

`
english-app/
├── backend/           # Python / FastAPI
│   ├── core/
│   │   ├── interfaces/   # SpeechToTextProvider, LLMProvider (abstract)
│   │   ├── services/     # Use cases / application services
│   │   └── models/       # Domain data models (TranscriptionResult, DiffResult, etc.)
│   ├── providers/     # Concrete implementations: Deepgram, OpenAI, etc.
│   ├── api/           # FastAPI routes
│   └── tests/         # pytest tests
├── frontend/          # Next.js (App Router)
├── docs/              # PRD, feature list
├── research/          # Per-feature research documents
├── plan/              # Per-feature plan documents
└── AGENTS.md          # AI agent workflow definition
`

## 13. Success Criteria

MVP is successful if:
- All pytest tests pass end-to-end with a real audio sample.
- Feedback score and error highlighting feel accurate during manual testing.
- Processing time stays under 10 seconds.
- System remains stable under 20 tests/day.

## 14. Feature List

See [docs/features.md](features.md) for the prioritized atomic feature backlog.