"""
reposicion.py — el tiempo del PROVEEDOR, que es el dato que faltaba.

Saber que te quedan 7 días de stock no sirve solo: sirve cruzado con cuánto
tarda ese proveedor en reponer. Si tarda 15, ya llegaste tarde. Si tarda 4,
tenés 3 días para negociar con tiempo — y comprar con tiempo es comprar barato;
comprar apurado por un quiebre es comprar caro.

Acá viven las dos lecturas que ese cruce necesita:
  · las CONDICIONES de cada proveedor (frecuencia de lista, suba promedio y —
    lo nuevo — `dias_reposicion`), y
  · las OFERTAS vigentes que el proveedor empuja (para cruzarlas contra la
    rotación real antes de comprar de más).

Funciones de lectura: no calculan hallazgos (eso es de oportunidades_neg), no
tocan UI y nunca explotan si el archivo no está.
"""
from __future__ import annotations

import json
import os

from . import paths

CONDICIONES_JSON = os.path.join(paths.DATA_DIR, "proveedores_condiciones.json")

# Si un proveedor no declara su tiempo, no se inventa uno optimista: se usa el
# default del archivo y, si tampoco está, dos semanas (lo que tarda el promedio
# de la plaza). Siempre se informa como supuesto en la tarjeta.
DIAS_REPOSICION_FALLBACK = 14


def _load() -> dict:
    try:
        with open(CONDICIONES_JSON, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:  # noqa: BLE001 — sin archivo, el módulo se calla
        return {}


def condiciones() -> list[dict]:
    return list(_load().get("proveedores") or [])


def condiciones_de(proveedor: str | None) -> dict | None:
    if not proveedor:
        return None
    objetivo = str(proveedor).strip().lower()
    for c in condiciones():
        if str(c.get("proveedor", "")).strip().lower() == objetivo:
            return c
    return None


def dias_reposicion(proveedor: str | None) -> tuple[int, bool]:
    """(días que tarda ese proveedor, si el dato es SUYO o un default).

    El booleano importa: una tarjeta que promete "tu proveedor tarda 4 días"
    tiene que poder decir si eso salió de sus condiciones o de un supuesto.
    """
    c = condiciones_de(proveedor)
    if c and c.get("dias_reposicion"):
        return int(c["dias_reposicion"]), True
    d = _load().get("dias_reposicion_default")
    return int(d or DIAS_REPOSICION_FALLBACK), False


def ofertas() -> list[dict]:
    """Ofertas que el proveedor está empujando hoy (las que todavía no vencieron
    se filtran en el hallazgo, que es quien conoce el 'hoy' del análisis)."""
    return list(_load().get("ofertas") or [])
