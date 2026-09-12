"""Run the evals and record the result.

This is the ONLY thing that produces the numbers the product shows on its
quality panel. `/api/evals` reads what this wrote; it never recomputes. That
split is deliberate — see the header of `core/evals.py`, rule 1.

Runs against the `demo` tenant, whose dataset is seeded and whose "today" is
frozen at 2026-07-07, so two runs differ only when the engine changed.

Run from the repo root:

    py backend/scripts/run_evals.py

Exit code is 0 even when cases miss: a miss is a measurement, not a build
failure. Pass --estricto to exit 1 when anything missed (for CI, where a drop
in the score SHOULD stop a merge).

Needs the same environment the backend needs (DATABASE_URL / APP_DATABASE_URL),
because the engine reads the tenant's real tables — an eval that ran against
something other than the product would be measuring the wrong thing.
"""
from __future__ import annotations

import argparse
import io
import os
import pathlib
import sys

os.environ.setdefault("POLPILOT_TENANT", "demo")
os.environ.setdefault("POLPILOT_DEMO_TODAY", "2026-07-07")

BACKEND = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

from core import evals  # noqa: E402


def _barra(aciertos: int, total: int, ancho: int = 24) -> str:
    if not total:
        return " " * ancho
    llenos = round(ancho * aciertos / total)
    return "#" * llenos + "." * (ancho - llenos)


def main() -> int:
    ap = argparse.ArgumentParser(description="Corre los evals y guarda el reporte.")
    ap.add_argument("--estricto", action="store_true",
                    help="salir con código 1 si algún caso falla")
    ap.add_argument("--seco", action="store_true",
                    help="correr sin guardar (ensayo antes de una demo)")
    args = ap.parse_args()

    # The lock lives in core/evals.py (FLAG_EVALS), not here, so that EVERY
    # caller hits it — not just this script. Catching it here only buys a
    # readable message instead of a traceback.
    if not evals.habilitados():
        print(f"\n  Los evals están APAGADOS.\n\n"
              f"  Correrlos recomputa todos los hallazgos tres veces y tarda.\n"
              f"  En una demo de 2m30 eso es latencia, así que el default es no correr.\n\n"
              f"  Para correrlos a propósito:\n"
              f"      {evals.FLAG_EVALS}=1 py backend/scripts/run_evals.py\n")
        return 2

    reporte = evals.correr()

    print()
    print(f"  EVALS · {reporte['empresa']} (tenant {reporte['tenant']})")
    print(f"  hoy del dataset: {reporte['hoy']} · corrida: {reporte['generado']}"
          f" · {reporte['duracion_s']}s")
    print(f"  dataset: {reporte['dataset']}")
    print()
    for s in reporte["suites"]:
        # The denominator is printed next to the score, always. Same rule the
        # screen follows (core/evals.py, rule 2).
        print(f"  {s['nombre']:<34} {s['aciertos']:>3} de {s['total']:<3} "
              f"[{_barra(s['aciertos'], s['total'])}]")
        for c in s["casos"]:
            if not c["ok"]:
                print(f"       falla · {c['id']}: {c['detalle']}")
    r = reporte["resumen"]
    print()
    print(f"  TOTAL: {r['aciertos']} de {r['total']}")

    cobertura = next((s.get("cobertura_observada") for s in reporte["suites"]
                      if s.get("cobertura_observada")), None)
    if cobertura:
        print(f"  (observado, sin puntuar: {len(cobertura['emitidos'])} de "
              f"{cobertura['del_catalogo']} cruces de umbral tienen datos hoy)")

    if args.seco:
        print("\n  --seco: no se guardó nada.\n")
    else:
        destino = evals.guardar(reporte)
        print(f"\n  guardado en {destino}\n")

    if args.estricto and r["aciertos"] < r["total"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
