# Productive Render Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the single `polpilot-demo` Render service into a productive, tenant-agnostic deployment pipeline — without splitting services — and fix the four defects found while designing the split.

**Architecture:** The Docker image stops carrying demo-specific configuration; all of it moves to `render.yaml`'s `envVars`. Migrations move out of the container entrypoint into a Render `preDeployCommand`, so a failed migration fails the deploy instead of taking the service down. Dataset seeding becomes opt-in so it can never run against a productive tenant. Two independent bugs are fixed along the way: the MCP tool call that blocks the single event loop, and the database URL scheme that names an uninstalled driver.

**Tech Stack:** Python 3.12 · FastAPI · SQLAlchemy 2 + `psycopg` v3 · Alembic · pytest · React 19 + Vite 7 · Vitest · Docker · Render Blueprints

**Spec:** `docs/superpowers/specs/2026-09-04-render-deployment-productive-design.md` — read it alongside this plan; the decision IDs (D1–D12, F1–F4) referenced below are defined there. The companion architecture doc is `deploy/ARCHITECTURE.md`.

## Global Constraints

- **All code, identifiers, comments, docstrings and commit messages are in English** (root `CLAUDE.md`). Several files you will touch have Spanish comments — that is fine, do not mass-translate them; write new and modified lines in English.
- **Do not restructure unrelated code.** Migrate a file's naming only when already working substantially in it.
- **Use the repo venv's interpreter, never bare `python`.** On this machine bare
  `python` is **3.11.5 without `python-dotenv`**, while the project requires 3.12+ and
  `.venv/Scripts/python.exe` is **3.12.10** with the dependencies installed. With
  `python-dotenv` absent, `backend/.env` is never loaded — `core/db/engine.py` and
  `tests/dbsetup.py` both swallow the `ImportError` (`dbsetup.py:139` says so) — which
  makes `ODOO_ENCRYPTION_KEY`, `WHATSAPP_ENCRYPTION_KEY` and the database URLs look
  unset and produces dozens of spurious failures. This cost Task 1 a full round of
  bogus test evidence.
- **Backend tests:** run from `backend/` with `../.venv/Scripts/python.exe -m pytest`.
  Single test: `../.venv/Scripts/python.exe -m pytest tests/test_x.py -k pattern`.
  Every `python -m pytest` shown in a task below means that interpreter.
- **After running the backend suite, restore the seeds:** `git checkout -- data-demo/` (the suite writes into the data dir).
- **The suite has its own database** (`polpilot_test`, provisioned by `tests/dbsetup.py`). Never point it at the dev database.
- **The suite runs as tenant `piloto`**, pinned in `tests/conftest.py`. Tests that need `demo` behavior shell out to a subprocess with `POLPILOT_TENANT=demo` — see `tests/test_deploy_hardening.py` for the established pattern.
- **Frontend tests are Vitest and must be named `*.test.ts` or `*.test.tsx`** — `vite.config.js`'s `test.include` is `["src/**/*.test.{ts,tsx}"]`, so a `.js` test file is silently never run. Run with `npm run test` in `frontend/`.
- **`npm run typecheck`** (`tsc --noEmit`) must pass; Vite/esbuild does not typecheck.
- **No new Python dependencies.** In particular there is no YAML parser installed — assert against `render.yaml` and `Dockerfile` as text.
- **Local Postgres is on port 5434**, matching `backend/.env`. Do not change it to 5432.
- **Commit after every task.** Frequent, scoped commits.

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/deploy_guard.py` | **New.** One job: refuse to boot a deployment whose tenant is not explicit. Top-level in `backend/` (not `core/`) because it is app/deploy plumbing, not a business domain — and because tests import `backend/`'s top-level modules directly (`import auth`, `import config`). |
| `backend/core/db/url.py` | **New.** One job: normalize a Postgres URL to the installed driver. Separate from `engine.py` so it is testable without touching engine state or env. |
| `backend/core/db/engine.py` | Modified: both engine builders route their URL through the normalizer. |
| `backend/mcp_server.py` | Modified: the tool dispatch stops blocking the event loop. |
| `deploy/migrate.py` | **New.** The pre-deploy step: guard the tenant, run Alembic. |
| `deploy/boot.py` | Modified: guard the tenant, no longer migrates, seeds only when asked. |
| `Dockerfile` | Modified: `ENV` reduced to image-wide values. |
| `render.yaml` | Rewritten: renamed service, demo config as `envVars`, `preDeployCommand`. |
| `frontend/src/lib/apiUrl.js` | **New.** One job: prefix a request path with `VITE_API_BASE`. Its own module to avoid the `api.js` ↔ `auth.js` import cycle. |
| `frontend/src/**` (9 files) | Modified: every PolPilot `fetch` goes through `apiUrl`. |
| `deploy/DEPLOY.md` | Rewritten in English for the renamed service and the new flags. |
| `deploy/ARCHITECTURE.md` | Updated: §2 stops being "planned" and becomes current. |

**Task order rationale:** Tasks 1–3 are self-contained bug fixes with no dependencies, safe to land and deploy on their own. Task 4 introduces the tenant guard that Tasks 5–6 depend on. Tasks 5–6 change the deployment contract and must land together with the docs (Task 7). Task 8 (frontend) is independent of all of them and can be done in any order — it is last because it delivers no behavior change today.

---

### Task 1: Stop the MCP tool call from blocking the event loop

Fixes **F2** per **D4**. This is a live defect in the deployed demo: `mcp_server.py:143` is an `async def` that calls `angela._run_tool` synchronously, and `deploy/boot.py` runs a single uvicorn worker with no `--workers`. One MCP client calling a heavy tool stalls every concurrent web request, including the `/api/angela/stream` chat stream.

**Files:**
- Modify: `backend/mcp_server.py:155`
- Test: `backend/tests/test_mcp_server.py` (append)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: nothing later tasks rely on.

**Why the test asserts a thread identity rather than timing:** a timing test ("the loop stayed responsive") is flaky under CI load. "`_run_tool` ran on a thread that is not the event loop's thread" is the same property, deterministically.

**Context you need:** `angela`'s session is request-scoped via `contextvars` (`angela.py:35-43`), and `_set_sesion` is called *before* the tool runs. `asyncio.to_thread` copies the current context into the worker thread, so the session still propagates — `angela.py:33`'s own comment already anticipates executor threads. Do not move `_set_sesion` into the thread.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_mcp_server.py`. Note the existing `tokens` fixture and `_mcp_call` helper at the top of that file — this test needs its own runner because it must observe the loop thread from inside the async body.

```python
def test_run_tool_does_not_run_on_the_event_loop(tokens, monkeypatch):
    """A heavy MCP tool must not occupy the event loop: on a single uvicorn
    worker that would stall every concurrent web request, the chat stream
    included. Asserting the executing thread is the deterministic form of
    'the loop stayed free' — a timing assertion would flake under CI load."""
    seen = {}
    real_run_tool = angela._run_tool

    def spy(name, args):
        seen["tool_thread"] = threading.get_ident()
        return real_run_tool(name, args)

    monkeypatch.setattr(angela, "_run_tool", spy)

    session_manager = StreamableHTTPSessionManager(
        app=mcp_server.server, json_response=True, stateless=True)

    async def asgi(scope, receive, send):
        await session_manager.handle_request(scope, receive, send)

    async def run():
        seen["loop_thread"] = threading.get_ident()
        transport = httpx.ASGITransport(app=asgi)
        headers = {"Authorization": f"Bearer {tokens['emilio']}"}

        def factory(**kw):
            kw.pop("transport", None)
            return httpx.AsyncClient(transport=transport, headers=headers, **kw)

        async with session_manager.run():
            async with streamablehttp_client("http://mcp.test/mcp",
                                             httpx_client_factory=factory) as (r, w, _):
                async with ClientSession(r, w) as session:
                    await session.initialize()
                    await session.call_tool("resumen_negocio", {})

    asyncio.run(run())

    assert "tool_thread" in seen, "_run_tool was never called"
    assert seen["tool_thread"] != seen["loop_thread"], (
        "angela._run_tool ran on the event loop thread — a slow tool call "
        "will stall every concurrent request on the single uvicorn worker"
    )
```

Add `import threading` and `import angela` to that file's imports if they are not already present (it currently imports `asyncio`, `httpx`, `pytest`, `auth`, `main`, `mcp_server`, and the MCP client symbols).

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/test_mcp_server.py -k does_not_run_on_the_event_loop -v
```

Expected: **FAIL** on the last assertion — the two thread ids are equal, because `_run_tool` currently runs inline on the loop.

If instead it fails with `_run_tool was never called`, the `factory`/`streamablehttp_client` wiring drifted from the version in `_mcp_call`; copy that helper's current shape.

- [ ] **Step 3: Make the change**

In `backend/mcp_server.py`, add `import asyncio` to the imports, then change the dispatch line:

```python
    args = _sanitize_args(name, arguments)
    # Off the event loop: _run_tool is synchronous, CPU-bound `core/` work and
    # uvicorn runs a single worker here, so calling it inline stalls every
    # concurrent request — main.py's own handlers avoid this by being plain
    # `def`, which FastAPI hands to the anyio threadpool. asyncio.to_thread
    # copies the current context, so the contextvars session _set_sesion just
    # installed still applies inside the thread.
    result, _accion = await asyncio.to_thread(angela._run_tool, name, args)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_mcp_server.py -v
```

Expected: **PASS**, all of them — the whole file, not just the new test, because the session must still reach the tool through the thread boundary. If a pre-existing feature-gating test now fails, the contextvars context is not propagating and the fix is wrong: do not "fix" it by moving `_set_sesion` inside the thread.

- [ ] **Step 5: Commit**

```bash
git add backend/mcp_server.py backend/tests/test_mcp_server.py
git commit -m "Run MCP tool calls off the event loop

mcp_server's call_tool is async but called angela._run_tool inline, and
uvicorn runs one worker with no --workers. A single MCP client calling a
heavy tool therefore stalled every concurrent web request, including the
/api/angela/stream chat stream. main.py avoids this by keeping 227 of its
230 handlers plain def, which FastAPI runs in the anyio threadpool.

The test asserts the executing thread rather than elapsed time, so it
states the property without flaking under load."
```

---

### Task 2: Normalize the database URL to the installed driver

Fixes **F3** per **D10**. `engine.py:41,49` pass `os.environ[...]` straight to `create_engine`. A `postgresql://…` URL — which is what Render's `fromDatabase` properties and most managed providers hand you — resolves to the **psycopg2** dialect, and `requirements.txt:18` installs only `psycopg[binary]` (v3). Today's Supabase URLs work only because someone hand-wrote the `+psycopg` prefix.

**Files:**
- Create: `backend/core/db/url.py`
- Modify: `backend/core/db/engine.py:38-52`
- Test: `backend/tests/test_db_url.py` (new)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `core.db.url.normalize_driver(url: str) -> str` — used by Task 2 only, but keep the name stable; `deploy/migrate.py` in Task 5 does **not** need it (Alembic builds its own engine from `migrations/env.py`).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_db_url.py`:

```python
"""Postgres URL normalization (core/db/url.py).

Managed providers hand out `postgresql://…`, which SQLAlchemy maps to the
psycopg2 dialect — and only psycopg v3 is installed (requirements.txt).
Without normalization the first query against such a URL dies with
ModuleNotFoundError, so this is the guard for that whole class of outage.
"""
from __future__ import annotations

import pytest

from core.db.url import normalize_driver


@pytest.mark.parametrize("given", [
    "postgresql://u:p@host:5432/db",
    "postgres://u:p@host:5432/db",
    "postgresql+psycopg://u:p@host:5432/db",
])
def test_every_postgres_spelling_lands_on_psycopg(given):
    assert normalize_driver(given).startswith("postgresql+psycopg://")


def test_the_rest_of_the_url_is_untouched():
    got = normalize_driver("postgres://u:p@host:6543/db?sslmode=require")
    assert got == "postgresql+psycopg://u:p@host:6543/db?sslmode=require"


def test_an_explicit_other_driver_is_left_alone():
    # Someone who deliberately asked for a different driver gets it: this
    # normalizer exists to fix an omission, not to override a choice.
    given = "postgresql+asyncpg://u:p@host:5432/db"
    assert normalize_driver(given) == given


def test_a_non_postgres_url_is_left_alone():
    given = "sqlite:///tmp/x.db"
    assert normalize_driver(given) == given


def test_empty_and_none_are_passed_through_unchanged():
    # engine.py raises its own KeyError for a missing variable; this helper
    # must not turn that into a confusing parse error.
    assert normalize_driver("") == ""
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/test_db_url.py -v
```

Expected: **FAIL** at collection — `ModuleNotFoundError: No module named 'core.db.url'`.

- [ ] **Step 3: Write the implementation**

Create `backend/core/db/url.py`:

```python
"""Normalizes a Postgres URL to the driver this project actually installs.

requirements.txt ships `psycopg[binary]` (v3) and nothing else, but
SQLAlchemy maps a bare `postgresql://` (and the `postgres://` alias managed
providers still emit) to the *psycopg2* dialect. A URL copied from a hosting
dashboard therefore fails at the first query with ModuleNotFoundError rather
than at startup, which is a slow and confusing way to find out.

An explicitly requested driver (`postgresql+asyncpg://`) is respected: this
exists to fill in an omission, not to override a decision.
"""
from __future__ import annotations

_TARGET = "postgresql+psycopg://"
_BARE_PREFIXES = ("postgresql://", "postgres://")


def normalize_driver(url: str) -> str:
    if not url:
        return url
    for prefix in _BARE_PREFIXES:
        if url.startswith(prefix):
            return _TARGET + url[len(prefix):]
    return url
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd backend && python -m pytest tests/test_db_url.py -v
```

Expected: **PASS** (7 tests — the parametrized one counts as 3).

- [ ] **Step 5: Route both engines through it**

In `backend/core/db/engine.py`, add the import alongside the existing ones:

```python
from core.db.url import normalize_driver
```

Then change the two builders:

```python
def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        url = normalize_driver(os.environ["APP_DATABASE_URL"])
        _ENGINE = create_engine(url, pool_pre_ping=True)
    return _ENGINE


def get_admin_engine() -> Engine:
    global _ADMIN_ENGINE
    if _ADMIN_ENGINE is None:
        url = normalize_driver(os.environ["DATABASE_URL"])
        _ADMIN_ENGINE = create_engine(url, pool_pre_ping=True)
    return _ADMIN_ENGINE
```

Keep `os.environ[...]` subscript access, not `.get()` — a missing variable must still raise `KeyError` immediately.

- [ ] **Step 6: Run the full suite to verify nothing regressed**

```bash
cd backend && python -m pytest -q
git checkout -- data-demo/
```

Expected: the same result as before your change (the local URLs already carry `+psycopg`, so this is a no-op for them). Restoring `data-demo/` is required — the suite writes into it.

- [ ] **Step 7: Commit**

```bash
git add backend/core/db/url.py backend/core/db/engine.py backend/tests/test_db_url.py
git commit -m "Normalize Postgres URLs to the installed psycopg v3 driver

SQLAlchemy maps a bare postgresql:// (and the postgres:// alias managed
providers still emit) to psycopg2, which this project does not install —
so a connection string copied from a hosting dashboard fails at the first
query with ModuleNotFoundError instead of at startup. Today's URLs work
only because the +psycopg prefix was written by hand.

An explicit driver is respected; this fills in an omission rather than
overriding a choice."
```

---

### Task 3: Refuse to deploy without an explicit tenant

Implements the guard **D6** requires. This must land *before* Task 6 removes `POLPILOT_TENANT` from the image, because `core/paths.py:22` reads `os.environ.get("POLPILOT_TENANT", "demo")` — **it defaults to demo**. Without this guard, taking the variable out of the image does not fix F1, it relocates it: a productive service that forgot to set it would silently serve the demo tenant.

The default cannot simply be deleted — local dev, `start_demo.py` and the whole test suite rely on it. So the requirement is enforced at *deploy* time, in the two entrypoints, which local dev and tests never call.

**Files:**
- Create: `backend/deploy_guard.py`
- Test: `backend/tests/test_deploy_guard.py` (new)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `deploy_guard.require_tenant(env: Mapping[str, str] | None = None) -> str` — returns the tenant slug, raises `SystemExit` with a diagnostic message when it is missing or blank. Task 5 (`deploy/migrate.py`) and Task 6 (`deploy/boot.py`) both call it. Also produces `deploy_guard.seed_on_boot(env: Mapping[str, str] | None = None) -> bool`, which Task 6 uses for D9's gate.

**Why `SystemExit` and not a custom exception:** both callers are scripts whose contract is "exit non-zero and let Render fail the deploy". `boot.py` already has a `fallar()` helper that prints and `sys.exit(1)`s; raising `SystemExit` from the guard keeps that behavior without either script needing a try/except.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_deploy_guard.py`:

```python
"""Deploy-time environment guards (backend/deploy_guard.py).

core/paths.py defaults POLPILOT_TENANT to "demo" so that local dev, the test
suite and start_demo.py need no configuration. That default is convenient
locally and dangerous in a deployment: once the variable is no longer baked
into the image, a productive service that forgets to set it would silently
come up serving the demo tenant. These guards make the deploy entrypoints —
and only them — demand it explicitly.
"""
from __future__ import annotations

import pytest

import deploy_guard


def test_require_tenant_returns_the_configured_slug():
    assert deploy_guard.require_tenant({"POLPILOT_TENANT": "horizonte"}) == "horizonte"


@pytest.mark.parametrize("env", [
    {},
    {"POLPILOT_TENANT": ""},
    {"POLPILOT_TENANT": "   "},
])
def test_require_tenant_exits_when_absent_or_blank(env):
    with pytest.raises(SystemExit) as excinfo:
        deploy_guard.require_tenant(env)
    assert excinfo.value.code != 0


def test_require_tenant_names_the_variable_in_its_message(capsys):
    with pytest.raises(SystemExit):
        deploy_guard.require_tenant({})
    printed = capsys.readouterr().out + capsys.readouterr().err
    assert "POLPILOT_TENANT" in printed


def test_require_tenant_does_not_accept_the_implicit_default(monkeypatch):
    # The point of the guard: core/paths.py's "demo" fallback must not be
    # what a deployment silently inherits. An explicit demo is fine; an
    # absent variable is not, even though paths.py would resolve it.
    monkeypatch.delenv("POLPILOT_TENANT", raising=False)
    with pytest.raises(SystemExit):
        deploy_guard.require_tenant({})
    assert deploy_guard.require_tenant({"POLPILOT_TENANT": "demo"}) == "demo"


@pytest.mark.parametrize("value,expected", [
    ("1", True),
    ("0", False),
    ("", False),
])
def test_seed_on_boot_is_opt_in(value, expected):
    assert deploy_guard.seed_on_boot({"POLPILOT_SEED_ON_BOOT": value}) is expected


def test_seed_on_boot_defaults_to_off():
    # Fails safe: regenerating the dataset on a productive tenant is data
    # loss, so a service that says nothing must not seed.
    assert deploy_guard.seed_on_boot({}) is False
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/test_deploy_guard.py -v
```

Expected: **FAIL** at collection — `ModuleNotFoundError: No module named 'deploy_guard'`.

- [ ] **Step 3: Write the implementation**

Create `backend/deploy_guard.py`:

```python
"""Environment guards for the deploy entrypoints (deploy/migrate.py and
deploy/boot.py).

Why these live here and not in core/paths.py: paths.py deliberately defaults
POLPILOT_TENANT to "demo" so local dev, the test suite and start_demo.py work
with no configuration at all. Removing that default would break all three.
But a *deployment* inheriting it silently is the failure this module exists
to prevent — a productive service that forgot the variable would come up
serving the demo tenant, with demo users and demo data, and nothing would
say so.

So the rule is enforced where it belongs: at deploy time, in the two scripts
Render runs. Local dev and tests never call them, and keep the default.
"""
from __future__ import annotations

import os
import sys
from typing import Mapping


def _env(env: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if env is None else env


def require_tenant(env: Mapping[str, str] | None = None) -> str:
    """The tenant this deployment serves, or exit non-zero saying so.

    Exits rather than raising a custom exception because both callers are
    scripts whose contract is to fail the deploy loudly."""
    tenant = _env(env).get("POLPILOT_TENANT", "").strip()
    if not tenant:
        print(
            "[deploy][X] POLPILOT_TENANT is not set.\n"
            "            Every deployment must name its tenant explicitly: "
            "core/paths.py falls back to 'demo', so an unset variable would "
            "silently serve the demo tenant's users and data.\n"
            "            Set it in the service's envVars (see render.yaml).",
            flush=True,
        )
        raise SystemExit(1)
    return tenant


def seed_on_boot(env: Mapping[str, str] | None = None) -> bool:
    """Whether this deployment should regenerate and seed its dataset.

    Opt-in, and it must stay opt-in: data-demo/generar.py rewrites the whole
    dataset deterministically, which is exactly right for the demo (Render's
    filesystem is ephemeral, and the admin reset endpoint depends on it) and
    is data loss on a productive tenant."""
    return _env(env).get("POLPILOT_SEED_ON_BOOT", "").strip() == "1"
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd backend && python -m pytest tests/test_deploy_guard.py -v
```

Expected: **PASS** (11 tests, counting the parametrized cases).

- [ ] **Step 5: Commit**

```bash
git add backend/deploy_guard.py backend/tests/test_deploy_guard.py
git commit -m "Add deploy-time guards for the tenant and the seed flag

core/paths.py defaults POLPILOT_TENANT to demo, which is what makes local
dev and the suite configuration-free — and what would make a productive
service that forgot the variable silently serve the demo tenant once the
value stops being baked into the image. Enforce it in the deploy
entrypoints instead, which local dev and tests never run.

seed_on_boot defaults to off for the same fail-safe reason: generar.py
rewrites the whole dataset, which is correct for the demo and data loss
anywhere else."
```

---

### Task 4: Add the pre-deploy migration step

Implements **D8**. Today `deploy/boot.py` step 1 runs `alembic upgrade head` inside the container, so a failed migration exits the process, the healthcheck fails, and the *service goes down*. As a Render `preDeployCommand` the deploy fails cleanly and the previously running instance keeps serving. It is also the mechanism that would stop two services racing on migrations if the split in D2 is ever built.

**Files:**
- Create: `deploy/migrate.py`
- Test: `backend/tests/test_deploy_scripts.py` (new)

**Interfaces:**
- Consumes: `deploy_guard.require_tenant` (Task 3).
- Produces: `deploy/migrate.py` as a runnable script — `python deploy/migrate.py` from the repo root. Task 5 references it in `render.yaml`'s `preDeployCommand`; Task 6 removes the equivalent step from `boot.py`.

**Note on scope:** D12 keeps the database on Supabase, where `docker/init-app-role.sql` has already created the restricted role. So this script does **not** create the app role — F4's role bootstrap belongs to the future move to Render Postgres, and this is the file it lands in when that happens. Say so in the docstring so the next person knows where it goes.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_deploy_scripts.py`:

```python
"""The deploy entrypoints (deploy/migrate.py, deploy/boot.py).

These are scripts Render runs, not importable app code, so they are checked
the way their failure actually shows up: run them with a deliberately
incomplete environment and assert they refuse, loudly and non-zero, instead
of proceeding on a default.
"""
from __future__ import annotations

import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIGRATE = os.path.join(REPO_ROOT, "deploy", "migrate.py")


def _run(script: str, env_overrides: dict[str, str | None]):
    env = dict(os.environ)
    for k, v in env_overrides.items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    return subprocess.run([sys.executable, script], capture_output=True,
                          text=True, cwd=REPO_ROOT, timeout=120, env=env)


def test_migrate_refuses_without_an_explicit_tenant():
    r = _run(MIGRATE, {"POLPILOT_TENANT": None})
    assert r.returncode != 0
    assert "POLPILOT_TENANT" in (r.stdout + r.stderr)


def test_migrate_refuses_a_blank_tenant():
    r = _run(MIGRATE, {"POLPILOT_TENANT": "   "})
    assert r.returncode != 0
    assert "POLPILOT_TENANT" in (r.stdout + r.stderr)
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/test_deploy_scripts.py -v
```

Expected: **FAIL** — `deploy/migrate.py` does not exist, so the subprocess exits non-zero for the wrong reason and the `"POLPILOT_TENANT" in output` assertion fails on Python's `No such file or directory` message. That distinction matters: the assertion on the message, not just the exit code, is what makes this test meaningful.

- [ ] **Step 3: Write the implementation**

Create `deploy/migrate.py`:

```python
"""Render's preDeployCommand: bring the schema to head before any instance
of the new version starts.

Why this is not in boot.py any more: when Alembic ran inside the container,
a failed migration exited the process, the healthcheck failed, and the
service went DOWN. As a pre-deploy step the deploy fails and the previously
running instance keeps serving — the failure stops being an outage.

It is also what keeps migrations single-writer if the service is ever split
into several (see D2 in the design doc): a pre-deploy step runs once per
deploy, while N booting containers would race.

Not here yet, deliberately: creating the restricted NOBYPASSRLS role that
APP_DATABASE_URL connects as. On Supabase that role already exists
(docker/init-app-role.sql is its local equivalent). A managed Render Postgres
has no docker-entrypoint-initdb.d hook, so when the database moves (D12),
this is the file that role bootstrap belongs in.
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BACKEND = os.path.join(ROOT, "backend")

sys.path.insert(0, BACKEND)
import deploy_guard  # noqa: E402  (needs BACKEND on the path first)


def main() -> None:
    tenant = deploy_guard.require_tenant()
    print(f"[migrate] tenant={tenant}", flush=True)

    r = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True, text=True, cwd=BACKEND, timeout=300,
    )
    if r.returncode != 0:
        print(r.stdout[-1500:] + r.stderr[-1500:], flush=True)
        print("[migrate][X] alembic upgrade head failed — the deploy stops "
              "here and the running instance keeps serving", flush=True)
        raise SystemExit(1)
    print("[migrate] schema at head", flush=True)


if __name__ == "__main__":
    main()
```

The timeout is 300s, not `boot.py`'s 120s: a pre-deploy step is no longer racing a healthcheck, and a first migration against a fresh database legitimately takes longer.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_deploy_scripts.py -v
```

Expected: **PASS** (2 tests). Both exercise only the guard, so neither needs a reachable database.

- [ ] **Step 5: Verify the happy path by hand**

```bash
cd backend && POLPILOT_TENANT=piloto python ../deploy/migrate.py
```

Expected: `[migrate] tenant=piloto` then `[migrate] schema at head`. This needs the local Postgres up (`docker compose up -d db`, port **5434**). If it reports a connection error, that is your local database, not this script.

- [ ] **Step 6: Commit**

```bash
git add deploy/migrate.py backend/tests/test_deploy_scripts.py
git commit -m "Add deploy/migrate.py as the pre-deploy migration step

Running Alembic inside the container meant a failed migration exited the
process, failed the healthcheck and took the service down. As Render's
preDeployCommand the deploy fails instead and the running instance keeps
serving. It also keeps migrations single-writer if the service is ever
split, where N booting containers would race.

Records where the NOBYPASSRLS role bootstrap goes when the database moves
off Supabase — Render Postgres has no docker-entrypoint-initdb.d."
```

---

### Task 5: Make boot.py tenant-explicit and seed only on request

Implements **D9** and the `boot.py` half of **D8**. After this, the entrypoint cannot regenerate a productive tenant's dataset, and no longer migrates.

**Files:**
- Modify: `deploy/boot.py` (docstring, steps 1 and 3–4)
- Test: `backend/tests/test_deploy_scripts.py` (append)

**Interfaces:**
- Consumes: `deploy_guard.require_tenant` and `deploy_guard.seed_on_boot` (Task 3).
- Produces: `boot.py`'s new contract — migrations are gone, seeding requires `POLPILOT_SEED_ON_BOOT=1`. Task 6's `render.yaml` must set that flag on the demo service, and Task 7 documents it.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_deploy_scripts.py`:

```python
BOOT = os.path.join(REPO_ROOT, "deploy", "boot.py")


def test_boot_refuses_without_an_explicit_tenant():
    r = _run(BOOT, {"POLPILOT_TENANT": None})
    assert r.returncode != 0
    assert "POLPILOT_TENANT" in (r.stdout + r.stderr)


def test_boot_no_longer_runs_alembic():
    # Migrations belong to deploy/migrate.py (the preDeployCommand) so that a
    # failed migration fails the deploy instead of taking the service down.
    source = open(BOOT, encoding="utf-8").read()
    assert "alembic" not in source.lower()


def test_boot_seeding_is_gated_on_the_flag():
    # generar.py rewrites the whole dataset: on a productive tenant that is
    # data loss, so the seed path must be reachable only via the flag.
    source = open(BOOT, encoding="utf-8").read()
    assert "seed_on_boot" in source
    # Naming the flag in a log line is good; re-reading it here is not — the
    # default must live in deploy_guard alone, or the two can disagree.
    assert 'environ.get("POLPILOT_SEED_ON_BOOT"' not in source
    assert "environ['POLPILOT_SEED_ON_BOOT'" not in source
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_deploy_scripts.py -v
```

Expected: the three new tests **FAIL** — `boot.py` still contains `alembic`, has no `seed_on_boot`, and does not guard the tenant. The two from Task 4 keep passing.

- [ ] **Step 3: Make the change**

In `deploy/boot.py`:

**(a)** Put `BACKEND` on the path and import the guard at the top, next to the existing constants:

```python
sys.path.insert(0, BACKEND)
import deploy_guard  # noqa: E402  (needs BACKEND on the path first)
```

**(b)** Delete step 1 entirely — the `alembic upgrade head` `subprocess.run` block and its `print`.

**(c)** Replace the top of `main()` so it guards first:

```python
def main() -> None:
    # Migrations are NOT here any more: deploy/migrate.py runs them as
    # Render's preDeployCommand, so a failed migration fails the deploy
    # instead of taking the running service down.
    tenant = deploy_guard.require_tenant()
    sys.path.insert(0, DATA_DIR)
    import seed_db
```

and drop the old `tenant = os.environ.get("POLPILOT_TENANT", "demo")` line together with the now-duplicated `sys.path.insert(0, BACKEND)`.

**(d)** Wrap steps 3 and 4 (the `generar.py` subprocess and `seed_db.run`) in the flag, keeping `ensure_tenant` unconditional — a tenant row is needed to serve, not only to seed:

```python
    # 2 · the tenant row must exist before generar.py — see the module
    #     docstring for the ordering bug this prevents.
    try:
        seed_db.ensure_tenant(tenant)
    except Exception as e:  # noqa: BLE001
        fallar(f"seed_db.ensure_tenant() failed ({e}) — the server does NOT come up without data")
    print(f"[boot] tenant row ensured (tenant={tenant})", flush=True)

    # 3-4 · dataset regeneration + seed: DEMO ONLY. generar.py rewrites the
    #       whole dataset deterministically, which is what makes the public
    #       demo self-healing on Render's ephemeral filesystem — and is data
    #       loss on a productive tenant. Opt-in, defaulting to off.
    if deploy_guard.seed_on_boot():
        gen = os.path.join(DATA_DIR, "generar.py")
        if not os.path.exists(gen):
            fallar(f"{gen} does not exist — did the image copy data-demo/?")
        r = subprocess.run([sys.executable, gen], capture_output=True, text=True,
                           cwd=DATA_DIR, timeout=180)
        if r.returncode != 0:
            print(r.stdout[-1500:] + r.stderr[-1500:], flush=True)
            fallar("generar.py failed — the server does NOT come up without data")
        print("[boot] seed verified (generar.py)", flush=True)

        try:
            seed_db.run(tenant)
        except Exception as e:  # noqa: BLE001
            fallar(f"seed_db.run() failed ({e}) — the server does NOT come up without data")
        print(f"[boot] Postgres seed ok (tenant={tenant})", flush=True)
    else:
        print("[boot] seeding skipped (POLPILOT_SEED_ON_BOOT is not 1)", flush=True)
```

**(e)** Leave steps 5–7 (the hard dataset verification, the canonical copy, `exec uvicorn`) exactly as they are. Step 5 still guards a productive tenant correctly: it asserts the inventory is non-empty *in Postgres*, which is true for a real tenant with real data and false for a misconfigured one.

**(f)** Update the module docstring: it currently numbers seven steps starting with Alembic. Renumber, say migrations moved to `deploy/migrate.py` and why, and note the seed gate. Write the new docstring in English.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_deploy_scripts.py -v
```

Expected: **PASS** (5 tests).

- [ ] **Step 5: Prove behaviorally that a productive shape never seeds**

The three tests above assert on `boot.py`'s *source text*, which catches the
gate being deleted but does not prove the gate works. D9's real requirement is
behavioral: with no flag set, `generar.py` and `seed_db.run` must never be
reached. Append this to `backend/tests/test_deploy_scripts.py`, moving the
three new imports up to the module's existing import block rather than
leaving them mid-file:

```python
import json
import subprocess
import tempfile


def _boot_with_sentinel_data_dir(seed_flag: str | None):
    """Runs boot.py against a throwaway data dir whose generar.py and seed_db
    only record that they were called. Returns the set of markers written.

    boot.py inserts DATA_DIR at the front of sys.path and imports seed_db from
    it, so the sentinel dir must provide that module too — otherwise the run
    dies on the import before ever reaching the gate under test."""
    data_dir = tempfile.mkdtemp(prefix="polpilot-bootgate-")
    marker = os.path.join(data_dir, "markers.jsonl")

    def _sentinel(name: str) -> str:
        return (
            "import json
"
            f"open({marker!r}, 'a', encoding='utf-8')"
            f".write(json.dumps({name!r}) + '\n')
"
        )

    with open(os.path.join(data_dir, "generar.py"), "w", encoding="utf-8") as fh:
        fh.write(_sentinel("generar"))
    with open(os.path.join(data_dir, "seed_db.py"), "w", encoding="utf-8") as fh:
        fh.write(
            "import json
"
            f"_M = {marker!r}
"
            "def _mark(w):
"
            "    open(_M, 'a', encoding='utf-8').write(json.dumps(w) + '\n')
"
            "def ensure_tenant(tenant):
"
            "    _mark('ensure_tenant')
"
            "def run(tenant):
"
            "    _mark('run')
"
        )

    overrides = {"POLPILOT_TENANT": "piloto", "POLPILOT_DATA_DIR": data_dir,
                 "POLPILOT_CANONICAL_DIR": None, "POLPILOT_SEED_ON_BOOT": seed_flag}
    try:
        _run(BOOT, overrides)
    except subprocess.TimeoutExpired:
        pass  # got as far as serving; the markers are what we assert on
    if not os.path.exists(marker):
        return set()
    with open(marker, encoding="utf-8") as fh:
        return {json.loads(line) for line in fh if line.strip()}


def test_a_productive_shape_never_regenerates_the_dataset():
    markers = _boot_with_sentinel_data_dir(seed_flag=None)
    assert "generar" not in markers, "generar.py ran without the flag — data loss"
    assert "run" not in markers, "seed_db.run ran without the flag — data loss"
    # The tenant row is still ensured: needed to serve, not only to seed.
    assert "ensure_tenant" in markers


def test_the_demo_shape_does_regenerate_the_dataset():
    # The positive control — without it the test above would also pass if the
    # seed path were deleted outright rather than gated.
    markers = _boot_with_sentinel_data_dir(seed_flag="1")
    assert {"generar", "run", "ensure_tenant"} <= markers
```

`_run` needs a timeout it can hit without failing the test: change its
`subprocess.run(...)` call to `timeout=90`, and note that `_boot_with_sentinel_data_dir`
catches `TimeoutExpired` above — if the dataset check in step 5 of `boot.py`
happens to pass, `boot.py` execs uvicorn and would otherwise hang the suite.

Run them:

```bash
cd backend && python -m pytest tests/test_deploy_scripts.py -v
```

Expected: **PASS** (7 tests). Against the pre-change `boot.py`,
`test_a_productive_shape_never_regenerates_the_dataset` fails — which is the
point.

- [ ] **Step 6: Verify both paths by hand**

```bash
# Productive shape: no seeding, and it must NOT rewrite data-demo/
cd backend && POLPILOT_TENANT=piloto python ../deploy/boot.py
```

Expected: `[boot] seeding skipped (POLPILOT_SEED_ON_BOOT is not 1)`, then either step 5's dataset check or uvicorn starting. Stop it with Ctrl-C.

```bash
git status --short data-demo/    # must be clean — nothing regenerated
```

- [ ] **Step 7: Commit**

```bash
git add deploy/boot.py backend/tests/test_deploy_scripts.py
git commit -m "Gate boot.py's seeding and drop its migration step

generar.py rewrites the whole dataset on every boot. That is what makes
the public demo self-healing on Render's ephemeral filesystem, and it is
data loss on a productive tenant — so it is now opt-in via
POLPILOT_SEED_ON_BOOT, defaulting to off.

Migrations move to deploy/migrate.py (the preDeployCommand). boot.py also
now refuses to start without an explicit POLPILOT_TENANT, which is what
lets the next commit take the value out of the image safely."
```

---

### Task 6: Make the image tenant-agnostic and rewrite the blueprint

Implements **D6** and **D7**, fixing **F1** — the highest-consequence finding: `POLPILOT_DEMO_AUTOLOGIN=1` is baked into the image, so any productive service built from it comes up autologged-in as the tenant owner.

**Files:**
- Modify: `Dockerfile` (the `ENV` block only)
- Modify: `render.yaml` (rewrite)
- Test: `backend/tests/test_deploy_config.py` (new)

**Interfaces:**
- Consumes: `deploy/migrate.py` (Task 4) for `preDeployCommand`; `POLPILOT_SEED_ON_BOOT` (Task 5).
- Produces: the deployment contract Task 7 documents.

**Do not touch the privacy guard.** The `RUN test ! -e /app/data && …` block stays exactly as strict. Its invariant is unchanged: productive data lives in Postgres, never in the image.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_deploy_config.py`:

```python
"""The deployment contract in Dockerfile and render.yaml.

These are text assertions on purpose: there is no YAML parser in
requirements.txt, and building the image in the suite would cost minutes.
What matters is checkable as text — which variables the image bakes in, and
which the blueprint sets.

The finding this file exists to prevent from recurring: the image used to
hard-code POLPILOT_TENANT=demo *and* POLPILOT_DEMO_AUTOLOGIN=1, so any
productive service built from it came up autologged-in as the tenant owner
unless each of them was overridden by hand in the dashboard. Silent, and an
unauthenticated production app.
"""
from __future__ import annotations

import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _read(name: str) -> str:
    with open(os.path.join(REPO_ROOT, name), encoding="utf-8") as fh:
        return fh.read()


def test_the_image_bakes_in_no_tenant_and_no_demo_switches():
    dockerfile = _read("Dockerfile")
    assert "POLPILOT_TENANT" not in dockerfile
    assert not re.search(r"POLPILOT_DEMO_\w+", dockerfile), (
        "demo-only configuration must live in render.yaml's envVars, never in "
        "the image — a productive service built from this image would inherit it"
    )


def test_the_image_keeps_its_image_wide_paths():
    # These are properties of the image layout, not of a tenant, so they stay.
    dockerfile = _read("Dockerfile")
    assert "POLPILOT_STATIC_DIR" in dockerfile
    assert "POLPILOT_CANONICAL_DIR" in dockerfile


def test_the_privacy_guard_is_still_in_the_image():
    dockerfile = _read("Dockerfile")
    assert "Supermercados Horizonte" in dockerfile, "the privacy guard was weakened"
    assert "credenciales.json" in dockerfile


def test_the_blueprint_sets_the_demo_configuration_explicitly():
    blueprint = _read("render.yaml")
    for key in ("POLPILOT_TENANT", "POLPILOT_DEMO_AUTOLOGIN",
                "POLPILOT_SEED_ON_BOOT", "ANGELA_MODEL"):
        assert key in blueprint, f"{key} must be declared in render.yaml"


def test_the_blueprint_runs_migrations_before_the_deploy():
    blueprint = _read("render.yaml")
    assert "preDeployCommand" in blueprint
    assert "deploy/migrate.py" in blueprint


def test_the_blueprint_no_longer_names_the_service_after_the_demo():
    blueprint = _read("render.yaml")
    assert re.search(r"^\s*name:\s*polpilot-app\s*$", blueprint, re.M), (
        "the service is polpilot-app; POLPILOT_TENANT decides which tenant it serves"
    )


def test_the_blueprint_keeps_every_secret_out_of_the_repo():
    blueprint = _read("render.yaml")
    for secret in ("ANTHROPIC_API_KEY", "POLPILOT_RESET_TOKEN",
                   "DATABASE_URL", "APP_DATABASE_URL"):
        assert secret in blueprint, f"{secret} must be declared"
    # Four secrets, four sync:false markers — a literal value here would
    # commit a credential.
    assert blueprint.count("sync: false") >= 4
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_deploy_config.py -v
```

Expected: **FAIL** on the tenant/demo-switch test, the blueprint's `preDeployCommand`, `POLPILOT_SEED_ON_BOOT`, and the service name. The privacy-guard and image-paths tests should already **PASS** — if either fails, stop: something else is wrong.

- [ ] **Step 3: Shrink the Dockerfile's ENV block**

Replace the whole `ENV` block in `Dockerfile` with:

```dockerfile
# Image-wide layout only. Everything tenant- or demo-specific lives in the
# service's envVars (see render.yaml): this image is built once and must be
# usable by any tenant. It used to bake in the tenant slug and the demo
# switches, which meant a productive service built from this image came up
# autologged-in as the tenant owner unless every one of them was overridden
# by hand — silently. tests/test_deploy_config.py now asserts none of those
# names appear in this file at all, comments included, so do not name them
# here even to explain them.
ENV POLPILOT_CANONICAL_DIR=/app/canonical \
    POLPILOT_STATIC_DIR=/app/frontend/dist \
    PYTHONUNBUFFERED=1
```

Leave every other line of the `Dockerfile` — both build stages, the WeasyPrint system libraries, the `COPY` steps and the privacy guard — untouched.

- [ ] **Step 4: Rewrite render.yaml**

Replace the file with the following. Comments are in English per the repo standard; the old file's were Spanish.

```yaml
# Render Blueprint. One Docker service: the API plus the compiled frontend on
# one port, backed by an external Postgres.
#
# The image is tenant-agnostic — POLPILOT_TENANT below is what decides which
# tenant this service serves. A second (productive) tenant is a copy of this
# service block with a different tenant and its own database, NOT a routing
# layer: one process serves one tenant (see backend/core/db/tenant.py).
#
# The documented target topology, and the triggers that would justify
# building it, are in deploy/ARCHITECTURE.md §3.
#
# "New +" -> "Blueprint" -> connect this repo -> Render reads this file.
services:
  - type: web
    name: polpilot-app
    runtime: docker
    plan: starter          # 512 MB is enough; free sleeps and ruins first impressions
    healthCheckPath: /api/health

    # Migrations run BEFORE any instance of the new version starts, so a
    # failed migration fails the deploy and the running instance keeps
    # serving. Inside the container it used to exit the process instead,
    # which took the service down. See deploy/migrate.py.
    preDeployCommand: python deploy/migrate.py

    envVars:
      # --- secrets: set in the dashboard, never in the repo -----------------
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: POLPILOT_RESET_TOKEN
        sync: false        # guards POST /api/admin/reset-demo
      - key: DATABASE_URL
        sync: false        # owner role: Alembic + tenant-row lookups
      - key: APP_DATABASE_URL
        sync: false        # NOBYPASSRLS role: every tenant-scoped query.
                           # Reusing DATABASE_URL here would make Row-Level
                           # Security silently do nothing, with no error.
                           # docker/init-app-role.sql is the local equivalent.

      # --- which tenant this service is ------------------------------------
      # Mandatory. deploy/migrate.py and deploy/boot.py both refuse to run
      # without it: core/paths.py falls back to "demo", so an unset variable
      # would silently serve the demo tenant's users and data.
      - key: POLPILOT_TENANT
        value: demo

      # Regenerate and reseed the dataset on every boot. Correct for the
      # demo — Render's filesystem is ephemeral, so each restart returns it
      # to a clean state, and /api/admin/reset-demo depends on the canonical
      # copy. NEVER set this on a productive tenant: data-demo/generar.py
      # rewrites the whole dataset.
      - key: POLPILOT_SEED_ON_BOOT
        value: "1"

      # --- demo-only behavior (was baked into the image; see D6/F1) --------
      # Do NOT copy this block to a productive service.
      - key: POLPILOT_DEMO_AUTOLOGIN
        value: "1"         # no login screen: the public link lands on Home
      - key: POLPILOT_DEMO_ROLE_SWITCH
        value: "1"         # "View as" role switcher
      - key: POLPILOT_DEMO_TODAY
        value: "2026-07-07"  # the seeded history's "today"
      - key: POLPILOT_DEMO_MSG_CAP
        value: "35"        # per-session message cap
      - key: POLPILOT_DEMO_IP_CAP
        value: "60"        # per-IP/day spend brake, survives a re-login
      - key: POLPILOT_DEFAULT_LANG
        value: en

      # --- config, deliberately explicit -----------------------------------
      # Not a secret, but it cannot be implicit either: without this line the
      # code falls back to its historical default (claude-sonnet-4-6, see
      # backend/config.MODELO_VALIDACION) and production would run a
      # different model than the one validated. Verified via /api/health ->
      # modelo_angela.
      - key: ANGELA_MODEL
        value: claude-sonnet-5

# The real ceiling on LLM spend is NOT in this file. The per-IP cap above is a
# soft brake; the limit that cannot be evaded is set outside the app — a spend
# limit or budget alert on the API key in the Anthropic console.
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_deploy_config.py -v
```

Expected: **PASS** (7 tests).

- [ ] **Step 6: Verify the image still builds and the guard still bites**

```bash
docker build -t polpilot-app:local .
docker run --rm polpilot-app:local sh -c 'env | grep -c POLPILOT_DEMO || echo "0 demo vars — correct"'
```

Expected: the build succeeds, ending in `privacy guard: OK`, and the `env` check reports no `POLPILOT_DEMO_*` variables in the image.

If Docker is unavailable locally, say so in your report rather than skipping silently — CI's `docker-build` job covers it, and `deploy/DEPLOY.md` records that this has been a genuine local blocker before.

- [ ] **Step 7: Commit**

```bash
git add Dockerfile render.yaml backend/tests/test_deploy_config.py
git commit -m "Take demo configuration out of the image; rename the service

The image hard-coded POLPILOT_TENANT=demo and POLPILOT_DEMO_AUTOLOGIN=1, so
any productive service built from it came up autologged-in as the tenant
owner unless every one of those was overridden by hand in the dashboard.
The failure was silent and the result an unauthenticated production app.

All of it moves to render.yaml's envVars, leaving the image with paths
only, so the first paying client is a copy of the service block with a
different tenant rather than an audit of which demo defaults leaked in.
The service becomes polpilot-app, migrations run as preDeployCommand, and
seeding is explicit. The privacy guard is untouched."
```

---

### Task 7: Rewrite the deployment docs

The deployment contract changed in Tasks 4–6; `deploy/DEPLOY.md` still describes the old one (service `polpilot-demo`, "the two secrets", migrations at boot) and is in Spanish. New docs are English per the repo standard.

**Files:**
- Modify: `deploy/DEPLOY.md` (rewrite)
- Modify: `deploy/ARCHITECTURE.md` (§2 becomes current)
- Modify: `backend/MCP.md` (one sentence — verify only)
- Modify: `CLAUDE.md` (the Deploy section)

**Interfaces:**
- Consumes: everything from Tasks 4–6.
- Produces: nothing.

- [ ] **Step 1: Rewrite `deploy/DEPLOY.md`**

Keep it a runbook, not an architecture doc — `ARCHITECTURE.md` is the shape and the why; this is what an operator types. Cover, in English:

1. **Creating the service** — Blueprint from `render.yaml`, service `polpilot-app`, healthcheck `/api/health`, plan Starter (Free sleeps).
2. **The four secrets**, as a table: `ANTHROPIC_API_KEY`, `POLPILOT_RESET_TOKEN`, `DATABASE_URL` (owner role), `APP_DATABASE_URL` (`NOBYPASSRLS` — and why reusing the first makes RLS a silent no-op).
3. **What the blueprint sets and why it is explicit** — `POLPILOT_TENANT`, `POLPILOT_SEED_ON_BOOT`, the `POLPILOT_DEMO_*` block, `ANGELA_MODEL`.
4. **A new "Deploying a productive tenant" section.** This is the part the old doc could not have: copy the service block, set `POLPILOT_TENANT` to the new slug, point `DATABASE_URL`/`APP_DATABASE_URL` at its database, **omit `POLPILOT_SEED_ON_BOOT` and the whole `POLPILOT_DEMO_*` block**, and state plainly that setting `POLPILOT_SEED_ON_BOOT=1` there would rewrite that tenant's dataset.
5. **Deploy order** — `preDeployCommand` (`deploy/migrate.py`) runs first; on failure the deploy stops and the old instance keeps serving. Then `boot.py`, then the healthcheck.
6. **The post-deploy checklist** — carry over the existing nine steps, in English, with the service name updated.
7. **Demo reset** — automatic on restart/redeploy (ephemeral filesystem + `POLPILOT_SEED_ON_BOOT=1`), or manual via `POST /api/admin/reset-demo?token=…`.
8. **Troubleshooting** — carry over the existing entries (`[boot][X]` messages, the privacy-guard build failure, WeasyPrint's missing system library, slow first load) and add two: a `preDeployCommand` failure (read the deploy log, the service is still up on the old version) and `[deploy][X] POLPILOT_TENANT is not set`.

Delete the "Estado de la verificación local" section's stale Docker-Desktop narrative, but keep the fact that a local build may be blocked and that the privacy guard runs in Render's build regardless.

- [ ] **Step 2: Update `deploy/ARCHITECTURE.md`**

- In the status table at the top, §2 becomes **Live** and §1 becomes the historical "before" — retitle it so no one reads it as current.
- In §1.5's configuration table, the "baked into the image" row moves to `render.yaml`.
- Delete the F2 paragraph's "and §2 fixes it", since it is fixed.
- Leave §3 exactly as it is: still documented, still not built.

- [ ] **Step 3: Verify `backend/MCP.md` needs no change**

It says there is "no separate service to deploy or tenant-routing layer to add". Per D3 that stays **true** — MCP remains mounted in the API app. Read the sentence, confirm it, change nothing. This step exists because the first draft of the design would have made it false.

- [ ] **Step 4: Update the Deploy section in `CLAUDE.md`**

It currently reads that `render.yaml` + `Dockerfile` bring up "a single Docker service" and that "the only secret is `ANTHROPIC_API_KEY`". The first half is still true; the second is not — there are four. Fix the secret count, name the service `polpilot-app`, and point at `deploy/ARCHITECTURE.md` for the topology alongside the existing `deploy/DEPLOY.md` reference.

- [ ] **Step 5: Check every reference to the old service name**

```bash
grep -rn "polpilot-demo" --include="*.md" --include="*.yaml" --include="*.yml" --include="*.py" . | grep -v node_modules | grep -v "docs/superpowers"
```

Update each hit that refers to the *Render service*. Leave alone: the local Docker image tag in CI (`polpilot-demo:ci`) unless you also change `.github/workflows/ci.yml`, and anything under `docs/superpowers/` (specs and plans are historical records — do not rewrite them).

- [ ] **Step 6: Commit**

```bash
git add deploy/DEPLOY.md deploy/ARCHITECTURE.md CLAUDE.md
git commit -m "Update the deployment docs for the productive pipeline

DEPLOY.md described the old contract: service polpilot-demo, two secrets,
migrations at boot. Rewritten in English for the renamed service, the four
secrets, the preDeployCommand order, and a new section on deploying a
productive tenant — which is the case the old doc could not describe,
including the warning that POLPILOT_SEED_ON_BOOT=1 there is data loss.

ARCHITECTURE.md's planned section is now the live one. MCP.md needed no
change: MCP stays mounted in the API app."
```

---

### Task 8: Route every fetch through one configurable base URL

Implements **D11**. No behavior change today — `VITE_API_BASE` defaults to `""`, so request URLs stay byte-identical. Its value is that the static-site split in D2 becomes a `render.yaml` edit plus one variable instead of a frontend refactor, and that 19 scattered literals become one seam.

**Files:**
- Create: `frontend/src/lib/apiUrl.js`
- Create: `frontend/src/lib/apiUrl.test.ts`
- Modify: `frontend/src/lib/api.js` (lines 32, 47, 63, 73, 83, 114, 260, 319, 351)
- Modify: `frontend/src/lib/auth.js` (28, 63), `frontend/src/lib/hoy.js` (22), `frontend/src/lib/i18n.js` (63), `frontend/src/lib/useEmpresa.js` (17)
- Modify: `frontend/src/App.jsx` (53, 55), `frontend/src/mobile/EquipoMobile.jsx` (23), `frontend/src/sections/GestionEquipo.jsx` (883), `frontend/src/sections/ObjetivosPanel.jsx` (88)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `apiUrl(path: string) => string` from `frontend/src/lib/apiUrl.js`.

**Why its own module:** `api.js` imports `authStore` from `./auth`, so housing `apiUrl` in `api.js` and importing it from `auth.js` would create a cycle. `apiUrl.js` imports nothing.

**Why the test is `.ts`:** `vite.config.js` sets `test.include` to `["src/**/*.test.{ts,tsx}"]`. A `.test.js` file is silently never run.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/apiUrl.test.ts`:

```ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiUrl } from "./apiUrl";

afterEach(() => { vi.unstubAllEnvs(); });

describe("apiUrl", () => {
  it("leaves the path untouched when no base is configured", () => {
    // The deployed default: the backend serves the bundle, so the API is
    // same-origin and every request URL must stay exactly as it was.
    vi.stubEnv("VITE_API_BASE", "");
    expect(apiUrl("/api/health")).toBe("/api/health");
    expect(apiUrl("/api/preferencias/foo?x=1")).toBe("/api/preferencias/foo?x=1");
  });

  it("prefixes an absolute base", () => {
    vi.stubEnv("VITE_API_BASE", "https://api.example.com");
    expect(apiUrl("/api/health")).toBe("https://api.example.com/api/health");
  });

  it("does not double the slash when the base has a trailing one", () => {
    vi.stubEnv("VITE_API_BASE", "https://api.example.com/");
    expect(apiUrl("/api/health")).toBe("https://api.example.com/api/health");
  });

  it("leaves an already-absolute URL alone", () => {
    vi.stubEnv("VITE_API_BASE", "https://api.example.com");
    expect(apiUrl("https://other.example.com/x")).toBe("https://other.example.com/x");
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd frontend && npm run test -- apiUrl
```

Expected: **FAIL** — cannot resolve `./apiUrl`.

- [ ] **Step 3: Write the implementation**

Create `frontend/src/lib/apiUrl.js`:

```js
// The single place a PolPilot request path becomes a URL.
//
// VITE_API_BASE is empty in every current deployment: the backend serves the
// compiled bundle itself, so the API is same-origin and these paths stay
// relative. The variable exists so that serving the frontend from its own
// origin (a CDN static site) needs a build-time value here instead of an edit
// at every call site — see deploy/ARCHITECTURE.md §3.
//
// This module imports nothing on purpose: api.js already imports authStore
// from auth.js, so living in api.js would make that pair circular.
const BASE = (import.meta.env?.VITE_API_BASE ?? "").replace(/\/$/, "");

export function apiUrl(path) {
  if (/^https?:\/\//.test(path)) return path;
  return BASE ? `${BASE}${path}` : path;
}
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd frontend && npm run test -- apiUrl
```

Expected: **PASS** (4 tests).

- [ ] **Step 5: Route every call site through it**

In each of the 9 files, import the helper and wrap the first argument of every `fetch` aimed at a PolPilot endpoint. Two shapes:

```js
// lib/api.js — the generic helpers take `path` from their callers, so one
// wrap here covers every caller. Do NOT also wrap at the call sites.
import { apiUrl } from "./apiUrl";

async function get(path) {
  const res = await fetch(apiUrl(path), { headers: _headers() });
  if (!res.ok) throw _error(path, res);   // keep `path` in the error: the
  return res.json();                      // message should stay stable
}
```

```js
// A literal call site, e.g. lib/auth.js:28
const res = await fetch(apiUrl("/api/login"), { ... });
```

Import paths differ by directory: `./apiUrl` inside `lib/`, `./lib/apiUrl` from `App.jsx`, `../lib/apiUrl` from `mobile/` and `sections/`.

Two things to leave alone:
- **`_error(path, res)` keeps the un-prefixed `path`.** It is user-facing message text; prefixing it would change what people see for no reason.
- Anything that is not a PolPilot API call. Re-run the enumeration below and confirm each hit is one before wrapping it.

- [ ] **Step 6: Verify no call site was missed**

```bash
cd frontend && grep -rn "fetch(" src/ | grep -v "\.test\." | grep -v "apiUrl("
```

Expected: **no output**. Any line printed is either a missed call site or a deliberate non-API fetch — if it is the latter, note it in your report.

- [ ] **Step 7: Run the full frontend gate**

```bash
cd frontend && npm run test && npm run typecheck && npm run build
```

Expected: all three pass. The build matters: `apiUrl.js` is new and reached from the entry graph, so a bad import path fails here rather than at runtime.

- [ ] **Step 8: Verify the app still works end to end**

With the backend running (`cd backend && python -m uvicorn main:app --port 8000`) and `npm run dev`, load the app and confirm login, Home, and a chat message all work — the chat especially, since `api.js:351`'s `/api/angela/stream` is the one streaming call.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/lib/apiUrl.js frontend/src/lib/apiUrl.test.ts \
        frontend/src/lib/api.js frontend/src/lib/auth.js frontend/src/lib/hoy.js \
        frontend/src/lib/i18n.js frontend/src/lib/useEmpresa.js \
        frontend/src/App.jsx frontend/src/mobile/EquipoMobile.jsx \
        frontend/src/sections/GestionEquipo.jsx frontend/src/sections/ObjetivosPanel.jsx
git commit -m "Route every API fetch through one configurable base URL

19 call sites across 9 files hard-coded relative /api paths, four of them
outside lib/. They now go through apiUrl(), which prefixes VITE_API_BASE —
empty in every current deployment, so request URLs are byte-identical and
nothing changes today.

What it buys: serving the frontend from its own origin becomes a build-time
variable instead of an edit at every call site. apiUrl lives in its own
module because api.js already imports authStore from auth.js."
```

---

## Verification

After all eight tasks:

```bash
cd backend && python -m pytest -q && git checkout -- data-demo/
cd ../frontend && npm run test && npm run typecheck && npm run build
cd .. && docker build -t polpilot-app:local .
```

All four must pass. The `git checkout -- data-demo/` is not optional — the suite writes into the data dir.

## What this plan does NOT do

Deferred by the spec, listed so no one treats them as omissions: separate `polpilot-web` / `polpilot-api` services (D1, D2), a separate MCP service (D3, rejected on the merits), per-request tenant routing (D5, rejected), the move to Render Postgres and the `NOBYPASSRLS` role bootstrap against it (D12, F4 — lands in `deploy/migrate.py` when it happens), CORS widening and cross-origin stream verification (D11 — untestable with one origin), custom domains, and PR preview environments.
