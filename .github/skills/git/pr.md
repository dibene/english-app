# Skill: GitHub PR con `gh` CLI

## Crear un PR

```bash
gh pr create \
  --repo dibene/english-app \
  --title "[F-XXX] Feature Name" \
  --body "Descripción del PR" \
  --draft \
  --base main \
  --head feat/<slug>
```

## Opciones clave

| Flag | Descripción |
|------|-------------|
| `--draft` | Abre como borrador (research/plan phases) |
| `--base main` | Rama destino |
| `--head feat/<slug>` | Rama origen |
| `--repo owner/repo` | Requerido si no estás en el repo principal |

## Marcar como listo para review

```bash
gh pr ready <number> --repo dibene/english-app
```

## Editar body/title (evitar GraphQL deprecated warning)

`gh pr edit` puede dar un warning de "Projects classic deprecated" con exit code 1
aunque el edit funcione. Para editarlo sin problemas, usar:

```bash
gh pr edit <number> --repo dibene/english-app \
  --title "nuevo título" \
  --body "nuevo body"
```

El warning es inofensivo pero rompe scripts. Ignorar o redirigir stderr:

```bash
gh pr edit <number> --repo dibene/english-app --body "..." 2>/dev/null || true
```

## Ver estado de un PR

```bash
gh pr view <number> --repo dibene/english-app
gh pr view <number> --repo dibene/english-app --json title,state,url
```

## Listar PRs abiertos

```bash
gh pr list --repo dibene/english-app
```

## Commit en worktrees (pre-commit hook)

En worktrees el pre-commit hook falla si el venv no está activado.
Para archivos no-Python (markdown, configs) usar `--no-verify`:

```bash
git -C "$WORKTREE_PATH" commit --no-verify -m "plan(slug): mensaje"
```

Para archivos Python, activar el venv del worktree antes de commitear:

```bash
cd "$WORKTREE_PATH/backend" && uv sync
git -C "$WORKTREE_PATH" add <files>
git -C "$WORKTREE_PATH" commit -m "feat(slug): mensaje"
```

## Flujo completo por fase

```bash
# Phase 2: Research
git -C "$WORKTREE_PATH" add research/<slug>.md
git -C "$WORKTREE_PATH" commit --no-verify -m "research(<slug>): add research document"
git -C "$WORKTREE_PATH" push -u origin feat/<slug>
gh pr create --repo dibene/english-app --title "[F-XXX] Name" --body "..." --draft --base main --head feat/<slug>

# Phase 3: Plan
git -C "$WORKTREE_PATH" add plan/<slug>.md
git -C "$WORKTREE_PATH" commit --no-verify -m "plan(<slug>): add implementation plan"
git -C "$WORKTREE_PATH" push
gh pr edit <number> --repo dibene/english-app --body "..." 2>/dev/null || true

# Phase 4: Implementation (post uv sync)
git -C "$WORKTREE_PATH" add <files>
git -C "$WORKTREE_PATH" commit -m "feat(<slug>): <step description>"
git -C "$WORKTREE_PATH" push
gh pr ready <number> --repo dibene/english-app
```
