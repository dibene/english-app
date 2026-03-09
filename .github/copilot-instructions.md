# GitHub Copilot Instructions

This project uses a unified agent workflow defined in [AGENTS.md](../AGENTS.md) at the repository root.

**All Copilot agent sessions must follow the workflow defined in [AGENTS.md](../AGENTS.md).**

---

## Quick Reference

| Document | Purpose |
|----------|---------|
| [AGENTS.md](../AGENTS.md) | Project rules: conventions, blocker protocol, skills index |
| [docs/mvp_prd.md](../docs/mvp_prd.md) | Product requirements, data flow, tech stack |
| [docs/features.md](../docs/features.md) | Prioritized atomic feature backlog |

## Skills

| Skill | When to Use |
|-------|-------------|
| [ship_feature](../skills/features/ship_feature.md) | Work on a new feature from the backlog |
| [iterate_feature_pr](../skills/features/iterate_feature_pr.md) | Apply changes to an existing open PR |
| [GitHub PR with `gh` CLI](../skills/git-usage/pr.md) | Before any `gh pr` command |
| [Commit messages](../skills/git-usage/commits.md) | Commit format and pre-commit hook notes |

---

## Where to Start

1. Read [docs/features.md](../docs/features.md) to find the next feature to work on.
2. Read [AGENTS.md](../AGENTS.md) for project rules and conventions.
3. Use the [ship_feature](../skills/features/ship_feature.md) skill for the step-by-step workflow.
