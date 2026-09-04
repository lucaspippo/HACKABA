# Render deployment — from demo service to productive pipeline

- **Date:** 2026-09-04
- **Status:** approved (design); implementation not started
- **Scope:** `render.yaml`, `Dockerfile`, `deploy/` (`boot.py`, `DEPLOY.md`),
  `backend/core/db/engine.py`, `backend/mcp_server.py`, and the API-call layer
  in `frontend/src/lib/`.

## Context

`render.yaml` today declares exactly one service, `polpilot-demo`: a Docker
web service that bundles the compiled Vite frontend, the FastAPI backend, the
synthetic dataset, and a boot script that migrates and seeds Postgres before
uvicorn starts. Postgres itself is external (a Supabase pooler, wired by four
hand-pasted `sync: false` secrets).

The repo is moving from YC pitch demo to real product (root `CLAUDE.md`), so
the goal was to split that monolith into separate Render services — frontend,
API, Postgres — and to stop calling the deployment "demo".

**Investigating the split changed the plan.** Three of the four things worth
fixing turned out to be independent of topology, and two of the proposed
splits turned out to cost more than they return at the current stage (no
paying clients yet). This document records the split as the documented
target, and lands now only the work that is valuable at one service.

### Greenfield

Supabase holds **no productive data**. Every database decision below is
therefore reversible at near-zero cost, whenever it is made — which is the
main reason several of them are deliberately deferred rather than taken now.

## Findings

These four came out of reading the deployment path, and they justify most of
the scope. They are stated here because each one is a live defect or a
latent one, not a preference.

### F1 · Demo-only env is baked into the image

`Dockerfile`'s `ENV` block hard-codes `POLPILOT_TENANT=demo`,
`POLPILOT_DEMO_AUTOLOGIN=1`, `POLPILOT_DEMO_ROLE_SWITCH=1`,
`POLPILOT_DEMO_TODAY=2026-07-07`, and the two spend caps.

Any productive service built from this same image inherits **autologin as
the tenant owner** unless every one of those is individually overridden in
the dashboard. This is the single highest-consequence item in the document:
the failure mode is an unauthenticated production app, and it is silent.

### F2 · The MCP mount stalls the whole process

`backend/mcp_server.py:143` declares `async def call_tool(...)` and then calls
`angela._run_tool(name, args)` **synchronously, on the event loop** — no
`asyncio.to_thread`, no `run_in_threadpool`.

By contrast, 227 of `backend/main.py`'s 230 handlers are plain `def`, which
FastAPI runs in the anyio threadpool; only 3 are `async`. And
`deploy/boot.py:119` execs a single uvicorn process with no `--workers`.

So one MCP client calling a heavy tool (`analisis_rotacion`,
`analisis_estacionalidad`) blocks the only event loop for the duration,
stalling every concurrent web request — the `/api/angela/stream` NDJSON chat
stream included. This is a defect in the currently deployed demo, not a
future risk.

### F3 · Render's connection string names a driver that is not installed

`backend/core/db/engine.py:41,49` pass `os.environ[...]` straight to
`create_engine` with no scheme normalization. Render's `fromDatabase`
properties yield a `postgresql://…` URL, which SQLAlchemy resolves to the
**psycopg2** dialect; `backend/requirements.txt:18` installs only
`psycopg[binary]` (v3). The first query on a Render-provisioned database
therefore dies with `ModuleNotFoundError: No module named 'psycopg2'`.

The existing Supabase URLs avoid this only because they were hand-written
with the `postgresql+psycopg://` prefix.

### F4 · Render Postgres has no `docker-entrypoint-initdb.d`

`docker/init-app-role.sql` creates `polpilot_app` — the `NOBYPASSRLS` role
that `APP_DATABASE_URL` connects as, and without which Row-Level Security
silently does nothing. It runs today only because the local `postgres:16`
container executes `/docker-entrypoint-initdb.d/*.sql` at first init.

A managed Render Postgres has no such hook, so that role has to be created
by a deploy step instead. Mitigating context: migrations `0002`–`0011`+ all
issue `FORCE ROW LEVEL SECURITY`, so even the database owner is subject to
RLS — but the restricted role still has to exist and still has to be the one
the app connects as.

## Decisions

### D1 · One Render service now; the split is documented, not built

**Decision:** keep a single Docker web service. Do not create separate
frontend, API, or MCP services yet. Record the target topology (D2) so the
split is a `render.yaml` change when a paying client makes it worth the
money.

**Why:** the split's benefits — independent scaling, separate deploy
cadence, CDN for the bundle — all accrue at traffic and revenue that do not
exist yet, while its costs are immediate and monthly. At zero clients the
correct optimization is engineering time and burn, not topology.

### D2 · The documented target topology

When the split is worth building, it is this:

```
databases:
  polpilot-db          prod Postgres (Render-managed, PG16)
  polpilot-demo-db     demo Postgres — needs no data migration:
                       boot regenerates it deterministically

services:
  polpilot-web    type: web, runtime: static   rootDir frontend/, CDN, SPA rewrite
  polpilot-api    type: web, runtime: docker   /api + /mcp   healthCheckPath /api/health
  polpilot-demo   type: web, runtime: docker   all-in-one, own bundle, /mcp kept
```

Note on names: `polpilot-demo` above is today's service, which D7 renames to
`polpilot-app` now. Under the split it goes back to demo-specific naming,
because that is what it will then be — the productive traffic having moved to
`polpilot-api`. Two renames rather than one is the price of not knowing today
whether a paying client arrives before the split does; the alternative is
naming today's service for a role it does not yet have.

Verified blueprint field names for that future edit: `databases` (with
`name`, `plan`, `databaseName`, `user`, `postgresMajorVersion`,
`ipAllowList`); `fromDatabase` (properties `connectionString`,
`connectionPoolString`, `user`, `password`, `database`, `host`, `port`);
`fromService` (properties `host`, `port`, `hostport`, `connectionString`);
`preDeployCommand`; static sites as `type: web` + `runtime: static` with
`staticPublishPath`, `buildCommand`, `routes`, `headers`; and
`envVarGroups`.

### D3 · MCP stays mounted in the API process — permanently, not just for now

**Decision:** `/mcp` remains mounted inside the FastAPI app
(`backend/main.py:138`) on every deployment, demo included. No
`polpilot-mcp` service, no `POLPILOT_SERVE_MCP` flag, no separate
`mcp_app.py`, and no `/health` endpoint invented to give an
`Authorization`-gated `/mcp` something Render can probe.

**Why:** F2 looks like an isolation argument for a separate service, but the
fix for F2 is a threadpool hop (D4) — splitting would merely relocate the
stall into the MCP service, where a second client still blocks the first.
Once F2 is fixed, the co-location argument holds on its merits:
`mcp_server.py` is stateless Streamable HTTP ("every request opens and
closes its own internal session"), so there is no session affinity to
arrange and it scales horizontally with the API. The four things a separate
service genuinely buys — independent scaling, a separate auth/rate-limit
surface, an independent deploy cadence, a separate domain — reduce here to
the fourth alone (`api.…/mcp` versus `mcp.…`), because it is the same image,
the same Postgres, the same code, and the same deploy.

The MCP specification is deliberately silent on deployment topology. The
part that is current practice is the transport, and this code is already on
it. The pattern of giving MCP its own service comes from stateful SSE
needing sticky routing, and from standalone MCP servers where the MCP server
*is* the product; PolPilot's is a facade over an API it already runs.

Consequence: `backend/MCP.md`'s claim that "there's no separate service to
deploy or tenant-routing layer to add" stays true and needs no correction.

### D4 · Fix the event-loop stall

**Decision:** `backend/mcp_server.py:155` becomes
`await asyncio.to_thread(angela._run_tool, name, args)`.

**Test:** a slow tool call must not block a concurrent request — assert
concurrency, not just that the call still returns. This is the one test that
would have caught F2, and its absence is why F2 shipped.

### D5 · Reject putting the demo tenant inside one multi-tenant app

**Decision:** do not make the demo a tenant of a single process. Tenancy
stays per-deployment.

**Why:** `backend/core/db/tenant.py`'s `current_tenant_id()` is
`@lru_cache(maxsize=1)` over `core/paths.py:22`'s `TENANT`, read once from
env at import — its own docstring states "one process still serves one
tenant". `auth.py` calls it at 11 sites, and `core/paths.py` isolates the
data directory the same process-global way.

Per-request tenancy therefore means replacing that global with a
contextvar threaded through `auth.py`, every `core/` module, and the
data-dir layer — while that value is precisely what RLS scoping depends on.
It is a security-boundary refactor, and it was proposed as a cost saving.
It is the most expensive option on the table, not the cheapest.

### D6 · The image becomes tenant-agnostic

**Decision:** every `POLPILOT_DEMO_*` variable and `POLPILOT_TENANT` move out
of `Dockerfile`'s `ENV` block and into the service's `envVars` in
`render.yaml`. The image keeps only genuinely image-wide values
(`POLPILOT_STATIC_DIR`, `POLPILOT_CANONICAL_DIR`, `PYTHONUNBUFFERED`).

This fixes F1 and is what actually makes the pipeline "productive": adding
the first paying client becomes a copy of the service block with a different
`POLPILOT_TENANT`, rather than an audit of which demo defaults leaked in.

The `Dockerfile`'s privacy guard is unchanged and stays exactly as strict.
Its invariant still holds: productive data lives in Postgres, never in the
image.

**One catch this creates.** `core/paths.py:22` reads
`os.environ.get("POLPILOT_TENANT", "demo")` — it *defaults to demo*. So once
the variable leaves the image, a productive service that forgets to set it
does not fail; it silently comes up as the demo tenant. That is the same
fail-unsafe shape as F1, just relocated.

The default cannot simply be removed: local dev, `start_demo.py`, and the
test suite all rely on it. So the requirement is enforced at
**deployment time, not import time** — `deploy/migrate.py` and
`deploy/boot.py` both refuse to run when `POLPILOT_TENANT` is unset. Local
dev and tests never call those, so they keep the convenient default while
every deployed service must be explicit.

### D7 · Rename the service to `polpilot-app`

**Decision:** rename `polpilot-demo` → `polpilot-app`, with
`POLPILOT_TENANT=demo` in its `envVars`.

The `.onrender.com` URL changes as a result, which the user has confirmed is
acceptable — the old link is not circulating. A custom domain, which would
decouple the public URL from the service name for good, is out of scope here.

### D8 · Migrations move to `preDeployCommand`

**Decision:** `alembic upgrade head` moves out of `deploy/boot.py` step 1
into the service's `preDeployCommand`, via a new `deploy/migrate.py` that
also ensures the restricted app role exists (F4).

**Why, even at one service:** today a failed migration exits the container,
so the service goes down and Render retries a broken image. With
`preDeployCommand` the deploy fails cleanly and **the old instance keeps
serving**. That is a production-readiness win at near-zero cost, and it is
also the mechanism that prevents two services racing on migrations under D2.

`boot.py` keeps steps 2–7 (tenant row, `generar.py`, seed, hard dataset
verification, canonical copy, exec uvicorn) and no longer migrates.

### D9 · Seeding is demo-only, behind an explicit flag

**Decision:** `boot.py`'s seed path (`generar.py` + `seed_db.run`) is gated
on `POLPILOT_SEED_ON_BOOT=1`, set only on a demo service.

**Why:** `generar.py` regenerates the synthetic dataset deterministically.
On a productive tenant that is data loss. The gate must default to **off**,
so that a new service that forgets to set it fails safe.

The demo's behavior is unchanged: it still re-seeds every boot, which is
what makes Render's ephemeral filesystem and the `/api/admin/reset-demo`
endpoint work.

### D10 · Normalize the database URL scheme

**Decision:** `engine.py` normalizes `postgres://` and `postgresql://` to
`postgresql+psycopg://` before `create_engine`, in one shared helper used by
both `get_engine()` and `get_admin_engine()`.

Fixes F3, is a no-op for the existing hand-written Supabase URLs, and means
a future move to Render Postgres is a URL swap rather than a crash.

### D11 · Consolidate the frontend API layer; defer the cross-origin work

**Decision:** route every `fetch` at a PolPilot endpoint through one
`apiUrl(path)` helper that prefixes a `VITE_API_BASE` defaulting to `""`.

**Correction to the original scope.** This was first written as "~15 call
sites in `frontend/src/lib/`". The actual count is **19 across 9 files**, and
four of them are *outside* `lib/` — `App.jsx:53,55`,
`mobile/EquipoMobile.jsx:23`, `sections/GestionEquipo.jsx:883`,
`sections/ObjetivosPanel.jsx:88`. Six of the `lib/api.js` sites (lines 32, 47,
63, 73, 83, 114) take `path` as a parameter and are already centralized, so
they need the prefix applied once each rather than at every caller.

`apiUrl` lives in its own module, not in `api.js`: `api.js` already imports
`authStore` from `./auth`, so putting the helper in `api.js` and importing it
from `auth.js` would create a cycle.

Default `""` means byte-identical request URLs and **no behavior change**
today. The value is hygiene now, and that the static-site split in D2 becomes
a `render.yaml` edit plus one env var instead of a frontend refactor.

**Explicitly deferred:** widening `CORSMiddleware`'s `allow_origins`
(`backend/main.py:124`, currently three hard-coded localhost entries) and
verifying that `api.js:351`'s `/api/angela/stream` NDJSON stream survives a
cross-origin `fetch` with `Authorization: Bearer`. That verification cannot
be done honestly until two origins exist, and guessing at it is how the most
important surface in the product would break invisibly.

### D12 · Stay on Supabase for now

**Decision:** keep `DATABASE_URL` / `APP_DATABASE_URL` as hand-set
`sync: false` secrets pointing at Supabase. Do not provision Render Postgres
yet.

**Why:** greenfield (see Context) means the move is cheap whenever it
happens, so there is no lock-in to escape and no urgency. Supabase's free
tier is $0 against roughly $6/month for Render Postgres after its 30-day
free window.

**Known caveat, accepted:** Supabase free projects pause after about a week
of inactivity, so an idle demo link may hit a cold database on first open.
If that first impression matters more than the saving, D12 is the decision to
revisit — and D10 is what makes revisiting it a URL swap.

## Out of scope

- Per-request tenant routing (rejected in D5).
- A separate MCP service (rejected in D3).
- Render Postgres provisioning and the app-role bootstrap against it
  (deferred in D12; `deploy/migrate.py` from D8 is where it lands when it
  happens).
- CORS widening and cross-origin stream verification (deferred in D11).
- Custom domains and DNS (noted in D7).
- Preview environments for pull requests.

## Files touched

| File | Change |
|---|---|
| `render.yaml` | Rewritten: service renamed per D7, demo env moved in per D6, `preDeployCommand` per D8, `POLPILOT_SEED_ON_BOOT=1` per D9. Comments in English per the repo standard. |
| `Dockerfile` | `ENV` block reduced to image-wide values (D6). Privacy guard untouched. |
| `deploy/migrate.py` | New. `alembic upgrade head` + app-role assurance (D8, F4); refuses to run with `POLPILOT_TENANT` unset (D6). |
| `deploy/boot.py` | Drops step 1; seed path gated on `POLPILOT_SEED_ON_BOOT` (D8, D9); refuses to run with `POLPILOT_TENANT` unset (D6). |
| `backend/core/db/engine.py` | Scheme normalization helper (D10). |
| `backend/mcp_server.py` | `asyncio.to_thread` at the `_run_tool` call (D4). |
| `frontend/src/lib/apiUrl.js` | New. `apiUrl(path)` — the single `VITE_API_BASE` prefix point (D11). |
| `frontend/src/**` | 19 `fetch` sites across 9 files routed through `apiUrl` (D11) — note four live outside `lib/`. |
| `deploy/DEPLOY.md` | Rewritten in English for the renamed service; documents the D2 target and what D9's flag means for a productive tenant. |

## Testing

- **D4:** a concurrency test — a slow MCP tool call must not delay a
  concurrent request. Fails against today's code.
- **D9:** a productive-shaped configuration (no `POLPILOT_SEED_ON_BOOT`)
  must not invoke `generar.py` or `seed_db.run`.
- **D10:** the normalizer maps `postgres://`, `postgresql://`, and an
  already-correct `postgresql+psycopg://` to the same driver, and leaves the
  rest of the URL untouched.
- **D11:** with `VITE_API_BASE` unset, request URLs are byte-identical to
  today's.
- **D6:** the built image must not carry `POLPILOT_DEMO_AUTOLOGIN` or
  `POLPILOT_TENANT` in its environment — an assertion, so F1 cannot
  regress. And `migrate.py` / `boot.py` must both refuse to run with
  `POLPILOT_TENANT` unset, so D6's relocated fail-unsafe default cannot bite.
- The existing suite runs against the `piloto` tenant over `data-demo/`
  (`backend/tests/conftest.py`) and must stay green. Per the root
  `CLAUDE.md`: restore the seeds with `git checkout -- data-demo/` after
  running it.
