# Prioridades Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. This session executes inline because the user asked to implement immediately.

**Goal:** Ship the unified Prioridades inbox (ranked act + watch) from `docs/superpowers/specs/2026-08-27-prioridades-design.md`.

**Architecture:** `core/priorities.py` composes opportunity cards, alert signals, and floor reports; merges duplicates; ranks; filters by role. `GET /api/prioridades` is the only inbox source. Desktop is master-detail work rows; mobile Insights consumes the same payload.

**Tech Stack:** FastAPI, `core/` deterministic modules, React/Vite desktop + mobile, existing `DrillNegocio` / i18n.

**Spec:** `docs/superpowers/specs/2026-08-27-prioridades-design.md`

## Global Constraints

- English identifiers in new code; Spanish UI copy, bilingual ES/EN at the source.
- Numbers from `core/` only; Ángela cites `priorities.inbox`, never re-ranks.
- No new “Quién ve qué” module. Nav shows if `alertas` OR `oportunidades`.
- Tests against piloto by default; canonical merge/rank on demo via subprocess (`POLPILOT_DEMO_TODAY=2026-07-07`). Restore `data-demo/` if tests write.

## Files

- Create: `backend/core/priorities.py`
- Create: `backend/tests/test_priorities.py`
- Create: `frontend/src/sections/Prioridades.jsx`
- Modify: `backend/authz.py` (any-of feature gate)
- Modify: `backend/main.py`, `backend/angela.py`, `backend/i18n.py`
- Modify: `frontend/src/lib/api.js`, `DesktopApp.jsx`, `App.jsx`, `Inicio.jsx`, `InsightsMobile.jsx`, `MobileApp.jsx`, `CardNegocio.jsx`, `roles.js`, locales
- Stop using: `centroAlertas.js` / `alertasNegocio.jsx` / `AlertasNegocio.jsx` / `OportunidadesNegocio.jsx` as page sources (keep files only if still imported; otherwise leave unused rather than a drive-by delete of i18n-heavy modules if something else still imports them)

## Tasks

### Task 1: Merge, rank, band (synthetic)

`compose_items` is not required yet. Pure functions: `merge_duplicates`, `split_and_rank`.

- [ ] Failing tests in `test_priorities.py`
- [ ] Implement `priorities.py` helpers
- [ ] Tests pass

### Task 2: `inbox(lang, features)` on demo

- [ ] Demo subprocess: no sibling ids `morosos`/`quiebre`/`pico` next to twins
- [ ] `badge == len(act)`; Watch ids not in act; leak-today before large dormant `$`
- [ ] Role filter: warehouse does not see `cobrar_morosos`

### Task 3: API + Ángela

- [ ] `GET /api/prioridades` gated by alertas OR oportunidades
- [ ] Cache key `prioridades` via `analisis_cache`
- [ ] Tool `listar_prioridades`; `navegar_a` includes `prioridades`

### Task 4: Desktop nav + page

- [ ] Leaves: Evolución, Prioridades; aliases redirect
- [ ] `Prioridades.jsx` work rows + master-detail; overlay under ~1200px
- [ ] Badge from API `badge`

### Task 5: Mobile, Home, cleanup

- [ ] InsightsMobile uses `/api/prioridades`
- [ ] Home CTAs → prioridades; today cards from `act`
- [ ] i18n ES/EN; purchasing role navigates to prioridades
