---
name: Architecture - Read & Improve
description: >
  Living architecture document. Records layer boundaries, patterns in use,
  and decisions made as the project evolves. Update this when a decision is made,
  not after the fact.
---

# Architecture - Read & Improve

This document is intentionally minimal. It records decisions already made and flags
things still being decided. It is not a full spec — see [mvp_prd.md](mvp_prd.md) for that.

---

## Layer Boundaries (Clean Architecture)

```
┌─────────────────────────────────────────┐
│  api/          FastAPI routes, DTOs      │
├─────────────────────────────────────────┤
│  providers/    External service impls    │  ← implements interfaces from core/
├─────────────────────────────────────────┤
│  core/                                   │
│    interfaces/   Abstract base classes   │
│    services/     Use cases / app logic   │
│    models/       Domain data models      │
└─────────────────────────────────────────┘
```

**Hard rule:** `core/` has zero imports from `providers/` or `api/`.
All cross-boundary calls go through abstract interfaces defined in `core/interfaces/`.

---

## Patterns in Use

### Interfaces
Defined as Python abstract base classes (`ABC`) in `core/interfaces/`.
Each provider implements exactly one interface.
Provider selection happens via env var (e.g. `STT_PROVIDER=deepgram`).

### Data Models
Plain Python `@dataclass` — no Pydantic in domain models.
Pydantic is used only at the API boundary (request/response serialization).

### Testing
- Unit tests mock external SDKs; no real API calls.
- Live tests (require real keys) are marked with `@pytest.mark.live` and run separately.
- Test file naming: `test_<module>.py`, live variant: `test_<module>_live.py`.

### Environment
- `uv` for dependency management (`pyproject.toml`, `.python-version`).
- Config via `.env` (loaded with `python-dotenv`). `.env.example` is the source of truth for required keys.

---

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend framework | FastAPI | Async, typed, easy to test |
| Package manager | uv | Fast, deterministic, replaces pip+venv |
| Primary analysis provider | Azure Cognitive Services PA | Returns STT + word accuracy + phoneme scores in one call — needed for per-phoneme feedback |
| STT fallback provider | Deepgram | Free tier, word-level confidence; used when Azure is not configured (no phoneme data) |
| LLM provider | OpenAI gpt-4o-mini | Structured output support; prompt includes phoneme scores when available |
| Pipeline data model | PronunciationResult (single) | Azure PA returns PronunciationResult directly; Deepgram TranscriptionResult is adapted by service layer |
| Domain models | dataclasses | No validation overhead in core layer |
| Frontend framework | Next.js (App Router) | TBD — not started yet |

---

## Open / To Be Decided

- How the frontend calls the backend (REST vs WebSocket for streaming audio)
- Error response schema for the API (problem+json vs custom)
- Frontend state management (if needed beyond RSC)
