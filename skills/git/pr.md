# Skill: GitHub PRs with `gh` CLI

## ⚠️ Known Issues (read before using any gh command)

### `gh pr edit` is permanently broken for this repo

**Symptom:** `gh pr edit` exits with code 1, PR body is NOT updated, no visible error.

**Cause:** The repo has "Projects (classic)" enabled. Every `gh pr edit` call runs a
GraphQL query for project cards that fails with a deprecation error, causing the whole
mutation to abort before updating the body.

**This is a repo-level issue. It will happen on every machine, every time.**

**Rule: Never use `gh pr edit --body` in this repo. Always use `gh api` (REST):**

```bash
PR_BODY=$(cat <<'BODY'
Your PR description here...
BODY
)
gh api repos/dibene/english-app/pulls/<number> \
  --method PATCH \
  --field body="$PR_BODY" \
  --jq '.body | split("\n") | .[0]'
```

---

## Create a PR

```bash
gh pr create \
  --repo dibene/english-app \
  --title "[F-XXX] Feature Name" \
  --body "PR description" \
  --draft \
  --base main \
  --head feat/<slug>
```

## Key flags

| Flag | Description |
|------|-------------|
| `--draft` | Opens as draft (use during research/plan phases) |
| `--base main` | Target branch |
| `--head feat/<slug>` | Source branch |
| `--repo owner/repo` | Required when not inside the main repo checkout |

## Mark as ready for review

```bash
gh pr ready <number> --repo dibene/english-app
```

## Edit PR body/title

`gh pr edit` is broken for this repo — the "Projects (classic) deprecated" GraphQL error
causes it to fail silently (exit code 1, **body not updated**). Do not use it.

**Use the REST API instead:**

```bash
# Store body in a variable (heredoc avoids escaping issues)
PR_BODY=$(cat <<'BODY'
Your PR description here...
BODY
)

# PATCH via REST API — no GraphQL, no Projects query, works reliably
gh api repos/dibene/english-app/pulls/<number> \
  --method PATCH \
  --field body="$PR_BODY" \
  --jq '.body | split("\n") | .[0]'  # prints first line as confirmation
```

Verify:
```bash
gh api repos/dibene/english-app/pulls/<number> --jq '.body | split("\n") | .[2]'
```

## View PR status

```bash
gh pr view <number> --repo dibene/english-app
gh pr view <number> --repo dibene/english-app --json title,state,url
```

## List open PRs

```bash
gh pr list --repo dibene/english-app
```

## Committing inside worktrees

The pre-commit hook fails in worktrees if the virtualenv is not activated.

**For non-Python files** (markdown, configs) — use `--no-verify`:
```bash
git -C "$WORKTREE_PATH" commit --no-verify -m "plan(<slug>): add implementation plan"
```

**For Python files** — run `uv sync` first so pre-commit has the venv:
```bash
cd "$WORKTREE_PATH/backend" && uv sync
git -C "$WORKTREE_PATH" add <files>
git -C "$WORKTREE_PATH" commit -m "feat(<slug>): description"
```

## Full workflow per phase

```bash
# Phase 2: Research
git -C "$WORKTREE_PATH" add research/F-XXX-<slug>.md
git -C "$WORKTREE_PATH" commit --no-verify -m "research(<slug>): add research document"
git -C "$WORKTREE_PATH" push -u origin feat/<slug>
gh pr create --repo dibene/english-app \
  --title "[F-XXX] Name" \
  --body "Research complete. Awaiting human review before planning." \
  --draft --base main --head feat/<slug>

# Phase 3: Plan
git -C "$WORKTREE_PATH" add plan/F-XXX-<slug>.md
git -C "$WORKTREE_PATH" commit --no-verify -m "plan(<slug>): add implementation plan"
git -C "$WORKTREE_PATH" push
# Use REST API — gh pr edit is broken (Projects classic GraphQL error)
PR_BODY="Plan added. Awaiting human review before implementation."
gh api repos/dibene/english-app/pulls/<number> --method PATCH --field body="$PR_BODY" --jq '.body'
# verify
gh api repos/dibene/english-app/pulls/<number> --jq '.body | split("\n") | .[0]'

# Phase 4: Implementation
cd "$WORKTREE_PATH/backend" && uv sync   # activate venv for pre-commit
git -C "$WORKTREE_PATH" add <files>
git -C "$WORKTREE_PATH" commit -m "feat(<slug>): <step description>"
git -C "$WORKTREE_PATH" push
gh pr ready <number> --repo dibene/english-app

# Remove worktree immediately after PR is ready — human reviews via git checkout
git -C "$REPO_ROOT" worktree remove "$WORKTREES_BASE/<slug>"

# Human reviews by checking out the branch normally:
# git fetch origin && git checkout feat/<slug>
# cd backend && uv sync && uv run pytest && uv run pytest -m live

# Cleanup after merge
git fetch --prune
git branch -d feat/<slug>
```

## Plan file naming convention

Plans follow the pattern `F-XXX-<slug>.md`, matching the feature ID:

| Feature | Plan file |
|---------|-----------|
| F-000 Backend Setup | `plan/F-000-backend-setup.md` |
| F-001 Deepgram STT | `plan/F-001-deepgram-stt-provider.md` |
| F-002 Text Comparison | `plan/F-002-text-comparison-engine.md` |
