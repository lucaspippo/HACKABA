"""
Depósito (capa sobre el WMS) — consultas, no picking.

PolPilot NO es un WMS: el sistema de depósito (Faro u otro) resuelve
ubicaciones, picking y espacios. Nosotros leemos su export (vía Staging Area)
y lo volvemos consultable por Ángela: dónde está un producto, qué vence pronto,
y dónde el stock físico no coincide con el contable.

Los datos viven en el apartado "deposito" (esquema/apartados.json): filas con
{codigo, producto, ubicacion, lote, vencimiento, cantidad}.
"""
from __future__ import annotations

import unicodedata

from . import esquema, store, conocimiento
from .fechas import parse_fecha, hoy

VENCIMIENTO_ALERTA_DIAS = 7  # default de "vence pronto"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _filas() -> list[dict]:
    return esquema.filas("deposito")


def hay_datos() -> bool:
    return bool(_filas())


def ubicacion_de(texto: str) -> list[dict]:
    """Dónde está un producto: matchea por código exacto o nombre parcial."""
    t = _norm(texto)
    out = []
    for f in _filas():
        por_codigo = t and str(f.get("codigo") or "") == t
        por_nombre = t and t in _norm(f.get("producto"))
        if por_codigo or por_nombre:
            out.append(dict(f))
    return out


def vencimientos(dias: int = VENCIMIENTO_ALERTA_DIAS) -> list[dict]:
    """Lotes que vencen dentro de N días (incluye hoy), ordenados por urgencia."""
    h = hoy()
    out = []
    for f in _filas():
        v = parse_fecha(f.get("vencimiento"))
        if v and 0 <= (v - h).days <= dias:
            out.append({**f, "dias_restantes": (v - h).days})
    return sorted(out, key=lambda x: x["dias_restantes"])


def vencidos() -> list[dict]:
    """Lotes cuyo vencimiento ya pasó (plata a punto de perderse o perdida)."""
    h = hoy()
    out = []
    for f in _filas():
        v = parse_fecha(f.get("vencimiento"))
        if v and v < h:
            out.append({**f, "dias_vencido": (h - v).days})
    return sorted(out, key=lambda x: x["dias_vencido"], reverse=True)


def discrepancias() -> list[dict]:
    """Stock físico (suma de lotes del depósito) vs stock contable (inventario).
    El clásico: el sistema dice 40 y en la estantería hay 25."""
    fisico: dict = {}
    for f in _filas():
        c = f.get("codigo")
        if c is None:
            continue
        fisico[c] = fisico.get(c, 0.0) + float(f.get("cantidad") or 0)
    contable = {d.get("codigo"): d for d in store.raw_actual()}
    out = []
    for c, cant in fisico.items():
        d = contable.get(c)
        if not d:
            continue  # producto no está en el inventario: lo frena el staging, no acá
        stock = float(d.get("stock") or 0)
        if abs(stock - cant) > 0.01:
            out.append({
                "codigo": c, "descripcion": d.get("descripcion"),
                "stock_contable": stock, "stock_fisico": round(cant, 2),
                "diferencia": round(cant - stock, 2),
            })
    return sorted(out, key=lambda x: abs(x["diferencia"]), reverse=True)


def discrepancias_conocimiento() -> dict:
    """Piece 12 — la excepción de Aldo ("la balanza 2 desvía <1%: no me alertes")
    saca de la lista visible las discrepancias de balanza por debajo del umbral,
    pero NO las esconde: van a `suprimidas` para el registro visible ("1 alerta
    suprimida por tu regla — vela acá"). Sin regla activa, todo queda visible."""
    disc = discrepancias()
    reglas = [p for p in conocimiento.aplicables(nodo="deposito", efecto="suprime_alerta")
              if (p.get("params") or {}).get("umbral_pct") is not None]
    if not reglas:
        return {"visibles": disc, "suprimidas": [], "reglas": []}
    tipo_por_cod = {d.get("codigo"): (d.get("tipo") or "") for d in store.raw_actual()}
    visibles, suprimidas = [], []
    for x in disc:
        es_balanza = "balanza" in str(tipo_por_cod.get(x["codigo"], "")).lower()
        base = x.get("stock_contable") or 0
        pct = abs(x.get("diferencia") or 0) / base * 100 if base else 0.0
        regla = next((r for r in reglas
                      if es_balanza and pct < r["params"]["umbral_pct"]), None)
        if regla:
            suprimidas.append({**x, "diferencia_pct": round(pct, 2),
                               "regla": conocimiento.resumen_pieza(regla)})
        else:
            visibles.append(x)
    return {"visibles": visibles, "suprimidas": suprimidas,
            "reglas": [conocimiento.resumen_pieza(r) for r in reglas]}


def resumen() -> dict:
    filas = _filas()
    return {
        "hay_datos": bool(filas),
        "lotes": len(filas),
        "ubicaciones": len({f.get("ubicacion") for f in filas if f.get("ubicacion")}),
        "por_vencer": len(vencimientos()),
        "vencidos": len(vencidos()),
        "discrepancias": len(discrepancias_conocimiento()["visibles"]),
    }
