"""Dump real tool results as the /showcase fixtures.

Python owns the tool result shapes, so the fixtures are generated from real
calls rather than hand-written: a hand-written one drifts silently and makes
the showcase lie about what a presenter will receive.

Runs against the `demo` tenant, whose dataset is seeded and whose "today" is
fixed, so a regenerated fixture differs only when a tool's output actually
changed. Lists are trimmed: a showcase needs enough rows to show the layout,
not the whole dataset.

Run from the repo root:  py backend/scripts/generate_tool_fixtures.py
"""
from __future__ import annotations

import io
import json
import os
import pathlib
import sys

os.environ.setdefault("POLPILOT_TENANT", "demo")
os.environ.setdefault("POLPILOT_DEMO_TODAY", "2026-07-07")

BACKEND = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import angela  # noqa: E402

DEST = (BACKEND.parent / "frontend" / "src" / "components" / "assistant" /
        "tools" / "fixtures.generated.json")

MAX_LIST = 4
MAX_STR = 400

# Trimming a table's rows is harmless; trimming a chart's values is not. A
# dimensional `consultar_serie` result carries its bars in `top`, so cutting
# that list drops bars the real call would have drawn. (A temporal one is
# already a summary — `puntos` is a count, not the points; the widget
# recalculates the full series, per the tool's own description.) Small results
# either way, so this tool keeps them whole.
NO_TRIM = {"consultar_serie"}

# One case per registered presenter, plus the states a chat turn cannot be
# made to produce on demand — which are the ones most likely to be broken.
CASES = [
    ("resumen_negocio", {}, "business_summary"),
    ("estado_caja", {}, "cash_drawer"),
    ("top_inmovilizado", {"n": 8}, "top_tied_up_capital"),
    ("listar_grupo", {"grupo": "sin_pvp", "limit": 10}, "item_group"),
    ("listar_prioridades", {}, "priorities"),
    ("cuentas_corrientes", {}, "accounts_receivable"),
    ("consultar_serie", {"fuente": "ventas", "metrica": "pesos", "agrupar": "mes"},
     "series_monthly_sales"),
    ("consultar_serie", {"fuente": "inventario", "metrica": "inmovilizado",
                         "agrupar": "categoria", "top_n": 6}, "series_by_category"),
    ("consultar_serie", {"fuente": "ventas", "metrica": "participacion",
                         "producto": "no-existe-este-producto",
                         "universo": "total_negocio"}, "series_no_match"),
    ("consultar_serie", {"fuente": "ventas", "metrica": "no_existe_esta_metrica"},
     "series_not_available"),
]


def trim(value):
    if isinstance(value, dict):
        return {k: trim(v) for k, v in value.items()}
    if isinstance(value, list):
        return [trim(v) for v in value[:MAX_LIST]]
    if isinstance(value, str) and len(value) > MAX_STR:
        return value[:MAX_STR] + "…"
    return value


def main() -> int:
    angela._set_sesion(usuario="aldo", rol="dueño", features=None, idioma="es")
    out: dict[str, dict] = {}
    for tool, args, label in CASES:
        result, _action = angela._run_tool(tool, dict(args))
        kept = result if tool in NO_TRIM else trim(result)
        out[label] = {"toolName": tool, "args": args, "result": kept}
        state = result.get("ok") if isinstance(result, dict) else None
        print(f"{label:24s} {tool:20s} ok={state}")
    io.open(DEST, "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=2, default=str) + "\n")
    print(f"wrote {DEST} ({DEST.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
