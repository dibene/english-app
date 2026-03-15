---
name: investigate
description: >
  Workflow for non-feature requests: bug reports, research questions, debugging,
  "what is X", "why does Y happen", "investigate Z".
  NEVER implement anything without a reviewed and approved plan.
---

# Skill: Investigate → Plan → Approval → Implement

Use this skill whenever the human is NOT asking to ship a feature but instead to:
- Report a bug ("hay un bug", "x no funciona", "x está roto")
- Ask a question ("por qué", "qué es", "cómo funciona")
- Request research ("investiga", "buscá", "averiguá")
- Request debugging ("debugueá", "encontrá el problema", "chequeá")

> ⚠️ **CRITICAL: Do NOT implement, fix, or change any code until the human has approved the plan.**

---

## Triggers

Activate this skill (instead of ship_feature) when the prompt contains any of these signals:
- Bug words: "bug", "roto", "broken", "no funciona", "falla", "error", "no muestra", "mal"
- Investigation words: "debugueá", "chequeá", "verificá", "averiguá", "investigá", "revisá"
- Question words: "por qué", "cómo", "qué es", "dónde", "cuándo", "sirve", "deberíamos"
- Research words: "investiga", "buscá", "encontrá", "es de nuestro lado o de"

---

## Workflow

### Phase 1 — Understand the problem
1. Read the prompt carefully. Identify what is claimed to be broken or unknown.
2. List all possible causes (at least 2-3 hypotheses).
3. Do NOT assume which cause is correct yet.

### Phase 2 — Research
Read the relevant code, logs, test output, and data to gather evidence:
- Read the affected files (frontend + backend, both sides of the boundary)
- Check what data flows in and out (API request/response, models, service layer)
- Check git history for recent changes that could be related
- Confirm which hypothesis is supported by the evidence

Do NOT modify any file during this phase.

### Phase 3 — Write findings + plan
Present to the human in this exact structure:

```
## Findings

**Root cause (or most likely cause):** [one clear sentence]

**Evidence:**
- [file:line or observation 1]
- [file:line or observation 2]

**Other hypotheses ruled out:** [why they don't apply]

---

## Proposed Plan

**Option 1 — [name]:** [description, pros, cons]
**Option 2 — [name]:** [description, pros, cons]  ← include if there are real alternatives

**My recommendation:** Option X because [reason].

---

Approve to proceed, or let me know which option you prefer.
```

### Phase 4 — Wait for approval

**STOP HERE.** Do not write a single line of code until the human responds.

Accepted approval signals: "ok", "hacelo", "aprobado", "sí", "go ahead", "implement it",
or any explicit confirmation.

### Phase 5 — Implement

Only after explicit approval:
- Implement the approved option
- Run relevant tests
- Build check if frontend was modified
- Commit and push

---

## What this skill forbids

- Writing code during Phase 1–3
- Assuming approval from silence or partial phrases
- Combining investigation and implementation in one response
- Committing speculative fixes "to see if it works"
- Reverting or editing files without stating why in the plan

---

## Example of correct behavior