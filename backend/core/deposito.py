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
    """Stock físico vs stock contable.

    CSV/WMS path: sum(cantidad) vs product.stock.
    When any depósito row for a product has counted_qty (Odoo inventory in
    progress), compare summed counted_qty vs summed cantidad instead.
    """
    by_code: dict = {}
    for f in _filas():
        c = f.get("codigo")
        if c is None:
            continue
        bucket = by_code.setdefault(c, {"cantidad": 0.0, "counted": 0.0, "has_counted": False})
        bucket["cantidad"] += float(f.get("cantidad") or 0)
        if f.get("counted_qty") is not None:
            bucket["has_counted"] = True
            bucket["counted"] += float(f.get("counted_qty") or 0)
    contable = {d.get("codigo"): d for d in store.raw_actual()}
    out = []
    for c, b in by_code.items():
        d = contable.get(c)
        if not d:
            continue
        if b["has_counted"]:
            stock_contable = b["cantidad"]
            stock_fisico = b["counted"]
        else:
            stock_contable = float(d.get("stock") or 0)
            stock_fisico = b["cantidad"]
        if abs(stock_contable - stock_fisico) > 0.01:
            out.append({
                "codigo": c, "descripcion": d.get("descripcion"),
                "stock_contable": round(stock_contable, 2),
                "stock_fisico": round(stock_fisico, 2),
                "diferencia": round(stock_fisico - stock_contable, 2),
            })
    return sorted(out, key=lambda x: abs(x["diferencia"]), reverse=True)


# Cuánto para atrás se mira una nota que explique una diferencia. Un aviso de
# hace un mes ya no explica el conteo de hoy; uno de la misma semana, sí.
DIAS_EXPLICACION = 15


def _ubicaciones_de(codigo) -> list[str]:
    return sorted({f.get("ubicacion") for f in _filas()
                   if f.get("codigo") == codigo and f.get("ubicacion")})


def explicaciones(disc: list[dict] | None = None,
                  dias: int = DIAS_EXPLICACION) -> list[dict]:
    """Cada diferencia, con lo que el equipo dijo de esa ubicación.

    EL ERP DICE «FALTAN 6,5». NOSOTROS PODEMOS DECIR POR QUÉ.

    En el dataset del demo hay una diferencia de −6,5 unidades de leche en
    Pasillo 4 · Rack B, y ese mismo día dos personas dejaron su aviso: Kevin
    («me mandaron a buscar leche al pasillo 4 y estaba en otro rack») y Nahuel
    («corrí las cajas del pasillo 4 para hacer lugar»). La diferencia ya estaba
    explicada y nadie los había juntado — el que la mira iba a mandar a
    recontar, o peor, a ajustar el stock por un faltante que no existe.

    La nota NO decide nada: es contexto para el que decide. Por eso viaja con
    la diferencia y no la borra de la lista.
    """
    from . import notas as notas_equipo
    from .fechas import hoy
    import datetime
    disc = discrepancias() if disc is None else disc
    if not disc:
        return []
    desde = (hoy() - datetime.timedelta(days=dias)).isoformat()
    out = []
    for d in disc:
        ubis = _ubicaciones_de(d.get("codigo"))
        notas = []
        vistas = set()
        for u in ubis:
            for n in notas_equipo.por_ubicacion(u, desde=desde):
                if n["id"] in vistas:
                    continue
                vistas.add(n["id"])
                notas.append({"id": n["id"], "autor": n.get("autor"),
                              "fecha": n.get("fecha"), "canal": n.get("canal"),
                              "ubicacion": n.get("ubicacion"), "texto": n.get("texto"),
                              "texto_en": n.get("texto_en")})
        out.append({**d, "ubicaciones": ubis,
                    "notas": sorted(notas, key=lambda x: x["fecha"] or "")})
    return out


def aging(as_of=None) -> list[dict]:
    """Units and inmovilizado by age of in_date vs fechas.hoy() (or as_of).
    Rows without a parseable in_date are omitted, never invented."""
    as_of = as_of or hoy()
    buckets = {
        "0_90": {"bucket": "0_90", "units": 0.0, "inmovilizado": 0.0},
        "91_180": {"bucket": "91_180", "units": 0.0, "inmovilizado": 0.0},
        "181_365": {"bucket": "181_365", "units": 0.0, "inmovilizado": 0.0},
        "365_plus": {"bucket": "365_plus", "units": 0.0, "inmovilizado": 0.0},
    }
    catalogo = {d.get("codigo"): d for d in store.raw_actual()}
    for f in _filas():
        d = parse_fecha(f.get("in_date"))
        if not d:
            continue
        days = (as_of - d).days
        if days < 0:
            continue
        if days <= 90:
            key = "0_90"
        elif days <= 180:
            key = "91_180"
        elif days <= 365:
            key = "181_365"
        else:
            key = "365_plus"
        qty = float(f.get("cantidad") or 0)
        art = catalogo.get(f.get("codigo")) or {}
        costo = float(art.get("costo_iva") or 0)
        buckets[key]["units"] += qty
        buckets[key]["inmovilizado"] += qty * costo
    return [
        {**b, "units": round(b["units"], 2), "inmovilizado": round(b["inmovilizado"], 2)}
        for b in buckets.values()
    ]


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
        "aging": aging(),
    }
