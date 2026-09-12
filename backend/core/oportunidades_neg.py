"""
P27·A — El SET CERRADO de oportunidades serias: plata concreta + una acción
concreta, cada una derivada de datos reales (o aditivos deterministas
commiteados). Sin dato que la sostenga, la tarjeta NO existe — se cae en
silencio, nunca se fuerza.

El set (y nada más que el set):
  1. cobrar_morosos      — cobrar a los que deben (con la curva de pago del peor)
  2. despertar_dormido   — liquidar el stock que no rota
  3. ventana_compra      — adelantar SOLO la compra que ibas a hacer igual,
                           antes de que pegue la lista nueva del proveedor
  4. cliente_frio        — el cliente que compra muy por debajo de SU histórico
  5. estrella_caida      — un top-10 por facturación cayendo ≥3 meses seguidos
  6. quiebre_inminente   — el producto clave que se agota antes (cobertura × ranking)
  7. pre_pico            — la compra grande del pico estacional se planifica antes
  8. concentracion       — top 3 clientes con demasiada porción de la facturación
  9. margen_bajo         — precios muy por debajo del promedio de su categoría

Cada tarjeta declara sus FUENTES cruzadas ("Crucé: …"), su drill-down con el
porqué narrado, el gráfico histórico (contrato P21: series/puntos/meta) y los
supuestos. "Cargar precios faltantes" ya NO vive acá: es un error de datos y
se atiende en Datos a corregir (P27·A10).
"""
from __future__ import annotations

import datetime
import json
import os

from . import paths, conocimiento, stock, insight as ins

CONDICIONES_JSON = os.path.join(paths.DATA_DIR, "proveedores_condiciones.json")

# Umbrales del set — declarados acá, no enterrados en los cálculos.
VENTANA_FRIO_DIAS = 180          # la ventana que el dato sostiene (ciclos de compra bimestrales)
UMBRAL_FRIO_PCT = 25             # caída mínima vs SU histórico para que la card viva
MIN_CLIENTES_CONC = 10           # concentración solo con cartera real de clientes
UMBRAL_CONCENTRACION_PCT = 40    # si el top 3 no llega, la card se cae (no se fuerza)
COBERTURA_QUIEBRE_DIAS = 14      # "inminente" = se agota en dos semanas o menos
TOP_RANK_QUIEBRE = 15            # solo productos que importan por facturación
RACHA_MIN_MESES = 3              # caída sostenida, no un mes flojo
TOP_RANK_ESTRELLA = 10
ROTACION_ALTA_DIAS = 60          # para la ventana de compra: los lentos no son "compra que ibas a hacer igual"


def _t(key: str, lang: str | None = None, **params) -> str:
    import i18n
    return i18n.t(key, lang, **params)


def _pesos(n, lang):
    import i18n
    return i18n.pesos(n or 0, lang)


def _num(x, lang) -> str:
    """Cantidad legible con separador de miles del idioma (ES 1.234,5 / EN 1,234.5).
    Sin decimales cuando es entero: 'vendés 612 unidades', no '612,0'."""
    v = float(x or 0)
    crudo = f"{v:,.0f}" if abs(v - round(v)) < 0.05 else f"{v:,.1f}"
    if lang == "en":
        return crudo
    return crudo.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _mes(numero: int, lang) -> str:
    import i18n
    return i18n.mes_nombre(numero, lang)


def _condiciones_proveedor() -> dict | None:
    try:
        d = json.load(open(CONDICIONES_JSON, encoding="utf-8"))
        return (d.get("proveedores") or [None])[0]
    except Exception:  # noqa: BLE001
        return None


def _grafico(nombre: str, puntos: list[dict], unidad: str, temporal: bool,
             ventana: str = "") -> dict:
    """El contrato P21 (consulta-serie): el frontend lo renderiza con el MISMO
    renderer que usa Ángela — cero código de chart nuevo."""
    return {"ok": True, "series": [{"nombre": nombre, "puntos": puntos}],
            "meta": {"unidad": unidad, "temporal": temporal, "ventana": ventana,
                     "composicion": False, "deflactado": False}}


def _project_drill(insight_val: dict) -> dict:
    """TEMPORARY one-way projection of an insight back into the old `drill`
    shape (porque/grafico/involucrados/supuestos).

    Some callers still read a card's `drill` directly instead of going
    through core/priorities.py's `_item()` — core/grafo.py's `caminos()`, and
    tests that call a `_card_*` builder standalone (test_oportunidades_ids,
    test_p25, test_p27). Builders here only ever author `insight`; `drill` is
    derived from it so those callers keep working while this module and its
    consumers migrate. Mirrors core/priorities.py::_legacy_drill, kept as a
    separate copy on purpose: that module's own docstring already declines to
    reach into this one's private helpers, and the same isolation applies in
    reverse. Delete both once every direct reader moves to `insight`."""
    ev = insight_val.get("evidence") or []
    porque = [p["label"] for p in (insight_val.get("pattern"), insight_val.get("hypothesis")) if p]
    porque += [e["label"] for e in ev if e["weight"] == "primary"]
    chart = next((e["chart"] for e in ev if e.get("chart")), None)
    involucrados = [
        {"id": r["id"], "kind": r["kind"], "nombre": r["name"],
         "monto": r["amount"], "detalle": r["detail"]}
        for e in ev for r in (e.get("records") or [])
    ]
    return {
        "porque": porque,
        "grafico": chart,
        "involucrados": involucrados,
        "supuestos": [a["label"] for a in (insight_val.get("assumptions") or [])],
    }


def _meses_rango(desde: str, hasta: str) -> list[str]:
    """Lista de meses YYYY-MM entre dos meses inclusive (para rellenar ceros:
    un cliente que DEJÓ de comprar se tiene que VER en la curva)."""
    out = []
    a, m = int(desde[:4]), int(desde[5:7])
    while f"{a:04d}-{m:02d}" <= hasta:
        out.append(f"{a:04d}-{m:02d}")
        m += 1
        if m > 12:
            a, m = a + 1, 1
    return out


# --- el contexto compartido: UNA pasada por los datos para todo el set ---------

def _ctx(lang) -> dict:
    from . import cuentas, esquema, fechas, store, ventas
    hoy = fechas.hoy()
    ctx: dict = {"hoy": hoy, "lang": lang, "excluir": set(),
                 "ventas_ok": False, "por_prod_mes": {}, "fact_12m": {},
                 "rank": [], "rank_pos": {}, "u12m_codigo": {},
                 "meses_completos": [], "arts": [], "clientes": []}
    try:
        ctx["arts"] = [a for a in store.raw_actual() if a.get("estado") == "activo"]
    except Exception:  # noqa: BLE001
        ctx["arts"] = []
    try:
        ctx["clientes"] = cuentas.listar()
    except Exception:  # noqa: BLE001
        ctx["clientes"] = []
    ctx["product_id_by_name"] = {a.get("descripcion"): a.get("codigo")
                                 for a in ctx["arts"] if a.get("descripcion")}
    ctx["client_id_by_name"] = {c.get("nombre"): c.get("id")
                                for c in ctx["clientes"] if c.get("nombre")}
    try:
        if not ventas.hay_datos() or not ventas.montos_confirmados():
            return ctx
    except Exception:  # noqa: BLE001
        return ctx
    corte_12m = (hoy - datetime.timedelta(days=365)).isoformat()
    mes_actual = hoy.isoformat()[:7]  # mes en curso: incompleto, no aporta racha
    por_prod_mes: dict[str, dict[str, float]] = {}
    fact_12m: dict[str, float] = {}
    u12m: dict = {}
    meses: set[str] = set()
    for f in esquema.filas("venta"):
        if f.get("codigo") is None:      # resúmenes por categoría (años 3-10) afuera
            continue
        fecha, prod = f.get("fecha") or "", f.get("producto") or ""
        if len(fecha) < 7 or not prod:
            continue
        monto = float(f.get("cantidad") or 0) * float(f.get("precio") or 0)
        mes = fecha[:7]
        por_prod_mes.setdefault(prod, {})
        por_prod_mes[prod][mes] = por_prod_mes[prod].get(mes, 0.0) + monto
        if mes != mes_actual:
            meses.add(mes)
        if fecha >= corte_12m:
            fact_12m[prod] = fact_12m.get(prod, 0.0) + monto
            u12m[f["codigo"]] = u12m.get(f["codigo"], 0.0) + float(f.get("cantidad") or 0)
    if not fact_12m:
        return ctx
    rank = sorted(fact_12m.items(), key=lambda kv: -kv[1])
    ctx.update({"ventas_ok": True, "por_prod_mes": por_prod_mes,
                "fact_12m": fact_12m, "rank": rank,
                "rank_pos": {p: i + 1 for i, (p, _) in enumerate(rank)},
                "u12m_codigo": u12m, "meses_completos": sorted(meses)})
    return ctx


def _cobertura(a: dict, ctx: dict) -> tuple[float | None, float]:
    """(cover days, daily units). Same daily rate as analisis.rotacion
    (12m units / 365), but qty is projected_stock so incoming/reserved
    match Reponer and forecast stockout."""
    u12 = ctx["u12m_codigo"].get(a.get("codigo"), 0.0)
    if u12 <= 0:
        return None, 0.0
    ritmo = u12 / 365.0
    return stock.days_of_cover(a, ritmo), ritmo


# --- 1 · cobrar a los morosos ---------------------------------------------------

def _card_morosos(lang, ctx) -> dict | None:
    morosos = [c for c in ctx["clientes"] if c.get("en_mora")]
    if not morosos:
        return None
    total = sum(c["saldo"] for c in morosos)
    peor = max(morosos, key=lambda c: c["dias_sin_pagar"])
    # La curva histórica de pago del peor (los movimientos sembrados): pagos por
    # mes, con los meses sin pago EN CERO — el corte se tiene que ver.
    grafico = None
    pagos = [m for m in (peor.get("movimientos") or [])
             if m.get("tipo") in ("pago", "cobro")]
    if len(pagos) >= 4:
        por_mes: dict[str, float] = {}
        for m in pagos:
            k = (m.get("fecha") or "")[:7]
            if k:
                por_mes[k] = por_mes.get(k, 0.0) + float(m.get("monto") or 0)
        meses = _meses_rango(min(por_mes), ctx["hoy"].isoformat()[:7])
        grafico = _grafico(_t("core.opn.morosos_g", lang, nombre=peor["nombre"]),
                           [{"x": k, "y": round(por_mes.get(k, 0.0), 2)} for k in meses],
                           "$", True, f"{meses[0]} → {meses[-1]}")
    prom_dias = peor.get("promedio_pago_dias") or 0
    evidencia = [
        ins.metric("overdue_total", label=_t("core.opn.overdue_total_ev", lang), value=total,
                   unit="ars", weight="primary",
                   method={"key": "core.method.mora_total",
                           "label": _t("core.method.mora_total", lang)}),
        ins.records("overdue_clients", label=_t("core.opn.morosos_t", lang, n=len(morosos)),
                    weight="primary",
                    rows=[ins.record(kind="client", id=c["id"], name=c["nombre"],
                                     amount=c["saldo"],
                                     detail=_t("core.opn.morosos_i", lang,
                                               dias=c["dias_sin_pagar"]))
                          for c in sorted(morosos, key=lambda x: -x["saldo"])],
                    method={"key": "core.method.mora_total",
                            "label": _t("core.method.mora_total", lang)}),
        ins.metric("days_overdue", label=_t("core.opn.morosos_p2", lang, peor=peor["nombre"],
                                            dias=peor["dias_sin_pagar"],
                                            prom=prom_dias or "—"),
                   value=peor["dias_sin_pagar"], unit="days", weight="primary",
                   baseline=({"value": prom_dias, "label": _t("core.method.prom_pago", lang)}
                             if prom_dias else None),
                   method={"key": "core.method.dias_mora",
                           "label": _t("core.method.dias_mora", lang)},
                   records=[ins.record(kind="client", id=peor["id"], name=peor["nombre"],
                                       amount=peor["saldo"],
                                       detail=_t("core.opn.morosos_i", lang,
                                                 dias=peor["dias_sin_pagar"]))]),
    ]
    if grafico:
        evidencia.append(ins.series(
            "debtor_payment_curve", label=_t("core.opn.morosos_g", lang, nombre=peor["nombre"]),
            chart=grafico, weight="supporting",
            method={"key": "core.method.debtor_payment_curve",
                    "label": _t("core.method.debtor_payment_curve", lang)}))
    insight_val = ins.build(
        pattern=ins.pattern(_t("core.opn.morosos_p1", lang, n=len(morosos),
                               total=_pesos(total, lang)),
                            scope={"kind": "clients", "count": len(morosos)}),
        evidence=evidencia,
        risk=ins.risk(_t("core.prio.mora_risk", lang), exposure=total),
        recommendation=ins.recommendation(
            _t("core.opn.morosos_t", lang, n=len(morosos)), navigate="cuentas",
            chat=_t("core.opn.morosos_chat", lang)),
    )
    return {
        "id": "cobrar_morosos", "tipo": "cobrar",
        # The worst debtor names the finding: if a DIFFERENT customer
        # becomes the worst later, that's a fresh finding, not a repeat.
        "fingerprint": f"cliente:{peor['nombre']}",
        "titulo": _t("core.opn.morosos_t", lang, n=len(morosos)),
        "monto": total,
        "resumen": _t("core.opn.morosos_r", lang, peor=peor["nombre"],
                      dias=peor["dias_sin_pagar"]),
        "accion_chat": _t("core.opn.morosos_chat", lang),
        "navegar": "cuentas",
        "fuentes": [_t("core.opn.f_cuentas", lang), _t("core.opn.f_movs", lang)],
        "insight": insight_val,
        "drill": _project_drill(insight_val),  # TEMPORARY, see _project_drill
    }


# --- 2 · despertar el stock dormido ----------------------------------------------

def _card_dormido(lang, ctx) -> dict | None:
    from . import analisis
    rot = analisis.rotacion(lang)
    if not rot.get("disponible") or not rot["por_estado"]["dormido"]:
        return None
    top = rot.get("dormidos_top") or []
    top5 = sum(x["inmovilizado"] for x in top[:5])
    grafico = _grafico(_t("core.opn.dormido_g", lang),
                       [{"x": x["producto"], "y": x["inmovilizado"]} for x in top[:6]],
                       "$", False) if top else None
    evidencia = [
        ins.metric("dormant_value", label=_t("core.opn.dormant_value_ev", lang),
                   value=rot["por_estado"]["dormido"], unit="ars", weight="primary",
                   method={"key": "core.method.dormant_value",
                           "label": _t("core.method.dormant_value", lang)}),
        ins.records("dormant_products", label=_t("core.opn.dormido_t", lang),
                    weight="primary",
                    rows=[ins.record(kind="product", id=x.get("codigo"), name=x["producto"],
                                     amount=x["inmovilizado"],
                                     detail=(_t("core.opn.dormido_dias", lang,
                                               dias=int(x["dias_rotacion"]))
                                             if x.get("dias_rotacion")
                                             else _t("core.opn.dormido_sin_venta", lang)))
                          for x in top[:6]],
                    method={"key": "core.method.dormant_products",
                            "label": _t("core.method.dormant_products", lang)}),
        ins.metric("dormant_top5_value", label=_t("core.opn.dormant_top5_ev", lang), value=top5, unit="ars",
                   weight="supporting",
                   method={"key": "core.method.dormant_top5_value",
                           "label": _t("core.method.dormant_top5_value", lang)}),
    ]
    if grafico:
        evidencia.append(ins.series(
            "dormant_chart", label=_t("core.opn.dormido_g", lang), chart=grafico,
            weight="supporting",
            method={"key": "core.method.dormant_products",
                    "label": _t("core.method.dormant_products", lang)}))
    assunciones = [ins.assumption(_t("core.opn.dormido_s1", lang))]
    card = {
        "id": "despertar_dormido", "tipo": "liquidar",
        # The single most-dormant product names the finding; if a different
        # product becomes the worst later, that's worth surfacing again.
        "fingerprint": f"producto:{top[0]['producto']}" if top else "agregado",
        "titulo": _t("core.opn.dormido_t", lang),
        "monto": rot["por_estado"]["dormido"],
        "resumen": _t("core.opn.dormido_r", lang, pct=rot["pct_dormido"],
                      top5=_pesos(top5, lang)),
        "accion_chat": _t("core.opn.dormido_chat", lang),
        "navegar": "inventario",
        "fuentes": [_t("core.opn.f_ventas12", lang), _t("core.opn.f_stock", lang),
                    _t("core.opn.f_costos", lang)],
    }
    # Piece 14 — el dormido de limpieza fue una compra por precio, no un error:
    # el hallazgo lo distingue del resto (contexto declarado, no un cálculo).
    k_dorm = [p for p in conocimiento.aplicables(nodo="inventario", efecto="contexto_para_angela")
              if "limpieza" in conocimiento._norm(p.get("entidad"))]
    if k_dorm:
        assunciones.append(ins.assumption(
            _t("core.opn.k_ensenaste", lang, texto=conocimiento.texto_en(k_dorm[0], lang))))
        card["conocimiento_aplicado"] = [conocimiento.resumen_pieza(p) for p in k_dorm]
    insight_val = ins.build(
        pattern=ins.pattern(_t("core.opn.dormido_p1", lang, pct=rot["pct_dormido"],
                               monto=_pesos(rot["por_estado"]["dormido"], lang))),
        hypothesis=ins.hypothesis(_t("core.opn.dormido_p2", lang, top5=_pesos(top5, lang))),
        evidence=evidencia,
        assumptions=assunciones,
        recommendation=ins.recommendation(
            _t("core.opn.dormido_t", lang), navigate="inventario",
            chat=_t("core.opn.dormido_chat", lang)),
    )
    card["insight"] = insight_val
    card["drill"] = _project_drill(insight_val)  # TEMPORARY, see _project_drill
    return card

def _card_ventana_compra(lang, ctx) -> dict | None:
    """P27·A3 — CORREGIDA: no es "comprá un mes entero por las dudas". Es
    "adelantá SOLO la compra que ibas a hacer igual": productos del proveedor
    con rotación alta cuya reposición cae ANTES de la lista siguiente — esos
    los vas a pagar sí o sí; pagarlos hoy es pagarlos sin la suba."""
    from . import macro
    cond = _condiciones_proveedor()
    if not cond or not ctx["ventas_ok"]:
        return None
    prov = cond["proveedor"]
    marca = "CAMPO ALEGRE"  # los productos del proveedor, por marca real
    suba = cond.get("ultima_suba_promedio_pct") or 5.7
    frec = int(cond.get("frecuencia_lista_dias") or 30)
    hoy = ctx["hoy"]
    try:
        proxima = datetime.date.fromisoformat(cond["ultima_lista"]) + \
            datetime.timedelta(days=frec)
    except Exception:  # noqa: BLE001
        proxima = hoy
    dias_hasta = max(0, (proxima - hoy).days)
    compra = 0.0
    items = []
    for a in ctx["arts"]:
        if marca not in (a.get("descripcion") or "") or not a.get("costo_iva"):
            continue
        cob, ritmo = _cobertura(a, ctx)
        if cob is None or cob > ROTACION_ALTA_DIAS:
            continue  # sin venta real o rotación lenta: no es compra segura
        # Lo que te va a faltar para llegar de la lista nueva a la siguiente:
        # eso lo comprás igual — la única decisión es a qué precio.
        stock_al_llegar = max(0.0, stock.projected_stock(a) - ritmo * dias_hasta)
        faltante_u = max(0.0, ritmo * frec - stock_al_llegar)
        if faltante_u <= 0:
            continue  # su reposición NO cae antes de la lista siguiente
        monto_item = faltante_u * a["costo_iva"]
        compra += monto_item
        items.append({"id": a.get("codigo"), "kind": "product",
                      "nombre": a["descripcion"], "monto": round(monto_item, 2),
                      "detalle": _t("core.opn.ventana_cob", lang, dias=int(cob))})
    if compra <= 0:
        return None
    ahorro = round(compra * suba / 100, 2)
    items.sort(key=lambda x: -x["monto"])
    historial = cond.get("historial_listas") or [
        {"fecha": cond.get("ultima_lista"), "suba_promedio_pct": suba}]
    grafico = _grafico(_t("core.opn.ventana_g", lang, proveedor=prov),
                       [{"x": h["fecha"], "y": h["suba_promedio_pct"]}
                        for h in historial if h.get("fecha")],
                       "%", True,
                       _t("core.opn.ventana_g_v", lang, n=len(historial)))
    cuando = (_t("core.opn.ventana_ya", lang) if dias_hasta <= 3
              else _t("core.opn.ventana_en", lang, n=dias_hasta))
    ipc = macro.consultar(["inflacion"], lang).get("inflacion") or {}

    supuestos = [ins.assumption(_t("core.opn.ventana_s1", lang)),
                 ins.assumption(_t("core.opn.ventana_s3", lang, n=len(historial), suba=f"{suba:g}"))]
    if ipc.get("disponible"):
        supuestos.append(ins.assumption(_t("core.opn.ventana_p3", lang,
                                           ipc=f"{ipc['valor']:g}", fuente=ipc.get("fuente") or "")))

    # Pieces 7+8 — lo que Aldo enseñó sobre este proveedor. La regla del viernes
    # es un efecto de comportamiento (el día sugerido nunca cae viernes) y la
    # suba mensual refuerza el porqué de comprar ahora. Ambas viajan como nodos
    # de conocimiento para el camino del mapa (E3).
    piezas_prov = conocimiento.para(prov, nodo="proveedores")
    regla_viernes = next((p for p in piezas_prov
                          if (p.get("params") or {}).get("evitar_dia") == "viernes"), None)
    ctx_suba = next((p for p in piezas_prov if p["tipo"] == "contexto"), None)
    base_dia = hoy if dias_hasta <= 3 else proxima
    dia_pedido, movido = base_dia, False
    if regla_viernes and base_dia.weekday() == 4:  # 4 = viernes
        dia_pedido, movido = base_dia - datetime.timedelta(days=1), True  # al jueves
    if ctx_suba:
        supuestos.insert(1, ins.assumption(_t("core.opn.ventana_k_suba", lang, proveedor=prov)))
    if regla_viernes:
        supuestos.append(ins.assumption(_t("core.opn.ventana_k_viernes_mov", lang) if movido
                                        else _t("core.opn.ventana_k_viernes", lang)))
    aplicadas = ([conocimiento.resumen_pieza(ctx_suba)] if ctx_suba else []) + \
                ([conocimiento.resumen_pieza(regla_viernes)] if regla_viernes else [])

    evidencia = [
        ins.metric("window_purchase_amount", label=_t("core.opn.window_purchase_ev", lang), value=compra,
                   unit="ars", weight="primary",
                   method={"key": "core.method.window_purchase",
                           "label": _t("core.method.window_purchase", lang)}),
        ins.metric("window_savings_amount", label=_t("core.opn.window_savings_ev", lang), value=ahorro,
                   unit="ars", weight="primary",
                   method={"key": "core.method.window_savings",
                           "label": _t("core.method.window_savings", lang)}),
        ins.records("window_items", label=_t("core.opn.ventana_t", lang, proveedor=prov),
                    weight="supporting",
                    rows=[ins.record(kind=it["kind"], id=it["id"], name=it["nombre"],
                                     amount=it["monto"], detail=it["detalle"])
                          for it in items[:6]],
                    method={"key": "core.method.window_purchase",
                            "label": _t("core.method.window_purchase", lang)}),
        ins.series("price_rise_history", label=_t("core.opn.ventana_g", lang, proveedor=prov),
                   chart=grafico, weight="supporting",
                   method={"key": "core.method.price_rise_history",
                           "label": _t("core.method.price_rise_history", lang)}),
    ]
    insight_val = ins.build(
        pattern=ins.pattern(_t("core.opn.ventana_q1", lang, proveedor=prov, frec=frec,
                               cuando=cuando, suba=f"{suba:g}")),
        hypothesis=ins.hypothesis(_t("core.opn.ventana_q2", lang, n=len(items),
                                     compra=_pesos(compra, lang))),
        evidence=evidencia,
        assumptions=supuestos,
        recommendation=ins.recommendation(
            _t("core.opn.ventana_t", lang, proveedor=prov), navigate=None,
            chat=_t("core.opn.ventana_chat", lang, proveedor=prov)),
        deadline=ins.deadline(date=proxima.isoformat(),
                              basis=_t("core.opn.ventana_deadline_basis", lang, proveedor=prov)),
    )
    card = {
        "id": "ventana_compra", "tipo": "comprar",
        "fingerprint": f"proveedor:{prov}",
        "titulo": _t("core.opn.ventana_t", lang, proveedor=prov),
        "monto": ahorro,
        "datos": {"compra": round(compra, 2), "ahorro": ahorro,
                  "dias_hasta_lista": dias_hasta, "productos": len(items),
                  "dia_pedido": dia_pedido.isoformat(), "evito_viernes": bool(regla_viernes)},
        "resumen": _t("core.opn.ventana_r2", lang, suba=f"{suba:g}", cuando=cuando),
        "accion_chat": _t("core.opn.ventana_chat", lang, proveedor=prov),
        "navegar": None,
        "fuentes": [_t("core.opn.f_lista", lang), _t("core.opn.f_stock", lang),
                    _t("core.opn.f_ventas12", lang), _t("core.opn.f_ipc", lang)],
        "macro": {"inflacion": ipc.get("valor"), "fuente": ipc.get("fuente"),
                  "fecha": ipc.get("fecha")} if ipc.get("disponible") else None,
        "insight": insight_val,
        "drill": _project_drill(insight_val),  # TEMPORARY, see _project_drill
    }
    if aplicadas:
        card["conocimiento_aplicado"] = aplicadas
    return card


# --- 4 · el cliente que se enfría -------------------------------------------------

def _card_cliente_frio(lang, ctx) -> dict | None:
    """Compras del período de cada cliente vs SU promedio histórico (movimientos
    sembrados). Ventana de 180 días: los ciclos de compra en cuenta corriente
    son bimestrales — una ventana menor confunde ciclo con enfriamiento."""
    hoy = ctx["hoy"]
    corte = (hoy - datetime.timedelta(days=VENTANA_FRIO_DIAS)).isoformat()
    factor = VENTANA_FRIO_DIAS / 30.44
    cands, total_hist = [], {}
    for c in ctx["clientes"]:
        vtas = [m for m in (c.get("movimientos") or []) if m.get("tipo") == "venta"]
        if len(vtas) < 6:
            continue  # sin historia suficiente no hay promedio defendible
        primera = min(m["fecha"] for m in vtas)
        antiguedad_dias = (hoy - datetime.date.fromisoformat(primera)).days
        if antiguedad_dias < 360:
            continue
        total = sum(float(m.get("monto") or 0) for m in vtas)
        total_hist[c["nombre"]] = total
        esperado = total / (antiguedad_dias / 30.44) * factor
        actual = sum(float(m.get("monto") or 0) for m in vtas if m["fecha"] >= corte)
        if esperado <= 0:
            continue
        caida = (1 - actual / esperado) * 100
        if caida >= UMBRAL_FRIO_PCT:
            cands.append({"c": c, "caida": caida, "actual": actual,
                          "esperado": esperado, "vtas": vtas})
    if not cands:
        return None
    cands.sort(key=lambda x: -x["caida"])
    peor = cands[0]
    ranking = sorted(total_hist.items(), key=lambda kv: -kv[1])
    pos = next((i + 1 for i, (n, _) in enumerate(ranking)
                if n == peor["c"]["nombre"]), None)
    monto = round(peor["esperado"] - peor["actual"], 2)
    # Su curva de compras, mes a mes, con los meses sin compra en cero.
    por_mes: dict[str, float] = {}
    for m in peor["vtas"]:
        k = m["fecha"][:7]
        por_mes[k] = por_mes.get(k, 0.0) + float(m.get("monto") or 0)
    meses = _meses_rango(min(por_mes), hoy.isoformat()[:7])
    grafico = _grafico(_t("core.opn.frio_g", lang, nombre=peor["c"]["nombre"]),
                       [{"x": k, "y": round(por_mes.get(k, 0.0), 2)} for k in meses],
                       "$", True, f"{meses[0]} → {meses[-1]}")
    insight_val = ins.build(
        pattern=ins.pattern(_t("core.opn.frio_q1", lang, nombre=peor["c"]["nombre"],
                               pct=f"{peor['caida']:.0f}",
                               actual=_pesos(peor["actual"], lang),
                               esperado=_pesos(peor["esperado"], lang)),
                            scope={"kind": "client", "count": 1}),
        evidence=[
            ins.metric("cooling_purchase_pace", label=_t("core.opn.cooling_pace_ev", lang),
                       value=peor["actual"], unit="ars", weight="primary",
                       baseline={"value": peor["esperado"],
                                 "label": _t("core.opn.frio_s1", lang, dias=VENTANA_FRIO_DIAS)},
                       method={"key": "core.method.client_cooling",
                               "label": _t("core.method.client_cooling", lang)}),
            ins.metric("cooling_revenue_gap", label=_t("core.opn.frio_q2", lang, pos=pos or "—",
                                                        monto=_pesos(monto, lang)),
                       value=monto, unit="ars", weight="primary",
                       method={"key": "core.method.client_cooling_gap",
                               "label": _t("core.method.client_cooling_gap", lang)}),
            ins.records("cooling_clients", label=_t("core.opn.frio_t", lang, nombre=peor["c"]["nombre"]),
                        weight="supporting",
                        rows=[ins.record(kind="client", id=x["c"].get("id"), name=x["c"]["nombre"],
                                         amount=round(x["actual"], 2),
                                         detail=_t("core.opn.frio_i", lang, pct=f"{x['caida']:.0f}"))
                              for x in cands[:4]],
                        method={"key": "core.method.client_cooling",
                                "label": _t("core.method.client_cooling", lang)}),
            ins.series("cooling_chart", label=_t("core.opn.frio_g", lang, nombre=peor["c"]["nombre"]),
                       chart=grafico, weight="supporting",
                       method={"key": "core.method.client_cooling",
                               "label": _t("core.method.client_cooling", lang)}),
        ],
        assumptions=[ins.assumption(_t("core.opn.frio_s1", lang, dias=VENTANA_FRIO_DIAS))],
        recommendation=ins.recommendation(
            _t("core.opn.frio_t", lang, nombre=peor["c"]["nombre"]), navigate="cuentas",
            chat=_t("core.opn.frio_chat", lang, nombre=peor["c"]["nombre"])),
    )
    return {
        "id": "cliente_frio", "tipo": "vender",
        "fingerprint": f"cliente:{peor['c']['nombre']}",
        "titulo": _t("core.opn.frio_t", lang, nombre=peor["c"]["nombre"]),
        "monto": monto,
        "datos": {"cliente": peor["c"]["nombre"], "caida_pct": round(peor["caida"]),
                  "rank_historico": pos, "ventana_dias": VENTANA_FRIO_DIAS},
        "resumen": _t("core.opn.frio_r", lang, pos=pos or "—",
                      pct=f"{peor['caida']:.0f}"),
        "accion_chat": _t("core.opn.frio_chat", lang, nombre=peor["c"]["nombre"]),
        "navegar": "cuentas",
        "fuentes": [_t("core.opn.f_cuentas", lang), _t("core.opn.f_movs", lang)],
        "insight": insight_val,
        "drill": _project_drill(insight_val),  # TEMPORARY, see _project_drill
    }


# --- 5 · producto estrella en caída ------------------------------------------------

def _card_estrella_caida(lang, ctx) -> dict | None:
    """Un top-10 por facturación con ventas cayendo ≥3 meses SEGUIDOS (serie
    SKU/mes, meses completos). Solo si el dataset lo muestra de verdad."""
    if not ctx["ventas_ok"]:
        return None
    meses = ctx["meses_completos"][-15:]
    if len(meses) < RACHA_MIN_MESES + 1:
        return None
    elegido = None
    for prod, _f12 in ctx["rank"][:TOP_RANK_ESTRELLA]:
        serie = [round(ctx["por_prod_mes"][prod].get(m, 0.0), 2) for m in meses]
        racha = 0
        for a, b in zip(serie[:-1], serie[1:]):
            racha = racha + 1 if b < a else 0
        if racha >= RACHA_MIN_MESES:
            elegido = (prod, serie, racha)
            break  # el rank ya viene por facturación: el primero es LA estrella
    if not elegido:
        return None
    prod, serie, racha = elegido
    ctx["excluir"].add(prod)  # que el quiebre inminente no repita el mismo producto
    pos = ctx["rank_pos"][prod]
    ultimo = serie[-1]
    # El $ honesto: contra el MISMO mes del año pasado (la estacionalidad no
    # ensucia); si el interanual no cae, contra el arranque de la racha.
    mes_ult = meses[-1]
    hace_anio = f"{int(mes_ult[:4]) - 1}{mes_ult[4:]}"
    y_prev = ctx["por_prod_mes"][prod].get(hace_anio, 0.0)
    perdida = round(y_prev - ultimo, 2) if y_prev > ultimo else \
        round(serie[-racha - 1] - ultimo, 2)
    if perdida <= 0:
        return None
    otros = []
    for p2, _ in ctx["rank"][:TOP_RANK_ESTRELLA]:
        if p2 == prod:
            continue
        s2 = [ctx["por_prod_mes"][p2].get(m, 0.0) for m in meses]
        r2 = 0
        for a, b in zip(s2[:-1], s2[1:]):
            r2 = r2 + 1 if b < a else 0
        if r2 >= RACHA_MIN_MESES:
            otros.append({"id": ctx["product_id_by_name"].get(p2), "kind": "product",
                          "nombre": p2, "monto": None,
                          "detalle": _t("core.opn.estrella_i", lang, n=r2)})
    grafico = _grafico(prod, [{"x": m, "y": v} for m, v in zip(meses, serie)],
                       "$", True, f"{meses[0]} → {meses[-1]}")
    perdida_label = (_t("core.opn.estrella_q2", lang, prev=_pesos(y_prev, lang),
                        perdida=_pesos(perdida, lang))
                     if y_prev > ultimo else
                     _t("core.opn.estrella_q3", lang, perdida=_pesos(perdida, lang)))
    insight_val = ins.build(
        pattern=ins.pattern(_t("core.opn.estrella_q1", lang, producto=prod, pos=pos,
                               n=racha, ultimo=_pesos(ultimo, lang)),
                            scope={"kind": "product", "count": 1}),
        evidence=[
            ins.metric("revenue_decline_streak", label=_t("core.opn.estrella_r", lang,
                                                           producto=prod, pos=pos, n=racha),
                       value=racha, unit="months", weight="primary",
                       method={"key": "core.method.streak_decline",
                               "label": _t("core.method.streak_decline", lang)}),
            ins.metric("revenue_loss", label=perdida_label, value=perdida, unit="ars",
                       weight="primary",
                       method={"key": "core.method.streak_loss",
                               "label": _t("core.method.streak_loss", lang)}),
            ins.records("falling_products", label=_t("core.opn.estrella_t", lang),
                        weight="supporting", rows=[
                            ins.record(kind="product", id=o["id"], name=o["nombre"],
                                      amount=o["monto"], detail=o["detalle"])
                            for o in otros[:4]],
                        method={"key": "core.method.streak_decline",
                                "label": _t("core.method.streak_decline", lang)}),
            ins.series("product_trend", label=prod, chart=grafico, weight="supporting",
                       method={"key": "core.method.streak_decline",
                               "label": _t("core.method.streak_decline", lang)}),
        ],
        assumptions=[ins.assumption(_t("core.opn.estrella_s1", lang))],
        recommendation=ins.recommendation(
            _t("core.opn.estrella_t", lang), navigate="evolucion",
            chat=_t("core.opn.estrella_chat", lang, producto=prod)),
    )
    return {
        "id": "estrella_caida", "tipo": "vender",
        "fingerprint": f"producto:{prod}",
        "titulo": _t("core.opn.estrella_t", lang),
        "monto": perdida,
        "datos": {"producto": prod, "racha_meses": racha, "rank_facturacion": pos},
        "resumen": _t("core.opn.estrella_r", lang, producto=prod, pos=pos, n=racha),
        "accion_chat": _t("core.opn.estrella_chat", lang, producto=prod),
        "navegar": "evolucion",
        "fuentes": [_t("core.opn.f_ventas24", lang), _t("core.opn.f_rank", lang)],
        "insight": insight_val,
        "drill": _project_drill(insight_val),  # TEMPORARY, see _project_drill
    }


# --- 6 · quiebre inminente ----------------------------------------------------------

def _card_quiebre_inminente(lang, ctx) -> dict | None:
    """P38·B — EL hallazgo de una distribuidora: quebrar con anticipación.

    Cobertura en días × ranking de facturación × TIEMPO DE REPOSICIÓN DEL
    PROVEEDOR. Sin el tercer factor esto es un dato; con él es una decisión:
    lo que te queda menos lo que tarda el proveedor son los días que tenés
    para negociar. Comprar con tiempo es comprar barato; esperar al quiebre
    es comprar apurado y caro.
    """
    from . import pricing, reposicion
    if not ctx["ventas_ok"]:
        return None
    cands = []
    for a in ctx["arts"]:
        prod = a.get("descripcion") or ""
        pos = ctx["rank_pos"].get(prod)
        if not pos or pos > TOP_RANK_QUIEBRE or prod in ctx["excluir"]:
            continue
        cob, ritmo = _cobertura(a, ctx)
        if cob is None or cob <= 0 or cob > COBERTURA_QUIEBRE_DIAS:
            continue
        cands.append((cob, pos, prod, a, ritmo))
    if not cands:
        return None
    # Piece 11 — la regla de Aldo ("X nunca puede quebrar") sube el producto
    # crítico al tope, por encima del orden natural (menor cobertura primero).
    def _critico(prod):
        return conocimiento.para(prod, nodo="inventario", efecto="genera_alerta", tipo="regla")
    cands.sort(key=lambda t: (0 if _critico(t[2]) else 1, t[0], t[1]))
    cob, pos, prod, art, ritmo = cands[0]
    piezas_k = _critico(prod)
    semanal = round(ctx["fact_12m"][prod] / 52, 2)
    meses = ctx["meses_completos"][-12:]
    grafico = _grafico(prod, [{"x": m, "y": round(ctx["por_prod_mes"][prod].get(m, 0.0), 2)}
                              for m in meses],
                       "$", True, f"{meses[0]} → {meses[-1]}") if meses else None

    # --- el tercer factor: cuánto tarda ESTE proveedor ---------------------
    proveedor = art.get("proveedor") or ""
    lead, lead_propio = reposicion.dias_reposicion(proveedor)
    dias_para_negociar = int(cob) - lead
    u_mes = round(ritmo * 30.44, 1)
    unidad = _t("core.opn.qi_u_kg" if pricing.es_por_peso(art) else "core.opn.qi_u_unidades", lang)
    # Lo que hay que pedir: reponer hasta un mes de venta, contando lo que se
    # va a consumir mientras el camión viene en camino.
    stock_al_llegar = max(0.0, stock.projected_stock(art) - ritmo * lead)
    sugerido = max(0.0, ritmo * 30.44 - stock_al_llegar)
    # Lo que se pide por unidad es entero (nadie pide 1.006,9 botellas); lo que
    # se pide por peso lleva su decimal.
    sugerido = round(sugerido, 1) if pricing.es_por_peso(art) else float(round(sugerido))

    if dias_para_negociar > 1:
        ventana = _t("core.opn.qi_q3_ventana", lang, n=dias_para_negociar)
    elif dias_para_negociar == 1:
        ventana = _t("core.opn.qi_q3_ventana_1", lang)
    elif dias_para_negociar == 0:
        ventana = _t("core.opn.qi_q3_justo", lang)
    else:
        ventana = _t("core.opn.qi_q3_tarde", lang, n=-dias_para_negociar)
    metodo_qi = {"key": "core.method.qi_stockout",
                 "label": _t("core.method.qi_stockout", lang)}
    evidencia = [
        ins.metric("stockout_count", label=_t("core.opn.stockout_count_ev", lang), value=len(cands),
                   unit="products", weight="primary", method=metodo_qi),
        ins.records("stockout_items",
                    label=_t("core.opn.qi_i", lang, dias=int(cob), pos=pos),
                    weight="primary",
                    rows=[ins.record(kind="product", id=_a.get("codigo"), name=p, amount=None,
                                     detail=_t("core.opn.qi_i", lang, dias=int(c), pos=ps))
                          for c, ps, p, _a, _r in cands[1:6]],
                    method=metodo_qi),
        ins.metric("weekly_revenue_at_stake", label=_t("core.opn.weekly_revenue_ev", lang), value=semanal,
                   unit="ars", weight="primary",
                   method={"key": "core.method.qi_weekly_revenue",
                           "label": _t("core.method.qi_weekly_revenue", lang)}),
        ins.metric("days_of_coverage", label=_t("core.opn.qi_m_days", lang, n=int(cob)),
                   value=int(cob), unit="days", weight="supporting",
                   method={"key": "core.method.days_of_coverage",
                           "label": _t("core.method.days_of_coverage", lang)}),
        ins.metric("supplier_lead_time", label=_t("core.opn.qi_m_days", lang, n=lead),
                   value=lead, unit="days", weight="supporting",
                   method={"key": "core.method.supplier_lead_time",
                           "label": _t("core.method.supplier_lead_time", lang)}),
        ins.metric("negotiating_window", label=ventana, value=dias_para_negociar,
                   unit="days", weight="supporting",
                   method={"key": "core.method.negotiating_window",
                           "label": _t("core.method.negotiating_window", lang)}),
    ]
    if grafico:
        evidencia.append(ins.series("product_sales_trend", label=prod, chart=grafico,
                                    weight="supporting", method=metodo_qi))
    supuestos = [ins.assumption(_t("core.opn.qi_s1", lang))]
    if not lead_propio:
        supuestos.append(ins.assumption(_t("core.opn.qi_s2", lang, lead=lead)))
    card = {
        "id": "quiebre_inminente", "tipo": "comprar",
        "fingerprint": f"producto:{prod}",
        "titulo": _t("core.opn.qi_t2", lang, producto=prod, dias=int(cob)),
        "monto": semanal,
        # Las tres claves históricas NO cambian: la notificación sembrada y el
        # camino del mapa las leen por nombre.
        "datos": {"producto": prod, "dias_cobertura": int(cob), "rank_facturacion": pos,
                  "dias_reposicion": lead, "dias_para_negociar": dias_para_negociar,
                  "unidades_mes": u_mes, "proveedor": proveedor,
                  "cantidad_sugerida": round(sugerido, 1)},
        "resumen": (_t("core.opn.qi_r2", lang, pos=pos, lead=lead, n=dias_para_negociar)
                    if dias_para_negociar > 0
                    else _t("core.opn.qi_r2_tarde", lang, pos=pos, lead=lead)),
        "accion_chat": _t("core.opn.qi_chat", lang, producto=prod),
        "navegar": "inventario",
        "fuentes": [_t("core.opn.f_ventas12", lang), _t("core.opn.f_stock", lang),
                    _t("core.opn.f_lead", lang)],
        # La propuesta con aprobación: Ángela la deja armada, NO la manda.
        "propuesta": {
            "tipo": "orden_compra",
            "titulo": _t("core.opn.qi_prop_t", lang),
            "detalle": _t("core.opn.qi_prop_d", lang, cant=_num(round(sugerido, 1), lang),
                          unidad=unidad, producto=prod, proveedor=proveedor, lead=lead),
            "codigo": art.get("codigo"), "producto": prod, "proveedor": proveedor,
            "cantidad": round(sugerido, 1),
        },
    }
    if piezas_k:
        # chip "Regla de Aldo: crítico" + la regla PRIMERO en la evidencia (misma
        # jerarquía que el viejo porque.insert(0, ...)) + el nodo de conocimiento
        # para el camino en el mapa (E3).
        card["chip_conocimiento"] = _t("core.opn.qi_k_chip", lang)
        evidencia.insert(0, ins.metric(
            "critical_rule_flag",
            label=_t("core.opn.qi_k_por", lang, texto=conocimiento.texto_en(piezas_k[0], lang)),
            value=None, unit=None, weight="primary",
            method={"key": "core.method.critical_rule",
                    "label": _t("core.method.critical_rule", lang)}))
        card["conocimiento_aplicado"] = [conocimiento.resumen_pieza(p) for p in piezas_k]
    insight_val = ins.build(
        pattern=ins.pattern(_t("core.opn.qi_q1b", lang, u=_num(u_mes, lang), unidad=unidad,
                               producto=prod, dias=int(cob), proveedor=proveedor, lead=lead),
                            scope={"kind": "product", "count": 1}),
        hypothesis=ins.hypothesis(_t("core.opn.qi_q2b", lang)),
        evidence=evidencia,
        assumptions=supuestos,
        risk=ins.risk(_t("core.prio.quiebre_risk", lang), exposure=semanal),
        recommendation=ins.recommendation(
            card["titulo"], proposal=card.get("propuesta"), navigate="inventario",
            chat=_t("core.opn.qi_chat", lang, producto=prod)),
        deadline=ins.deadline(date=(ctx["hoy"] + datetime.timedelta(days=lead)).isoformat(),
                              basis=_t("core.opn.qi_deadline_basis", lang, lead=lead)),
    )
    card["insight"] = insight_val
    card["drill"] = _project_drill(insight_val)  # TEMPORARY, see _project_drill
    return card


# --- 7 · pre-pico estacional ---------------------------------------------------------

def _card_pre_pico(lang, ctx) -> dict | None:
    """Estacionalidad × cobertura: la compra grande del pico se PLANIFICA —
    tono de planificación, no urgencia falsa."""
    from . import analisis
    est = analisis.estacionalidad(lang)
    if not est.get("disponible") or not est.get("categorias"):
        return None
    cats = {c: d for c, d in est["categorias"].items() if d.get("picos")}
    if not cats or not ctx["ventas_ok"]:
        return None
    cat = max(cats, key=lambda c: cats[c]["idx_max"])
    import i18n
    cat_disp = i18n.categoria(cat, lang)  # E3·2 — rubro traducido para el display
    d = cats[cat]
    idx, mes_pico = d["idx_max"], d["pico_max"]
    mes_plan = (min(d["picos"]) - 2) % 12 + 1  # un mes antes del primer pico
    compra, stock_u, ritmo_pico_u = 0.0, 0.0, 0.0
    for a in ctx["arts"]:
        if (a.get("tipo") or "") != cat or not a.get("costo_iva"):
            continue
        cob, ritmo = _cobertura(a, ctx)
        if cob is None:
            continue
        rp = ritmo * idx
        stock_u += stock.projected_stock(a)
        ritmo_pico_u += rp
        compra += max(0.0, rp * 31 - stock.projected_stock(a)) * a["costo_iva"]
    if compra <= 0 or ritmo_pico_u <= 0:
        return None
    cob_pico = int(stock_u / ritmo_pico_u)
    indice = d.get("indice") or {}
    grafico = _grafico(_t("core.opn.pico_g", lang, cat=cat_disp),
                       [{"x": _mes(m, lang), "y": indice.get(m) or indice.get(str(m)) or 0}
                        for m in range(1, 13)],
                       "×", False, _t("core.opn.pico_g_v", lang,
                                      anios=est.get("anios_analizados") or 0))
    nombre_pico = _mes(mes_pico, lang)
    nombre_plan = _mes(mes_plan, lang)
    hoy = ctx["hoy"]
    anio_pico = hoy.year if mes_pico >= hoy.month else hoy.year + 1
    fecha_pico = datetime.date(anio_pico, mes_pico, 1)
    insight_val = ins.build(
        pattern=ins.pattern(_t("core.opn.pico_q1", lang, mes=nombre_pico, idx=f"{idx:g}",
                               cat=cat_disp, anios=est.get("anios_analizados") or 0)),
        evidence=[
            ins.metric("peak_multiplier", label=f"×{idx:g}", value=idx, unit="×",
                       weight="primary",
                       method={"key": "core.method.peak_multiplier",
                               "label": _t("core.method.peak_multiplier", lang)}),
            ins.metric("peak_purchase_amount",
                       label=_t("core.opn.pico_q3", lang, compra=_pesos(compra, lang),
                                plan=nombre_plan),
                       value=compra, unit="ars", weight="primary",
                       method={"key": "core.method.peak_purchase",
                               "label": _t("core.method.peak_purchase", lang)}),
            ins.metric("peak_coverage_days", label=_t("core.opn.pico_q2", lang, dias=cob_pico),
                       value=cob_pico, unit="days", weight="supporting",
                       method={"key": "core.method.peak_coverage",
                               "label": _t("core.method.peak_coverage", lang)}),
            ins.series("seasonality_index", label=_t("core.opn.pico_g", lang, cat=cat_disp),
                       chart=grafico, weight="supporting",
                       method={"key": "core.method.peak_multiplier",
                               "label": _t("core.method.peak_multiplier", lang)}),
        ],
        assumptions=[ins.assumption(_t("core.opn.pico_s1", lang))],
        recommendation=ins.recommendation(
            _t("core.opn.pico_t", lang, cat=cat_disp), navigate="evolucion",
            chat=_t("core.opn.pico_chat", lang, cat=cat_disp, mes=nombre_pico)),
        deadline=ins.deadline(date=fecha_pico.isoformat(),
                              basis=_t("core.opn.pico_deadline_basis", lang, mes=nombre_pico)),
    )
    return {
        "id": "pre_pico", "tipo": "planificar",
        "fingerprint": f"categoria:{cat}",
        "titulo": _t("core.opn.pico_t", lang, cat=cat_disp),
        "monto": round(compra, 2),
        "datos": {"categoria": cat, "indice": idx, "mes_pico": mes_pico,
                  "mes_plan": mes_plan, "cobertura_pico_dias": cob_pico},
        "resumen": _t("core.opn.pico_r", lang, mes=nombre_pico, idx=f"{idx:g}",
                      cat=cat_disp, dias=cob_pico, plan=nombre_plan),
        "accion_chat": _t("core.opn.pico_chat", lang, cat=cat_disp, mes=nombre_pico),
        "navegar": "evolucion",
        "fuentes": [_t("core.opn.f_ventas10a", lang), _t("core.opn.f_estacion", lang),
                    _t("core.opn.f_stock", lang)],
        "insight": insight_val,
        "drill": _project_drill(insight_val),  # TEMPORARY, see _project_drill
    }


# --- 8 · concentración de clientes ----------------------------------------------------

def _card_concentracion(lang, ctx) -> dict | None:
    """% de la facturación EN CUENTA CORRIENTE que concentran los top 3
    clientes (movimientos sembrados). Solo si el % es significativo (>40)."""
    hoy = ctx["hoy"]
    corte = (hoy - datetime.timedelta(days=365)).isoformat()
    por_cliente = {}
    for c in ctx["clientes"]:
        v = sum(float(m.get("monto") or 0) for m in (c.get("movimientos") or [])
                if m.get("tipo") == "venta" and (m.get("fecha") or "") >= corte)
        if v > 0:
            por_cliente[c["nombre"]] = v
    if len(por_cliente) < MIN_CLIENTES_CONC:
        return None
    total = sum(por_cliente.values())
    ranking = sorted(por_cliente.items(), key=lambda kv: -kv[1])
    top3 = ranking[:3]
    pct = sum(v for _, v in top3) / total * 100
    if pct <= UMBRAL_CONCENTRACION_PCT:
        return None  # el dato no lo sostiene: la card se cae, no se fuerza
    monto = round(sum(v for _, v in top3), 2)
    grafico = _grafico(_t("core.opn.conc_g", lang),
                       [{"x": n, "y": round(v / total * 100, 1)}
                        for n, v in ranking[:5]],
                       "%", False, _t("core.opn.conc_g_v", lang))
    card = {
        "id": "concentracion", "tipo": "diversificar",
        # The top-3 SET names the finding: swap even one of the three out
        # and it's a different exposure worth re-flagging.
        "fingerprint": "clientes:" + ",".join(sorted(n for n, _ in top3)),
        "titulo": _t("core.opn.conc_t", lang),
        "monto": monto,
        # P30·A2 — el $ es FACTURACIÓN de 12 meses, NO deuda: la etiqueta lo dice
        # (la deuda total de la cartera es otra magnitud, $311,4M).
        "monto_label": _t("core.opn.conc_monto_label", lang),
        "datos": {"pct_top3": round(pct, 1), "clientes": [n for n, _ in top3],
                  "facturacion_total_12m": round(total, 2)},
        "resumen": _t("core.opn.conc_r", lang, pct=f"{pct:.0f}",
                      monto=_pesos(monto, lang)),
        "accion_chat": _t("core.opn.conc_chat", lang),
        "navegar": "cuentas",
        "fuentes": [_t("core.opn.f_cuentas", lang), _t("core.opn.f_movs", lang)],
    }
    # Piece 4 — el matiz de Aldo: son los que pagan en fecha, el riesgo es de
    # concentración, no de cobro. Reencuadra la card sin cambiar el número.
    asunciones = [ins.assumption(_t("core.opn.conc_s1", lang))]
    k_conc = [p for p in conocimiento.aplicables(nodo="clientes", efecto="contexto_para_angela")
              if p.get("ambito") == "global" and (p.get("params") or {}).get("marca") == "concentracion"]
    if k_conc:
        asunciones.append(ins.assumption(
            _t("core.opn.k_ensenaste", lang, texto=conocimiento.texto_en(k_conc[0], lang))))
        card["conocimiento_aplicado"] = [conocimiento.resumen_pieza(p) for p in k_conc]
    insight_val = ins.build(
        pattern=ins.pattern(_t("core.opn.conc_q1", lang, pct=f"{pct:.0f}",
                               monto=_pesos(monto, lang)),
                            scope={"kind": "clients", "count": 3}),
        evidence=[
            ins.metric("client_concentration_pct", label=f"{pct:.0f}%", value=round(pct, 1),
                       unit="pct", weight="primary",
                       method={"key": "core.method.client_concentration",
                               "label": _t("core.method.client_concentration", lang)}),
            ins.records("top_clients", label=_t("core.opn.conc_t", lang), weight="primary",
                        rows=[ins.record(kind="client", id=ctx["client_id_by_name"].get(n),
                                         name=n, amount=round(v, 2),
                                         detail=_t("core.opn.conc_i", lang,
                                                   pct=f"{v / total * 100:.0f}"))
                              for n, v in top3],
                        method={"key": "core.method.client_concentration",
                                "label": _t("core.method.client_concentration", lang)}),
            ins.series("client_share_chart", label=_t("core.opn.conc_g", lang), chart=grafico,
                       weight="supporting",
                       method={"key": "core.method.client_concentration",
                               "label": _t("core.method.client_concentration", lang)}),
        ],
        assumptions=asunciones,
        risk=ins.risk(_t("core.opn.conc_q2", lang), exposure=monto),
        recommendation=ins.recommendation(
            _t("core.opn.conc_t", lang), navigate="cuentas",
            chat=_t("core.opn.conc_chat", lang)),
    )
    card["insight"] = insight_val
    card["drill"] = _project_drill(insight_val)  # TEMPORARY, see _project_drill
    return card


# --- 9 · margen bajo ---------------------------------------------------------------

def _card_margen_bajo(lang, ctx) -> dict | None:
    """Productos activos con margen anómalamente bajo vs SU categoría (PVP vs
    costo, dato existente). Solo si el cálculo cierra con ventas reales."""
    import i18n
    from . import analisis
    rot = analisis.rotacion(lang)
    if not rot.get("disponible"):
        return None
    det = {x["producto"]: x for x in rot.get("detalle") or []}
    por_cat: dict[str, list] = {}
    for a in ctx["arts"]:
        if not a.get("pvp") or not a.get("costo_iva"):
            continue
        m = (a["pvp"] - a["costo_iva"]) / a["pvp"] * 100
        por_cat.setdefault(a.get("tipo") or "?", []).append((a, m))
    UMBRAL_PP = 6.0
    bajos = []
    ganancia_total = 0.0
    peor = None   # el que más lejos está del promedio de SU grupo
    for cat, items in por_cat.items():
        if len(items) < 5:
            continue
        prom = sum(m for _, m in items) / len(items)
        for a, m in items:
            if m >= prom - UMBRAL_PP or m < 0:
                continue
            d = det.get(a["descripcion"])
            if not d or not d.get("unidades_12m"):
                continue
            u_mes = d["unidades_12m"] / 12
            pvp_obj = a["costo_iva"] / (1 - prom / 100)
            extra_mes = u_mes * (pvp_obj - a["pvp"])
            if extra_mes <= 0:
                continue
            ganancia_total += extra_mes
            bajos.append({"id": a.get("codigo"), "kind": "product",
                          "nombre": a["descripcion"], "monto": round(extra_mes, 2),
                          "detalle": _t("core.opn.margen_i", lang, m=f"{m:.1f}",
                                        prom=f"{prom:.1f}",
                                        cat=i18n.categoria(cat, lang))})
            if peor is None or (prom - m) > peor["brecha"]:
                peor = {"producto": a["descripcion"], "margen": m, "prom": prom,
                        "cat": cat, "brecha": prom - m, "pvp": a["pvp"],
                        "pvp_objetivo": pvp_obj, "extra_mes": extra_mes}
    if not bajos:
        return None
    bajos.sort(key=lambda x: -x["monto"])
    grafico = _grafico(_t("core.opn.margen_g", lang),
                       [{"x": b["nombre"], "y": b["monto"]} for b in bajos[:6]],
                       "$", False)
    # P38·C — la card NOMBRA al producto: "estás vendiendo X con Y% de margen,
    # muy por debajo del Z% promedio de su grupo". Un conteo no mueve a nadie;
    # un producto con nombre y apellido sí. El resto queda en los involucrados.
    cat_disp = i18n.categoria(peor["cat"], lang)
    otros = len(bajos) - 1
    insight_val = ins.build(
        pattern=ins.pattern(_t("core.opn.margen_p0", lang, producto=peor["producto"],
                               m=f"{peor['margen']:.1f}", prom=f"{peor['prom']:.1f}",
                               cat=cat_disp),
                            scope={"kind": "product", "count": 1}),
        evidence=[
            ins.metric("margin_gap_pct", label=f"{peor['margen']:.1f}%", value=round(peor["margen"], 1),
                       unit="pct", weight="primary",
                       baseline={"value": round(peor["prom"], 1),
                                 "label": _t("core.opn.margen_prom_label", lang)},
                       method={"key": "core.method.margin_gap",
                               "label": _t("core.method.margin_gap", lang)}),
            ins.metric("extra_profit_monthly",
                       label=_t("core.opn.margen_p2", lang, pvp=_pesos(peor["pvp"], lang),
                                objetivo=_pesos(peor["pvp_objetivo"], lang),
                                extra=_pesos(peor["extra_mes"], lang)),
                       value=peor["extra_mes"], unit="ars", weight="primary",
                       method={"key": "core.method.margin_extra_profit",
                               "label": _t("core.method.margin_extra_profit", lang)}),
            ins.metric("extra_profit_total",
                       label=_t("core.opn.margen_p1", lang, n=len(bajos),
                                extra=_pesos(ganancia_total, lang)),
                       value=ganancia_total, unit="ars", weight="supporting",
                       method={"key": "core.method.margin_extra_total",
                               "label": _t("core.method.margin_extra_total", lang)}),
            ins.records("low_margin_products", label=_t("core.opn.margen_t2", lang,
                                                         producto=peor["producto"],
                                                         m=f"{peor['margen']:.1f}"),
                        weight="supporting",
                        rows=[ins.record(kind=b["kind"], id=b["id"], name=b["nombre"],
                                         amount=b["monto"], detail=b["detalle"])
                              for b in bajos[:8]],
                        method={"key": "core.method.margin_extra_total",
                                "label": _t("core.method.margin_extra_total", lang)}),
            ins.series("margin_chart", label=_t("core.opn.margen_g", lang), chart=grafico,
                       weight="supporting",
                       method={"key": "core.method.margin_extra_total",
                               "label": _t("core.method.margin_extra_total", lang)}),
        ],
        assumptions=[ins.assumption(_t("core.opn.margen_s1", lang))],
        recommendation=ins.recommendation(
            _t("core.opn.margen_t2", lang, producto=peor["producto"], m=f"{peor['margen']:.1f}"),
            navigate="inventario",
            chat=_t("core.opn.margen_chat2", lang, producto=peor["producto"])),
    )
    return {
        "id": "margen_bajo", "tipo": "ajustar_precio",
        "fingerprint": f"producto:{peor['producto']}",
        "titulo": _t("core.opn.margen_t2", lang, producto=peor["producto"],
                     m=f"{peor['margen']:.1f}"),
        "monto": round(ganancia_total, 2),
        "datos": {"producto": peor["producto"], "margen_pct": round(peor["margen"], 1),
                  "promedio_grupo_pct": round(peor["prom"], 1), "grupo": peor["cat"],
                  "productos_bajos": len(bajos)},
        "resumen": _t("core.opn.margen_r2", lang, prom=f"{peor['prom']:.1f}",
                      cat=cat_disp, n=otros) if otros > 0
                   else _t("core.opn.margen_r2_solo", lang, prom=f"{peor['prom']:.1f}",
                           cat=cat_disp),
        "accion_chat": _t("core.opn.margen_chat2", lang, producto=peor["producto"]),
        "navegar": "inventario",
        "fuentes": [_t("core.opn.f_costos", lang), _t("core.opn.f_ventas12", lang)],
        "insight": insight_val,
        "drill": _project_drill(insight_val),  # TEMPORARY, see _project_drill
    }


# --- 10 · sobrecompra: la oferta que te la vas a comer -------------------------------

def _card_sobrecompra(lang, ctx) -> dict | None:
    """P38·D — el error más caro del rubro: entrar a una oferta del proveedor
    sin mirar la rotación. El descuento es real; el problema es la cantidad.

    Cruce: oferta × rotación real × vencimiento del lote ofrecido. Lo que podés
    absorber es lo que vendés HASTA que ese lote venza, menos lo que ya tenés.
    El resto no es stock: es mercadería que vas a tirar con 18% de descuento."""
    from . import pricing, reposicion
    if not ctx["ventas_ok"]:
        return None
    hoy = ctx["hoy"]
    por_codigo = {a.get("codigo"): a for a in ctx["arts"]}
    mejor = None
    for of in reposicion.ofertas():
        vence_of = of.get("vence_oferta") or ""
        if vence_of and vence_of < hoy.isoformat():
            continue  # oferta caída: no se muestra una decisión que ya no existe
        a = por_codigo.get(of.get("codigo"))
        if not a or not a.get("costo_iva"):
            continue
        _cob, ritmo = _cobertura(a, ctx)
        if ritmo <= 0:
            continue
        try:
            vto = datetime.date.fromisoformat(of["vencimiento_lote"])
        except Exception:  # noqa: BLE001
            continue
        dias_vida = max(0, (vto - hoy).days)
        cantidad = float(of.get("cantidad") or 0)
        if cantidad <= 0:
            continue
        stock = max(0.0, float(a.get("stock") or 0))
        # lo que sí podés vender de ESA compra antes de que el lote se venza
        absorbible = max(0.0, ritmo * dias_vida - stock)
        sobrante = max(0.0, cantidad - absorbible)
        if sobrante <= 0:
            continue  # la oferta entra entera: no hay nada que advertir
        desc = float(of.get("descuento_pct") or 0)
        costo_of = a["costo_iva"] * (1 - desc / 100)
        candidato = {
            "of": of, "a": a, "ritmo": ritmo, "cantidad": cantidad,
            "dias_vida": dias_vida, "absorbible": absorbible, "sobrante": sobrante,
            "desc": desc, "tirar": round(sobrante * costo_of, 2),
            "ahorro": round(absorbible * a["costo_iva"] * desc / 100, 2),
        }
        if mejor is None or candidato["tirar"] > mejor["tirar"]:
            mejor = candidato
    if not mejor:
        return None

    a, of = mejor["a"], mejor["of"]
    prod = a.get("descripcion")
    prov = of.get("proveedor") or a.get("proveedor") or ""
    por_peso = pricing.es_por_peso(a)
    unidad = _t("core.opn.qi_u_kg" if por_peso else "core.opn.qi_u_unidades", lang)
    u_mes = mejor["ritmo"] * 30.44
    meses = mejor["cantidad"] / u_mes if u_mes else 0
    # En piezas, que es como se pide de verdad ("3 planchas", no "89 kg").
    pieza = a.get("valor_peso") if por_peso else None
    piezas_of = of.get("piezas")
    piezas_sug = round(mejor["absorbible"] / pieza) if pieza else None
    sug_txt = _num(round(mejor["absorbible"], 1), lang) + f" {unidad}"
    if piezas_sug:
        sug_txt += _t("core.opn.sobre_piezas", lang, n=_num(piezas_sug, lang))
    oferta_txt = _num(mejor["cantidad"], lang) + f" {unidad}"
    if piezas_of:
        oferta_txt += _t("core.opn.sobre_piezas", lang, n=_num(piezas_of, lang))

    propuesta = {
        "tipo": "orden_compra",
        "titulo": _t("core.opn.sobre_prop_t", lang),
        "detalle": _t("core.opn.sobre_prop_d", lang, sug=sug_txt,
                      producto=prod, proveedor=prov, oferta=oferta_txt),
        "codigo": a.get("codigo"), "producto": prod, "proveedor": prov,
        "cantidad": round(mejor["absorbible"], 1),
    }
    grafico = _grafico(
        _t("core.opn.sobre_g", lang, unidad=unidad),
        [{"x": _t("core.opn.sobre_g_oferta", lang), "y": round(mejor["cantidad"], 1)},
         {"x": _t("core.opn.sobre_g_vendible", lang), "y": round(mejor["absorbible"], 1)},
         {"x": _t("core.opn.sobre_g_stock", lang), "y": round(max(0.0, a.get("stock") or 0), 1)}],
        unidad, False)
    insight_val = ins.build(
        pattern=ins.pattern(_t("core.opn.sobre_q1", lang, proveedor=prov, oferta=oferta_txt,
                               producto=prod, desc=f"{mejor['desc']:g}"),
                            scope={"kind": "product", "count": 1}),
        hypothesis=ins.hypothesis(_t("core.opn.sobre_q2", lang, u=_num(round(u_mes, 1), lang),
                                     unidad=unidad, meses=f"{meses:.0f}", dias=mejor["dias_vida"])),
        evidence=[
            ins.metric("waste_value",
                       label=_t("core.opn.sobre_q3", lang,
                                sobrante=_num(round(mejor["sobrante"], 1), lang),
                                unidad=unidad, tirar=_pesos(mejor["tirar"], lang)),
                       value=mejor["tirar"], unit="ars", weight="primary",
                       method={"key": "core.method.overbuy_waste",
                               "label": _t("core.method.overbuy_waste", lang)}),
            ins.metric("discount_savings",
                       label=_t("core.opn.sobre_q4", lang, sug=sug_txt,
                                ahorro=_pesos(mejor["ahorro"], lang)),
                       value=mejor["ahorro"], unit="ars", weight="supporting",
                       method={"key": "core.method.overbuy_savings",
                               "label": _t("core.method.overbuy_savings", lang)}),
            ins.series("overbuy_chart", label=_t("core.opn.sobre_g", lang, unidad=unidad),
                       chart=grafico, weight="supporting",
                       method={"key": "core.method.overbuy_waste",
                               "label": _t("core.method.overbuy_waste", lang)}),
        ],
        assumptions=[ins.assumption(_t("core.opn.sobre_s1", lang, fecha=of.get("vencimiento_lote"))),
                     ins.assumption(_t("core.opn.qi_s1", lang))],
        recommendation=ins.recommendation(
            _t("core.opn.sobre_t", lang, proveedor=prov, producto=prod, desc=f"{mejor['desc']:g}"),
            proposal=propuesta, navigate="inventario",
            chat=_t("core.opn.sobre_chat", lang, producto=prod)),
    )
    return {
        "id": "sobrecompra", "tipo": "comprar",
        "fingerprint": f"producto:{prod}:proveedor:{prov}",
        "titulo": _t("core.opn.sobre_t", lang, proveedor=prov, producto=prod,
                     desc=f"{mejor['desc']:g}"),
        "monto": mejor["tirar"],
        "monto_label": _t("core.opn.sobre_monto_label", lang),
        "datos": {"producto": prod, "proveedor": prov, "oferta": mejor["cantidad"],
                  "descuento_pct": mejor["desc"], "meses_para_venderlo": round(meses, 1),
                  "cantidad_sugerida": round(mejor["absorbible"], 1),
                  "dias_vida_lote": mejor["dias_vida"]},
        "resumen": _t("core.opn.sobre_r", lang, meses=f"{meses:.0f}",
                      dias=mejor["dias_vida"], sug=sug_txt),
        "accion_chat": _t("core.opn.sobre_chat", lang, producto=prod),
        "navegar": "inventario",
        "fuentes": [_t("core.opn.f_oferta", lang), _t("core.opn.f_ventas12", lang),
                    _t("core.opn.f_vida_util", lang)],
        "propuesta": propuesta,
        "insight": insight_val,
        "drill": _project_drill(insight_val),  # TEMPORARY, see _project_drill
    }


# --- el set, cerrado -----------------------------------------------------------------

TIPOS_VALIDOS = ("cobrar", "liquidar", "ajustar_precio", "comprar",
                 "vender", "planificar", "diversificar")

# P30·A1 — la NATURALEZA de cada hallazgo: la fuente única para que ninguna
# pantalla sume magnitudes incompatibles (el bug del "$900M").
#   · recuperable = capital de trabajo que se convierte en liquidez, HOMOGÉNEO
#     y sumable entre sí (cobranza vencida + capital dormido liberable +
#     ahorro de compras). ESTE es el único grupo que se suma.
#   · accionable  = tiene $ y acción pero magnitud/ventana distinta (protección
#     de venta, ganancia recurrente, facturación perdida): se muestra, no se suma.
#   · riesgo      = EXPOSICIÓN, no plata (facturación concentrada): jamás en una
#     suma de plata capturable — compite en su propia liga.
NATURALEZA = {
    "cobrar_morosos": "recuperable",
    "despertar_dormido": "recuperable",
    "ventana_compra": "recuperable",
    "concentracion": "riesgo",
    # P38·D — sobrecompra es PÉRDIDA EVITADA, no capital que se libera: se
    # muestra y se acciona, pero jamás entra en la suma de capital recuperable.
    "sobrecompra": "accionable",
    # el resto: accionable (default)
}

# P43·C3 — DE QUIÉN ES CADA HALLAZGO.
#
# El problema que esto arregla: al encargado de depósito le llegaban las mismas
# nueve tarjetas que al dueño, incluidas "cobrá los $85,7M de morosos" y "3
# clientes concentran $470,8M". Eso no es información para alguien que recibe
# mercadería: es ruido, y encima es plata de la que no tiene por qué enterarse.
#
# La regla NO es una lista de usernames: cada tarjeta declara los MÓDULOS que hay
# que tener para verla, en el mismo vocabulario de «Quién ve qué» (auth.MODULOS).
# Si el rol no tiene el módulo, la tarjeta no existe para él. Así, cuando el dueño
# le habilita un módulo a alguien, los hallazgos de ese dominio aparecen solos —
# sin tocar código.
#
# Se piden TODOS los módulos de la tupla, y ahí está el matiz que importa:
#   · `cuentas` sola  → el preventista ve la cobranza de sus clientes (es su trabajo).
#   · `cuentas` + `oportunidades` → la EXPOSICIÓN global del negocio es una
#     lectura de estrategia, no de gestión diaria: sólo la ve quien administra el
#     negocio, no quien lo ejecuta.
#   · `inventario` sola → "se te está por acabar esto" es operativo: lo ve el
#     depósito, que es quien lo repone.
#   · `inventario` + `oportunidades` → comprar, liquidar, mover precios y planificar
#     temporada son DECISIONES de compra: del dueño y de quien compra, no del que
#     descarga el camión.
DOMINIO = {
    "cobrar_morosos":    ("cuentas",),
    "cliente_frio":      ("cuentas",),
    "concentracion":     ("cuentas", "oportunidades"),
    "quiebre_inminente": ("inventario",),
    "despertar_dormido": ("inventario", "oportunidades"),
    "ventana_compra":    ("inventario", "oportunidades"),
    "estrella_caida":    ("inventario", "oportunidades"),
    "pre_pico":          ("inventario", "oportunidades"),
    "margen_bajo":       ("inventario", "oportunidades"),
    "sobrecompra":       ("inventario", "oportunidades"),
}


def recuperable(cards_: list[dict] | None = None, lang: str | None = None) -> dict:
    """EL capital recuperable — el número del guion, calculado en un solo lugar.

    P45·T2 — el mapa mostraba «$156,3M de capital recuperable» sumando en el
    cliente las tarjetas de naturaleza `recuperable`, y Ángela no tenía forma de
    llegar a ese número: si le preguntaban, contestaba con el capital dormido o
    con la plata de datos sucios, y ninguno era el del mapa. Ahora la suma vive
    acá y las dos pantallas leen de la misma función.

    Qué entra y qué no lo decide `NATURALEZA`, no esta función: sólo lo
    `recuperable` es homogéneo y sumable (cobranza vencida + capital dormido
    liberable + ahorro de compra). La exposición de clientes es riesgo y la
    sobrecompra es pérdida evitada: se muestran, no se suman. Esa distinción es
    la que evitó el «$900M» de doble conteo, y se respeta acá."""
    import i18n
    cards_ = cards(lang) if cards_ is None else cards_
    partes = [c for c in cards_ if c.get("naturaleza") == "recuperable"]
    partes.sort(key=lambda c: -(c.get("monto") or 0))
    total = round(sum(c.get("monto") or 0 for c in partes), 2)
    return {
        "disponible": bool(partes),
        "total": total,
        # `total` a secas no entra en las claves de plata genéricas (en otras
        # tools es un conteo), así que lo formatea la dueña del número.
        "total_fmt": i18n.pesos(total, lang),
        "componentes": [{"id": c["id"], "titulo": c.get("titulo"),
                         "monto": c.get("monto"), "tipo": c.get("tipo")}
                        for c in partes],
        "excluidos": [{"id": c["id"], "titulo": c.get("titulo"),
                       "monto": c.get("monto"), "naturaleza": c.get("naturaleza"),
                       "motivo": c.get("monto_label")}
                      for c in cards_ if c.get("naturaleza") != "recuperable"
                      and (c.get("monto") or 0) > 0],
    }


def visibles_para(cards_: list[dict], features) -> list[dict]:
    """Las tarjetas que le corresponden a un rol, por sus módulos.

    Se aplica DESPUÉS del cache a propósito: el cálculo es uno solo y sigue
    siendo el canónico (el dueño ve el set completo, los tests lo fijan); lo que
    cambia por persona es qué se le muestra, no qué se calcula. Filtrar adentro
    del cache guardaría el recorte del primero que preguntó.

    Una tarjeta sin dominio declarado NO se muestra: si mañana se agrega un
    hallazgo y nadie dijo de quién es, el default seguro es no filtrarlo a
    quien no corresponde. Hay un test que lo exige declarado."""
    feats = set(features or ())
    return [c for c in cards_
            if set(DOMINIO.get(c.get("id"), ("__sin_dominio__",))) <= feats]


# El orden importa: estrella_caida ANTES que quiebre_inminente (marca su
# producto en ctx["excluir"] para que dos cards no repitan el mismo ítem).
_SET = (_card_morosos, _card_dormido, _card_ventana_compra, _card_cliente_frio,
        _card_estrella_caida, _card_quiebre_inminente, _card_pre_pico,
        _card_concentracion, _card_margen_bajo, _card_sobrecompra)


def cards(lang: str | None = None) -> list[dict]:
    from . import pattern_feedback
    ctx = _ctx(lang)
    out = []
    for fn in _SET:
        try:
            c = fn(lang, ctx)
        except Exception:  # noqa: BLE001 — una card rota no tira la sección
            c = None
        if c:
            c["naturaleza"] = NATURALEZA.get(c["id"], "accionable")
            out.append(c)
    out = pattern_feedback.drop_handled(out)
    out.sort(key=lambda c: -(c.get("monto") or 0))
    return out


def record_feedback(card_id: str, action: str, *, actor: str,
                    note: str | None = None, lang: str | None = None) -> dict:
    """The owner's reaction (accepted/dismissed/already knew) to one of the
    cards above, via the SAME mechanism core/patrones.py uses
    (core/pattern_feedback.py) — the closed set stays closed and hand-coded;
    only the "don't show me this exact instance again" memory is shared."""
    from . import pattern_feedback
    return pattern_feedback.record(lambda: cards(lang), card_id, action,
                                   actor=actor, note=note)
