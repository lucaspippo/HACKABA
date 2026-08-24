"""
Sync bidireccional con sistemas externos (Faro/Tango) — Fase 1: delta export.

PolPilot limpia los datos; los cambios tienen que poder VOLVER al sistema origen,
pero SOLO los registros que cambiaron (deltas), nunca la base entera, y solo como
UPDATE (nunca DELETE/INSERT ciego). El delta sale de comparar el estado actual del
núcleo de verdad contra el baseline original (inventory.json) — esa es la delta table.

Fase 2 (webhook) y Fase 3 (MCP/API) quedan como hooks; ver core/conectores.py.
"""
from __future__ import annotations

import csv
import io
import json
import os

from . import paths
from . import store, pricing

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = paths.DATA_DIR  # por-tenant: env POLPILOT_DATA_DIR o data/ (ver core/paths.py)
BASELINE_JSON = os.path.join(DATA_DIR, "inventory.json")  # lo que vino de Faro (origen)

# Campos que viajan en el delta (los que PolPilot corrige sobre un producto).
CAMPOS_EXPORT = ["pvp", "costo_iva", "stock", "estado", "valor_peso"]

# --- Resolución de conflictos: quién gana por tipo de dato (configurable) ---
# precios/estados/cuentas → PolPilot (los corregimos); stock vivo/fiscal → Faro.
SOURCE_OF_TRUTH = {
    "pvp": "polpilot", "costo_iva": "polpilot", "estado": "polpilot", "valor_peso": "polpilot",
    "stock": "faro", "cuit": "faro", "condicion_iva": "faro",
}


def quien_gana(campo: str, default: str = "polpilot") -> str:
    return SOURCE_OF_TRUTH.get(campo, default)


def set_source_of_truth(campo: str, sistema: str) -> None:
    """El dueño puede ajustar quién gana en cada campo."""
    SOURCE_OF_TRUTH[campo] = sistema


def _baseline() -> dict:
    try:
        data = json.load(open(BASELINE_JSON, encoding="utf-8"))
        return {d.get("codigo"): d for d in data["articulos"]}
    except Exception:
        return {}


def deltas() -> list[dict]:
    """Solo los registros EXISTENTES que cambiaron vs. el origen (UPDATEs)."""
    base = _baseline()
    out = []
    for d in store.raw_actual():
        cod = d.get("codigo")
        b = base.get(cod)
        if not b:
            continue  # registro nuevo → sería INSERT, no va en el delta de UPDATE
        cambios = {c: {"antes": b.get(c), "ahora": d.get(c)}
                   for c in CAMPOS_EXPORT if d.get(c) != b.get(c)}
        if cambios:
            out.append({"codigo": cod, "descripcion": d.get("descripcion"), "cambios": cambios})
    return out


# Columnas por formato de destino (cuando se conozca el schema exacto de Faro/Tango
# se ajustan acá; hoy comparten estructura genérica con cabeceras propias).
# 'unidad' es explícita para que el pvp NUNCA se lea mal: $/kg (balanza) vs $/u.
_FORMATOS = {
    "generico": {"codigo": "codigo", "descripcion": "descripcion", "unidad": "unidad_precio",
                 "pvp": "pvp", "costo_iva": "costo", "stock": "stock", "estado": "estado",
                 "valor_peso": "valor_peso"},
    "faro": {"codigo": "CODIGO", "descripcion": "DESCRIPCION", "unidad": "UNIDAD_PRECIO",
              "pvp": "PVENTA", "costo_iva": "COSTO", "stock": "STOCK", "estado": "ESTADO",
              "valor_peso": "VALOR_PESO"},
    "tango": {"codigo": "COD_ARTICU", "descripcion": "DESCRIPCIO", "unidad": "UNIDAD_PRECIO",
              "pvp": "PRECIO", "costo_iva": "COSTO", "stock": "CANT_STOCK", "estado": "ESTADO",
              "valor_peso": "PESO"},
}


def generar_delta_export(formato: str = "generico") -> dict:
    """Genera el CSV con SOLO los registros modificados, listo para re-importar (UPDATE)."""
    cols = _FORMATOS.get(formato, _FORMATOS["generico"])
    ds = deltas()
    buf = io.StringIO()
    w = csv.writer(buf)
    # ID + descripción + UNIDAD (kg/unidad) + campos cambiados. La unidad va SIEMPRE
    # para que el destino sepa que el pvp de una balanza es $/kg, no $/unidad.
    encabezados = ([cols["codigo"], cols["descripcion"], cols["unidad"]]
                   + [cols[c] for c in CAMPOS_EXPORT])
    w.writerow(encabezados)
    balanzas = 0
    for d in ds:
        actual = store_record(d["codigo"])
        u = pricing.unidad(actual)  # "kg" para balanza, "unidad" para el resto
        if u == "kg":
            balanzas += 1
        fila = ([d["codigo"], d["descripcion"], u]
                + [actual.get(c, "") for c in CAMPOS_EXPORT])
        w.writerow(fila)
    nota = ("Solo los registros que cambiaron. Re-importable como UPDATE (no duplica: "
            "matchea por código). No incluye altas ni bajas.")
    if balanzas:
        nota += (f" OJO: {balanzas} son productos por peso — su precio (PVENTA) está en "
                 f"$/kg, no $/unidad. La columna UNIDAD_PRECIO lo indica en cada fila.")
    return {"formato": formato, "registros": len(ds), "balanzas": balanzas,
            "csv": buf.getvalue(), "nota": nota}


def store_record(codigo) -> dict:
    return next((d for d in store.raw_actual() if d.get("codigo") == codigo), {})


def detectar_conflictos(cambios_externos: list[dict] | None = None) -> list[dict]:
    """Conflictos: un registro que el sistema externo cambió DESPUÉS de importarlo y que
    PolPilot también cambió. Hoy no hay feed externo (Fase 2/3) → lista vacía. La lógica
    de 'quién gana' (quien_gana) ya está separada y lista para ejecutarse sin humano."""
    conflictos = []
    nuestros = {d["codigo"]: d for d in deltas()}
    for ext in (cambios_externos or []):
        cod = ext.get("codigo")
        if cod in nuestros:
            for campo in ext.get("campos", []):
                if campo in nuestros[cod]["cambios"]:
                    conflictos.append({"codigo": cod, "campo": campo, "gana": quien_gana(campo)})
    return conflictos
