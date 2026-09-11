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
  the owner). Passwords are generated on first boot, printed to the console,
  and left in `data-demo/credenciales.json` (gitignored).
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

## Tests

```bash
cd backend && python -m pytest
```
Single test: `pytest tests/test_<name>.py -k <pattern>`.

The suite runs against the `piloto` tenant over `data-demo/` (see
`tests/conftest.py`). **Careful:** tests write into the data dir — after
running them, restore the seeds with `git checkout -- data-demo/`.

## Deploy

`render.yaml` + `Dockerfile` bring everything up as a single Docker service
(compiled frontend served by the backend). See `deploy/DEPLOY.md`. The only
secret is `ANTHROPIC_API_KEY` (set in the hosting dashboard, never in the repo).
