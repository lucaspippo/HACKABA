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
  5. Dataset verification against POSTGRES (not the JSON file on disk, which
     the server no longer reads at runtime). It separates two failures the
     old single assertion conflated — and conflating them made a productive
     tenant's FIRST deploy impossible, because the only way to load its data
     is through an app that would not start:
       - Postgres unreadable (no APP_DATABASE_URL, refused connection, bad
         credentials, missing schema, no `tenants` row): a real
         misconfiguration, hard exit.
       - Postgres readable but this tenant has no inventory yet: with
         seeding ON that means the seed silently did nothing, so it is still
         a hard exit. With seeding OFF it is a legitimate day-one productive
         tenant that has not loaded its data yet — warn loudly and serve, so
         the operator can actually load it.
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
from typing import NoReturn

HERE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(HERE)
BACKEND = os.path.join(RAIZ, "backend")
DATA_DIR = os.environ.get("POLPILOT_DATA_DIR") or os.path.join(RAIZ, "data-demo")
CANONICAL = os.environ.get("POLPILOT_CANONICAL_DIR")

sys.path.insert(0, BACKEND)
import deploy_guard  # noqa: E402  (needs BACKEND on the path first)


def fallar(msg: str) -> NoReturn:
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
        # Skipped is not the same as unchecked: if this tenant HAS a seed
        # baseline and the dataset under it changed, say so out loud.
        # Never fatal — a productive tenant with its own data is the
        # normal case, and nothing here touches it.
        try:
            seed_db.revisar_seeds()
        except Exception as e:  # noqa: BLE001 — a warning must never stop a boot
            print(f"[boot] seed check skipped ({e})", flush=True)

    # 5 · dataset verification against POSTGRES, the real runtime source
    #     (inventory.json on disk is only the seed source above). Reading and
    #     being empty are DIFFERENT failures — see the module docstring.
    try:
        from core.db import inventory_repo
        from core.db import tenant as db_tenant
        articulos = inventory_repo.get_articles(db_tenant.current_tenant_id())
    except Exception as e:  # noqa: BLE001
        fallar(f"Postgres unreadable ({e}) — check APP_DATABASE_URL, the "
               f"credentials and that the schema is migrated (deploy/migrate.py)")
    n = len(articulos or [])
    if n > 0:
        print(f"[boot] dataset ok: {n} artículos (Postgres)", flush=True)
    elif deploy_guard.seed_on_boot():
        # Seeding ran and left nothing behind: silent data loss, not a
        # day-one tenant. Never serve an empty demo.
        fallar(f"tenant '{tenant}' has no inventory in Postgres even though "
               f"POLPILOT_SEED_ON_BOOT is on — the seed did nothing")
    else:
        print(f"[boot][!] tenant '{tenant}' has no inventory in Postgres yet — "
              f"serving anyway so its data can be loaded through the app. "
              f"This is expected on a productive tenant's first deploy; if it "
              f"persists, check that POLPILOT_TENANT and APP_DATABASE_URL name "
              f"the intended tenant and database.", flush=True)

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
