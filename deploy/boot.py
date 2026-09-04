"""Container entrypoint (Render): the seed + healthcheck from start_demo,
ported. The server NEVER comes up without data: if the seed fails, this
process exits with an error, the container never goes healthy, and Render
does not publish it.

Steps:
  1. deploy_guard.require_tenant(): refuses to boot without an explicit
     POLPILOT_TENANT, so a misconfigured deployment cannot silently serve
     the demo tenant's data.
  2. seed_db.ensure_tenant(): creates the `tenants` row if it does not exist
     yet. MUST run before generar.py, not after: generar.py calls straight
     into already-Postgres modules (core.staging, core.perfiles,
     core.comprobantes) partway through (sembrar_staging/sembrar_
     auditoria/etc.), and those calls fail without a tenant row. On a
     repeated boot this was masked (the row already existed from a previous
     boot) — a genuinely new Postgres (first real boot, or CI) breaks
     immediately. See the real bug documented in
     backend/core/db/MIGRATING_A_MODULE.md.
  3-4. generar.py + seed_db.run(): DEMO ONLY, gated behind
     deploy_guard.seed_on_boot() (POLPILOT_SEED_ON_BOOT=1). generar.py
     rewrites the whole source dataset in DATA_DIR (inventory.json and the
     rest) deterministically, and also seeds some already-Postgres domains
     (staging, auditoria, perfiles, comprobantes) directly, the same way a
     real usage would. That is exactly right for the public demo — it makes
     the dataset self-healing on Render's ephemeral filesystem — and it is
     data loss on a productive tenant, so it defaults to off. seed_db.run()
     then seeds Postgres: auth_credentials and every migrated domain
     generar.py has not already seeded directly (see
     backend/core/db/MIGRATING_A_MODULE.md). Idempotent: re-creating the
     tenant row here is a no-op (ensure_tenant() already created it in
     step 2).
  5. Hard verification: the inventory landed in POSTGRES (not the JSON file
     on disk, which the server no longer reads at runtime). This still
     guards a misconfigured productive tenant correctly — it is true for a
     real tenant with real data and false otherwise.
  6. Canonical copy for RESET (DATA_DIR -> POLPILOT_CANONICAL_DIR): the
     admin reset endpoint restores THIS state without restarting the
     container. (Render's filesystem is also ephemeral: every
     restart/redeploy already reverts to the image's own state.)
  7. exec uvicorn on $PORT — the analysis warm-up runs in the lifespan.

Migrations are NOT here: they moved to deploy/migrate.py, which Render runs
as the preDeployCommand. That way a failed migration fails the deploy
instead of exiting this process and taking a running instance down.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(HERE)
BACKEND = os.path.join(RAIZ, "backend")
DATA_DIR = os.environ.get("POLPILOT_DATA_DIR") or os.path.join(RAIZ, "data-demo")
CANONICAL = os.environ.get("POLPILOT_CANONICAL_DIR")

sys.path.insert(0, BACKEND)
import deploy_guard  # noqa: E402  (needs BACKEND on the path first)


def fallar(msg: str) -> None:
    print(f"[boot][X] {msg}", flush=True)
    sys.exit(1)


def main() -> None:
    # Migrations are NOT here any more: deploy/migrate.py runs them as
    # Render's preDeployCommand, so a failed migration fails the deploy
    # instead of taking the running service down.
    tenant = deploy_guard.require_tenant()
    sys.path.insert(0, DATA_DIR)
    import seed_db

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

    # 5 · verificación dura del dataset — contra POSTGRES, la fuente real en
    #     runtime (inventory.json en disco es sólo el seed source de arriba)
    try:
        from core import store as core_store
        n = len(core_store.raw_actual())
        assert n > 0
    except Exception as e:  # noqa: BLE001
        fallar(f"inventario ilegible o vacío en Postgres ({e}) — el server NO levanta sin datos")
    print(f"[boot] dataset ok: {n} artículos (Postgres)", flush=True)

    # 6 · copia canónica para el reset manual
    if CANONICAL:
        if os.path.isdir(CANONICAL):
            shutil.rmtree(CANONICAL)
        shutil.copytree(DATA_DIR, CANONICAL)
        print(f"[boot] copia canónica en {CANONICAL} (reset admin disponible)", flush=True)

    # 7 · uvicorn en el puerto que Render asigna
    puerto = os.environ.get("PORT", "8000")
    os.chdir(BACKEND)
    os.execvp(sys.executable, [sys.executable, "-m", "uvicorn", "main:app",
                               "--host", "0.0.0.0", "--port", puerto])


if __name__ == "__main__":
    main()
