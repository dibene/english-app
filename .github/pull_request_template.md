# [FEATURE-ID] Feature Name

<!--
Replace with actual feature ID and name, e.g.:
[F-002] Deepgram STT Provider
-->

## Type of Change
<!-- Check the relevant option -->
- [ ] Research document
- [ ] Plan document
- [ ] Feature implementation
- [ ] Bug fix
- [ ] Refactor
- [ ] Documentation
- [ ] Chore (dependencies, tooling, config)

## Feature ID
<!-- e.g., F-002 -->
**Feature ID:**

## Slug
<!-- e.g., deepgram-stt-provider -->
**Slug:**

---

## Research (if applicable)
<!-- Link to research document if this feature required research -->
- [ ] Research document added: `research/<slug>.md`
- [ ] Research reviewed and approved by human

**Research Summary:**
<!-- Brief summary of research findings and chosen approach -->

---

## Plan
<!-- Link to plan document -->
- [ ] Plan document added: `plan/<feature-id>-<slug>.md`
- [ ] Plan reviewed and approved by human

**Plan Summary:**
<!-- Brief summary of what will be implemented -->

---

## Implementation

### What was implemented
<!-- Describe what was built in this PR -->

### Files Changed
<!-- List key files created or modified -->
-
-
-

### Tests
<!-- Describe test coverage -->
- [ ] All tests passing
- [ ] Coverage meets requirements (list % if available)

**Test Summary:**
```
# Paste pytest output here
```

---

## Code Quality Checks

- [ ] All tests pass: `uv run pytest`
- [ ] Type checking passes: `uv run mypy .`
- [ ] Linting passes: `uv run pylint api/ core/ tests/`
- [ ] Code formatting correct: `uv run black . --check`
- [ ] Import sorting correct: `uv run isort . --check`
- [ ] Pre-commit hooks pass: `uv run pre-commit run --all-files`

---

## Clean Architecture Compliance

- [ ] Domain layer (`core/`) has no external dependencies
- [ ] No provider imports in `core/`
- [ ] Interfaces defined before implementations
- [ ] All functions have type hints

---

## Definition of Done (from plan)

<!-- Copy checklist from plan/<feature-id>-<slug>.md -->
- [ ] Item 1
- [ ] Item 2
- [ ] ...

---

## Breaking Changes
<!-- Describe any breaking changes or migration steps required -->
- [ ] No breaking changes
- [ ] Breaking changes (describe below):

---

## How to Test

> **Agents must fill this section completely before marking a PR as ready for review.**

### Setup

```bash
# 1. Checkout the branch
git fetch origin
git checkout feat/<slug>

# 2. Install all dependencies (including dev)
cd backend
uv sync

# 3. Copy or symlink your .env (must contain required API keys)
cp /path/to/your/.env .env
```

### Generate fixtures (if applicable)
<!-- Remove this block if the feature has no generated fixtures -->
```bash
# Run from backend/
uv run python tests/fixtures/generate_fixtures.py
```

### Run unit tests (no external services required)

```bash
cd backend
uv run pytest
```

Expected output:
```
# Paste expected output here
```

### Run live tests (requires API keys + network)
<!-- Remove this block if the feature has no live tests -->
```bash
cd backend
uv run pytest -m live -v
```

Expected output:
```
# Paste expected output here
```

### Required environment variables
<!-- List every env var needed to run the tests -->
| Variable | Required for | Where to get it |
|----------|-------------|-----------------|
| `DEEPGRAM_API_KEY` | live tests | Deepgram console |

---

## Screenshots / Demo (if applicable)
<!-- Add screenshots, GIFs, or link to demo video -->

---

## Additional Notes
<!-- Any additional context, concerns, or decisions made during implementation -->

---

## Checklist Before Requesting Review

- [ ] PR title follows convention: `[F-XXX] Feature Name`
- [ ] Branch follows convention: `feat/<slug>`
- [ ] All commits follow convention: `<type>(<slug>): <description>`
- [ ] Plan document exists and was approved
- [ ] Implementation matches plan (or deviations are documented)
- [ ] All code quality checks pass
- [ ] Tests are comprehensive and passing
- [ ] Documentation is updated (README, comments, etc.)
- [ ] No sensitive data (API keys, credentials) committed
- [ ] PR is ready for human review

---

## Reviewer Notes
<!-- Space for reviewer feedback -->
