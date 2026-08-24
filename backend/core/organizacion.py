"""
Organización (tenant) — la base multi-tenant.

Cada PyME es una organización con su config y sus usuarios. Hoy Horizonte es
el tenant único, pero la estructura está lista para sumar un segundo sin tocar
la lógica: los datos y la config viven por organización.

Distinción de scope (clave del producto):
  - config de ORGANIZACIÓN (margen mínimo, balanzas por peso): la fija el dueño,
    afecta a todos los usuarios del tenant. Scope "organization".
  - personalización de VISTA (gráficos, columnas): la hace cada usuario para sí.
    Scope "user" (vive en su memoria, no acá).
"""
from __future__ import annotations

import json
import os

from . import paths

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = paths.DATA_DIR  # por-tenant: env POLPILOT_DATA_DIR o data/ (ver core/paths.py)
ORG_JSON = os.path.join(DATA_DIR, "organizacion.json")

DEFAULT = {
    "id": "piloto",
    "nombre": "Supermercados Horizonte",
    "rubro": "distribuidora + supermercado + franquicias",
    "config": {
        "margen_minimo": 30,        # %; Ángela alerta lo que esté por debajo
        "balanza_por_peso": True,   # los productos de balanza se computan por kg
    },
}

# Cambios que afectan a TODA la organización → requieren rol dueño/admin.
CLAVES_ORG = {"margen_minimo", "balanza_por_peso"}


def get() -> dict:
    try:
        return {**DEFAULT, **json.load(open(ORG_JSON, encoding="utf-8"))}
    except Exception:
        return dict(DEFAULT)


def set_config(clave: str, valor) -> dict:
    org = get()
    org["config"][clave] = valor
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(org, open(ORG_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return org


def puede_config_org(rol: str | None) -> bool:
    """Sólo el dueño (o admin delegado) cambia config de organización."""
    return (rol or "").strip().lower() in ("dueño", "dueno", "admin")
