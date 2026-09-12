"""
mostrador.py — el OTRO canal: los locales propios.

Una distribuidora de alimentos no vende de una sola manera. Por un lado el
mayorista: ~430 SKUs a precio de lista, márgenes de distribución (15-21%). Por
el otro el mostrador de sus bocas propias, donde los márgenes son otro planeta
— una horma de fiambre feteada deja ~80% sobre el costo, la misma horma vendida
entera ~30%. Mezclar los dos canales en un solo "margen" no responde la
pregunta que el dueño hace de verdad, que es por GRUPO y por canal.

Lo que hay acá:
  · `grupos()`     — los grupos de mostrador con su recargo (dato del rubro).
  · `cierres()`    — el cierre diario de CADA local (Bloque E). La plata no se
                     inventa: es la misma caja diaria, abierta por boca.
  · `comparativo()`— el reporte que hoy una empleada arma a mano en un Excel.

Si el tenant no tiene canal minorista (el piloto), todo devuelve vacío y las
pantallas que dependen de esto sencillamente no aparecen.
"""
from __future__ import annotations

import datetime
import json
import os

from . import fechas, paths

MOSTRADOR_JSON = os.path.join(paths.DATA_DIR, "mostrador.json")

# Los cierres cubren ~2 meses. Para llevarlos a 12 meses se proyecta el ritmo
# sobre los días hábiles del año (365 − 52 domingos): el supuesto se declara
# en toda pantalla que use el número.
DIAS_HABILES_ANIO = 313


def _seed_inicial() -> dict:
    if not os.path.exists(MOSTRADOR_JSON):
        return {}
    try:
        with open(MOSTRADOR_JSON, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:  # noqa: BLE001
        return {}


def _load() -> dict:
    from core.db import blob_repo
    from core.db import tenant as _tenant
    tid = _tenant.current_tenant_id()
    data = blob_repo.get_blob("retail_counter_data", tid)
    if data is None:
        data = _seed_inicial()
        blob_repo.save_blob("retail_counter_data", tid, data)
    return data


def hay_datos() -> bool:
    return bool(_load().get("cierres"))


def locales() -> list[str]:
    return list(_load().get("locales") or [])


def grupos() -> list[dict]:
    return list(_load().get("grupos") or [])


def cierres() -> list[dict]:
    return list(_load().get("cierres") or [])


def venta_diaria() -> float:
    return float(_load().get("venta_diaria_promedio") or 0.0)


def venta_12m() -> float:
    """Proyección a 12 meses del ritmo real de los cierres cargados."""
    return round(venta_diaria() * DIAS_HABILES_ANIO, 2)


def grupo_de_categoria(categoria: str) -> list[dict]:
    """Los grupos de mostrador que se alimentan de una categoría del catálogo.
    Fiambrería devuelve DOS (feteado y pieza entera): es el mismo producto
    vendido de dos maneras, y ahí está la diferencia de margen más grande."""
    return [g for g in grupos() if categoria in (g.get("categorias") or [])]


# --- El costo viejo, donde alguien puede hacer algo -----------------------------
#
# `quality.py` ya marca los costos de más de un año: es una de las categorías
# del libro triado del dueño. El descubrimiento del relevamiento es DÓNDE sirve
# ese dato — el jamón cocido de balanza tiene el costo cargado hace 535 días y
# su precio de venta salió de ahí, y quien mira ese precio todos los días es la
# que está en el mostrador, no el dueño en un análisis de escritorio.
#
# El cruce que lo vuelve suyo es el GRUPO: sólo se listan los artículos cuya
# categoría alimenta un grupo de mostrador. El resto del catálogo no es de ella
# y llenarle la pantalla con 430 SKUs es la forma más rápida de que no mire
# ninguno.

def costos_viejos(lang: str | None = None) -> dict:
    """Los productos del mostrador cuyo precio salió de un costo viejo.

    El umbral es el de `quality.UMBRAL_COSTO_VIEJO_DIAS` — el mismo que ya usa
    el libro del dueño. Dos pantallas que cuenten "costo viejo" con umbrales
    distintos son dos verdades, y ya sabemos cómo termina eso.

    NO HAY TOTAL, y es a propósito (PRODUCT.md, The Counting Rule). Sumar el
    inmovilizado de estos cinco artículos daría un número que parece plata en
    juego y no lo es: el costo viejo no dice cuánto se pierde, dice que no se
    sabe cuánto se gana. Cada fila responde por sí sola.
    """
    from . import quality, store
    filas = []
    for a in store.raw_actual():
        if a.get("estado") != "activo":
            continue
        dias = a.get("antiguedad_costo_dias") or 0
        if dias <= quality.UMBRAL_COSTO_VIEJO_DIAS:
            continue
        gs = grupo_de_categoria(a.get("tipo") or "")
        if not gs:
            continue        # no se vende en el mostrador: no es de ella
        costo = a.get("costo_neto") or 0.0
        pvp = a.get("pvp") or 0.0
        filas.append({
            "codigo": a.get("codigo"),
            "producto": a.get("descripcion"),
            "categoria": a.get("tipo"),
            "dias": int(dias),
            "pvp": pvp,
            "costo_neto": costo,
            "venta_x_peso": bool(a.get("venta_x_peso")),
            # El recargo que REALMENTE tiene hoy sobre ese costo viejo, y el
            # que la casa espera para este grupo. La fiambrería devuelve dos
            # grupos (feteado y pieza entera) porque es el mismo producto
            # vendido de dos maneras: se muestran los dos en vez de elegir uno,
            # que sería inventar cuál de las dos presentaciones es ésta.
            "recargo_actual_pct": (round((pvp / costo - 1) * 100, 1)
                                   if costo > 0 and pvp > 0 else None),
            "grupos": [{"id": g.get("id"),
                        "presentacion": g.get("presentacion"),
                        "recargo_esperado_pct": g.get("recargo_sobre_costo_pct")}
                       for g in gs],
        })
    filas.sort(key=lambda f: f["dias"], reverse=True)
    return {"disponible": bool(filas), "umbral_dias": quality.UMBRAL_COSTO_VIEJO_DIAS,
            "items": filas}


# --- Bloque E · el reporte de cierres que hoy se hace a mano --------------------

def _semana(desde: datetime.date, hasta: datetime.date) -> dict[str, float]:
    por_local: dict[str, float] = {}
    for c in cierres():
        f = fechas.parse_fecha(c.get("fecha"))
        if not f or not (desde <= f <= hasta):
            continue
        por_local[c["local"]] = por_local.get(c["local"], 0.0) + float(c.get("total") or 0)
    return por_local


def comparativo(dias: int = 7) -> dict:
    """El reporte que el dueño pide cada 4-5 días: cuánto hizo cada local en la
    ventana, contra la ventana anterior del mismo largo. Hoy alguien lo imputa
    a mano en un Excel; acá sale de los cierres que ya existen."""
    if not hay_datos():
        return {"disponible": False}
    dias = max(1, min(int(dias or 7), 60))
    ultimo = max((fechas.parse_fecha(c["fecha"]) for c in cierres()
                  if fechas.parse_fecha(c["fecha"])), default=None)
    if not ultimo:
        return {"disponible": False}
    hasta = min(ultimo, fechas.hoy())
    desde = hasta - datetime.timedelta(days=dias - 1)
    prev_hasta = desde - datetime.timedelta(days=1)
    prev_desde = prev_hasta - datetime.timedelta(days=dias - 1)

    actual, previo = _semana(desde, hasta), _semana(prev_desde, prev_hasta)
    filas = []
    for local in locales():
        a, p = actual.get(local, 0.0), previo.get(local, 0.0)
        filas.append({
            "local": local,
            "total": round(a, 2),
            "total_previo": round(p, 2),
            "variacion_pct": round((a / p - 1) * 100, 1) if p > 0 else None,
        })
    filas.sort(key=lambda f: -f["total"])
    total = sum(f["total"] for f in filas)
    total_prev = sum(f["total_previo"] for f in filas)
    con_var = [f for f in filas if f["variacion_pct"] is not None]
    return {
        "disponible": True,
        "dias": dias,
        "desde": desde.isoformat(), "hasta": hasta.isoformat(),
        "desde_previo": prev_desde.isoformat(), "hasta_previo": prev_hasta.isoformat(),
        "locales": filas,
        "total": round(total, 2),
        "total_previo": round(total_prev, 2),
        "variacion_pct": round((total / total_prev - 1) * 100, 1) if total_prev > 0 else None,
        "mejor": max(con_var, key=lambda f: f["variacion_pct"]) if con_var else None,
        "peor": min(con_var, key=lambda f: f["variacion_pct"]) if con_var else None,
    }
