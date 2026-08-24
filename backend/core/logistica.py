"""
Logística (capa sobre el TMS) — estado de envíos, no optimización de rutas.

PolPilot NO es un TMS: el sistema de reparto asigna camiones y rutas. Nosotros
leemos su export (vía Staging Area) y lo volvemos consultable por Ángela:
"¿salió el pedido de García?", "¿qué entregas hay hoy?", "¿qué está atrasado?".

Los datos viven en el apartado "logistica" (esquema/apartados.json): filas con
{pedido, cliente, direccion, estado, fecha_prevista, transporte}.
"""
from __future__ import annotations

import unicodedata

from . import esquema
from .fechas import parse_fecha, hoy


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _estado_norm(estado: str) -> str:
    """Los TMS escriben el estado como quieren; acá lo normalizamos a tres valores."""
    e = _norm(estado)
    if any(k in e for k in ("entregad", "cumplid", "finaliz")):
        return "entregado"
    if any(k in e for k in ("camino", "transito", "salio", "despachad", "viaje")):
        return "en_camino"
    return "pendiente"


def _enriquecer(f: dict) -> dict:
    fecha = parse_fecha(f.get("fecha_prevista"))
    estado = _estado_norm(f.get("estado"))
    return {
        **f,
        "estado_norm": estado,
        "atrasado": bool(fecha and fecha < hoy() and estado != "entregado"),
    }


def envios() -> list[dict]:
    return [_enriquecer(f) for f in esquema.filas("logistica")]


def hay_datos() -> bool:
    return bool(esquema.filas("logistica"))


def de_hoy() -> list[dict]:
    """Las entregas previstas para hoy (el día de reparto)."""
    h = hoy()
    return [e for e in envios() if parse_fecha(e.get("fecha_prevista")) == h]


def atrasados() -> list[dict]:
    """Entregas con fecha prevista pasada que todavía no se entregaron."""
    return sorted((e for e in envios() if e["atrasado"]),
                  key=lambda e: str(e.get("fecha_prevista")))


def estado_pedido(texto: str) -> list[dict]:
    """Estado de un pedido: por número exacto o por nombre (parcial) del cliente."""
    t = _norm(texto)
    if not t:
        return []
    out = []
    for e in envios():
        por_pedido = str(e.get("pedido") or "").strip().lower() == t
        por_cliente = t in _norm(e.get("cliente"))
        if por_pedido or por_cliente:
            out.append(e)
    return out


def resumen_reparto() -> dict:
    """El día de reparto de un vistazo: por camión, cuánto salió y cuánto falta."""
    del_dia = de_hoy()
    por_transporte: dict = {}
    for e in del_dia:
        t = e.get("transporte") or "Sin asignar"
        d = por_transporte.setdefault(t, {"transporte": t, "total": 0, "entregados": 0,
                                          "en_camino": 0, "pendientes": 0})
        d["total"] += 1
        d[{"entregado": "entregados", "en_camino": "en_camino"}.get(e["estado_norm"], "pendientes")] += 1
    return {
        "hay_datos": hay_datos(),
        "entregas_hoy": len(del_dia),
        "atrasados": len(atrasados()),
        "camiones": sorted(por_transporte.values(), key=lambda d: d["transporte"]),
    }
