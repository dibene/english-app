---
name: ship_feature
description: >
  Full lifecycle for shipping a new feature: worktree isolation, research (optional),
  plan, implementation, tests, and PR. Use this when asked to work on a feature from docs/features.md.
---

# Skill: Ship a Feature

Use this skill when the human asks you to work on a feature from the backlog.

**Triggers:** "work on F-XXX", "implement the next feature", "ship [feature name]"

> ⚠️ **Read [skills/git-usage/pr.md](../git-usage/pr.md) before running any `gh` command.**
> ⚠️ **Read [skills/git-usage/commits.md](../git-usage/commits.md) before any commit.**

---

## Context Management — Use Sub-Agents

This workflow involves multiple heavy phases (research, planning, implementation).
To keep the main agent context clean and focused:

- **Delegate exploration work to sub-agents.** Use a sub-agent for:
  - Researching the codebase (reading existing interfaces, services, models)
  - Fetching and summarizing external docs or SDK references
  - Producing the first draft of the plan document
  - Implementing individual plan steps (one sub-agent per step when steps are independent)
- **The main agent** keeps the git state, coordinates phases, commits, pushes, and communicates with the human.
- Sub-agents return results; the main agent writes files and runs git commands.

This prevents context overflow and keeps each phase focused.

---

## Feature Lifecycle

```
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
                              [5] MERGE (human only) -> cleanup
```

---

## Phase 0: Setup - Create Worktree

Before any work begins, create an isolated git worktree.

```bash
# Resolve paths dynamically (run once per feature)
REPO_ROOT=$(git rev-parse --show-toplevel)
WORKTREES_BASE=$(dirname "$REPO_ROOT")/english-app-worktrees
mkdir -p "$WORKTREES_BASE"

# Pull latest main
git -C "$REPO_ROOT" fetch origin
git -C "$REPO_ROOT" checkout main && git -C "$REPO_ROOT" pull

# Create worktree with feature branch
git -C "$REPO_ROOT" worktree add "$WORKTREES_BASE/<slug>" -b feat/<slug>
WORKTREE_PATH="$WORKTREES_BASE/<slug>"

# Verify
git -C "$WORKTREE_PATH" status
# Should show: On branch feat/<slug>, nothing to commit, working tree clean
```

**CRITICAL: From this point forward, ALL work happens inside `$WORKTREE_PATH`.**
- All file reads/writes use absolute paths inside `$WORKTREE_PATH`
- All git commands use `git -C "$WORKTREE_PATH"` syntax
- All test/build commands run with `$WORKTREE_PATH/backend` as working directory

---

## Phase 1: Assess - Research or Skip?

**Do research when:**
- Feature involves an external API or library not yet in the codebase
- Multiple valid implementation approaches with real trade-offs
- Feature touches architectural decisions (new interface, new data model)
- Implementation approach is not obvious from the PRD + existing code

**Types of research — use whichever applies (can combine both):**
- **Web research**: fetch official docs, SDK references, GitHub examples, changelogs
- **Local file research**: read the existing codebase to understand patterns before changing them

**Skip research when:**
- Feature is fully specified in `docs/features.md` with clear scope
- Implementation follows a pattern already established in the codebase
- You can write a confident, complete plan without additional information

If you skip research, state explicitly in the PR description why it was not needed.

---

## Phase 2: Research (when required)

Create `research/<slug>.md` and commit it.

**`research/<slug>.md` must include:**
- Why this research was needed (one sentence)
- Options considered (each with pros/cons)
- Recommended approach with rationale
- Key risks or unknowns
- References (official docs, repos, articles)

**Agent actions:**

```bash
# Create the file, then commit
git -C "$WORKTREE_PATH" add research/<slug>.md
git -C "$WORKTREE_PATH" commit --no-verify -m "research(<slug>): add research document"
git -C "$WORKTREE_PATH" push -u origin feat/<slug>

# Open draft PR (read skills/git-usage/pr.md for gh command details)
gh pr create --repo dibene/english-app \
  --title "[F-XXX] Feature Name" \
  --body "Research complete. Awaiting human review before planning." \
  --draft --base main --head feat/<slug>
```

**WAIT** for human to review. Human will say "looks good, make the plan" or give feedback.

> 🔴 **CRITICAL: Do NOT proceed to Phase 3 until the human explicitly approves the research.**

---

## Phase 3: Plan

Create `plan/<slug>.md` in the same PR branch (or as the first commit if research was skipped).

**`plan/<slug>.md` must include:**

```markdown
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
- backend/providers/deepgram_stt.py - create
- backend/tests/test_deepgram_stt.py - create

## Interfaces and Data Models
Define any new interfaces, abstract classes, or data models with their signatures.

## Implementation Steps
1. ...
2. ...

## Test Cases
- test_transcribe_returns_result_with_text()
- test_transcribe_raises_on_empty_audio()
- ...

## Definition of Done
- [ ] All planned test cases pass (pytest)
- [ ] No domain layer imports provider code
- [ ] Typing is complete (no untyped functions)
- [ ] Plan steps are all implemented
```

**Agent actions:**

```bash
# If this is the first commit (no research), push and open PR now
git -C "$WORKTREE_PATH" add plan/<slug>.md
git -C "$WORKTREE_PATH" commit --no-verify -m "plan(<slug>): add implementation plan"
git -C "$WORKTREE_PATH" push

# Update PR description via REST API (gh pr edit is broken — see skills/git-usage/pr.md)
PR_BODY="Plan added. Awaiting human review before implementation."
gh api repos/dibene/english-app/pulls/<number> \
  --method PATCH --field body="$PR_BODY" --jq '.body | split("\n") | .[0]'
```

**WAIT** for human to say "implement it" or give feedback.

> 🔴 **CRITICAL: Do NOT start implementation until the human explicitly says to. Presenting the plan is not permission to implement.**

---

## Phase 4: Implementation

Triggered by human saying: **"implement it"** or **"go ahead"**.

> 🔴 **CRITICAL: If at any point during implementation you deviate from the plan, or hit a blocker, STOP — commit what exists, push, and notify the human immediately. Do not silently adapt or skip steps.**

**Agent actions:**

```bash
# Activate virtualenv so pre-commit works for Python files
cd "$WORKTREE_PATH/backend" && uv sync

# Work and commit after each logical step
git -C "$WORKTREE_PATH" add <files>
git -C "$WORKTREE_PATH" commit -m "feat(<slug>): <what was done in this step>"
git -C "$WORKTREE_PATH" push
```

Before the final commit, **run all tests**:

```bash
cd "$WORKTREE_PATH/backend" && uv run pytest
```

Final commit when all tests pass:

```bash
git -C "$WORKTREE_PATH" add -A
git -C "$WORKTREE_PATH" commit -m "feat(<slug>): implementation complete, all tests passing"
git -C "$WORKTREE_PATH" push
```

Mark PR as ready for review:

```bash
gh pr ready <number> --repo dibene/english-app
```

Update PR description with implementation summary + test results (use `gh api` REST, not `gh pr edit`).

**Remove the worktree immediately** — human reviews via `git checkout`, not from the worktree:

```bash
git -C "$REPO_ROOT" worktree remove "$WORKTREES_BASE/<slug>"
```

**Rules:**
- Do NOT deviate from the plan without flagging it in a PR comment explaining why.
- If a blocker is found mid-implementation, commit what exists, push, describe the blocker in a PR comment, and wait.
- Do NOT modify files outside the feature scope without explicit human approval.

---

## Phase 5: Human Review and Merge

Human reviews by checking out the branch:

```bash
git fetch origin && git checkout feat/<slug>
cd backend && uv sync
uv run pytest
uv run pytest -m live   # if live tests exist
```

If changes are requested → use the **[iterate_feature_pr](iterate_feature_pr.md)** skill.

After human approves and merges:

```bash
git fetch --prune
git branch -d feat/<slug>   # if not already deleted
```

---

## Pre-Commit Hook Note

The pre-commit hook fails in worktrees if the virtualenv is not activated.

- **Non-Python files** (markdown, configs): use `--no-verify`
- **Python files**: run `cd "$WORKTREE_PATH/backend" && uv sync` first, then commit normally

---

## Worktree Commands Reference

```bash
# Setup
REPO_ROOT=$(git rev-parse --show-toplevel)
WORKTREES_BASE=$(dirname "$REPO_ROOT")/english-app-worktrees
mkdir -p "$WORKTREES_BASE"

# Create
git -C "$REPO_ROOT" worktree add "$WORKTREES_BASE/<slug>" -b feat/<slug>
WORKTREE_PATH="$WORKTREES_BASE/<slug>"

# Git operations inside worktree
git -C "$WORKTREE_PATH" status
git -C "$WORKTREE_PATH" add <files>
git -C "$WORKTREE_PATH" commit -m "message"
git -C "$WORKTREE_PATH" push

# Remove after merge
git -C "$REPO_ROOT" worktree remove "$WORKTREES_BASE/<slug>"
git -C "$REPO_ROOT" branch -d feat/<slug>   # only after merge
```

---

## Backend Commands Reference

```bash
# Install / sync dependencies
cd "$WORKTREE_PATH/backend" && uv sync

# Run the API server
uv run uvicorn api.main:app --reload

# Run all tests
uv run pytest

# Run a specific test file
uv run pytest tests/test_stt.py -v

# Run live tests (requires real API keys in .env)
uv run pytest -m live
```

---

## Project Structure Reference

```
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
├── research/                 # Per-feature research docs
└── plan/                     # Per-feature plans
```

**Architecture rule:** The domain layer (`core/`) must have zero imports from `providers/`.
All cross-boundary communication goes through interfaces defined in `core/interfaces/`.
