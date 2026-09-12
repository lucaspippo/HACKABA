"""
reponer.py · QUÉ REPONER PRIMERO — el orden de compra, priorizado.

El hallazgo de quiebre (`oportunidades_neg._card_quiebre_inminente`) ya cruza
cobertura × ranking × tiempo del proveedor, y es bueno. Pero muestra UN
producto: el peor del top-15 por facturación. En el dataset del piloto hay
cientos de artículos por debajo de la cobertura, y varias decenas donde el
camión YA no llega a tiempo — todos invisibles.

Este módulo no reemplaza esa card: la profundiza. Contesta la pregunta que el
dueño hace apenas ve la primera: *"¿y qué más? ¿por dónde sigo?"*

CÓMO SE PRIORIZA — y por qué no es un score inventado:

    dias_sin_stock = max(0, lead_del_proveedor − cobertura_actual)
    plata_en_riesgo = dias_sin_stock × venta_diaria_del_producto

Es decir: si el proveedor tarda 21 días y te quedan 7 de stock, vas a estar
14 días sin ese producto; multiplicado por lo que ese producto vende por día,
eso es la plata que NO vas a facturar. No es un puntaje de 0 a 100 que haya
que explicar: son pesos, con una derivación de una línea.

Ordenar por eso es el ranking. Un producto que rota poco pero tarda mucho puede
importar más que uno que rota mucho y se repone en dos días — y al revés. Los
tres factores que pidió el negocio (plata, rotación, demora del proveedor) ya
están adentro de esa multiplicación; no hacen falta pesos arbitrarios encima.

AGRUPADO POR PROVEEDOR porque así se compra de verdad: no se emiten nueve
órdenes, se emite una por proveedor con nueve renglones.

Determinista de punta a punta. Cover days use `stock.days_of_cover` (on-hand
+ incoming − outgoing) so Reponer, Prioridades, and forecast stockout share
one number. Rotation-in-days / inmovilizado stay on on-hand: that is capital,
not the truck that is already coming.
"""
from __future__ import annotations

from . import analisis, forecast, pricing, reposicion, stock, store

# Solo entran los que ya están en zona: por encima de esto no hay decisión que
# tomar hoy. 45 días cubre el lead más largo del set de proveedores (21) con
# margen para que la alerta llegue ANTES y no cuando ya es tarde.
COBERTURA_MAX_DIAS = 45
MIN_PLATA_RIESGO = 1.0      # menos de un peso en juego no es un hallazgo
DIAS_COBERTURA_OBJETIVO = 30.44   # a cuánto se repone: un mes de venta


def _venta_diaria_pesos(art: dict, ritmo_u: float) -> float:
    """Lo que ese producto factura por día, al precio de venta vigente."""
    pvp = art.get("pvp") or 0
    return round(ritmo_u * float(pvp), 2)


def analizar(limite: int = 12) -> dict:
    """El ranking de reposición. Sin idioma: son números y códigos."""
    rot = analisis.rotacion()
    if not rot.get("disponible"):
        return {"disponible": False, "motivo": rot.get("motivo"), "items": []}

    u12 = analisis._unidades_por_codigo(365)
    stockout = set()
    fc = forecast.forecast_demand()
    if fc.get("available"):
        stockout = {it["product_code"] for it in fc.get("items") or []
                    if it.get("stockout_risk")}
    items = []
    for a in store.raw_actual():
        if (a.get("estado") or "activo") != "activo":
            continue
        u = u12.get(a.get("codigo"), 0.0)
        if u <= 0:
            continue
        ritmo = u / 365.0                      # misma derivación que rotación
        cobertura = stock.days_of_cover(a, ritmo)
        if cobertura > COBERTURA_MAX_DIAS:
            continue

        proveedor = a.get("proveedor") or ""
        lead, lead_propio = reposicion.dias_reposicion(proveedor)
        # el MISMO número que usa la card de quiebre: lo que te queda menos lo
        # que tarda el proveedor. Positivo = te da para negociar; negativo = el
        # camión no llega y vas a estar esos días sin el producto.
        dias_para_negociar = round(cobertura - lead, 1)
        dias_sin_stock = max(0.0, -dias_para_negociar)
        venta_diaria = _venta_diaria_pesos(a, ritmo)
        plata = round(dias_sin_stock * venta_diaria, 2)
        # Los que TODAVÍA llegan a tiempo entran igual (plata 0): son la lista
        # de a-quién-mirar-la-semana-que-viene, y sin ellos el ranking miente
        # por omisión — parecería que todo está perdido.
        if plata < MIN_PLATA_RIESGO and dias_para_negociar < 0:
            continue

        # cuánto pedir: reponer a un mes de venta, descontando lo que se va a
        # consumir mientras el camión viene en camino (misma cuenta que la card)
        stock_al_llegar = max(0.0, stock.projected_stock(a) - ritmo * lead)
        sugerido = max(0.0, ritmo * DIAS_COBERTURA_OBJETIVO - stock_al_llegar)
        sugerido = (round(sugerido, 1) if pricing.es_por_peso(a)
                    else float(round(sugerido)))

        items.append({
            "codigo": a.get("codigo"),
            "producto": a.get("descripcion"),
            "proveedor": proveedor,
            "stock": round(stock.on_hand(a), 2),
            "incoming_qty": float(a.get("incoming_qty") or 0),
            "outgoing_qty": float(a.get("outgoing_qty") or 0),
            "projected_stock": round(stock.projected_stock(a), 2),
            "cobertura_dias": round(cobertura, 1),
            "lead_dias": lead,
            "lead_propio": lead_propio,      # False = supuesto, no dato del proveedor
            "dias_para_negociar": dias_para_negociar,
            "dias_sin_stock": round(dias_sin_stock, 1),
            "venta_diaria_pesos": venta_diaria,
            "plata_en_riesgo": plata,
            "sugerido": sugerido,
            "por_peso": pricing.es_por_peso(a),
            "stockout_risk": a.get("codigo") in stockout,
        })

    # primero por plata (los que ya no llegan), después por urgencia entre los
    # que todavía tienen tiempo: menos margen = antes en la lista
    items.sort(key=lambda x: (-x["plata_en_riesgo"], x["dias_para_negociar"]))
    top = items[:limite]

    # agrupado por proveedor: así se compra de verdad — una orden, N renglones
    por_prov: dict[str, dict] = {}
    for it in items:
        g = por_prov.setdefault(it["proveedor"], {
            "proveedor": it["proveedor"], "lead_dias": it["lead_dias"],
            "items": 0, "plata_en_riesgo": 0.0, "productos": []})
        g["items"] += 1
        g["plata_en_riesgo"] = round(g["plata_en_riesgo"] + it["plata_en_riesgo"], 2)
        if len(g["productos"]) < 6:
            g["productos"].append({"codigo": it["codigo"], "producto": it["producto"],
                                   "sugerido": it["sugerido"]})
    proveedores = sorted(por_prov.values(), key=lambda g: -g["plata_en_riesgo"])

    return {
        "disponible": True,
        "items": top,
        "total_en_zona": len(items),
        # las dos caras: a cuántos el camión ya no les llega, y a cuántos sí
        "ya_tarde": sum(1 for x in items if x["dias_para_negociar"] < 0),
        "con_tiempo": sum(1 for x in items if x["dias_para_negociar"] >= 0),
        "stockout_mes": sum(1 for x in items if x["stockout_risk"]),
        "plata_total": round(sum(x["plata_en_riesgo"] for x in items), 2),
        "proveedores": proveedores,
        "cobertura_max_dias": COBERTURA_MAX_DIAS,
    }
