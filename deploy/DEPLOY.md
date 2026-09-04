# Deploying `polpilot-app` to Render — step by step

**What ships:** the Docker image is tenant-agnostic — it is built once and can
serve any tenant. Which tenant a given service serves is decided entirely by
that service's `POLPILOT_TENANT` environment variable (see
`deploy/ARCHITECTURE.md` for why). Whichever tenant's data directory, `.env`,
and credentials are not that service's own stay out of the image: excluded by
`.dockerignore` **and** re-checked by the Dockerfile's own privacy guard,
which fails the build if anything sensitive slipped in.

This is the runbook — what an operator actually types. For the shape of the
system and why it is built this way, see `deploy/ARCHITECTURE.md`.

## 1 · Creating the service

1. An account at https://render.com (sign in with GitHub works).
2. **New +** → **Blueprint** → connect this repo.
3. Render reads `render.yaml` (repo root) and proposes the service
   **`polpilot-app`** — `runtime: docker`, plan **Starter**, health check
   path `/api/health`.
   - If the Blueprint option doesn't show up: **New +** → **Web Service** →
     this repo → Runtime **Docker** → Health Check Path `/api/health` → plan
     **Starter** (the Free plan sleeps — a bad first impression for anyone
     opening a shared link).

## 2 · The four secrets

Render never reads a secret from `render.yaml` — it only declares that these
keys exist (`sync: false`) and must be set by hand, once, in the service's
**Environment** tab before the first deploy:

| Variable | What it is | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | Real Anthropic API key | Never commit it; it lives only in `backend/.env` locally and in Render's dashboard here. |
| `POLPILOT_RESET_TOKEN` | A long random string (e.g. from https://1password.com/password-generator) | Guards `POST /api/admin/reset-demo` — without the exact token the endpoint 404s and doesn't even reveal it exists. |
| `DATABASE_URL` | Postgres connection string, **owner role** | Used by Alembic (`preDeployCommand`) and by tenant-row lookups. |
| `APP_DATABASE_URL` | Postgres connection string, **`NOBYPASSRLS` role** | Every tenant-scoped query goes through this connection (`backend/core/db/engine.py`). |

**Do not point `APP_DATABASE_URL` at the same role as `DATABASE_URL`.** Row-
Level Security policies do not apply to a role with bypass privileges, so
reusing the owner connection here makes RLS silently do nothing — no error,
no warning, just every tenant boundary quietly gone. `docker/init-app-role.sql`
is the local equivalent that creates the restricted role for the dev database;
a managed Postgres needs that role created by hand (or, once the database
moves off Supabase, by `deploy/migrate.py` — see `deploy/ARCHITECTURE.md` §3.1).

## 3 · What the blueprint sets, and why it's explicit

`render.yaml` also declares non-secret config directly, as literal values —
these are correct for the **demo** service and are not meant to be edited per
deploy:

- **`POLPILOT_TENANT: demo`** — mandatory. `core/paths.py:22` falls back to
  `"demo"` when this is unset, so `deploy/migrate.py` and `deploy/boot.py`
  both refuse to run without it (`[deploy][X] POLPILOT_TENANT is not set`) —
  otherwise a misconfigured service would silently serve the demo tenant's
  users and data instead of failing loudly.
- **`POLPILOT_SEED_ON_BOOT: "1"`** — regenerates and reseeds the whole
  dataset on every boot (`data-demo/generar.py`, then `seed_db.run()`).
  Correct for the demo: Render's filesystem is ephemeral, so every restart
  returns it to a clean, seeded state, and the admin reset endpoint depends
  on it. **Never set this on a productive tenant** — see §4.
- **The `POLPILOT_DEMO_*` block** — `POLPILOT_DEMO_AUTOLOGIN=1` (no login
  screen, the link lands straight on Home), `POLPILOT_DEMO_ROLE_SWITCH=1`
  ("View as" role switcher), `POLPILOT_DEMO_TODAY=2026-07-07` (the seeded
  history's frozen "today"), `POLPILOT_DEMO_MSG_CAP=35` (per-session chat
  message cap), `POLPILOT_DEMO_IP_CAP=60` (per-IP/day spend brake). Also
  grouped in this block, though its name doesn't carry the `DEMO` prefix:
  `POLPILOT_DEFAULT_LANG=en` — the demo defaults to English; a productive
  tenant may want its own default. `render.yaml`'s own comment on this block
  is blunt about it: "Do NOT copy this block to a productive service."
- **`ANGELA_MODEL: claude-sonnet-5`** — not a secret, but deliberately
  explicit rather than left to the code's default. Without this line the
  code falls back to its historical default (`claude-sonnet-4-6`, see
  `backend/config.MODELO_VALIDACION`), and production would silently run a
  different model than the one actually validated. Verify it took effect via
  `GET /api/health` → `modelo_angela`.

All of this used to be baked into the Docker image itself (`Dockerfile`
`ENV`); it now lives entirely in `render.yaml`, which is why a productive
tenant is a copy of the service block rather than a different image.

## 4 · Deploying a productive tenant

This is the case the old, demo-only deploy could not describe. A productive
tenant is **a copy of the `polpilot-app` service block in `render.yaml`**,
not a routing layer inside the existing service — one process still serves
one tenant (`backend/core/db/tenant.py`).

To add one:

1. Duplicate the `services:` entry for `polpilot-app` (either by editing
   `render.yaml` and adding a second service, or by creating a second
   Blueprint/Web Service by hand pointed at the same repo) and give it its
   own `name`.
2. Set **`POLPILOT_TENANT`** to the new tenant's slug.
3. Point **`DATABASE_URL`** and **`APP_DATABASE_URL`** at *that tenant's own
   database* — not the demo's. Reusing the demo's database would mix a
   paying client's data with the public demo's.
4. **Omit `POLPILOT_SEED_ON_BOOT` entirely**, and **omit the whole
   `POLPILOT_DEMO_*` / `POLPILOT_DEFAULT_LANG` block** described in §3. None
   of it belongs on a productive service.

**Do not set `POLPILOT_SEED_ON_BOOT=1` on a productive tenant.** It gates
`data-demo/generar.py`, which deterministically **rewrites the entire
dataset** on every boot. That is exactly what makes the public demo
self-healing on Render's ephemeral filesystem — and on a real tenant with
real data, it is data loss, on every single restart or redeploy. The gate
defaults to off for this reason: a service that forgets to set it fails
safe, not destructively.

## 5 · Deploy order

Render runs three things in sequence, and the order is deliberate:

1. **`preDeployCommand: python deploy/migrate.py`** — brings the schema to
   `alembic upgrade head` before any instance of the new version starts. If
   it fails, **the deploy stops here and the previously running instance
   keeps serving** — a bad migration no longer takes the service down, it
   just blocks the release.
2. **`deploy/boot.py`** (the container's `CMD`) — no longer migrates.
   It ensures the tenant row exists, optionally reseeds (§3), hard-checks
   that the inventory landed in Postgres, copies the canonical dataset for
   the admin reset endpoint, then `exec`s uvicorn on `$PORT`.
3. **The healthcheck** (`GET /api/health`) — only once it passes does Render
   route traffic to the new instance.

## 6 · Post-deploy checklist (incognito window)

1. Open `https://polpilot-app.onrender.com` (or your service's actual
   `onrender.com` URL) → land DIRECTLY as the owner (Aldo), in English, a
   full Home with data ($444.7M tied up, cards, feed). No login screen.
2. Ask Ángela something ("who owes me money?") → she answers with real
   numbers.
3. **Load data** → *Load from photo* → *Try a sample document* → the price
   list → diff with its 2 anomalies → OK → margin changes → "revert the
   price update" in the chat → it reverts.
4. **Documents** → Executive summary → **Download PDF** → a real PDF with the
   logo comes down (this exercises WeasyPrint ON LINUX).
5. **My profile** → *View as* → Vanesa (Collections) and Ramón (Warehouse).
6. Open from an actual **phone** → the owner's pulse widget + chat with the
   camera.
7. **Two tabs at once** chatting (different roles via View as) → zero data
   crossing between them.
8. Send messages past 35 → the cap cuts in with an honest message.
9. Verify tenant isolation: the company is "Distribuidora del Litoral"
   everywhere; `https://…/api/health` reports its source as "(DEMO)"; no
   other tenant's data anywhere in the served bundle (the build's privacy
   guard is what enforces this).

## 7 · Resetting the demo

- **Automatic**: every restart or redeploy returns to the canonical state —
  Render's filesystem is ephemeral, and with `POLPILOT_SEED_ON_BOOT=1` the
  boot re-seeds from scratch every time.
- **Manual** (before sharing the link, or if someone left it in a dirty
  state):
  ```bash
  curl -X POST "https://polpilot-app.onrender.com/api/admin/reset-demo?token=THE_RESET_TOKEN"
  ```
  → `{"ok": true}`. Without the exact token it 404s (it doesn't even reveal
  the endpoint exists). Alternative with no `curl`: **Manual Deploy →
  Restart** in the dashboard.

## 8 · Troubleshooting

- **Logs**: service → **Logs** tab.
  - `deploy/migrate.py` speaks plainly: `[migrate] tenant=…` →
    `[migrate] schema at head`. A failed migration prints
    `[migrate][X] alembic upgrade head failed …` — **the deploy stops there
    and the previously running instance keeps serving**; there is no outage
    to firefight, just a release to fix and retry. Read the deploy log (not
    the service's runtime log) for the Alembic error.
  - `deploy/boot.py` is equally explicit: `[boot] tenant row ensured` →
    (if seeding is on) `[boot] seed verified (generar.py)` →
    `[boot] Postgres seed ok` → `[boot] dataset ok: N artículos (Postgres)` →
    uvicorn starts. A `[boot][X]` line says exactly which step failed.
  - **`[deploy][X] POLPILOT_TENANT is not set`** (from either script): the
    service is missing `POLPILOT_TENANT` in its envVars. Set it — see §3.
    This is deliberate: `core/paths.py` would otherwise silently default to
    `demo`.
- **Build fails at the privacy guard**: something from another tenant made it
  into the build context — check `.dockerignore` and what changed recently.
  This is the guard doing exactly what it's for; nothing gets published.
- **PDF doesn't generate**: look in the Logs for
  `OSError: cannot load library` — a Linux system library WeasyPrint needs is
  missing (the list is in the `Dockerfile`; on local Windows dev it's the
  GTK3 runtime, the image already has all of them).
- **First load is slow**: the analysis warms up at startup (in the FastAPI
  lifespan); give a freshly started instance ~20s before judging it.
- **Chat doesn't respond**: check `ANTHROPIC_API_KEY` in the Environment tab
  first — if it's missing or invalid, Ángela currently falls back to a
  deterministic simulated router (still functional, but with canned
  answers) rather than a real error. Set the key and redeploy.

## Local verification (optional)

A local `docker build` can be blocked by an unfinished Docker Desktop /
WSL setup on a given machine — that is a local environment problem, not a
gap in the protection. The privacy guard runs as a `RUN` step **inside** the
`Dockerfile`, so it executes identically in Render's own build regardless of
whether a local build ever ran: if another tenant's data, an asset, a `.env`,
or credentials reached the image, Render's build fails and nothing gets
published.

When a local build does work:

```bash
docker build -t polpilot-app .
docker run --rm polpilot-app sh -c "ls /app && test ! -e /app/data && echo NO-OTHER-TENANT-DATA-OK"
docker run --rm -p 8080:8000 -e ANTHROPIC_API_KEY=YOUR_KEY -e POLPILOT_TENANT=demo -e POLPILOT_SEED_ON_BOOT=1 polpilot-app
```

Then `http://localhost:8080` → run the §6 checklist (PDF included, to prove
WeasyPrint on Linux).
