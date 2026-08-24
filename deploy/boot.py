"""
P22·C — Arranque del contenedor (Render): el seed + healthcheck de start_demo,
portado. El servidor JAMÁS levanta sin datos: si el seed falla, este proceso
sale con error, el contenedor no queda healthy y Render no lo publica.

Pasos:
  1. generar.py (idempotente, determinista): siembra lo que falte en DATA_DIR.
  2. Verificación dura: inventario cargado y con artículos.
  3. Copia canónica para el RESET (DATA_DIR → POLPILOT_CANONICAL_DIR): el
     endpoint admin de reset restaura ESTE estado sin reiniciar el contenedor.
     (Además, el filesystem de Render es efímero: cada restart/redeploy ya
     vuelve solo al estado de la imagen.)
  4. exec uvicorn en $PORT — el precalentado del análisis corre en el lifespan.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(HERE)
DATA_DIR = os.environ.get("POLPILOT_DATA_DIR") or os.path.join(RAIZ, "data-demo")
CANONICAL = os.environ.get("POLPILOT_CANONICAL_DIR")


def fallar(msg: str) -> None:
    print(f"[boot][X] {msg}", flush=True)
    sys.exit(1)


def main() -> None:
    # 1 · seed idempotente (el mismo generar.py de siempre)
    gen = os.path.join(DATA_DIR, "generar.py")
    if not os.path.exists(gen):
        fallar(f"no existe {gen} — ¿la imagen copió data-demo/?")
    r = subprocess.run([sys.executable, gen], capture_output=True, text=True,
                       cwd=DATA_DIR, timeout=180)
    if r.returncode != 0:
        print(r.stdout[-1500:] + r.stderr[-1500:], flush=True)
        fallar("generar.py falló — el server NO levanta sin datos")
    print("[boot] seed verificado (generar.py)", flush=True)

    # 2 · verificación dura del dataset
    inv = os.path.join(DATA_DIR, "inventory.json")
    try:
        articulos = json.load(open(inv, encoding="utf-8"))
        n = len(articulos.get("articulos") or articulos) if isinstance(articulos, dict) else len(articulos)
        assert n > 0
    except Exception as e:  # noqa: BLE001
        fallar(f"inventario ilegible o vacío ({e}) — el server NO levanta sin datos")
    print(f"[boot] dataset ok: {n} artículos", flush=True)

    # 3 · copia canónica para el reset manual
    if CANONICAL:
        if os.path.isdir(CANONICAL):
            shutil.rmtree(CANONICAL)
        shutil.copytree(DATA_DIR, CANONICAL)
        print(f"[boot] copia canónica en {CANONICAL} (reset admin disponible)", flush=True)

    # 4 · uvicorn en el puerto que Render asigna
    puerto = os.environ.get("PORT", "8000")
    os.chdir(os.path.join(RAIZ, "backend"))
    os.execvp(sys.executable, [sys.executable, "-m", "uvicorn", "main:app",
                               "--host", "0.0.0.0", "--port", puerto])


if __name__ == "__main__":
    main()
