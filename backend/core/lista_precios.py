"""
P22·A — La lista de precios del proveedor: el evento más común de una
distribuidora, por los rieles existentes.

Llega la lista nueva (foto o CSV) → el DIFF contra el catálogo real marca lo
raro (el validador de escala y el matcheo código↔nombre hacen el trabajo;
Ángela lo narra) → preview editable → con el OK, actualización masiva de
costos CON BACKUP (reversible byte-igual, como todo) → el efecto en cascada
es visible: margen teórico e inmovilizado recalculados de la misma fuente.

Convención de precios: la lista del proveedor trae el costo FINAL (IVA
incluido), igual que el campo costo_iva del catálogo — se comparan directo.

Anomalías que el diff detecta solo:
  - salto_sospechoso: la suba del ítem se despega del resto de la lista
    (> UMBRAL_SALTO % cuando la mediana viene de aumentos normales) — el
    clásico error de tipeo del proveedor.
  - codigo_no_coincide: el código apunta a UN producto del catálogo pero la
    descripción dice OTRO — el clásico desastre de las listas reales. Se
    sugiere el producto que el nombre sí matchea; no se aplica sin decisión.
"""
from __future__ import annotations

import statistics
import unicodedata

from . import store

UMBRAL_SALTO = 20.0   # % de suba que se despega de una lista normal (~4-7%)
_STOPWORDS = {"campo", "alegre", "la", "de", "el", "x", "con", "sin"}


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _palabras(s) -> set[str]:
    return {w for w in _norm(s).replace("(", " ").replace(")", " ").split()
            if len(w) > 2 and w not in _STOPWORDS}


def _catalogo() -> dict[int, dict]:
    return {a.get("codigo"): a for a in store.raw_actual()}


def _buscar_por_nombre(descripcion: str) -> dict | None:
    """El artículo del catálogo cuyo nombre mejor matchea la descripción."""
    objetivo = _palabras(descripcion)
    if not objetivo:
        return None
    mejor, puntaje = None, 0.0
    for a in store.raw_actual():
        propias = _palabras(a.get("descripcion"))
        if not propias:
            continue
        inter = len(objetivo & propias) / len(objetivo | propias)
        if inter > puntaje:
            mejor, puntaje = a, inter
    return mejor if puntaje >= 0.5 else None


def diff(extraccion: dict, lang: str | None = None) -> dict:
    """La lista leída (items con codigo/descripcion/precio_unitario) contra el
    catálogo REAL. No muta nada: es el análisis previo al OK."""
    import i18n
    cat = _catalogo()
    proveedor = (extraccion.get("proveedor") or {}).get("razon_social") or ""
    items_out, subas_limpias = [], []
    for it in extraccion.get("items") or []:
        codigo = it.get("codigo")
        try:
            codigo = int(codigo)
        except (TypeError, ValueError):
            codigo = None
        precio_nuevo = it.get("precio_unitario")
        a = cat.get(codigo)
        item = {"codigo": codigo, "descripcion_lista": it.get("descripcion"),
                "precio_nuevo": precio_nuevo, "estado": "ok"}
        if a is None:
            item["estado"] = "sin_catalogo"
            items_out.append(item)
            continue
        item["producto_catalogo"] = a.get("descripcion")
        item["costo_actual"] = a.get("costo_iva")
        if item["costo_actual"] and precio_nuevo:
            item["pct"] = round((float(precio_nuevo) / float(item["costo_actual"]) - 1) * 100, 1)
        # ¿el nombre de la lista habla de OTRO producto? (código pisado)
        desc = it.get("descripcion") or ""
        if desc and _palabras(desc) and \
           len(_palabras(desc) & _palabras(a.get("descripcion"))) == 0:
            sugerido = _buscar_por_nombre(desc)
            item["estado"] = "codigo_no_coincide"
            if sugerido:
                item["sugerido"] = {"codigo": sugerido["codigo"],
                                    "producto": sugerido["descripcion"],
                                    "costo_actual": sugerido.get("costo_iva")}
        items_out.append(item)

    # el salto sospechoso se juzga CONTRA la propia lista (la mediana)
    pcts = [x["pct"] for x in items_out if x.get("pct") is not None and x["estado"] == "ok"]
    mediana = statistics.median(pcts) if pcts else 0.0
    for x in items_out:
        if x["estado"] == "ok" and x.get("pct") is not None:
            if x["pct"] > max(UMBRAL_SALTO, mediana * 3):
                x["estado"] = "salto_sospechoso"
            else:
                subas_limpias.append(x["pct"])

    limpios = [x for x in items_out if x["estado"] == "ok"]
    dudosos = [x for x in items_out if x["estado"] in ("salto_sospechoso", "codigo_no_coincide")]
    return {
        "proveedor": proveedor,
        "n": len(items_out),
        "limpios": len(limpios),
        "dudosos": dudosos,
        "items": items_out,
        "promedio_pct": round(statistics.mean(subas_limpias), 1) if subas_limpias else None,
        "mediana_pct": round(mediana, 1) if pcts else None,
        "nota": i18n.t("core.lista.nota_diff", lang),
    }


def _margen_teorico_pct() -> float | None:
    """El MISMO margen ponderado por capital del KPI de Trend (una sola verdad)."""
    from . import analisis
    k = analisis.kpis()
    m = k.get("margen_teorico")
    return m.get("pct") if isinstance(m, dict) else m


def aplicar(items: list[dict], actor: str = "dueño", lang: str | None = None) -> dict:
    """Actualización masiva de costos CON BACKUP — el mismo patrón que el
    saneamiento: backup → muta → guarda → audita. items: [{codigo, precio_nuevo}].
    El revert es el de siempre (revertir_version con el id del backup)."""
    import i18n
    from . import analisis
    raw = store.raw_actual()
    por_codigo = {a.get("codigo"): a for a in raw}
    aplicables = []
    for it in items:
        a = por_codigo.get(it.get("codigo"))
        nuevo = it.get("precio_nuevo")
        if a is not None and nuevo:
            aplicables.append((a, float(nuevo)))
    if not aplicables:
        return {"ok": False, "motivo": i18n.t("core.lista.nada_que_aplicar", lang)}

    # el inmovilizado sale del MISMO agregador que el Home y las tools (una
    # sola verdad — la regla propia daba otro número por los fantasmas)
    import data_store as ds
    margen_antes = _margen_teorico_pct()
    inmov_antes = ds.resumen()["resumen"]["inmovilizado_total"]
    backup = store.versiones.save({"articulos": raw},
                                  motivo="Backup antes de aplicar lista de precios",
                                  autor=actor)
    for a, nuevo in aplicables:
        a["costo_iva"] = nuevo
        a["antiguedad_costo_dias"] = 0  # el costo quedó fresco: es de HOY
        # el capital inmovilizado del artículo se REVALÚA al costo nuevo (el
        # campo es precomputado: si no se toca, el resumen no se entera)
        a["inmovilizado"] = round(max(a.get("stock") or 0, 0) * nuevo, 2)
    store.guardar(raw)
    store.audit.record(actor=actor, accion="aplicar_lista_precios",
                       antes={"version_backup": backup["id"]},
                       despues={"items": len(aplicables)})
    margen_despues = _margen_teorico_pct()
    inmov_despues = ds.resumen()["resumen"]["inmovilizado_total"]
    return {"ok": True, "tipo": "lista_precios", "items": len(aplicables),
            "version_backup": backup["id"],
            "margen_antes": margen_antes, "margen_despues": margen_despues,
            "inmovilizado_antes": inmov_antes, "inmovilizado_despues": inmov_despues}
