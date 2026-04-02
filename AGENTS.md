---
name: AGENTS.md
description: >
  AI agent workflow definition for the Read & Improve project.
  Applies to GitHub Copilot, Claude Code, OpenAI Codex, and any AI coding agent.
  This is the single source of truth for project-level rules and conventions.
---

# Agent Workflow - Read & Improve

This file defines project-level rules that all agents must follow.
For step-by-step operational workflows, use the skills referenced below.

---

## Repository Context

- **Project:** Read & Improve - AI Pronunciation Feedback MVP
- **Stack:** Python/FastAPI (backend) + Next.js (frontend)
- **Architecture:** Clean Architecture — domain layer (`core/`) has zero imports from `providers/`
- **PRD:** [docs/mvp_prd.md](docs/mvp_prd.md)
- **Architecture decisions:** [docs/architecture.md](docs/architecture.md)
- **Feature list:** [docs/features.md](docs/features.md)

---

## Core Principles

> Never implement without a reviewed plan.
> Never plan without sufficient context — research first when needed.
> Work in isolation using git worktrees.
> One feature = one PR. Each phase = one commit.
> Only humans merge PRs.

---

## Skills

Use the appropriate skill for structured multi-step operations:

| Skill | When to Use |
|-------|-------------|
| [investigate](skills/investigate/investigate.md) | Bug reports, research questions, debugging, "why/how/what" — **research → plan → approval → implement** |
| [ship_feature](skills/features/ship_feature.md) | Work on a new feature from the backlog (worktree → research → plan → implement → PR) |
| [iterate_feature_pr](skills/features/iterate_feature_pr.md) | Apply changes to an existing open PR based on review feedback or new instructions |
| [GitHub PR with `gh` CLI](skills/git-usage/pr.md) | Create, edit, and manage PRs — **read before any `gh` command** |
| [Commit messages](skills/git-usage/commits.md) | Commit message format, types, and pre-commit hook notes |

---

## Handling Blockers

**CRITICAL: When you encounter a blocker, error, or problem, you MUST:**

1. **STOP immediately** — do not try alternatives without human approval
2. **COMMIT and PUSH** what exists so far
3. **NOTIFY the human:**

   > ❌ BLOCKER ENCOUNTERED
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
   >
   > How would you like to proceed?

4. **WAIT for human response**

**Blocker examples:** missing auth, missing deps, permission errors, ambiguous requirements,
external service failures, test failures that require architectural decisions.

---

## What Agents Must NOT Do

- Do NOT implement without a `plan/<slug>.md` that the human has reviewed
- Do NOT commit directly to `main`
- Do NOT bundle multiple features in one PR
- Do NOT skip the worktree setup
- Do NOT modify files outside the feature scope without flagging it
- Do NOT merge PRs — only humans merge
- Do NOT keep the worktree after the PR is marked ready — remove it immediately
- Do NOT silently deviate from the plan — flag deviations as PR comments
