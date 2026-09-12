"""
Prioridades — the ranked “what should I do now” inbox.

Composes opportunity cards (`oportunidades_neg`), business-alert signals
(ported from the old frontend centroAlertas), and floor reports (`piso`).
Merges duplicate facts, splits act vs watch, ranks, then filters by the
caller’s modules. Ángela and every UI read this; they do not re-sort.
"""
from __future__ import annotations

from . import oportunidades_neg as opn
from . import patrones

# Alert id → opportunity id when both describe the same fact.
MERGE_INTO = {
    "morosos": "cobrar_morosos",
    "moroso_atraso": "cobrar_morosos",
    "quiebre": "quiebre_inminente",
    "pico": "pre_pico",
}

DROP_IDS = frozenset({"solicitud_pendiente"})

# Sort first within `act` (stop the leak today).
LEAK_TODAY = frozenset({
    "cobrar_morosos", "morosos", "moroso_atraso",
    "quiebre_inminente", "quiebre",
    "venc_riesgo", "dep_vencidos", "pago_vencido",
})

# Informational / exposure — own heading, does not compete with `act`.
WATCH_IDS = frozenset({
    "concentracion", "cheques", "caja_inusual", "caida_interanual", "pico",
})

ALERT_MODULOS = {
    "morosos": ("cuentas",),
    "moroso_atraso": ("cuentas",),
    "quiebre": ("inventario",),
    "pico": ("inventario", "oportunidades"),
    "pago_vencido": ("finanzas",),
    "pago_semana": ("finanzas",),
    "cheques": ("finanzas",),
    "dep_vencidos": ("deposito",),
    "dep_porvencer": ("deposito",),
    "dep_discrep": ("deposito",),
    "venc_riesgo": ("deposito",),
    "costo_viejo": ("inventario",),
    "caja_inusual": ("caja",),
    "caida_interanual": ("evolucion",),
}

CHIP_BY_TIPO = {
    "cobrar": "core.prio.chip_cobrar",
    "liquidar": "core.prio.chip_liquidar",
    "ajustar_precio": "core.prio.chip_precio",
    "comprar": "core.prio.chip_comprar",
    "vender": "core.prio.chip_vender",
    "planificar": "core.prio.chip_planificar",
    "diversificar": "core.prio.chip_riesgo",
    "reclamar": "core.prio.chip_equipo",
    "revisar": "core.prio.chip_revisar",
}

CHIP_BY_ID = {
    "quiebre_inminente": "core.prio.chip_reponer",
    "quiebre": "core.prio.chip_reponer",
    "concentracion": "core.prio.chip_riesgo",
    "caida_interanual": "core.prio.chip_riesgo",
}

# Canonical action key for chips, filters and icons (one fact → one verb).
ACTION_BY_ID = {
    "quiebre_inminente": "reponer",
    "quiebre": "reponer",
    "concentracion": "diversificar",
    "caida_interanual": "diversificar",
    "morosos": "cobrar",
    "moroso_atraso": "cobrar",
    "pago_vencido": "pagar",
    "pago_semana": "pagar",
    "cheques": "ver",
    "caja_inusual": "ver",
    "dep_vencidos": "deposito",
    "dep_porvencer": "deposito",
    "dep_discrep": "deposito",
    "venc_riesgo": "deposito",
    "costo_viejo": "ajustar_precio",
    "pico": "planificar",
}


def _t(key: str, lang: str | None = None, **params) -> str:
    import i18n
    return i18n.t(key, lang, **params)


def _pesos(n, lang) -> str:
    import i18n
    return i18n.pesos(n or 0, lang)


def _num(x, lang) -> str:
    v = float(x or 0)
    crudo = f"{v:,.0f}" if abs(v - round(v)) < 0.05 else f"{v:,.1f}"
    if lang == "en":
        return crudo
    return crudo.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _safe(fn):
    try:
        return fn()
    except Exception:  # noqa: BLE001 — one broken signal must not kill the inbox
        return None


def _blank_drill():
    return {"porque": [], "grafico": None, "involucrados": [], "supuestos": []}


def _grafico(nombre: str, puntos: list[dict], unidad: str, temporal: bool,
             ventana: str = "") -> dict:
    """Contract P21 (consulta-serie) — same shape as oportunidades_neg._grafico,
    duplicated locally: priorities.py composes alerts standalone and
    shouldn't reach into opn's private helpers."""
    return {"ok": True, "series": [{"nombre": nombre, "puntos": puntos}],
            "meta": {"unidad": unidad, "temporal": temporal, "ventana": ventana,
                     "composicion": False, "deflactado": False}}


def _deposito_lot_value(rows: list[dict]) -> list[dict]:
    """Deposito rows (vencidos()/vencimientos()) don't carry cost — join
    with the article catalog so each lot's peso value can drive a chart and
    a monto on its involucrado row."""
    from . import store
    costo_by_codigo = {a.get("codigo"): a.get("costo_iva") or 0
                       for a in store.raw_actual()}
    out = []
    for f in rows:
        costo = costo_by_codigo.get(f.get("codigo"), 0)
        out.append({**f, "valor": round(float(f.get("cantidad") or 0) * costo, 2)})
    return out


def _item(*, id, tono, chip, titulo, resumen, origen, modulos, lang=None,
          monto=None, monto_label=None, cifra_texto=None, fuentes=None,
          navegar=None, accion_chat=None, propuesta=None, piso=False,
          macro=None, naturaleza=None, tipo=None, drill=None, reportes=None):
    return {
        "id": id,
        "tono": tono,
        "chip": chip,
        "titulo": titulo,
        "resumen": resumen,
        "monto": monto,
        "monto_label": monto_label,
        "cifra_texto": cifra_texto,
        "fuentes": fuentes or [],
        "origen": list(origen),
        "navegar": navegar,
        "accion_chat": accion_chat,
        "propuesta": propuesta,
        "piso": bool(piso),
        "macro": macro,
        "naturaleza": naturaleza,
        "tipo": ACTION_BY_ID.get(id) or tipo,
        "modulos": tuple(modulos),
        "drill": drill or _blank_drill(),
        "reportes": reportes,
        "band": None,
    }


def _chip(card_or_id, lang, tipo=None) -> str:
    cid = card_or_id if isinstance(card_or_id, str) else card_or_id.get("id")
    tipo = tipo or (card_or_id.get("tipo") if isinstance(card_or_id, dict) else None)
    key = CHIP_BY_ID.get(cid) or CHIP_BY_TIPO.get(tipo) or "core.prio.chip_ver"
    return _t(key, lang)


def merge_duplicates(items: list[dict]) -> list[dict]:
    """One fact, one card. Drop twins when the canonical opportunity exists."""
    by_id: dict[str, dict] = {}
    order: list[str] = []
    for it in items:
        cid = it["id"]
        if cid in DROP_IDS:
            continue
        if cid in by_id:
            by_id[cid] = _combine(by_id[cid], it)
            continue
        by_id[cid] = dict(it)
        order.append(cid)
    for src, dst in MERGE_INTO.items():
        if src in by_id and dst in by_id:
            by_id[dst] = _combine(by_id[dst], by_id.pop(src))
            order = [i for i in order if i != src]
    return [by_id[i] for i in order if i in by_id]


def _combine(keep: dict, extra: dict) -> dict:
    origen = list(dict.fromkeys(
        (keep.get("origen") or []) + (extra.get("origen") or [])))
    tono = "rojo" if "rojo" in (keep.get("tono"), extra.get("tono")) else keep.get("tono")
    drill = dict(keep.get("drill") or _blank_drill())
    extra_drill = extra.get("drill") or {}
    extra_p = extra_drill.get("porque") or []
    if extra_p:
        seen = set(drill.get("porque") or [])
        porque = list(drill.get("porque") or [])
        for p in extra_p:
            if p not in seen:
                porque.append(p)
                seen.add(p)
        drill["porque"] = porque
    if not drill.get("grafico") and extra_drill.get("grafico"):
        drill["grafico"] = extra_drill["grafico"]
    extra_inv = extra_drill.get("involucrados") or []
    if extra_inv and not (drill.get("involucrados") or []):
        drill["involucrados"] = extra_inv
    out = dict(keep)
    out["origen"] = origen
    out["tono"] = tono
    out["drill"] = drill
    return out


def split_and_rank(items: list[dict]) -> tuple[list[dict], list[dict]]:
    act, watch = [], []
    for it in items:
        band = "watch" if _is_watch(it) else "act"
        row = dict(it)
        row["band"] = band
        (watch if band == "watch" else act).append(row)

    def act_key(it):
        leak = 0 if it["id"] in LEAK_TODAY else 1
        has_monto = 0 if (it.get("monto") or 0) > 0 else 1
        return (leak, has_monto, -(it.get("monto") or 0))

    act.sort(key=act_key)
    watch.sort(key=lambda i: -(i.get("monto") or 0))
    return act, watch


def _is_watch(it: dict) -> bool:
    if it.get("naturaleza") == "riesgo":
        return True
    return it["id"] in WATCH_IDS


def badge_of(inbox: dict) -> int:
    return len(inbox.get("act") or [])


def visibles_para(items: list[dict], features) -> list[dict]:
    if features is None:
        return list(items)
    feats = set(features)
    return [c for c in items
            if set(c.get("modulos") or ("__sin_dominio__",)) <= feats]


def inbox(lang: str | None = None, features=None) -> dict:
    from . import analisis_cache
    composed = analisis_cache.get_o_computar(
        "prioridades", lang, lambda: _compose(lang))
    items = visibles_para(list(composed["items"]), features)
    act, watch = split_and_rank(items)
    return {
        "act": act,
        "watch": watch,
        "badge": len(act),
        "hay_ventas": bool(composed.get("hay_ventas")),
        # Same items already carry `naturaleza` from the opportunity cards, so
        # this reuses the one canonical sum (opn.recuperable) instead of
        # re-filtering/summing here — that duplication is what caused the
        # "$900M" double-counting bug (see opn.recuperable's docstring).
        # Computed post-`visibles_para` so a role only sees its own exposure.
        "recuperable": opn.recuperable(cards_=items, lang=lang),
    }


def _compose(lang) -> dict:
    from . import confidence
    items: list[dict] = []
    items.extend(_opportunity_items(lang))
    items.extend(_pattern_items(lang))
    items.extend(_drop_alerts_for_handled_destinations(_alert_items(lang)))
    items.extend(_piso_items(lang))
    merged = merge_duplicates(items)
    for it in merged:
        it["drill"]["confidence"] = confidence.level_for(it["drill"], lang)
    hay_ventas = False
    try:
        from . import ventas
        hay_ventas = bool(ventas.hay_datos() and ventas.montos_confirmados())
    except Exception:  # noqa: BLE001
        hay_ventas = False
    return {"items": merged, "hay_ventas": hay_ventas}


def _drop_alerts_for_handled_destinations(alert_items: list[dict]) -> list[dict]:
    """A raw alert (e.g. "morosos") normally disappears by MERGING into its
    oportunidad ("cobrar_morosos", via MERGE_INTO) whenever both exist in the
    same request. Once the owner gives feedback on that oportunidad
    (core/pattern_feedback.py) it stops existing at all — with nothing left
    to merge into, the alert would resurface UNMERGED, undoing the very
    thing the owner just said. Drop it too: it's the same underlying fact,
    just from a code path pattern_feedback doesn't fingerprint on its own."""
    from core.db import pattern_feedback_repo
    from core.db import tenant as _tenant
    try:
        handled = pattern_feedback_repo.latest_by_fingerprint(_tenant.current_tenant_id())
    except Exception:  # noqa: BLE001 — a lookup failure must not hide every alert
        return alert_items
    handled_ids = {key.split(":", 1)[0] for key in handled}
    return [it for it in alert_items if MERGE_INTO.get(it["id"], it["id"]) not in handled_ids]


def _opportunity_items(lang) -> list[dict]:
    out = []
    for c in _safe(lambda: opn.cards(lang)) or []:
        out.append(_item(
            id=c["id"],
            tono="oro" if c.get("naturaleza") == "riesgo" else "salvia",
            chip=_chip(c, lang),
            titulo=c["titulo"],
            resumen=c.get("resumen") or "",
            origen=[f"oportunidad:{c['id']}"],
            modulos=opn.DOMINIO.get(c["id"], ("__sin_dominio__",)),
            monto=c.get("monto"),
            monto_label=c.get("monto_label"),
            fuentes=c.get("fuentes") or [],
            navegar=c.get("navegar"),
            accion_chat=c.get("accion_chat"),
            propuesta=c.get("propuesta"),
            macro=c.get("macro"),
            naturaleza=c.get("naturaleza"),
            tipo=c.get("tipo"),
            drill=c.get("drill") or _blank_drill(),
        ))
    return out


def _pattern_items(lang) -> list[dict]:
    """Continuous learning (core/patrones.py) — findings no standard report
    summarizes because they're a correlation, not a single number. Same card
    shape as an opportunity; they enter the inbox as one more source."""
    out = []
    for c in _safe(lambda: patrones.cards(lang)) or []:
        out.append(_item(
            id=c["id"],
            tono="oro" if c.get("naturaleza") == "riesgo" else "salvia",
            chip=_chip(c, lang),
            titulo=c["titulo"],
            resumen=c.get("resumen") or "",
            origen=[f"patron:{c['id']}"],
            modulos=patrones.MODULES_BY_ID.get(c["id"], ("__sin_dominio__",)),
            monto=c.get("monto"),
            monto_label=c.get("monto_label"),
            fuentes=c.get("fuentes") or [],
            navegar=c.get("navegar"),
            accion_chat=c.get("accion_chat"),
            naturaleza=c.get("naturaleza"),
            tipo=c.get("tipo"),
            drill=c.get("drill") or _blank_drill(),
        ))
    return out


def _piso_items(lang) -> list[dict]:
    from . import piso
    out = []
    for c in _safe(lambda: piso.propuestas(lang)) or []:
        out.append(_item(
            id=c["id"],
            tono="azul",
            chip=_t("core.prio.chip_equipo", lang),
            titulo=c["titulo"],
            resumen=c.get("resumen") or "",
            origen=["piso:" + c["id"]],
            modulos=("alertas",),
            monto=c.get("monto"),
            fuentes=c.get("fuentes") or [],
            navegar=None,
            accion_chat=c.get("accion_chat"),
            piso=True,
            tipo=c.get("tipo"),
            drill=c.get("drill") or _blank_drill(),
            reportes=c.get("reportes"),
        ))
    return out


def _alert_items(lang) -> list[dict]:
    out: list[dict] = []
    out.extend(_safe(lambda: _alerts_cuentas(lang)) or [])
    out.extend(_safe(lambda: _alerts_ventas(lang)) or [])
    out.extend(_safe(lambda: _alerts_pagos(lang)) or [])
    out.extend(_safe(lambda: _alerts_deposito(lang)) or [])
    out.extend(_safe(lambda: _alerts_inventario(lang)) or [])
    out.extend(_safe(lambda: _alerts_caja(lang)) or [])
    out.extend(_safe(lambda: _alerts_evolucion(lang)) or [])
    out.extend(_safe(lambda: _alerts_pico(lang)) or [])
    return out


def _alerts_cuentas(lang) -> list[dict]:
    from . import cuentas
    out = []
    al = cuentas.alertas()
    if al.get("cantidad"):
        out.append(_item(
            id="morosos", tono="rojo", chip=_t("core.prio.chip_cobrar", lang),
            titulo=_t("core.prio.morosos_t", lang),
            resumen=_t("core.prio.morosos_r", lang, n=_num(al["cantidad"], lang),
                       monto=_pesos(al["impacto_pesos"], lang)),
            origen=["alerta:morosos"], modulos=ALERT_MODULOS["morosos"],
            monto=al["impacto_pesos"],
            fuentes=[_t("core.prio.f_cuentas", lang)],
            navegar="cuentas",
            accion_chat=_t("core.prio.morosos_chat", lang),
            drill={"porque": [_t("core.prio.morosos_p", lang, n=_num(al["cantidad"], lang),
                                 monto=_pesos(al["impacto_pesos"], lang))],
                   "grafico": None, "involucrados": [], "supuestos": []},
        ))
    atrasados = [c for c in cuentas.listar()
                 if c.get("en_mora") and (c.get("atraso_vs_promedio") or 0) >= 80]
    if atrasados:
        d = max(atrasados, key=lambda c: c.get("atraso_vs_promedio") or 0)
        out.append(_item(
            id="moroso_atraso", tono="rojo", chip=_t("core.prio.chip_cobrar", lang),
            titulo=_t("core.prio.atraso_t", lang, nombre=d["nombre"]),
            resumen=_t("core.prio.atraso_r", lang, dias=_num(d["dias_sin_pagar"], lang),
                       atraso=_num(d["atraso_vs_promedio"], lang)),
            origen=["alerta:moroso_atraso"], modulos=ALERT_MODULOS["moroso_atraso"],
            monto=d.get("saldo"),
            fuentes=[_t("core.prio.f_cuentas", lang)],
            navegar="cuentas",
            accion_chat=_t("core.prio.atraso_chat", lang, nombre=d["nombre"]),
            drill={"porque": [_t("core.prio.atraso_p", lang, nombre=d["nombre"],
                                 dias=_num(d["dias_sin_pagar"], lang),
                                 prom=_num(d.get("promedio_pago_dias") or 0, lang))],
                   "grafico": None, "involucrados": [], "supuestos": []},
        ))
    return out


def _alerts_ventas(lang) -> list[dict]:
    from . import ventas
    pan = ventas.panorama(lang)
    if not pan.get("disponible"):
        return []
    q = pan.get("quiebre") or {}
    if not q.get("cantidad"):
        return []
    return [_item(
        id="quiebre", tono="rojo", chip=_t("core.prio.chip_reponer", lang),
        titulo=_t("core.prio.quiebre_t", lang),
        resumen=_t("core.prio.quiebre_r", lang, n=_num(q["cantidad"], lang)),
        origen=["alerta:quiebre"], modulos=ALERT_MODULOS["quiebre"],
        cifra_texto=_num(q["cantidad"], lang),
        fuentes=[_t("core.prio.f_stock", lang), _t("core.prio.f_ventas", lang)],
        navegar="inventario",
        accion_chat=_t("core.prio.quiebre_chat", lang),
        drill={"porque": [_t("core.prio.quiebre_p", lang, n=_num(q["cantidad"], lang))],
               "grafico": None, "involucrados": [], "supuestos": []},
    )]


def _alerts_pagos(lang) -> list[dict]:
    from . import pagos
    pv = pagos.resumen()
    out = []
    if pv.get("pagos_vencidos"):
        out.append(_item(
            id="pago_vencido", tono="rojo", chip=_t("core.prio.chip_pagar", lang),
            titulo=_t("core.prio.pago_vencido_t", lang),
            resumen=_t("core.prio.pago_vencido_r", lang,
                       n=_num(pv["pagos_vencidos"], lang),
                       monto=_pesos(pv["vencidos_total"], lang)),
            origen=["alerta:pago_vencido"], modulos=ALERT_MODULOS["pago_vencido"],
            monto=pv["vencidos_total"],
            fuentes=[_t("core.prio.f_finanzas", lang)],
            navegar="finanzas",
            accion_chat=_t("core.prio.pago_vencido_chat", lang),
            drill={"porque": [_t("core.prio.pago_vencido_p", lang,
                                 n=_num(pv["pagos_vencidos"], lang))],
                   "grafico": None, "involucrados": [], "supuestos": []},
        ))
    if pv.get("por_pagar_semana"):
        out.append(_item(
            id="pago_semana", tono="azul", chip=_t("core.prio.chip_pagar", lang),
            titulo=_t("core.prio.pago_semana_t", lang),
            resumen=_t("core.prio.pago_semana_r", lang,
                       monto=_pesos(pv["por_pagar_semana"], lang)),
            origen=["alerta:pago_semana"], modulos=ALERT_MODULOS["pago_semana"],
            monto=pv["por_pagar_semana"],
            fuentes=[_t("core.prio.f_finanzas", lang)],
            navegar="finanzas",
            accion_chat=_t("core.prio.pago_semana_chat", lang),
            drill=_blank_drill(),
        ))
    if pv.get("cheques_cartera"):
        out.append(_item(
            id="cheques", tono="azul", chip=_t("core.prio.chip_ver", lang),
            titulo=_t("core.prio.cheques_t", lang),
            resumen=_t("core.prio.cheques_r", lang,
                       n=_num(pv["cheques_cartera"], lang),
                       monto=_pesos(pv["cheques_total"], lang)),
            origen=["alerta:cheques"], modulos=ALERT_MODULOS["cheques"],
            monto=pv["cheques_total"],
            fuentes=[_t("core.prio.f_finanzas", lang)],
            navegar="finanzas",
            accion_chat=_t("core.prio.cheques_chat", lang),
            drill=_blank_drill(),
        ))
    return out


def _alerts_deposito(lang) -> list[dict]:
    from . import deposito, vencimientos
    out = []
    dep = deposito.resumen()
    if dep.get("vencidos"):
        lotes = sorted(_deposito_lot_value(deposito.vencidos()),
                       key=lambda x: -x["valor"])[:8]
        out.append(_item(
            id="dep_vencidos", tono="rojo", chip=_t("core.prio.chip_deposito", lang),
            titulo=_t("core.prio.dep_vencidos_t", lang),
            resumen=_t("core.prio.dep_vencidos_r", lang, n=_num(dep["vencidos"], lang)),
            origen=["alerta:dep_vencidos"], modulos=ALERT_MODULOS["dep_vencidos"],
            cifra_texto=_num(dep["vencidos"], lang),
            monto=round(sum(x["valor"] for x in lotes), 2),
            fuentes=[_t("core.prio.f_deposito", lang)],
            navegar="deposito",
            accion_chat=_t("core.prio.dep_vencidos_chat", lang),
            drill={
                "porque": [_t("core.prio.dep_vencidos_p", lang, n=_num(dep["vencidos"], lang),
                              monto=_pesos(sum(x["valor"] for x in lotes), lang))],
                "grafico": _grafico(_t("core.prio.dep_vencidos_g", lang),
                                    [{"x": x.get("producto") or "", "y": x["valor"]}
                                     for x in lotes], "$", False),
                "involucrados": [{"id": x.get("codigo"), "kind": "product",
                                  "nombre": x.get("producto") or "", "monto": x["valor"],
                                  "detalle": _t("core.prio.dep_vencidos_i", lang,
                                                dias=x.get("dias_vencido") or 0)}
                                 for x in lotes],
                "supuestos": [_t("core.prio.dep_vencidos_s", lang)],
            },
        ))
    if dep.get("por_vencer"):
        lotes = sorted(_deposito_lot_value(deposito.vencimientos()),
                       key=lambda x: -x["valor"])[:8]
        out.append(_item(
            id="dep_porvencer", tono="oro", chip=_t("core.prio.chip_deposito", lang),
            titulo=_t("core.prio.dep_porvencer_t", lang),
            resumen=_t("core.prio.dep_porvencer_r", lang, n=_num(dep["por_vencer"], lang)),
            origen=["alerta:dep_porvencer"], modulos=ALERT_MODULOS["dep_porvencer"],
            cifra_texto=_num(dep["por_vencer"], lang),
            monto=round(sum(x["valor"] for x in lotes), 2),
            fuentes=[_t("core.prio.f_deposito", lang)],
            navegar="deposito",
            accion_chat=_t("core.prio.dep_porvencer_chat", lang),
            drill={
                "porque": [_t("core.prio.dep_porvencer_p", lang, n=_num(dep["por_vencer"], lang))],
                "grafico": _grafico(_t("core.prio.dep_porvencer_g", lang),
                                    [{"x": x.get("producto") or "", "y": x["valor"]}
                                     for x in lotes], "$", False),
                "involucrados": [{"id": x.get("codigo"), "kind": "product",
                                  "nombre": x.get("producto") or "", "monto": x["valor"],
                                  "detalle": _t("core.prio.dep_porvencer_i", lang,
                                                dias=x.get("dias_restantes") or 0)}
                                 for x in lotes],
                "supuestos": [_t("core.prio.dep_vencidos_s", lang)],
            },
        ))
    if dep.get("discrepancias"):
        out.append(_item(
            id="dep_discrep", tono="oro", chip=_t("core.prio.chip_deposito", lang),
            titulo=_t("core.prio.dep_discrep_t", lang),
            resumen=_t("core.prio.dep_discrep_r", lang, n=_num(dep["discrepancias"], lang)),
            origen=["alerta:dep_discrep"], modulos=ALERT_MODULOS["dep_discrep"],
            cifra_texto=_num(dep["discrepancias"], lang),
            fuentes=[_t("core.prio.f_deposito", lang)],
            navegar="deposito",
            accion_chat=_t("core.prio.dep_discrep_chat", lang),
            drill=_blank_drill(),
        ))
    venc = vencimientos.en_riesgo(30, lang)
    if venc.get("disponible") and venc.get("lotes_en_riesgo"):
        items = sorted(venc.get("items") or [], key=lambda x: -x["plata_en_riesgo"])[:8]
        top = items[0]
        out.append(_item(
            id="venc_riesgo", tono="rojo", chip=_t("core.prio.chip_deposito", lang),
            titulo=_t("core.prio.venc_riesgo_t", lang, n=_num(venc["lotes_en_riesgo"], lang)),
            resumen=_t("core.prio.venc_riesgo_r", lang,
                       producto=top.get("producto") or "",
                       dias=_num(top.get("dias_restantes") or 0, lang),
                       monto=_pesos(venc.get("total_en_riesgo") or 0, lang)),
            origen=["alerta:venc_riesgo"], modulos=ALERT_MODULOS["venc_riesgo"],
            monto=venc.get("total_en_riesgo"),
            fuentes=[_t("core.prio.f_deposito", lang), _t("core.prio.f_ventas", lang)],
            navegar="deposito",
            accion_chat=_t("core.prio.venc_riesgo_chat", lang),
            drill={
                "porque": [_t("core.prio.venc_riesgo_p", lang,
                              n=_num(venc["lotes_en_riesgo"], lang),
                              monto=_pesos(venc.get("total_en_riesgo") or 0, lang))],
                "grafico": _grafico(_t("core.prio.venc_riesgo_g", lang),
                                    [{"x": x.get("producto") or "", "y": x["plata_en_riesgo"]}
                                     for x in items], "$", False),
                "involucrados": [{"id": x.get("codigo"), "kind": "product",
                                  "nombre": x.get("producto") or "",
                                  "monto": x["plata_en_riesgo"],
                                  "detalle": _t("core.prio.venc_riesgo_i", lang,
                                                dias=x.get("dias_restantes") or 0)}
                                 for x in items],
                "supuestos": [_t("core.prio.venc_riesgo_s", lang)],
            },
        ))
    return out


def _alerts_inventario(lang) -> list[dict]:
    from . import store
    cv = (store.panorama().get("alertas") or {}).get("costo_viejo") or {}
    if not cv.get("cantidad"):
        return []
    return [_item(
        id="costo_viejo", tono="oro", chip=_t("core.prio.chip_precio", lang),
        titulo=_t("core.prio.costo_viejo_t", lang),
        resumen=_t("core.prio.costo_viejo_r", lang, n=_num(cv["cantidad"], lang)),
        origen=["alerta:costo_viejo"], modulos=ALERT_MODULOS["costo_viejo"],
        cifra_texto=_num(cv["cantidad"], lang),
        fuentes=[_t("core.prio.f_costos", lang)],
        navegar="inventario",
        accion_chat=_t("core.prio.costo_viejo_chat", lang),
        drill=_blank_drill(),
    )]


def _alerts_caja(lang) -> list[dict]:
    from . import caja
    cj = caja.estado()
    tot = (cj.get("totales") or {}).get("total") or 0
    hist = [h for h in (cj.get("historial") or []) if (h.get("total") or 0) > 0]
    if not (cj.get("abierta") and tot > 0 and len(hist) >= 5):
        return []
    prom = sum(h["total"] for h in hist) / len(hist)
    desvio = abs(tot - prom) / prom if prom else 0
    if desvio <= 0.4:
        return []
    return [_item(
        id="caja_inusual", tono="oro", chip=_t("core.prio.chip_ver", lang),
        titulo=_t("core.prio.caja_t", lang),
        resumen=_t("core.prio.caja_r", lang, total=_pesos(tot, lang),
                   prom=_pesos(prom, lang)),
        origen=["alerta:caja_inusual"], modulos=ALERT_MODULOS["caja_inusual"],
        monto=tot,
        fuentes=[_t("core.prio.f_caja", lang)],
        navegar="caja",
        accion_chat=_t("core.prio.caja_chat", lang),
        drill=_blank_drill(),
    )]


def _alerts_evolucion(lang) -> list[dict]:
    from . import evolucion
    pan = evolucion.panorama(lang)
    if pan.get("hay_datos") is False:
        return []
    out = []
    for a in evolucion.alertas_de(pan, lang):
        out.append(_item(
            id="caida_interanual", tono="rojo", chip=_t("core.prio.chip_riesgo", lang),
            titulo=a["titulo"],
            resumen=a["detalle"],
            origen=["alerta:caida_interanual"],
            modulos=ALERT_MODULOS["caida_interanual"],
            fuentes=[_t("core.prio.f_ventas", lang)],
            navegar="evolucion",
            accion_chat=_t("core.prio.caida_chat", lang),
            drill=_blank_drill(),
        ))
    return out


def _alerts_pico(lang) -> list[dict]:
    from . import analisis
    est = analisis.estacionalidad(lang)
    if not est.get("disponible"):
        return []
    pico = (est.get("proximos_picos") or [None])[0]
    if not pico:
        return []
    return [_item(
        id="pico", tono="azul", chip=_t("core.prio.chip_planificar", lang),
        titulo=_t("core.prio.pico_t", lang),
        resumen=pico.get("aviso") or "",
        origen=["alerta:pico"], modulos=ALERT_MODULOS["pico"],
        cifra_texto=f"×{pico.get('indice')}",
        fuentes=[_t("core.prio.f_ventas", lang)],
        navegar="evolucion",
        accion_chat=_t("core.prio.pico_chat", lang, cat=pico.get("categoria") or ""),
        drill={"porque": [_t("core.prio.pico_p", lang, mes=pico.get("mes") or "",
                             cat=pico.get("categoria") or "")],
               "grafico": None, "involucrados": [], "supuestos": []},
    )]
