# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status: becoming the main product

This repo is transitioning from a YC pitch demo into the real product: a real
database backing productive (paying) clients, while keeping a fast synthetic
demo mode (`data-demo/`'s deterministic generator, tenant `demo`) available for
showcasing. The multi-tenant design (`POLPILOT_TENANT` + `POLPILOT_DATA_DIR`,
see Architecture below) already isolates tenants by directory — extend that
pattern for real, DB-backed tenants rather than forking the demo data path.

## Coding standards

- **All code, identifiers, comments, commit messages, and docstrings are in
  English**, regardless of what language surrounding code or docs used before.
  Product-facing/UI copy shown to end users may stay in Spanish (the product's
  user base is Argentine PyMEs) — this rule is about the codebase, not the UI text.
- This applies to all new and modified code from now on. Do not do a
  blanket rewrite of existing Spanish identifiers as a side effect of an
  unrelated change; migrate a file's naming only when you're already working
  substantially in it.
- Follow normal language idioms/conventions for whichever part of the stack
  you're touching (PEP 8 / type hints in `backend/`, idiomatic React/ES
  modules in `frontend/`) rather than importing patterns across the boundary.

## Running the demo

Requirements: Python 3.12+, Node 20+.

```bash
# Backend (tenant `demo` and data-demo/ are the defaults — nothing to configure)
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --port 8000

# Frontend (separate terminal)
cd frontend
npm ci
npm run dev          # http://localhost:5173
```

Or everything at once, with seeding and a healthcheck: `python start_demo.py`.

- **Users:** the fictional team lives in `backend/usuarios_demo.py` (`aldo` is
  the owner). **Log in with the fixed seeded password: `demo-password`**
  (override with `POLPILOT_DEMO_PASSWORD`; always set it for any deployment
  reachable from outside a dev machine). Only bcrypt hashes are persisted, in
  Postgres `auth_credentials` — plaintext is never written to disk, and there
  is no `credenciales.json`. `data-demo/seed_db.py` re-asserts the fixed
  password on every seed, so a drifted hash is repaired by re-seeding.
  A user with no row yet still gets a random password, held only in the
  running process's memory; `POLPILOT_PRINT_CREDS=1` prints those.
- **Ángela (AI chat):** optional. Export `ANTHROPIC_API_KEY` before starting the
  backend; without it, everything else still works — the analyses are
  deterministic and don't depend on the LLM.
- **The dataset's "today" is 2026-07-07.** Run with `POLPILOT_DEMO_TODAY=2026-07-07`
  so analyses line up with the seeded history (`start_demo.py` already sets this).

## Architecture

```
backend/    FastAPI · deterministic core (core/) + Ángela (angela.py)
frontend/   React + Vite · desktop and mobile
data-demo/  the synthetic dataset (seed) + its deterministic generator
deploy/     production boot (single service: API + compiled frontend)
```

- The **deterministic edge** lives in `backend/core/` (one file per domain —
  `ventas.py`, `caja.py`, `cobranza.py`, `saneamiento.py`, `oportunidades_neg.py`,
  etc.): every number comes from calculation, never from the model. Ángela
  narrates and calls tools; she never invents a figure. When adding a feature,
  put the calculation in `core/`, not in a prompt or in `angela.py`.
- **Multi-tenant by design:** `POLPILOT_TENANT` + `POLPILOT_DATA_DIR` fully
  isolate instances (directories, users, credentials). This repo ships two
  example tenants, both fictional: `demo` (Distribuidora del Litoral, the
  default) and `piloto` (Supermercados Horizonte, the small seed in
  `backend/auth.py`).
- **MCP server (`backend/mcp_server.py`, mounted at `/mcp`):** a read-only
  bridge for users to query their PolPilot data from an external LLM
  (Claude Desktop, claude.ai, any MCP client). Every tool wraps
  `angela._run_tool` — no calculation of its own — and is gated by the same
  per-user `features` Ángela's chat tools already respect. See `backend/MCP.md`.

## The Ángela chat surface

Built on `@assistant-ui/react` 0.15 (`frontend/src/components/assistant/`,
`frontend/src/lib/chat*`, `frontend/src/views/Chat*`) over the NDJSON stream at
`/api/angela/stream`. **Read
`docs/superpowers/specs/2026-09-02-chat-experience-design.md` before changing
this layer** — it records the decisions below and why, including the ones a
well-meaning change would otherwise undo.

**Status (2026-09-05):** Phase 1 (foundation) and Phase 3's presenter
registry have landed, plus a markdown/accessibility pass and a rebuilt
composer (D11). **Phase 1.5 landed** — `_fallback` is gone; a missing model
is an error, never a keyword-matched reply. Phase 2 (run context,
suggestions, `useAskAngela`) has not started.
Where the code still contradicts a rule below, the rule wins and the code
is what changes. Update this status line as phases land.

Hard rules:

- **Tool UI is a registry, not a branch.** Add a module under
  `components/assistant/tools/` and register it. `ChatThread` must never grow a
  per-tool `if`. A presenter is always an *override*: the shape-based
  `Fallback` must keep giving new Python tools a usable UI with zero frontend
  work.
- **Presenters are pure** functions of `(args, result)`. Side effects
  (navigate, create widget, apply preference) belong in the action applier, not
  in a renderer.
- **Do not adopt `defineToolkit`.** assistant-ui toolkits assume the tool loop
  runs in JS; here it runs in Python (`angela.py`), so there is no client-side
  `execute` to co-locate. The inline `MessagePrimitive.Parts` tool override in
  use is the *non-deprecated* path for rendering — `makeAssistantToolUI` and
  friends are the deprecated ones. See D2 in the design doc, which also lists
  what keeps a future migration mechanical.
- **No deterministic LLM fallback.** A missing/bad API key is a config error
  and the chat feature is flagged off; a failed model call surfaces a real
  error with retry. Dev/test/demo use an explicitly labeled `LLM_MODE=fake`,
  never reachable in prod. Do not reintroduce a keyword router that answers as
  if it were Ángela — it duplicates UI that already exists, hides outages, and
  in an inventory/money product a plausible-but-wrong answer is the expensive
  failure. See D9.
- **App context is data, never instructions, and never the answer.** Sections
  feed Ángela what is on screen via `useAssistantContext`; she still calls
  `core/` tools for every number. Context says *what to ask about*.
- **Charts read `meta`, not guesses.** `consultar_serie` already returns
  `meta.temporal` / `unidad` / `composicion` / `deflactado` — that is the
  discriminator for line vs. bars vs. stacked-share vs. %-line. Never leave
  real-vs-nominal ambiguous.
- **`violeta` is Ángela, never data.** Every color means exactly one thing
  (see `DESIGN.md` and `lib/paleta.js`); data series come from `paleta.SERIES`.
- **Tool labels and all user-facing copy are i18n keys**, never inline strings.
- The chat layer is **TypeScript** (`allowJs` elsewhere). Vite/esbuild does not
  typecheck — run `npm run typecheck` before merging or the types rot.

## Tests

```bash
cd backend && ../.venv/Scripts/python.exe -m pytest
```
Single test: `../.venv/Scripts/python.exe -m pytest tests/test_<name>.py -k <pattern>`.

**Use the venv's interpreter, not bare `python`.** On a dev box where bare
`python` is an older interpreter without this project's dependencies, the
failure is confusing rather than obvious: `python-dotenv` is missing, so
`backend/.env` is never loaded at all — `core/db/engine.py` and
`tests/dbsetup.py` both swallow that `ImportError` deliberately
(`dbsetup.py` says so outright) — and dozens of tests then fail on
configuration that is in fact present in `.env`. Measured here on
2026-09-04: bare `python` was 3.12's predecessor with no dotenv, `.venv` was
3.12.10 with everything.

**Two secrets must be non-empty or ~80 tests fail.** `ODOO_ENCRYPTION_KEY`
and `WHATSAPP_ENCRYPTION_KEY` ship in `.env.example` as empty placeholders,
and `core/db/odoo_connections_repo.py` (plus the WhatsApp equivalent) does
`os.environ.get(...)` then `if not key: raise` — an **empty string is
falsy**, so a present-but-blank value fails exactly like a missing one. Fill
both, per environment:

```bash
../.venv/Scripts/python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

They only ever en/decrypt values in that environment's own database, so a
local throwaway key is fine — CI commits its own in `ci.yml` for that reason.
With both set, the suite is green (1501 passed, 39 skipped as of 2026-09-04).

The suite runs against the `piloto` tenant over `data-demo/` (see
`tests/conftest.py`). **Careful:** tests write into the data dir — after
running them, restore the seeds with `git checkout -- data-demo/`.

**The suite has its own database.** `tests/dbsetup.py` derives a sibling name
from `DATABASE_URL` (`polpilot` → `polpilot_test`), creates it, replicates the
app role's grants, migrates it to head, and repoints
`DATABASE_URL`/`APP_DATABASE_URL` in `os.environ` before `core.db.engine` is
imported — so spawned subprocesses inherit it too. Override with
`POLPILOT_TEST_DATABASE_URL` / `POLPILOT_TEST_APP_DATABASE_URL`.

Never point the suite at the dev database: `conftest.py` deletes and reseeds
the `demo` tenant's `auth_credentials` at *import* time, so while the two were
shared, merely collecting tests silently rewrote every demo user's dev login
password and left no record of the plaintext. `tests/test_test_db_isolation.py`
guards this and will fail loudly if the isolation is ever lost.

**Local Postgres ports:** `docker-compose.yml` publishes **5434**, matching
`backend/.env`. Don't move it to 5432 — other Postgres containers on a typical
dev machine hold that port, and the collision makes this service come up with
no published port and an apparently empty schema.

## Deploy

`render.yaml` + `Dockerfile` bring everything up as a single Docker service
(`polpilot-app`, compiled frontend served by the backend). See
`deploy/DEPLOY.md` for the runbook and `deploy/ARCHITECTURE.md` for the
topology and why it's shaped this way. There are four secrets, all set in the
hosting dashboard, never in the repo: `ANTHROPIC_API_KEY`,
`POLPILOT_RESET_TOKEN`, `DATABASE_URL` (owner role), and `APP_DATABASE_URL`
(`NOBYPASSRLS` role).
