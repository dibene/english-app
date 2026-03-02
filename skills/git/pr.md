# Skill: GitHub PRs with `gh` CLI

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

`gh pr edit` may produce a "Projects classic deprecated" GraphQL warning with exit code 1
even when the edit succeeds. Always suppress with `2>/dev/null || true`:

```bash
gh pr edit <number> --repo dibene/english-app \
  --body "new body" 2>/dev/null || true
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
gh pr edit <number> --repo dibene/english-app \
  --body "Plan added. Awaiting human review before implementation." 2>/dev/null || true

# Phase 4: Implementation
cd "$WORKTREE_PATH/backend" && uv sync   # activate venv for pre-commit
git -C "$WORKTREE_PATH" add <files>
git -C "$WORKTREE_PATH" commit -m "feat(<slug>): <step description>"
git -C "$WORKTREE_PATH" push
gh pr ready <number> --repo dibene/english-app

# Cleanup after merge
git -C "$REPO_ROOT" worktree remove "$WORKTREES_BASE/<slug>"
git -C "$REPO_ROOT" branch -d feat/<slug>
```

## Plan file naming convention

Plans follow the pattern `F-XXX-<slug>.md`, matching the feature ID:

| Feature | Plan file |
|---------|-----------|
| F-000 Backend Setup | `plan/F-000-backend-setup.md` |
| F-001 Deepgram STT | `plan/F-001-deepgram-stt-provider.md` |
| F-002 Text Comparison | `plan/F-002-text-comparison-engine.md` |
