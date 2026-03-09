---
name: iterate_feature_pr
description: >
  Apply changes to an existing open PR based on review feedback or new instructions.
  Use this after ship_feature has created the PR and the human has requested changes,
  or when you need to act on GitHub PR review comments.
---

# Skill: Iterate on a Feature PR

Use this skill when a PR already exists and you need to apply changes to it.

**Triggers:**
- "fix these PR comments"
- "apply these changes to the PR"
- "update feat/<slug> with..."
- Human leaves review feedback on GitHub and you need to address it

> ⚠️ **Read [skills/git-usage/pr.md](../git-usage/pr.md) before running any `gh` command.**

---

## Overview

The PR is already open. The worktree from the original `ship_feature` run has been removed.
You need to create a **new worktree on the same existing branch**, apply changes, and push.

---

## Phase IT-0: Identify PR and Branch

If you don't already have the PR number and branch name:

```bash
# List open PRs to find the one you need
gh pr list --repo dibene/english-app

# Get branch name from a PR number
gh pr view <number> --repo dibene/english-app --json headRefName --jq '.headRefName'
# Returns: feat/<slug>
```

---

## Phase IT-1: Setup Worktree on Existing Branch

The branch already exists on the remote — do NOT use `-b` (that would create a new branch).

```bash
# Resolve paths (same as ship_feature)
REPO_ROOT=$(git rev-parse --show-toplevel)
WORKTREES_BASE=$(dirname "$REPO_ROOT")/english-app-worktrees
mkdir -p "$WORKTREES_BASE"

# Fetch the latest state of the branch
git -C "$REPO_ROOT" fetch origin

# Create worktree on the EXISTING remote branch (no -b flag)
git -C "$REPO_ROOT" worktree add "$WORKTREES_BASE/<slug>" feat/<slug>
WORKTREE_PATH="$WORKTREES_BASE/<slug>"

# Verify you are on the right branch and have the latest commits
git -C "$WORKTREE_PATH" status
git -C "$WORKTREE_PATH" log --oneline -5
```

---

## Phase IT-2: Understand What Needs to Change

**Option A — Human described changes in the chat:** use those directly.

**Option B — Address GitHub PR review comments:**

```bash
# View the full PR with all comments
gh pr view <number> --repo dibene/english-app --comments

# Or fetch just the review comments via REST
gh api repos/dibene/english-app/pulls/<number>/comments \
  --jq '.[].body'

# Fetch review-level comments (submitted via "Review changes")
gh api repos/dibene/english-app/pulls/<number>/reviews \
  --jq '.[].body'
```

Summarize every open comment before starting. If any comment is ambiguous or conflicts with the original plan, stop and ask the human for clarification before changing code.

---

## Phase IT-3: Apply Changes

- Work inside `$WORKTREE_PATH`
- Follow the same architecture rules as the original feature (see [ship_feature](ship_feature.md))
- Do NOT change files outside the scope of the reviewed feedback
- If a requested change requires deviating from the original `plan/<slug>.md`, note it clearly in the commit message and PR comment

For Python files, activate the virtualenv first:

```bash
cd "$WORKTREE_PATH/backend" && uv sync
```

---

## Phase IT-4: Test

Always run the full test suite before committing:

```bash
cd "$WORKTREE_PATH/backend" && uv run pytest
```

If tests fail:
- Fix the failures (they are likely related to the changes you just made)
- If a failing test is unrelated to your changes and was already failing on the branch, report it as a blocker — do not mask it

---

## Phase IT-5: Commit and Push

```bash
# Commit the changes
git -C "$WORKTREE_PATH" add <files>
git -C "$WORKTREE_PATH" commit -m "fix(<slug>): <describe what review feedback was addressed>"
git -C "$WORKTREE_PATH" push
```

Use `fix(<slug>):` for addressing review feedback.
Use `feat(<slug>):` for adding new functionality that was requested in the review.

---

## Phase IT-6: Remove Worktree

```bash
git -C "$REPO_ROOT" worktree remove "$WORKTREES_BASE/<slug>"
```

Human reviews the new commits via `git pull` or GitHub directly.

---

## Phase IT-7: (Optional) Reply to PR Comments

If the human asked you to mark comments as resolved or reply to them:

```bash
# Reply to a specific review comment (get the comment ID from the API call above)
gh api repos/dibene/english-app/pulls/comments/<comment-id>/replies \
  --method POST \
  --field body="Fixed in $(git -C "$WORKTREE_PATH" rev-parse --short HEAD)."
```

---

## Rules

- Do NOT force-push unless the human explicitly asks.
- Do NOT rebase mid-review — plain commits on top of the existing branch are sufficient.
- Do NOT close or reopen the PR yourself.
- If the scope of requested changes is large enough to warrant a new plan step, say so before implementing.
