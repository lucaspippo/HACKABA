"""Stock visualizations — every figure is a cut of an existing core derivation.

Hoy already states idle money, ranks actions, and maps capital by category.
These payloads answer other questions (excess vs necessary, cover vs lead,
rotation vs capital, expiry weeks, seasonality vs cover, GMROI, aging,
promised vs real lead, SKU burn). Ángela narrates; she does not compute.
"""
from __future__ import annotations

import datetime
import statistics

from . import analisis, fechas, lotes, margenes, reposicion, rotacion, stock, store
from . import vencimientos as venc_mod
from .fechas import parse_fecha


def _t(key, lang=None, **p):
    import i18n
    return i18n.t(key, lang, **p)


def _guard(lang=None):
    return analisis._no_disponible(lang)


# --- excess vs necessary by aisle ------------------------------------------------

def excess_by_category(lang: str | None = None) -> dict:
    """Same split as rotacion.analizar(), rolled up by tipo."""
    guard = _guard(lang)
    if guard:
        return guard
    unidades = analisis._unidades_por_codigo(365)
    por: dict[str, dict] = {}
    for a in store.raw_actual():
        if a.get("estado") != "activo":
            continue
        inmov = float(a.get("inmovilizado") or 0)
        if inmov <= 0:
            continue
        m = rotacion.metricas_articulo(
            a.get("stock") or 0, a.get("costo_iva") or 0,
            unidades.get(a.get("codigo"), 0), 365,
        )
        cat = a.get("tipo") or "?"
        g = por.setdefault(cat, {"necesario": 0.0, "excedente": 0.0})
        g["excedente"] += m["plata_excedente"]
        g["necesario"] += max(0.0, inmov - m["plata_excedente"])
    cats = sorted(
        ({"x": k, "necesario": round(v["necesario"], 2),
          "excedente": round(v["excedente"], 2)} for k, v in por.items()),
        key=lambda r: -(r["necesario"] + r["excedente"]),
    )[:8]
    return {
        "disponible": True,
        "categorias": cats,
        "total_necesario": round(sum(c["necesario"] for c in cats), 2),
        "total_excedente": round(sum(c["excedente"] for c in cats), 2),
    }


# --- rotation × capital ---------------------------------------------------------

def rotation_scatter(lang: str | None = None) -> dict:
    rot = analisis.rotacion(lang)
    if not rot.get("disponible"):
        return rot
    puntos = [{
        "codigo": x["codigo"],
        "producto": x["producto"],
        "categoria": x.get("categoria"),
        "dias": x["dias_rotacion"] if x["dias_rotacion"] is not None else 180,
        "sin_venta": x["dias_rotacion"] is None,
        "inmovilizado": x["inmovilizado"],
        "estado": x["estado"],
    } for x in rot.get("detalle") or []]
    return {
        "disponible": True,
        "cortes": {"sano": 35, "atencion": 60},
        "por_estado": rot["por_estado"],
        "puntos": puntos[:150],
    }


# --- expiry horizon -------------------------------------------------------------

def expiry_horizon(lang: str | None = None, dias: int = 56) -> dict:
    r = venc_mod.en_riesgo(dias, lang)
    if not r.get("disponible"):
        return r
    n_weeks = max(1, (dias + 6) // 7)
    weeks = [{"semana": i, "monto": 0.0, "lotes": 0} for i in range(n_weeks)]
    for it in r.get("items") or []:
        w = min(n_weeks - 1, max(0, int(it.get("dias_restantes") or 0) // 7))
        weeks[w]["monto"] = round(weeks[w]["monto"] + (it.get("plata_en_riesgo") or 0), 2)
        weeks[w]["lotes"] += 1
    return {
        "disponible": True,
        "total_en_riesgo": r.get("total_en_riesgo") or 0,
        "lotes_en_riesgo": r.get("lotes_en_riesgo") or 0,
        "weeks": weeks,
    }


# --- seasonality vs cover -------------------------------------------------------

def seasonality_cover(lang: str | None = None) -> dict:
    est = analisis.estacionalidad(lang)
    if not est.get("disponible"):
        return est
    unidades = analisis._unidades_por_codigo(365)
    cover_by_cat: dict[str, list] = {}
    for a in store.raw_actual():
        if a.get("estado") != "activo":
            continue
        u = unidades.get(a.get("codigo"), 0.0)
        if u <= 0:
            continue
        cat = a.get("tipo") or "?"
        cover_by_cat.setdefault(cat, []).append(
            stock.days_of_cover(a, u / 365.0))
    featured = None
    picos = est.get("proximos_picos") or []
    if picos:
        featured = picos[0].get("categoria")
    if not featured:
        cats = est.get("categorias") or {}
        if cats:
            featured = max(cats, key=lambda c: cats[c].get("idx_max") or 0)
    cat_data = (est.get("categorias") or {}).get(featured) or {}
    indice = cat_data.get("indice") or {}
    meses = [round(float(indice.get(m, 1.0)), 2) for m in range(1, 13)]
    covers = cover_by_cat.get(featured) or []
    cover_dias = round(statistics.median(covers), 1) if covers else None
    typical = 30.44
    cover_ratio = round(cover_dias / typical, 2) if cover_dias is not None else None
    return {
        "disponible": True,
        "featured": featured,
        "indice": meses,
        "cover_dias": cover_dias,
        "cover_ratio": cover_ratio,
        "proximos_picos": picos[:4],
        "anios_analizados": est.get("anios_analizados") or 0,
    }


# --- GMROI ----------------------------------------------------------------------

def gmroi(lang: str | None = None) -> dict:
    may = margenes.mayorista(lang)
    if not may.get("disponible"):
        return may
    inmov: dict[str, float] = {}
    for a in store.raw_actual():
        if a.get("estado") != "activo":
            continue
        cat = a.get("tipo") or "?"
        inmov[cat] = inmov.get(cat, 0.0) + float(a.get("inmovilizado") or 0)
    grupos = []
    for g in may.get("grupos") or []:
        inv = inmov.get(g["id"], 0.0)
        gan = float(g.get("ganancia_12m") or 0)
        ratio = round(gan / inv, 2) if inv > 0 else None
        grupos.append({
            "id": g["id"],
            "label": g["label"],
            "ganancia_12m": round(gan, 2),
            "inmovilizado": round(inv, 2),
            "gmroi": ratio,
            "margen_pct": g.get("margen_pct"),
        })
    grupos = [g for g in grupos if g["gmroi"] is not None]
    grupos.sort(key=lambda g: -(g["gmroi"] or 0))
    return {"disponible": True, "grupos": grupos[:8]}


# --- aging (days on the floor) --------------------------------------------------

_AGE_BUCKETS = (
    ("0_30", 0, 30),
    ("31_90", 31, 90),
    ("91_180", 91, 180),
    ("181_365", 181, 365),
    ("365_plus", 366, 10_000),
)


def aging(lang: str | None = None) -> dict:
    h = fechas.hoy()
    arts = {a.get("codigo"): a for a in store.raw_actual()}
    buckets = {k: {"id": k, "monto": 0.0, "lotes": 0} for k, *_ in _AGE_BUCKETS}
    con_fecha, sin_fecha = 0, 0
    for f in lotes.listar():
        d = parse_fecha(f.get("in_date"))
        a = arts.get(f.get("codigo"))
        costo = float((a or {}).get("costo_iva") or 0)
        cant = float(f.get("cantidad") or 0)
        if cant <= 0:
            continue
        if not d:
            sin_fecha += 1
            continue
        con_fecha += 1
        age = (h - d).days
        for key, lo, hi in _AGE_BUCKETS:
            if lo <= age <= hi:
                buckets[key]["monto"] = round(buckets[key]["monto"] + cant * costo, 2)
                buckets[key]["lotes"] += 1
                break
    total = con_fecha + sin_fecha
    if con_fecha == 0:
        return {
            "disponible": False,
            "motivo": _t("core.stock_viz.aging_sin_fecha", lang),
        }
    return {
        "disponible": True,
        "buckets": [buckets[k] for k, *_ in _AGE_BUCKETS],
        "con_fecha": con_fecha,
        "sin_fecha": sin_fecha,
        "cubierto_pct": round(100 * con_fecha / total, 1) if total else 0,
    }


# --- promised vs real lead ------------------------------------------------------

def lead_truth(lang: str | None = None) -> dict:
    from core.db import purchase_orders_repo
    from core.db import tenant as _tenant
    from . import esquema

    try:
        tid = _tenant.current_tenant_id()
        orders = {o["numero"]: o for o in purchase_orders_repo.list_orders(tid)}
    except Exception:  # noqa: BLE001 — no PO table / no tenant: honest lock
        return {"disponible": False, "motivo": _t("core.stock_viz.lead_sin_ordenes", lang)}
    if not orders:
        return {"disponible": False, "motivo": _t("core.stock_viz.lead_sin_ordenes", lang)}
    por: dict[str, list] = {}
    for f in esquema.filas("recepciones"):
        num = f.get("po_number") or ""
        po = orders.get(num)
        if not po:
            continue
        rec = parse_fecha(f.get("fecha"))
        ped = parse_fecha(po.get("fecha"))
        if not rec or not ped:
            continue
        delay = (rec - ped).days
        if delay < 0 or delay > 180:
            continue
        prov = (f.get("proveedor") or po.get("proveedor") or "").strip()
        if not prov:
            continue
        por.setdefault(prov, []).append(delay)
    if not por:
        return {"disponible": False, "motivo": _t("core.stock_viz.lead_sin_pares", lang)}
    proveedores = []
    for prov, delays in por.items():
        assumed, propio = reposicion.dias_reposicion(prov)
        proveedores.append({
            "proveedor": prov,
            "assumed": assumed,
            "lead_propio": propio,
            "actual_median": round(statistics.median(delays), 1),
            "n": len(delays),
        })
    proveedores.sort(key=lambda g: -(g["actual_median"] - g["assumed"]))
    return {"disponible": True, "proveedores": proveedores[:8]}


# --- 60-day burn for one SKU ----------------------------------------------------

def product_burn(codigo, lang: str | None = None) -> dict:
    try:
        codigo = int(codigo)
    except (TypeError, ValueError):
        return {"disponible": False, "motivo": _t("core.stock_viz.burn_sin_sku", lang)}
    art = next((a for a in store.raw_actual() if a.get("codigo") == codigo), None)
    if not art:
        return {"disponible": False, "motivo": _t("core.stock_viz.burn_sin_sku", lang)}
    unidades = analisis._unidades_por_codigo(365)
    u = unidades.get(codigo, 0.0)
    if u <= 0:
        return {"disponible": False, "motivo": _t("core.stock_viz.burn_sin_ritmo", lang)}
    ritmo = u / 365.0
    sellable = max(0.0, stock.on_hand(art) - float(art.get("outgoing_qty") or 0))
    incoming = float(art.get("incoming_qty") or 0)
    lead, _propio = reposicion.dias_reposicion(art.get("proveedor"))
    steps = list(range(0, 61, 7))
    sin_camion, con_camion = [], []
    stockout_day = None
    for d in steps:
        consumed = ritmo * d
        base = max(0.0, sellable - consumed)
        sin_camion.append(round(base, 1))
        landed = incoming if d >= lead else 0.0
        con_camion.append(round(base + landed, 1))
        if stockout_day is None and base <= 0:
            stockout_day = d
    return {
        "disponible": True,
        "codigo": codigo,
        "producto": art.get("descripcion"),
        "dias": steps,
        "sin_camion": sin_camion,
        "con_camion": con_camion,
        "incoming_qty": incoming,
        "lead_dias": lead,
        "stockout_day": stockout_day,
        "ritmo_diario": round(ritmo, 3),
    }


def pack(lang: str | None = None) -> dict:
    """One round-trip for the Inventario screens (not the SKU burn)."""
    return {
        "excess_by_category": excess_by_category(lang),
        "rotation": rotation_scatter(lang),
        "expiry_horizon": expiry_horizon(lang),
        "seasonality": seasonality_cover(lang),
        "gmroi": gmroi(lang),
        "aging": aging(lang),
        "lead_truth": lead_truth(lang),
    }
