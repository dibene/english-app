# Skill: Commit Messages

## Format

```
<type>(<slug>): <short description (imperative, lowercase)>
```

## Types

| Type | When to use |
|------|-------------|
| `research` | Research document added or updated |
| `plan` | Plan document added or updated |
| `feat` | Feature implementation code |
| `fix` | Bug fix, including addressing review feedback |
| `test` | Test additions or changes only |
| `refactor` | Code restructure without behavior change |
| `chore` | Tooling, deps, config, env files |

## Examples

```
research(deepgram-stt-provider): add research document
plan(deepgram-stt-provider): add implementation plan
feat(deepgram-stt-provider): define SpeechToTextProvider interface
feat(deepgram-stt-provider): implement DeepgramSTTProvider
feat(deepgram-stt-provider): implementation complete, all tests passing
fix(deepgram-stt-provider): address review feedback on error handling
chore(backend): add python-dotenv to dependencies
```

## Pre-Commit Hook Note

The hook fails in worktrees if the virtualenv is not activated.

- **Non-Python files** (markdown, configs): use `--no-verify`
  ```bash
  git -C "$WORKTREE_PATH" commit --no-verify -m "plan(<slug>): add implementation plan"
  ```
- **Python files**: run `uv sync` first so the hook has access to the venv:
  ```bash
  cd "$WORKTREE_PATH/backend" && uv sync
  git -C "$WORKTREE_PATH" add <files>
  git -C "$WORKTREE_PATH" commit -m "feat(<slug>): description"
  ```
