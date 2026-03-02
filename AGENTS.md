---
name: AGENTS.md
description: >
  AI agent workflow definition for the Read & Improve project.
  Applies to GitHub Copilot, Claude Code, OpenAI Codex, and any AI coding agent.
  This is the single source of truth for how agents operate in this repository.
---

# Agent Workflow - Read & Improve

This file defines how AI agents must operate in this repository.
All agents (GitHub Copilot, Claude, OpenAI Codex, and others) must follow this workflow.

---

## Repository Context

- **Project:** Read & Improve - AI Pronunciation Feedback MVP
- **Stack:** Python/FastAPI (backend) + Next.js (frontend)
- **Architecture:** Clean Architecture - domain layer has zero provider dependencies
- **PRD:** [docs/mvp_prd.md](docs/mvp_prd.md)
- **Feature list:** [docs/features.md](docs/features.md)

---

## Core Principle

> Never implement without a reviewed plan.
> Never plan without sufficient context (research first if needed).
> Work in isolation using git worktrees.
> One feature = one PR. Each phase = one commit.
> Only humans merge PRs.

---

## Feature Lifecycle

Every feature goes through these phases **in order**:

`
[1] ASSESS - decide if research is needed
      |
      +-- research needed --> [2] RESEARCH -> commit research/<slug>.md
      |                            |
      +-- well-defined    ---------+
                                   |
                              [3] PLAN -> commit plan/<slug>.md (same PR)
                                   |
                              Human reviews plan -> approves
                                   |
                              [4] IMPLEMENT -> code commits in same worktree (same PR)
                                   |
                              Human reviews -> requests changes or approves
                                   |
                              [5] MERGE (human only) -> cleanup worktree
`

---

## Phase 0: Setup - Create Worktree

Before any work begins, create an isolated git worktree for the feature.

`Bash
# From the main repo root
git worktree add ../worktrees/<slug> -b feat/<slug>
cd ../worktrees/<slug>
`

All work for the feature happens inside this worktree.

---

## Phase 1: Assess - Research or Skip?

**Do research when:**
- The feature involves an external API or library not yet used in the codebase
- There are multiple valid implementation approaches with real trade-offs
- The feature touches architectural decisions (new interface, new data model)
- The implementation approach is not obvious from the PRD + existing code

**Types of research - use whichever applies (can combine both):**
- **Web research** (fetch official docs, SDK references, GitHub examples, changelogs):
  use when the feature requires an external API, third-party library, or protocol
  not yet used in the codebase. Fetch the relevant docs and summarize findings.
- **Local file research** (read existing codebase with file/grep tools):
  use when the feature extends or modifies an existing pattern, interface, or service
  already in the repo. Always do this before planning to avoid duplicating or
  conflicting with existing code.

**Skip research when:**
- The feature is fully specified in [docs/features.md](docs/features.md) with a clear scope
- The implementation follows a pattern already established in the codebase
- You can write a complete, confident plan without additional information

If you skip research, state explicitly in the PR description **why research was not needed**.

---

## Phase 2: Research (when required)

Create 
esearch/<slug>.md and commit it.

**research/<slug>.md must include:**
- Why this research was needed (one sentence)
- Options considered (list each with pros/cons)
- Recommended approach with rationale
- Key risks or unknowns
- References (official docs, repos, articles)

**Agent actions:**
1. Create research/<slug>.md with the required content
2. Commit: git commit -m "research(<slug>): add research document"
3. Push and open a **draft PR** titled: [<FEATURE-ID>] <Feature Name>
4. PR description must say: "Research complete. Awaiting human review before planning."
5. Wait for human to review. Human will say: "looks good, make the plan" or give feedback.

---

## Phase 3: Plan

Create plan/<slug>.md in the **same PR branch** as research (or as the first commit if research was skipped).

**plan/<slug>.md must include:**

`markdown
# Plan: <Feature Name> (<Feature ID>)

## Goal
One sentence: what this feature achieves.

## Scope
**In scope:**
- ...

**Out of scope (this PR):**
- ...

## Files to Create or Modify
- backend/core/interfaces/stt.py - create
- backend/providers/deepgram.py - create
- backend/tests/test_deepgram.py - create

## Interfaces and Data Models
Define any new interfaces, abstract classes, or data models with their signatures.

## Implementation Steps
Ordered list of what to build, step by step.
1. ...
2. ...

## Test Cases
What pytest tests will validate this feature as complete:
- test_transcribe_returns_result_with_text()
- test_transcribe_raises_on_empty_audio()
- ...

## Definition of Done
- [ ] All planned test cases pass (pytest)
- [ ] No domain layer imports provider code
- [ ] Typing is complete (no untyped functions)
- [ ] Plan steps are all implemented
`

**Agent actions:**
1. Create plan/<slug>.md in the same worktree
2. Commit: git commit -m "plan(<slug>): add implementation plan"
3. Push to the open PR.
4. Update PR description: "Plan added. Awaiting human review before implementation."
5. Wait. Human will review and say "implement it" or give feedback.

---

## Phase 4: Implementation

Triggered by human saying: "implement it" or "go ahead".

**Agent actions:**
1. Work inside the existing worktree (already set up).
2. Follow the plan steps in order.
3. Commit after each logical step:
   git commit -m "feat(<slug>): <what was done in this step>"
4. Before the final commit, run all tests:
   `Bash
   cd backend && uv run pytest
   `
5. If tests pass, final commit:
   git commit -m "feat(<slug>): implementation complete, all tests passing"
6. Push. Convert the PR from **draft to ready for review**.
7. Update PR description with: summary of what was implemented + test results.

**Rules during implementation:**
- Do NOT deviate from the plan without flagging it as a PR comment explaining why.
- If a blocker is found mid-implementation, commit what exists, push, and describe
  the blocker in a PR comment. Do not silently abandon steps.
- Do NOT modify files outside the feature scope without explicit human approval.
- Do NOT close or remove the worktree until the human approves and merges the PR.

---

## Phase 5: Human Review and Merge

- Human reviews the PR.
- If changes are requested: human describes them, agent applies them in the same
  worktree, commits, and pushes.
- Once the human approves and merges:

`Bash
# Cleanup worktree after merge
git worktree remove ../worktrees/<slug>
git branch -d feat/<slug>
`

---

## Commit Message Convention

`
<type>(<slug>): <short description (imperative, lowercase)>

Types:
  research  - research document added or updated
  plan      - plan document added or updated
  feat      - feature implementation code
  fix       - bug fix
  test      - test additions or changes only
  refactor  - code restructure without behavior change
  chore     - tooling, deps, config, env files
`

Examples:
`
research(deepgram-stt-provider): add research document
plan(deepgram-stt-provider): add implementation plan
feat(deepgram-stt-provider): define SpeechToTextProvider interface
feat(deepgram-stt-provider): implement DeepgramSTTProvider
feat(deepgram-stt-provider): implementation complete, all tests passing
`

---

## PR Convention

- **Title:** [<FEATURE-ID>] <Feature Name> - e.g. [F-002] Deepgram STT Provider
- **Branch:** Feat/<slug> - e.g. Feat/deepgram-stt-provider
- **Status:** Draft during research + plan phases; Ready for Review after implementation
- **One PR per feature** - never bundle multiple features
- **PR description** must be updated at each phase transition

---

## Worktree Commands Reference

`Bash
# Create worktree for a new feature
git worktree add ../worktrees/<slug> -b feat/<slug>

# List all active worktrees
git worktree list

# Remove after merge
git worktree remove ../worktrees/<slug>
git branch -d feat/<slug>
`

Worktrees are created in ../worktrees/ (outside the main repo folder).

---

## Backend Commands Reference

`Bash
# Install dependencies (first time or after pyproject.toml changes)
cd backend
uv sync

# Run the API server
uv run uvicorn api.main:app --reload

# Run all tests
uv run pytest

# Run a specific test file
uv run pytest tests/test_stt.py -v
`

---

## Project Structure Reference

`
english-app/
├── backend/
│   ├── core/
│   │   ├── interfaces/       # Abstract interfaces: SpeechToTextProvider, LLMProvider
│   │   ├── services/         # Application services / use cases
│   │   └── models/           # Domain data models (dataclasses / pydantic)
│   ├── providers/            # Concrete implementations: Deepgram, OpenAI, etc.
│   ├── api/                  # FastAPI routes and app setup
│   └── tests/                # pytest tests
├── frontend/                 # Next.js (App Router)
├── docs/                     # PRD, feature list
├── research/                 # Per-feature research: research/<slug>.md
├── plan/                     # Per-feature plans: plan/<slug>.md
└── AGENTS.md                 # This file
`

---

## What Agents Must NOT Do

- Do NOT implement without a plan/<slug>.md that the human has reviewed
- Do NOT commit directly to main
- Do NOT bundle multiple features in one PR
- Do NOT skip the worktree setup
- Do NOT modify files outside the feature scope without flagging it
- Do NOT merge PRs - only humans merge
- Do NOT remove the worktree until after the human merges the PR
- Do NOT silently deviate from the plan - flag deviations as PR comments