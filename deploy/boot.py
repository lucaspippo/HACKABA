"""
P22·C — Arranque del contenedor (Render): el seed + healthcheck de start_demo,
portado. El servidor JAMÁS levanta sin datos: si el seed falla, este proceso
sale con error, el contenedor no queda healthy y Render no lo publica.

Pasos:
  1. Alembic (backend/migrations): el schema de Postgres queda al día antes
     de que el server toque una sola tabla.
  2. generar.py (idempotente, determinista): siembra lo que falte en DATA_DIR
     para los dominios que TODAVÍA son JSON (inventario y el resto — ver
     backend/core/db/MIGRATING_A_MODULE.md para qué falta migrar).
  3. seed_db.run(): siembra Postgres para los dominios YA migrados (tenant,
     auth_credentials, cuentas — ver Task 8/9 del plan de fundación).
  4. Verificación dura: inventario cargado y con artículos.
  5. Copia canónica para el RESET (DATA_DIR → POLPILOT_CANONICAL_DIR): el
     endpoint admin de reset restaura ESTE estado sin reiniciar el contenedor.
     (Además, el filesystem de Render es efímero: cada restart/redeploy ya
     vuelve solo al estado de la imagen.)
  6. exec uvicorn en $PORT — el precalentado del análisis corre en el lifespan.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(HERE)
BACKEND = os.path.join(RAIZ, "backend")
DATA_DIR = os.environ.get("POLPILOT_DATA_DIR") or os.path.join(RAIZ, "data-demo")
CANONICAL = os.environ.get("POLPILOT_CANONICAL_DIR")


def fallar(msg: str) -> None:
    print(f"[boot][X] {msg}", flush=True)
    sys.exit(1)


def main() -> None:
    # 1 · migraciones (Alembic) — el server NO levanta con un schema viejo.
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True, text=True, cwd=BACKEND, timeout=120,
    )
    if r.returncode != 0:
        print(r.stdout[-1500:] + r.stderr[-1500:], flush=True)
        fallar("alembic upgrade head falló — el server NO levanta con un schema desactualizado")
    print("[boot] migraciones aplicadas", flush=True)

    # 2 · seed idempotente (el mismo generar.py de siempre — dominios aún JSON)
    gen = os.path.join(DATA_DIR, "generar.py")
    if not os.path.exists(gen):
        fallar(f"no existe {gen} — ¿la imagen copió data-demo/?")
    r = subprocess.run([sys.executable, gen], capture_output=True, text=True,
                       cwd=DATA_DIR, timeout=180)
    if r.returncode != 0:
        print(r.stdout[-1500:] + r.stderr[-1500:], flush=True)
        fallar("generar.py falló — el server NO levanta sin datos")
    print("[boot] seed verificado (generar.py)", flush=True)

    # 3 · seed idempotente de Postgres (dominios ya migrados: tenant, auth, cuentas)
    tenant = os.environ.get("POLPILOT_TENANT", "demo")
    sys.path.insert(0, DATA_DIR)
    sys.path.insert(0, BACKEND)
    import seed_db
    try:
        seed_db.run(tenant)
    except Exception as e:  # noqa: BLE001
        fallar(f"seed_db.run() falló ({e}) — el server NO levanta sin datos")
    print(f"[boot] Postgres seed ok (tenant={tenant})", flush=True)

    # 4 · verificación dura del dataset
    inv = os.path.join(DATA_DIR, "inventory.json")
    try:
        articulos = json.load(open(inv, encoding="utf-8"))
        n = len(articulos.get("articulos") or articulos) if isinstance(articulos, dict) else len(articulos)
        assert n > 0
    except Exception as e:  # noqa: BLE001
        fallar(f"inventario ilegible o vacío ({e}) — el server NO levanta sin datos")
    print(f"[boot] dataset ok: {n} artículos", flush=True)

    # 5 · copia canónica para el reset manual
    if CANONICAL:
        if os.path.isdir(CANONICAL):
            shutil.rmtree(CANONICAL)
        shutil.copytree(DATA_DIR, CANONICAL)
        print(f"[boot] copia canónica en {CANONICAL} (reset admin disponible)", flush=True)

    # 6 · uvicorn en el puerto que Render asigna
    puerto = os.environ.get("PORT", "8000")
    os.chdir(BACKEND)
    os.execvp(sys.executable, [sys.executable, "-m", "uvicorn", "main:app",
                               "--host", "0.0.0.0", "--port", puerto])


if __name__ == "__main__":
    main()
