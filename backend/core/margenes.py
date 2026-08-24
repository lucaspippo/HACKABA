"""
margenes.py — cuánto ganás por grupo, que es LO que el dueño pregunta.

Un dueño de distribuidora no decide por facturación: decide por margen, y el
margen es distinto en cada familia. Congelados no es almacén, y una horma de
fiambre feteada no es la misma horma vendida entera. Sin margen por grupo, "qué
productos me conviene tener" es una opinión.

Dos definiciones, ambas a la vista, porque el rubro habla las dos:
  · margen sobre la VENTA  = (precio − costo) / precio   ← el del P&L
  · recargo sobre el COSTO = (precio − costo) / costo    ← "le pongo un 45%"

Cómo se calcula (declarado, no escondido):
  · MAYORISTA: precios y costos de HOY, ponderados por las unidades realmente
    vendidas en 12 meses. Es margen de lista a precios de hoy — el mismo
    criterio que ya usa el KPI de margen teórico (core/analisis.kpis), no un
    margen realizado sobre precios históricos, que la inflación ensuciaría.
  · MOSTRADOR: la venta de mostrador (los cierres de caja reales, proyectados a
    12 meses) repartida por el mix de cada grupo, con el recargo del rubro.

Nada se inventa: si no hay ventas cargadas o validadas, `disponible=False` con
el motivo, igual que el resto de los análisis.
"""
from __future__ import annotations

from . import analisis, mostrador, store

# Un grupo con menos de esto no tiene promedio defendible: se muestra, pero no
# se lo usa para acusar a un producto de estar "abajo de su grupo".
MIN_PRODUCTOS_GRUPO = 5
# Cuántos puntos por debajo del promedio de su grupo hacen ruido de verdad.
UMBRAL_BAJO_PP = 6.0


def _t(key, lang=None, **p):
    import i18n
    return i18n.t(key, lang, **p)


def _pct(numerador: float, denominador: float) -> float | None:
    return round(numerador / denominador * 100, 1) if denominador else None


def _fila(ventas: float, costo: float) -> dict:
    ganancia = ventas - costo
    return {
        "ventas_12m": round(ventas, 2),
        "costo_12m": round(costo, 2),
        "ganancia_12m": round(ganancia, 2),
        "margen_pct": _pct(ganancia, ventas),
        "recargo_pct": _pct(ganancia, costo),
    }


# --- mayorista ------------------------------------------------------------------

def _por_producto() -> list[dict]:
    """Cada artículo activo con precio y costo, con lo que realmente vendió."""
    import i18n  # noqa: F401 — sólo para dejar claro que el label sale de i18n
    unidades = analisis._unidades_por_codigo(365)
    out = []
    for a in store.raw_actual():
        if a.get("estado") != "activo":
            continue
        pvp, costo = a.get("pvp"), a.get("costo_iva")
        if not pvp or not costo:
            continue
        u = unidades.get(a.get("codigo"), 0.0)
        out.append({
            "codigo": a.get("codigo"),
            "producto": a.get("descripcion"),
            "categoria": a.get("tipo") or "?",
            "unidades_12m": round(u, 1),
            "pvp": pvp, "costo_iva": costo,
            "por_peso": bool(a.get("venta_x_peso")),
            **_fila(u * pvp, u * costo),
            # el margen unitario NO depende del volumen: es el del producto
            "margen_unitario_pct": _pct(pvp - costo, pvp),
            "recargo_unitario_pct": _pct(pvp - costo, costo),
        })
    return out


def mayorista(lang: str | None = None) -> dict:
    guard = analisis._no_disponible(lang)
    if guard:
        return guard
    import i18n
    productos = _por_producto()
    por_cat: dict[str, list] = {}
    for p in productos:
        por_cat.setdefault(p["categoria"], []).append(p)

    grupos = []
    for cat, items in por_cat.items():
        vendidos = [p for p in items if p["unidades_12m"] > 0]
        ventas = sum(p["ventas_12m"] for p in vendidos)
        costo = sum(p["costo_12m"] for p in vendidos)
        if ventas <= 0:
            continue
        # promedio SIMPLE del margen unitario: es el que sirve para decir "este
        # producto está por debajo de su grupo" (el ponderado lo domina el líder)
        unit = [p["margen_unitario_pct"] for p in items if p["margen_unitario_pct"] is not None]
        grupos.append({
            "id": cat,
            "label": i18n.categoria(cat, lang),
            "productos": len(items),
            "unidades_12m": round(sum(p["unidades_12m"] for p in vendidos), 1),
            "margen_unitario_promedio_pct": round(sum(unit) / len(unit), 1) if unit else None,
            **_fila(ventas, costo),
        })
    grupos.sort(key=lambda g: -(g["margen_pct"] or 0))
    ventas_t = sum(g["ventas_12m"] for g in grupos)
    costo_t = sum(g["costo_12m"] for g in grupos)
    return {"disponible": True, "grupos": grupos, "total": _fila(ventas_t, costo_t)}


def detalle(grupo: str, lang: str | None = None, limit: int = 40) -> dict:
    """Los productos de un grupo, del que menos margen deja al que más. Marca
    los que están claramente por debajo del promedio de SU grupo."""
    guard = analisis._no_disponible(lang)
    if guard:
        return guard
    import i18n
    items = [p for p in _por_producto() if p["categoria"] == grupo]
    if not items:
        return {"disponible": True, "grupo": grupo, "items": [], "promedio_pct": None}
    unit = [p["margen_unitario_pct"] for p in items if p["margen_unitario_pct"] is not None]
    promedio = round(sum(unit) / len(unit), 1) if unit else None
    defendible = len(items) >= MIN_PRODUCTOS_GRUPO and promedio is not None
    for p in items:
        m = p["margen_unitario_pct"]
        p["diferencia_pp"] = round(m - promedio, 1) if (m is not None and promedio is not None) else None
        p["bajo_su_grupo"] = bool(defendible and m is not None and m < promedio - UMBRAL_BAJO_PP)
    items.sort(key=lambda p: (p["margen_unitario_pct"] if p["margen_unitario_pct"] is not None else 999))
    return {
        "disponible": True, "grupo": grupo, "label": i18n.categoria(grupo, lang),
        "promedio_pct": promedio, "promedio_defendible": defendible,
        "items": items[:limit], "total_items": len(items),
    }


# --- mostrador (locales propios) ------------------------------------------------

def minorista(lang: str | None = None) -> dict:
    """El canal de las bocas propias. La plata sale de los cierres de caja
    reales; el recargo, del rubro (feteado ~80%, pieza entera ~30%)."""
    if not mostrador.hay_datos():
        return {"disponible": False}
    import i18n
    total_12m = mostrador.venta_12m()
    grupos = []
    for g in mostrador.grupos():
        ventas = total_12m * float(g.get("share_venta") or 0)
        recargo = float(g.get("recargo_sobre_costo_pct") or 0) / 100
        costo = ventas / (1 + recargo) if recargo else ventas
        cats = g.get("categorias") or []
        label = i18n.t(f"core.margen.grupo_{g['id']}", lang)
        grupos.append({
            "id": g["id"], "label": label,
            "categorias": cats,
            "presentacion": g.get("presentacion"),
            "recargo_pct_rubro": g.get("recargo_sobre_costo_pct"),
            **_fila(ventas, costo),
        })
    grupos.sort(key=lambda g: -(g["margen_pct"] or 0))
    ventas_t = sum(g["ventas_12m"] for g in grupos)
    costo_t = sum(g["costo_12m"] for g in grupos)
    return {"disponible": True, "locales": mostrador.locales(),
            "venta_diaria": mostrador.venta_diaria(),
            "grupos": grupos, "total": _fila(ventas_t, costo_t)}


def completo(lang: str | None = None) -> dict:
    may = mayorista(lang)
    out = {"mayorista": may, "minorista": minorista(lang),
           "disponible": bool(may.get("disponible"))}
    if not may.get("disponible"):
        out["motivo"] = may.get("motivo")
    return out
