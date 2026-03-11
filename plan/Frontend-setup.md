# Plan: Frontend Project Setup (F-012)

## Goal
Bootstrap the Next.js frontend project so that every subsequent frontend feature
has a working app shell to build on — the frontend equivalent of F-000.

## Scope

**In scope:**
- Scaffold a Next.js 14 app in `frontend/` (TypeScript, App Router, Tailwind CSS)
- Folder structure: `app/`, `components/`, `lib/`
- Empty `lib/api.ts` placeholder (typed API client stub — filled in by F-009)
- Minimal root page confirming the app starts
- `frontend/.env.local.example` with `NEXT_PUBLIC_API_URL=http://localhost:8000`
- `frontend/.env.local` in `.gitignore`

**Out of scope (this PR):**
- Any real UI components (F-006+)
- Actual API client implementation (F-009)
- Root README update (F-010)
- CI/CD or Docker setup

## Files to Create or Modify

| File | Action |
|------|--------|
| `frontend/` (whole directory) | create via `create-next-app` |
| `frontend/app/page.tsx` | update — minimal static heading |
| `frontend/lib/api.ts` | create — empty typed stub |
| `frontend/.env.local.example` | create |
| `.gitignore` (root) | modify — add `frontend/.env.local` if not already ignored |

## Tech Choices

| Decision | Choice | Reason |
|----------|--------|--------|
| Next.js version | 14 (latest stable) | App Router is default, aligns with PRD |
| Package manager | npm | Default for `create-next-app`; keeps setup simple |
| Styling | Tailwind CSS | Fastest to use for F-006–F-008 UI work |
| TypeScript | Yes | Strict mode; required for typed API client in F-009 |
| ESLint | Yes | Code quality, standard with Next.js |
| src/ directory | No | Keeps paths short (`app/` not `src/app/`) |
| import alias | `@/*` | Standard Next.js default |

## Implementation Steps

1. **Scaffold the app**
   ```bash
   cd /home/kratos/projects/english-app-worktrees/Frontend-setup
   npx create-next-app@14 frontend \
     --typescript \
     --tailwind \
     --eslint \
     --app \
     --no-src-dir \
     --import-alias "@/*" \
     --no-git
   ```
   `--no-git` because this is already inside a git worktree.

2. **Simplify `app/page.tsx`** — replace generated boilerplate with a minimal static heading:
   ```tsx
   export default function Home() {
     return (
       <main className="p-8">
         <h1 className="text-2xl font-bold">Read &amp; Improve</h1>
         <p className="mt-2 text-gray-500">Frontend setup complete.</p>
       </main>
     );
   }
   ```

3. **Create `frontend/lib/api.ts`** — typed stub for the API client:
   ```ts
   // Typed API client — implemented in F-009
   const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
   export { API_URL };
   ```

4. **Create `frontend/.env.local.example`**:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

5. **Update root `.gitignore`** — add `frontend/.env.local` if not already covered.

6. **Smoke-test** — verify the dev server starts and the root page loads:
   ```bash
   cd frontend && npm run dev &
   # open http://localhost:3000 — should show the heading
   ```

## Test Cases

This feature has no automated tests (there is no domain logic).
The definition of done is verified manually:

- [ ] `npm run dev` starts without errors
- [ ] http://localhost:3000 renders the heading
- [ ] `npm run build` completes without errors
- [ ] `npm run lint` produces no errors

## Definition of Done

- [ ] `frontend/` directory scaffolded with TypeScript + App Router + Tailwind
- [ ] `frontend/lib/api.ts` stub exists
- [ ] `frontend/.env.local.example` exists with `NEXT_PUBLIC_API_URL`
- [ ] `frontend/.env.local` is gitignored
- [ ] `npm run dev` starts cleanly
- [ ] `npm run build` passes
- [ ] `npm run lint` passes
