#!/usr/bin/env python3
"""
start_demo.py - one command, demo ready.
=========================================
Boots the PolPilot demo (Distribuidora del Litoral) with zero manual steps:

    python start_demo.py

What it does, in order:
  1. Kills orphaned listeners on :8001/:5174 (the known trap of stale
     uvicorn/vite processes running outdated code/data).
  2. Warns if the versioned dataset differs from the committed snapshot
     (leftovers from manual testing).
  3. Starts Postgres (`docker compose up -d db`) - skipped if a database is
     already reachable at the configured DATABASE_URL, so repeat runs don't
     pay the docker-compose overhead.
  4. Applies pending Alembic migrations (`alembic upgrade head`, a no-op
     when the schema is already current).
  5. Ensures the `demo` tenant row exists (must happen before step 6: the
     seed generator writes straight into Postgres-backed core modules that
     need the tenant to already exist).
  6. Runs data-demo/generar.py: seeds whatever is missing on disk
     (deterministic; existing data is left untouched).
  7. Seeds Postgres (auth credentials + every domain migrated off disk) -
     idempotent, same as generar.py.
  8. Starts the backend with every demo env var and waits for the REAL
     healthcheck: dataset loaded, activity seeded, analysis pre-warmed.
  9. Starts the frontend and prints the link.

Ctrl+C shuts backend and frontend down together (Postgres is left running -
it's a persistent local service, not part of this script's process
lifecycle). Meant to be reused by the deploy boot path (deploy/boot.py runs
the same migrate -> seed -> healthcheck sequence for a Render container).
"""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

# Windows consoles (cp1252) choke on accents/glyphs: UTF-8 with replacement,
# never a crash.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(HERE, "backend")
FRONTEND = os.path.join(HERE, "frontend")
DATA_DEMO = os.path.join(HERE, "data-demo")
BACKEND_ENV_FILE = os.path.join(BACKEND, ".env")
API_PORT = 8001
FRONT_PORT = 5174
TENANT = "demo"
IS_WINDOWS = os.name == "nt"

DEMO_ENV = {
    "POLPILOT_TENANT": TENANT,
    "POLPILOT_DATA_DIR": "../data-demo",
    "POLPILOT_DEFAULT_LANG": "en",
    "POLPILOT_DEMO_TODAY": "2026-07-07",
    "POLPILOT_DEMO_ROLE_SWITCH": "1",
    "POLPILOT_DEMO_MSG_CAP": "35",
    "POLPILOT_DEMO_AUTOLOGIN": "1",
    "PYTHONUNBUFFERED": "1",  # so backend log lines stream live, not batched
}

RESET = "\033[0m"
GREEN, RED, YELLOW = "\033[92m", "\033[91m", "\033[93m"
CYAN, BLUE, MAGENTA = "\033[96m", "\033[94m", "\033[95m"

# One color per service family: data layer (db/migrate/seed) vs. the two
# long-lived servers, so a scrolling console still reads as "who said this".
TAG_COLORS = {
    "db": CYAN, "migrate": CYAN, "seed": CYAN,
    "backend": BLUE, "frontend": MAGENTA,
}


def log(msg: str) -> None:
    print(f"  {msg}", flush=True)


def ok(msg: str) -> None:
    print(f"{GREEN}[OK]{RESET} {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"{YELLOW}[!] {msg}{RESET}", flush=True)


def fail(msg: str) -> None:
    print(f"{RED}[X] {msg}{RESET}", flush=True)


def _print_tagged(tag: str, line: str) -> None:
    color = TAG_COLORS.get(tag, RESET)
    print(f"{color}[{tag:>8}]{RESET} {line.rstrip()}", flush=True)


# -----------------------------------------------------------------------
# Process lifecycle: launching with a killable tree, and killing that tree
# -----------------------------------------------------------------------

def _popen_kwargs() -> dict:
    """Spawns the child in its own process group/session so a later kill
    reaches everything under it (npm.cmd -> node, uvicorn -> workers), not
    just the direct child - the exact gap that used to leave orphaned
    listeners on :8001/:5174 behind."""
    if IS_WINDOWS:
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def start_streamed(cmd: list[str], *, cwd: str, tag: str, env: dict | None = None) -> subprocess.Popen:
    """Launches a long-lived process (backend/frontend) with its output
    streamed live through a colored, tagged prefix on a background thread."""
    p = subprocess.Popen(
        cmd, cwd=cwd, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        **_popen_kwargs(),
    )

    def _pump() -> None:
        try:
            for line in iter(p.stdout.readline, ""):
                if not line:
                    break
                _print_tagged(tag, line)
        except (OSError, ValueError):
            pass

    threading.Thread(target=_pump, daemon=True).start()
    return p


def run_streamed(cmd: list[str], *, cwd: str, tag: str, env: dict | None = None,
                  timeout: float | None = None) -> int:
    """Runs a short-lived setup command (docker compose, alembic, seed
    scripts) to completion, streaming its output through the same tagged
    prefix as the servers."""
    p = subprocess.Popen(
        cmd, cwd=cwd, env=env or os.environ.copy(),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    for line in iter(p.stdout.readline, ""):
        if not line:
            break
        _print_tagged(tag, line)
    try:
        return p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        return -1


def kill_process_tree(proc: subprocess.Popen | None, name: str) -> None:
    if proc is None or proc.poll() is not None:
        return
    log(f"stopping {name}…")
    if IS_WINDOWS:
        # /T kills the whole tree: without it, terminate() only hits
        # npm.cmd/uvicorn's launcher and leaves node/reload workers running,
        # which is exactly how :8001/:5174 used to end up orphaned.
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, timeout=15)
    else:
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def _on_sigterm(signum, frame) -> None:  # noqa: ARG001
    raise KeyboardInterrupt


# ----------------------------------------------------------------------------
# 1 · Clean ports: kill orphaned listeners (runbook from 7/23, automated)
# ----------------------------------------------------------------------------

def _listening_pids(port: int) -> set[int]:
    pids: set[int] = set()
    try:
        if IS_WINDOWS:
            # No "-p TCP": that filters to IPv4 only and Vite listens on
            # [::1] - the known trap that made frontend orphans invisible.
            out = subprocess.run(["netstat", "-ano"],
                                 capture_output=True, text=True, timeout=15).stdout
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 5 and parts[0] == "TCP" and "LISTENING" in line:
                    if parts[1].endswith(f":{port}"):
                        pids.add(int(parts[-1]))
        else:
            out = subprocess.run(["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"],
                                 capture_output=True, text=True, timeout=15).stdout
            pids = {int(p) for p in out.split() if p.strip()}
    except (subprocess.SubprocessError, ValueError, FileNotFoundError):
        pass
    return pids


def clean_port(port: int) -> None:
    pids = _listening_pids(port)
    if not pids:
        return
    for pid in pids:
        warn(f"port {port} held by PID {pid} — killing the orphaned process")
        try:
            if IS_WINDOWS:
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                               capture_output=True, timeout=15)
            else:
                os.kill(pid, signal.SIGTERM)
        except (subprocess.SubprocessError, OSError) as e:
            fail(f"couldn't kill PID {pid}: {e} — close it manually and retry")
            sys.exit(1)
    time.sleep(1.5)
    if _listening_pids(port):
        fail(f"port {port} is still held — close it manually and retry")
        sys.exit(1)


# ----------------------------------------------------------------------------
# 2 · Snapshot guard
# ----------------------------------------------------------------------------

def guard_snapshot() -> None:
    try:
        out = subprocess.run(["git", "status", "--porcelain", "data-demo/"],
                             capture_output=True, text=True, cwd=HERE, timeout=15).stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        return  # no git (e.g. deploy): the deterministic seed is the source of truth
    dirty = [l for l in out.splitlines() if l.strip() and not l.lstrip().startswith("??")]
    if dirty:
        warn("THE VERSIONED DATASET DIFFERS FROM THE COMMITTED SNAPSHOT:")
        for l in dirty:
            warn(f"   {l.strip()}")
        warn("   (leftovers from manual testing — `git checkout -- data-demo/` for the canonical state)")
    else:
        ok("versioned dataset = committed snapshot")


# ----------------------------------------------------------------------------
# 3 · Postgres (docker compose db), only started if not already reachable
# ----------------------------------------------------------------------------

def _read_env_var(path: str, key: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return None


def _db_target() -> tuple[str, int]:
    url = _read_env_var(BACKEND_ENV_FILE, "DATABASE_URL") or \
        "postgresql+psycopg://polpilot:polpilot@localhost:5434/polpilot"
    parsed = urllib.parse.urlparse(url)
    return parsed.hostname or "localhost", parsed.port or 5434


def _tcp_open(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def ensure_db() -> None:
    host, port = _db_target()
    if _tcp_open(host, port):
        ok(f"Postgres already reachable at {host}:{port} — skipping docker compose")
        return
    log(f"Postgres not reachable at {host}:{port} — starting docker compose db…")
    rc = run_streamed(["docker", "compose", "up", "-d", "db"], cwd=HERE, tag="db")
    if rc != 0:
        fail("`docker compose up -d db` failed — is Docker running?")
        sys.exit(1)
    deadline = time.time() + 40
    while time.time() < deadline:
        if _tcp_open(host, port):
            break
        time.sleep(1)
    else:
        fail(f"Postgres didn't come up on {host}:{port} in time")
        sys.exit(1)
    for _ in range(15):
        r = subprocess.run(["docker", "compose", "exec", "-T", "db", "pg_isready", "-U", "polpilot"],
                           cwd=HERE, capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            break
        time.sleep(1)
    ok(f"Postgres ready at {host}:{port}")


# ----------------------------------------------------------------------------
# 4 · Migrations (Alembic; a no-op when the schema is already current)
# ----------------------------------------------------------------------------

def run_migrations() -> None:
    log("applying database migrations (alembic upgrade head)…")
    rc = run_streamed([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, tag="migrate")
    if rc != 0:
        fail("`alembic upgrade head` failed")
        sys.exit(1)
    ok("schema up to date")


# ----------------------------------------------------------------------------
# 5-7 · Seed: ensure_tenant() -> generar.py -> seed_db.run() (this exact
# order matters — see data-demo/seed_db.py and deploy/boot.py's docstrings)
# ----------------------------------------------------------------------------

def ensure_tenant() -> None:
    code = (f"import sys; sys.path.insert(0, {DATA_DEMO!r}); "
            f"import seed_db; seed_db.ensure_tenant({TENANT!r})")
    rc = run_streamed([sys.executable, "-c", code], cwd=BACKEND, tag="seed")
    if rc != 0:
        fail("seed_db.ensure_tenant() failed")
        sys.exit(1)


def seed_dataset() -> None:
    rc = run_streamed([sys.executable, os.path.join(DATA_DEMO, "generar.py")],
                      cwd=DATA_DEMO, tag="seed")
    if rc != 0:
        fail("generar.py failed")
        sys.exit(1)
    ok("dataset seed verified (generar.py: seeds only what's missing, byte-identical)")


def seed_postgres() -> None:
    rc = run_streamed([sys.executable, os.path.join(DATA_DEMO, "seed_db.py"), TENANT],
                      cwd=DATA_DEMO, tag="seed")
    if rc != 0:
        fail("seed_db.run() failed")
        sys.exit(1)
    ok("Postgres seed applied (auth credentials + migrated domains)")


# ----------------------------------------------------------------------------
# 8 · Backend + real healthcheck
# ----------------------------------------------------------------------------

def _http(method: str, path: str, token: str | None = None, timeout: float = 10.0):
    req = urllib.request.Request(f"http://127.0.0.1:{API_PORT}{path}", method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if method == "POST":
        req.add_header("Content-Length", "0")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def start_backend() -> subprocess.Popen:
    env = {**os.environ, **DEMO_ENV}
    return start_streamed(
        [sys.executable, "-m", "uvicorn", "main:app", "--port", str(API_PORT)],
        cwd=BACKEND, tag="backend", env=env,
    )


def wait_backend(proc: subprocess.Popen, timeout_s: int = 45) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        if proc.poll() is not None:
            fail("the backend died on startup — check the uvicorn error above")
            sys.exit(1)
        try:
            h = _http("GET", "/api/health", timeout=3)
            if h.get("meta", {}).get("empresa"):
                ok(f"backend up: {h['meta']['empresa']} (autologin={'yes' if h.get('autologin') else 'NO'})")
                return
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            pass
        time.sleep(1)
    fail(f"backend didn't respond on /api/health within {timeout_s}s")
    sys.exit(1)


def healthcheck(proc: subprocess.Popen) -> None:
    """The three checks that catch an 'empty Home that looks real'."""
    try:
        session = _http("POST", "/api/demo/autologin")
        token = session["token"]
    except Exception as e:  # noqa: BLE001 — any failure here is fatal and worth reporting
        fail(f"autologin failed ({e}) — did POLPILOT_DEMO_AUTOLOGIN=1 reach the backend?")
        sys.exit(1)

    problems = []
    try:
        inv = _http("GET", "/api/inventario", token)
        n_items = inv.get("resumen", {}).get("total_articulos", 0)
        if n_items > 0:
            ok(f"dataset loaded: {n_items} items, ${inv['resumen']['inmovilizado_total']:,.0f} tied up")
        else:
            problems.append("empty inventory (did generar.py run? is DATA_DIR correct?)")
    except Exception as e:  # noqa: BLE001
        problems.append(f"/api/inventario failed: {e}")

    try:
        home = _http("GET", "/api/inicio", token)
        feed = (home.get("actividad") or {}).get("feed") or []
        if feed:
            ok(f"activity seeded: {len(feed)} events in the feed")
        else:
            problems.append("empty activity feed (Home would say 'nothing happened' — false)")
    except Exception as e:  # noqa: BLE001
        problems.append(f"/api/inicio failed: {e}")

    try:
        # besides verifying, this hit also warms the cache if the startup
        # pre-computation is still running
        for _ in range(10):
            an = _http("GET", "/api/analisis", token, timeout=30)
            if an.get("disponible"):
                ok("analysis pre-warmed (Oportunidades loads instantly)")
                break
            time.sleep(1)
        else:
            problems.append("analysis never reports available (unvalidated sales?)")
    except Exception as e:  # noqa: BLE001
        problems.append(f"/api/analisis failed: {e}")

    # The map fires ~16 requests on open (signals + crosses + knowledge) and
    # the backend is a sync worker: if those endpoints are hit COLD, the
    # first open takes ~45s (a serialized request storm). Pre-warming them
    # here makes the first map open take a few seconds (revisits: instant
    # via the frontend cache). Best-effort: if one fails, the map still loads.
    map_endpoints = ("/api/oportunidades", "/api/cuentas", "/api/ventas",
                     "/api/pagos", "/api/deposito", "/api/evolucion",
                     "/api/inicio", "/api/calidad", "/api/macro",
                     "/api/anomalias", "/api/equipo/actividad", "/api/conocimiento")
    warm = 0
    for route in map_endpoints:
        try:
            _http("GET", route, token, timeout=30)
            warm += 1
        except Exception:  # noqa: BLE001 — best-effort, the map doesn't depend on this
            pass
    ok(f"map pre-warmed ({warm}/{len(map_endpoints)} endpoints — first open is fast)")

    if problems:
        for p in problems:
            fail(p)
        fail("healthcheck FAILED: the demo is NOT ready to show. Backend stays up for diagnosis.")
        sys.exit(1)


# ----------------------------------------------------------------------------
# 9 · Frontend
# ----------------------------------------------------------------------------

def start_frontend() -> subprocess.Popen:
    # Re-clean right before launching: if startup killed a previous
    # start_demo, its Vite can take a few seconds to release the port (a
    # race seen on 7/20: the frontend ended up on 5176 and the canonical
    # link stayed dead). --strictPort: if the port is still taken, Vite
    # FAILS instead of silently falling back to another one.
    clean_port(FRONT_PORT)
    env = {**os.environ, "POLPILOT_API_PORT": str(API_PORT)}
    npm = "npm.cmd" if IS_WINDOWS else "npm"
    return start_streamed(
        [npm, "run", "dev", "--", "--port", str(FRONT_PORT), "--strictPort"],
        cwd=FRONTEND, tag="frontend", env=env,
    )


def wait_port(port: int, proc: subprocess.Popen, timeout_s: int = 60) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        if proc.poll() is not None:
            fail("the frontend died on startup (pending npm install?)")
            sys.exit(1)
        try:
            # "localhost" tries every resolved address (127.0.0.1 and ::1):
            # Vite on Windows often listens on IPv6 only - the known trap.
            with socket.create_connection(("localhost", port), timeout=1):
                return
        except OSError:
            time.sleep(1)
    fail(f"frontend didn't open port {port} within {timeout_s}s")
    sys.exit(1)


def main() -> None:
    signal.signal(signal.SIGTERM, _on_sigterm)

    print(f"\n{BLUE}PolPilot{RESET} - Distribuidora del Litoral demo\n" + "-" * 45)
    clean_port(API_PORT)
    clean_port(FRONT_PORT)
    guard_snapshot()
    ensure_db()
    run_migrations()
    ensure_tenant()
    seed_dataset()
    seed_postgres()

    backend = start_backend()
    frontend = None
    try:
        wait_backend(backend)
        healthcheck(backend)
        frontend = start_frontend()
        wait_port(FRONT_PORT, frontend)
        print("-" * 45)
        ok(f"Demo ready -> http://localhost:{FRONT_PORT}")
        log("(logs straight in as the owner; EN|ES top right; Ctrl+C stops everything)")
        while True:
            time.sleep(2)
            for name, p in (("backend", backend), ("frontend", frontend)):
                if p.poll() is not None:
                    fail(f"{name} crashed (exit {p.returncode})")
                    raise KeyboardInterrupt
    except KeyboardInterrupt:
        print()
        log("shutting down…")
    finally:
        kill_process_tree(frontend, "frontend")
        kill_process_tree(backend, "backend")
        ok("ports clean (Postgres left running — `docker compose down` also stops it)")


if __name__ == "__main__":
    main()
