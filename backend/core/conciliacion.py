"""Warehouse count reconciliation — hypothesis cascade over lot gaps.

Every number is computed here. Ángela narrates; she never invents a figure.
First matching rule wins. Tiny tara gaps are folded out of the open list.
"""
from __future__ import annotations

from . import conocimiento, esquema, lotes, store
from .fechas import hoy, parse_fecha
from i18n import t

QTY_EPS = 0.01
DEFAULT_TARA_PCT = 0.5
SEARCHED = ["sales", "receipts", "pipeline", "expiry", "sibling_counts"]


def _qty(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _qty_eq(a, b) -> bool:
    a, b = _qty(a), _qty(b)
    if a is None or b is None:
        return False
    return abs(a - b) <= QTY_EPS


def _close(a, b) -> bool:
    """Near but not exact. Close-but-not-exact is never `high`."""
    a, b = _qty(a), _qty(b)
    if a is None or b is None or _qty_eq(a, b):
        return False
    denom = max(abs(a), abs(b), 1.0)
    return abs(a - b) <= max(2.0, 0.2 * denom)


def _codigo(row: dict) -> int | None:
    c = row.get("codigo")
    if c is None or c == "":
        return None
    try:
        return int(c)
    except (TypeError, ValueError):
        return None


def _counted_present(row: dict) -> bool:
    return row.get("counted_qty") is not None and row.get("counted_qty") != ""


def _hip(clase: str, confianza: str, acciones: list[str], evidencia: dict,
         params: dict | None = None, lang: str | None = None) -> dict:
    params = params or {}
    return {
        "clase": clase,
        "confianza": confianza,
        "acciones": acciones,
        "evidencia": evidencia,
        "params": params,
        "lk": f"conc.hip.{clase}",
        "texto": t(f"conc.hip.{clase}", lang, **params),
    }


def _umbral_tara(art: dict | None) -> tuple[float, str]:
    """Aldo's scale-drift rule (balanza) is high; the 0.5% default is medium."""
    reglas = [p for p in conocimiento.aplicables(nodo="deposito", efecto="suprime_alerta")
              if (p.get("params") or {}).get("umbral_pct") is not None]
    tipo = str((art or {}).get("tipo") or "").lower()
    es_balanza = "balanza" in tipo or bool((art or {}).get("venta_x_peso"))
    if reglas and es_balanza:
        return float(reglas[0]["params"]["umbral_pct"]), "high"
    return DEFAULT_TARA_PCT, "medium"


def _same_sku(rows: list[dict], codigo: int | None) -> list[dict]:
    if codigo is None:
        return []
    return [r for r in rows if _codigo(r) == codigo]


def _clasificar(lot: dict, *, lots: list[dict], catalog: dict, ventas: list[dict],
                recepciones: list[dict], lang: str | None) -> dict | None:
    if not _counted_present(lot):
        return None
    cantidad = _qty(lot.get("cantidad")) or 0.0
    counted = _qty(lot.get("counted_qty"))
    if counted is None:
        return None
    diff = round(counted - cantidad, 2)
    if abs(diff) <= QTY_EPS:
        return None

    codigo = _codigo(lot)
    art = catalog.get(codigo) if codigo is not None else None
    costo = _qty((art or {}).get("costo_iva"))
    impacto = round(abs(diff) * costo, 2) if costo is not None else None
    shortage = -diff if diff < 0 else None
    surplus = diff if diff > 0 else None
    sku_lots = _same_sku(lots, codigo)
    sku_sales = [s for s in ventas if _codigo(s) == codigo]
    sku_receipts = [r for r in recepciones if _codigo(r) == codigo]

    def pack(hip: dict) -> dict:
        return {
            "id": lot.get("id"),
            "codigo": codigo,
            "producto": lot.get("producto") or (art or {}).get("descripcion"),
            "ubicacion": lot.get("ubicacion"),
            "lote": lot.get("lote"),
            "vencimiento": lot.get("vencimiento"),
            "cantidad": cantidad,
            "counted_qty": counted,
            "diferencia": diff,
            "impacto": impacto,
            "hipotesis": hip,
        }

    uncounted = [s for s in sku_lots
                 if s.get("id") != lot.get("id") and not _counted_present(s)]
    if uncounted:
        return pack(_hip(
            "conteo_incompleto", "unverified", ["preguntar_angela"],
            {"uncounted_lots": [{"id": s.get("id"), "lote": s.get("lote"),
                                 "ubicacion": s.get("ubicacion"),
                                 "cantidad": s.get("cantidad")} for s in uncounted],
             "buscado_en": ["sibling_counts"]},
            {"n": len(uncounted), "producto": lot.get("producto") or ""},
            lang,
        ))

    umbral, tara_band = _umbral_tara(art)
    pct = abs(diff) / cantidad * 100 if cantidad else None
    if pct is not None and pct < umbral:
        return pack(_hip(
            "tara", tara_band, [],
            {"umbral_pct": umbral, "diferencia_pct": round(pct, 2),
             "buscado_en": ["tara"]},
            {"pct": round(pct, 2), "umbral": umbral},
            lang,
        ))

    if shortage is not None and sku_sales:
        exact = [s for s in sku_sales if _qty_eq(s.get("cantidad"), shortage)]
        if len(exact) == 1:
            s = exact[0]
            return pack(_hip(
                "venta_sin_bajar_stock", "high", ["aceptar_conteo"],
                {"venta": {"id": s.get("id"), "fecha": s.get("fecha"),
                           "cantidad": s.get("cantidad"), "producto": s.get("producto")},
                 "buscado_en": ["sales"]},
                {"qty": s.get("cantidad"), "fecha": s.get("fecha") or "",
                 "producto": s.get("producto") or ""},
                lang,
            ))
        total = sum(_qty(s.get("cantidad")) or 0 for s in sku_sales)
        close_one = next((s for s in sku_sales if _close(s.get("cantidad"), shortage)), None)
        if _qty_eq(total, shortage) or _close(total, shortage) or close_one or len(exact) > 1:
            s = exact[0] if exact else (close_one or sku_sales[0])
            return pack(_hip(
                "venta_sin_bajar_stock", "medium", ["aceptar_conteo"],
                {"venta": {"id": s.get("id"), "fecha": s.get("fecha"),
                           "cantidad": s.get("cantidad"), "producto": s.get("producto")},
                 "suma": round(total, 2),
                 "buscado_en": ["sales"]},
                {"qty": s.get("cantidad"), "fecha": s.get("fecha") or "",
                 "producto": s.get("producto") or ""},
                lang,
            ))

    if surplus is not None and sku_receipts:
        exact = [r for r in sku_receipts if _qty_eq(r.get("cantidad"), surplus)]
        if len(exact) == 1:
            r = exact[0]
            return pack(_hip(
                "recepcion_sin_cargar", "high", ["preguntar_angela"],
                {"recepcion": {"id": r.get("id"), "fecha": r.get("fecha"),
                               "cantidad": r.get("cantidad"), "producto": r.get("producto")},
                 "buscado_en": ["receipts"]},
                {"qty": r.get("cantidad"), "fecha": r.get("fecha") or "",
                 "producto": r.get("producto") or ""},
                lang,
            ))
        total = sum(_qty(r.get("cantidad")) or 0 for r in sku_receipts)
        close_one = next((r for r in sku_receipts if _close(r.get("cantidad"), surplus)), None)
        if _qty_eq(total, surplus) or _close(total, surplus) or close_one or len(exact) > 1:
            r = exact[0] if exact else (close_one or sku_receipts[0])
            return pack(_hip(
                "recepcion_sin_cargar", "medium", ["preguntar_angela"],
                {"recepcion": {"id": r.get("id"), "fecha": r.get("fecha"),
                               "cantidad": r.get("cantidad"), "producto": r.get("producto")},
                 "suma": round(total, 2),
                 "buscado_en": ["receipts"]},
                {"qty": r.get("cantidad"), "fecha": r.get("fecha") or "",
                 "producto": r.get("producto") or ""},
                lang,
            ))

    incoming = _qty((art or {}).get("incoming_qty")) or 0
    outgoing = _qty((art or {}).get("outgoing_qty")) or 0
    if surplus is not None and incoming and _qty_eq(incoming, surplus):
        return pack(_hip(
            "en_transito", "high", ["preguntar_angela"],
            {"incoming_qty": incoming, "buscado_en": ["pipeline"]},
            {"qty": incoming, "lado": t("conc.pipeline_in", lang)},
            lang,
        ))
    if shortage is not None and outgoing and _qty_eq(outgoing, shortage):
        return pack(_hip(
            "en_transito", "high", ["preguntar_angela"],
            {"outgoing_qty": outgoing, "buscado_en": ["pipeline"]},
            {"qty": outgoing, "lado": t("conc.pipeline_out", lang)},
            lang,
        ))

    if counted and cantidad and (
            _qty_eq(counted * 10, cantidad) or _qty_eq(counted / 10, cantidad)
            or _qty_eq(cantidad * 10, counted) or _qty_eq(cantidad / 10, counted)):
        return pack(_hip(
            "cantidad_mal_tipeada", "medium", ["aceptar_conteo"],
            {"cantidad": cantidad, "counted_qty": counted, "buscado_en": ["typo"]},
            {"counted": counted, "cantidad": cantidad},
            lang,
        ))

    venc = parse_fecha(lot.get("vencimiento"))
    if shortage is not None and venc and venc < hoy():
        return pack(_hip(
            "lote_vencido", "medium", ["preguntar_angela"],
            {"vencimiento": lot.get("vencimiento"), "buscado_en": ["expiry"]},
            {"vencimiento": lot.get("vencimiento") or ""},
            lang,
        ))

    return pack(_hip(
        "sin_explicacion", "low", ["aceptar_conteo", "preguntar_angela"],
        {"buscado_en": list(SEARCHED)},
        {"producto": lot.get("producto") or ""},
        lang,
    ))


def resumen(lang: str | None = None) -> dict:
    lots = lotes.listar()
    catalog = {_codigo(d): d for d in store.raw_actual() if _codigo(d) is not None}
    ventas = esquema.filas("venta")
    recepciones = esquema.filas("recepciones")
    diferencias, taras = [], []
    for lot in lots:
        row = _clasificar(lot, lots=lots, catalog=catalog, ventas=ventas,
                          recepciones=recepciones, lang=lang)
        if row is None:
            continue
        if row["hipotesis"]["clase"] == "tara":
            taras.append(row)
        else:
            diferencias.append(row)
    diferencias.sort(key=lambda r: abs(r.get("diferencia") or 0), reverse=True)
    con_impacto = [r["impacto"] for r in diferencias if r.get("impacto") is not None]
    return {
        "resumen": {
            "abiertas": len(diferencias),
            "taras": len(taras),
            "impacto": round(sum(con_impacto), 2) if con_impacto else None,
        },
        "diferencias": diferencias,
        "taras": taras,
    }


def aceptar(id_: str, actor: str) -> dict:
    """Write lot.cantidad ← counted_qty and move product.stock by the same delta."""
    filas = lotes.listar()
    lot = next((f for f in filas if f.get("id") == id_), None)
    if lot is None:
        raise KeyError(id_)
    counted = _qty(lot.get("counted_qty"))
    if counted is None:
        raise ValueError("sin_conteo")
    cantidad = _qty(lot.get("cantidad")) or 0.0
    delta = counted - cantidad
    updated = lotes.actualizar(id_, {"cantidad": counted}, actor)
    codigo = _codigo(lot)
    if codigo is not None and abs(delta) > QTY_EPS:
        try:
            art = next(d for d in store.raw_actual() if _codigo(d) == codigo)
            nuevo = (_qty(art.get("stock")) or 0.0) + delta
            store.actualizar_articulo(codigo, {"stock": nuevo}, actor)
        except StopIteration:
            pass
    return updated
