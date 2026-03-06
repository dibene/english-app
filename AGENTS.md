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

## Handling Blockers and Problems

**CRITICAL RULE: When you encounter a blocker, error, or problem that prevents you from continuing, you MUST:**

1. **STOP immediately** - do not try alternative solutions without human approval
2. **COMMIT and PUSH** what exists so far (if anything was done)
3. **EXPLICITLY NOTIFY the human** with a clear message like:

   > "❌ BLOCKER ENCOUNTERED
   >
   > **Problem:** [exact error or issue]
   >
   > **What I tried:** [command/action that failed]
   >
   > **What's needed to proceed:** [missing tool, auth, permission, etc.]
   >
   > **Options to resolve:**
   > 1. [Option 1]
   > 2. [Option 2]
   > 3. [Option 3]
   >
   > How would you like to proceed?"

4. **WAIT for human response** - do not assume what they want

**Examples of blockers that require human notification:**
- Missing authentication (GitHub, API keys, etc.)
- Missing tools or dependencies (not installed, wrong version)
- Permission errors (file system, git, etc.)
- Ambiguous requirements (multiple valid approaches)
- External service failures (API down, network issues)
- Test failures that require architectural decisions
- Conflicts with existing code that require human judgment

**What NOT to do:**
- ❌ Try to work around the problem silently
- ❌ Skip steps without notifying
- ❌ Present options after the fact as if work was done
- ❌ Assume what the human wants without asking

**What TO do:**
- ✅ Be explicit about what's blocking you
- ✅ Provide clear options with trade-offs
- ✅ Wait for human decision before proceeding
- ✅ Save progress (commit/push) before waiting

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

**Worktree Strategy:**
- Every feature runs in its own git worktree, isolated from the main checkout
- Worktrees live in a sibling directory: `../english-app-worktrees/`
- All file operations, git commands, and tests run inside the worktree
- **Never run commands from the main repo after worktree is created**

**Setup steps:**

1. **Resolve paths dynamically** (run once at workflow start):
   ```bash
   # Get absolute path to main repo
   REPO_ROOT=$(git rev-parse --show-toplevel)

   # Compute worktrees base directory (sibling to main repo)
   WORKTREES_BASE=$(dirname "$REPO_ROOT")/english-app-worktrees

   # Create base directory if it doesn't exist
   mkdir -p "$WORKTREES_BASE"
   ```

2. **Create the worktree** (from main repo, only once):
   ```bash
   # Pull latest main
   git -C "$REPO_ROOT" fetch origin
   git -C "$REPO_ROOT" checkout main && git -C "$REPO_ROOT" pull

   # Create worktree with feature branch
   git -C "$REPO_ROOT" worktree add "$WORKTREES_BASE/<slug>" -b feat/<slug>

   # Set worktree path for all subsequent operations
   WORKTREE_PATH="$WORKTREES_BASE/<slug>"
   ```

3. **Verify the worktree**:
   ```bash
   git -C "$WORKTREE_PATH" status
   # Should show: On branch feat/<slug>, nothing to commit, working tree clean
   ```

**CRITICAL: From this point forward, ALL work happens inside `$WORKTREE_PATH`.**
- All file reads/writes use absolute paths inside `$WORKTREE_PATH`
- All git commands use `git -C "$WORKTREE_PATH"` syntax
- All test/build commands run with `$WORKTREE_PATH` as working directory
- Never `cd` back to `$REPO_ROOT` during the feature workflow

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
1. Create `$WORKTREE_PATH/research/<slug>.md` with the required content
2. Commit and push from worktree:
   ```bash
   git -C "$WORKTREE_PATH" add research/<slug>.md
   git -C "$WORKTREE_PATH" commit -m "research(<slug>): add research document"
   git -C "$WORKTREE_PATH" push -u origin feat/<slug>
   ```
3. Open a **draft PR** titled: [<FEATURE-ID>] <Feature Name>
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
1. Create `$WORKTREE_PATH/plan/<slug>.md` in the same worktree
2. Commit and push from worktree:
   ```bash
   git -C "$WORKTREE_PATH" add plan/<slug>.md
   git -C "$WORKTREE_PATH" commit -m "plan(<slug>): add implementation plan"
   git -C "$WORKTREE_PATH" push
   ```
3. Update PR description: "Plan added. Awaiting human review before implementation."
4. Wait. Human will review and say "implement it" or give feedback.

---

## Phase 4: Implementation

Triggered by human saying: "implement it" or "go ahead".

**Agent actions:**
1. Work inside the existing worktree (already set up in Phase 0).
2. Follow the plan steps in order.
3. Commit after each logical step:
   ```bash
   git -C "$WORKTREE_PATH" add <files>
   git -C "$WORKTREE_PATH" commit -m "feat(<slug>): <what was done in this step>"
   git -C "$WORKTREE_PATH" push
   ```
4. Before the final commit, run all tests from worktree:
   ```bash
   cd "$WORKTREE_PATH/backend" && uv run pytest
   ```
5. If tests pass, final commit:
   ```bash
   git -C "$WORKTREE_PATH" add -A
   git -C "$WORKTREE_PATH" commit -m "feat(<slug>): implementation complete, all tests passing"
   git -C "$WORKTREE_PATH" push
   ```
6. Convert the PR from **draft to ready for review**.
7. Update PR description with: summary of what was implemented + test results.
8. **Remove the worktree** — human will review via `git checkout`, not from the worktree:
   ```bash
   git -C "$REPO_ROOT" worktree remove "$WORKTREES_BASE/<slug>"
   ```

**Rules during implementation:**
- Do NOT deviate from the plan without flagging it as a PR comment explaining why.
- If a blocker is found mid-implementation, commit what exists, push, and describe
  the blocker in a PR comment. Do not silently abandon steps.
- Do NOT modify files outside the feature scope without explicit human approval.
- Do NOT close or remove the worktree until the human approves and merges the PR.

---

## Phase 5: Human Review and Merge

- Once the PR is marked ready for review, **remove the worktree immediately**:

```bash
git -C "$REPO_ROOT" worktree remove "$WORKTREES_BASE/<slug>"
```

- The human reviews and tests by checking out the feature branch normally:

```bash
git fetch origin
git checkout feat/<slug>
cd backend
uv sync
uv run pytest
uv run pytest -m live   # if live tests exist
```

- If changes are requested: human describes them, agent creates a new worktree on the same branch, applies the changes, commits, pushes, and removes the worktree again.
- Once the human approves and merges:

```bash
# On main, after merge: delete the remote-tracking branch
git fetch --prune
git branch -d feat/<slug>   # if not already deleted
```

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

```bash
# Setup: Resolve paths dynamically (do once per feature)
REPO_ROOT=$(git rev-parse --show-toplevel)
WORKTREES_BASE=$(dirname "$REPO_ROOT")/english-app-worktrees
mkdir -p "$WORKTREES_BASE"

# Create worktree for a new feature
git -C "$REPO_ROOT" worktree add "$WORKTREES_BASE/<slug>" -b feat/<slug>
WORKTREE_PATH="$WORKTREES_BASE/<slug>"

# List all active worktrees
git worktree list

# Work inside the worktree (all git commands use -C)
git -C "$WORKTREE_PATH" status
git -C "$WORKTREE_PATH" add <files>
git -C "$WORKTREE_PATH" commit -m "message"
git -C "$WORKTREE_PATH" push

# Remove after merge
git -C "$REPO_ROOT" worktree remove "$WORKTREES_BASE/<slug>"
git -C "$REPO_ROOT" branch -d feat/<slug>
```

**Worktrees are created in `../english-app-worktrees/` (sibling to main repo).**

**Key principle**: Use `git -C "$WORKTREE_PATH"` for all git commands to be explicit about the working directory. Never rely on `cd` alone.

---

## Backend Commands Reference

```bash
# Install dependencies (first time or after pyproject.toml changes)
cd "$WORKTREE_PATH/backend"
uv sync

# Run the API server
uv run uvicorn api.main:app --reload

# Run all tests
uv run pytest

# Run a specific test file
uv run pytest tests/test_stt.py -v
```

**All backend commands run from `$WORKTREE_PATH/backend` directory.**

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
- Do NOT keep the worktree after the PR is marked ready — remove it immediately so the human reviews via `git checkout`
- Do NOT silently deviate from the plan - flag deviations as PR comments
