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

---

## PR Convention

- **Title:** `[<FEATURE-ID>] <Feature Name>` — e.g. `[F-001] Deepgram STT Provider`
- **Branch:** `feat/<slug>` — e.g. `feat/deepgram-stt-provider`
- **Status:** Draft during research + plan phases; Ready for Review after implementation
- **One PR per feature** — never bundle multiple features
- **PR description** must be updated at each phase transition
