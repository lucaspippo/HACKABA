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


def _blank_insight():
    from . import insight
    return insight.blank()


def _legacy_drill(ins: dict) -> dict:
    """TEMPORARY one-way projection of an insight back into the old `drill`
    shape, so the untouched frontend keeps rendering while the builders
    migrate. Nothing is dual-authored: builders only ever write insights and
    this derives from them. DELETE once CardNegocio.jsx reads `insight`
    (see docs/superpowers/plans/2026-09-01-structured-insight-contract.md,
    Task 13)."""
    ev = ins.get("evidence") or []
    porque = [p["label"] for p in (ins.get("pattern"), ins.get("hypothesis")) if p]
    porque += [e["label"] for e in ev if e["weight"] == "primary"]
    chart = next((e["chart"] for e in ev if e.get("chart")), None)
    involucrados = [
        {"id": r["id"], "kind": r["kind"], "nombre": r["name"],
         "monto": r["amount"], "detalle": r["detail"]}
        for e in ev for r in (e.get("records") or [])
    ]
    conf = ins.get("confidence") or {}
    return {
        "porque": porque,
        "grafico": chart,
        "involucrados": involucrados,
        "supuestos": [a["label"] for a in (ins.get("assumptions") or [])],
        "confidence": conf.get("data"),
    }


def _insight_from_legacy_drill(drill: dict) -> dict:
    """TEMPORARY reverse shim: wrap a not-yet-migrated builder's `drill` into a
    minimal insight, so builders can migrate one task at a time instead of all
    ~25 in a single commit. The pattern is the drill's first prose line; the
    rest become supporting metrics with no value, which is honest — legacy
    prose has no raw number to recover.

    DELETE with `_legacy_drill` and the `drill=` keyword (Task 13)."""
    from . import insight as ins
    porque = list(drill.get("porque") or [])
    evidence = []
    if drill.get("grafico"):
        evidence.append(ins.series("legacy_chart", label=porque[0] if porque else "",
                                   chart=drill["grafico"],
                                   method={"key": "core.method.legacy", "label": ""}))
    if drill.get("involucrados"):
        evidence.append(ins.records(
            "legacy_records", label="",
            rows=[ins.record(kind=iv.get("kind"), id=iv.get("id"),
                             name=iv.get("nombre") or "", amount=iv.get("monto"),
                             detail=iv.get("detalle"))
                  for iv in drill["involucrados"]],
            method={"key": "core.method.legacy", "label": ""}))
    return ins.build(
        pattern=ins.pattern(porque[0]) if porque else None,
        evidence=evidence,
        assumptions=[ins.assumption(s) for s in (drill.get("supuestos") or [])],
    )


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
          macro=None, naturaleza=None, tipo=None, drill=None, insight=None,
          reportes=None):
    # `insight=` is the real keyword; `drill=` is transitional and still
    # used by every not-yet-migrated builder (Tasks 5-9). `_legacy_drill`
    # keeps the untouched frontend fed until Task 13 removes both shims.
    resolved_insight = insight or (
        _insight_from_legacy_drill(drill) if drill else _blank_insight())
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
        "insight": resolved_insight,
        "drill": _legacy_drill(resolved_insight),  # TEMPORARY, Task 13
        "reportes": reportes,
        "band": None,
        "action_taken": None,
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
    """One fact, one card. Evidence unions by stable `id`, so two builders
    describing the same number in different words can no longer both survive
    — which is exactly what string de-duplication failed to prevent."""
    origen = list(dict.fromkeys(
        (keep.get("origen") or []) + (extra.get("origen") or [])))
    tono = "rojo" if "rojo" in (keep.get("tono"), extra.get("tono")) else keep.get("tono")
    out = dict(keep)
    out["origen"] = origen
    out["tono"] = tono
    out["insight"] = _merge_insights(keep.get("insight") or _blank_insight(),
                                     extra.get("insight") or _blank_insight())
    out["drill"] = _legacy_drill(out["insight"])  # TEMPORARY, Task 13
    return out


def _merge_insights(keep: dict, extra: dict) -> dict:
    """The canonical card's reading wins; the twin only contributes evidence
    and caveats it uniquely has."""
    merged = dict(keep)
    by_id = {e["id"]: dict(e) for e in keep.get("evidence") or []}
    order = [e["id"] for e in keep.get("evidence") or []]
    for e in extra.get("evidence") or []:
        if e["id"] not in by_id:
            by_id[e["id"]] = dict(e)
            order.append(e["id"])
        elif e["weight"] == "primary":
            # Load-bearing beats supporting; the twin may know better.
            by_id[e["id"]]["weight"] = "primary"
    merged["evidence"] = [by_id[i] for i in order]

    for key in ("assumptions", "alternatives", "falsifiers"):
        seen, rows = set(), []
        for row in (keep.get(key) or []) + (extra.get(key) or []):
            if row["label"] in seen:
                continue
            seen.add(row["label"])
            rows.append(row)
        merged[key] = rows

    # pattern / hypothesis / risk / recommendation / deadline: keep the
    # canonical card's. Concatenating two readings of one fact is what
    # produced the duplicated prose this contract replaces.
    return merged


def split_and_rank(items: list[dict]) -> tuple[list[dict], list[dict]]:
    act, watch = [], []
    for it in items:
        band = "watch" if _is_watch(it) else "act"
        row = dict(it)
        row["band"] = band
        (watch if band == "watch" else act).append(row)

    def act_key(it):
        # Executed cards stay visible but sink below open work.
        done = 1 if it.get("action_taken") else 0
        leak = 0 if it["id"] in LEAK_TODAY else 1
        has_monto = 0 if (it.get("monto") or 0) > 0 else 1
        return (done, leak, has_monto, -(it.get("monto") or 0))

    act.sort(key=act_key)
    watch.sort(key=lambda i: -(i.get("monto") or 0))
    return act, watch


def _is_watch(it: dict) -> bool:
    if it.get("naturaleza") == "riesgo":
        return True
    return it["id"] in WATCH_IDS


def badge_of(inbox: dict) -> int:
    """Open work only — a card whose proposal was already executed is done,
    and counting it would keep nagging about finished work."""
    return sum(1 for c in (inbox.get("act") or []) if not c.get("action_taken"))


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
    # `composed` comes out of a PROCESS-LIFETIME cache (core/analisis_cache.py),
    # so `action_taken` cannot be derived inside `_compose`: the first request
    # would freeze "not done yet" into the cache and approving would never show
    # up until the process restarted. Derive it here, per request, on shallow
    # COPIES — with_action_taken() writes in place, and mutating the cached
    # dicts would put the stale value straight back into the global cache.
    # Cost is at most two small SELECTs (only quiebre_inminente and sobrecompra
    # carry a proposal), and it is what makes cancelling an order release the
    # card on the next load.
    items = [dict(c) for c in visibles_para(list(composed["items"]), features)]
    with_action_taken(items)
    act, watch = split_and_rank(items)
    return {
        "act": act,
        "watch": watch,
        "badge": badge_of({"act": act}),
        "hay_ventas": bool(composed.get("hay_ventas")),
        # Same items already carry `naturaleza` from the opportunity cards, so
        # this reuses the one canonical sum (opn.recuperable) instead of
        # re-filtering/summing here — that duplication is what caused the
        # "$900M" double-counting bug (see opn.recuperable's docstring).
        # Computed post-`visibles_para` so a role only sees its own exposure.
        "recuperable": opn.recuperable(cards_=items, lang=lang),
    }


def with_action_taken(items: list[dict]) -> list[dict]:
    """Mark each card whose proposal already produced a real record.

    Derived per request from the domain table (see core/proposal_state.py),
    so every user sees the same answer and a reload never resurrects a
    proposal somebody already approved.
    """
    from . import proposal_state
    for it in items:
        it["action_taken"] = proposal_state.for_proposal(it.get("propuesta"), it["id"])
    return items


URGENCY_THIS_WEEK_DAYS = 7


def _derive(item: dict, lang) -> None:
    """Fill the insight fields that need the finished insight (and the
    tenant's team) rather than one builder's local knowledge."""
    from . import confidence, insight_owner
    ins = item["insight"]
    ins["confidence"] = confidence.split_for(ins, lang)
    ins["owner"] = insight_owner.suggest(item.get("modulos") or ())
    if ins.get("risk"):
        ins["risk"]["level"] = _risk_level(item, ins["risk"].get("exposure"))
    if ins.get("deadline"):
        ins["deadline"]["urgency"] = _urgency(ins["deadline"].get("date"))
    item["drill"] = _legacy_drill(ins)  # TEMPORARY, Task 13


def _risk_level(item: dict, exposure) -> str:
    """A leak-today card is high risk by definition; otherwise exposure
    decides. Watch-band cards are never high: that band exists precisely
    because they are not dispatchable work today."""
    if item["id"] in LEAK_TODAY:
        return "high"
    if _is_watch(item):
        return "low" if not exposure else "medium"
    return "medium" if exposure else "low"


def _urgency(date: str | None) -> str | None:
    if not date:
        return None
    from datetime import date as _date
    from . import fechas
    today = fechas.hoy()
    try:
        due = _date.fromisoformat(date[:10])
    except ValueError:
        return None
    days = (due - today).days
    if days < 0:
        return "overdue"
    if days == 0:
        return "today"
    if days <= URGENCY_THIS_WEEK_DAYS:
        return "this_week"
    return "later"


def _compose(lang) -> dict:
    items: list[dict] = []
    items.extend(_opportunity_items(lang))
    items.extend(_pattern_items(lang))
    items.extend(_drop_alerts_for_handled_destinations(_alert_items(lang)))
    items.extend(_piso_items(lang))
    merged = merge_duplicates(items)
    for it in merged:
        _derive(it, lang)
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
    from . import cuentas, insight as ins
    out = []
    al = cuentas.alertas()
    if al.get("cantidad"):
        morosos = [c for c in cuentas.listar() if c.get("en_mora")]
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
            insight=ins.build(
                pattern=ins.pattern(_t("core.prio.morosos_p", lang,
                                       n=_num(al["cantidad"], lang),
                                       monto=_pesos(al["impacto_pesos"], lang)),
                                    scope={"kind": "clients", "count": al["cantidad"]}),
                hypothesis=ins.hypothesis(_t("core.prio.morosos_hyp", lang)),
                evidence=[
                    ins.metric("overdue_total",
                               label=_pesos(al["impacto_pesos"], lang),
                               value=al["impacto_pesos"], unit="ars", weight="primary",
                               method={"key": "core.method.mora_total",
                                       "label": _t("core.method.mora_total", lang)}),
                    ins.records("overdue_clients",
                                label=_t("core.prio.morosos_t", lang),
                                weight="primary",
                                rows=[ins.record(kind="client", id=c.get("id"),
                                                 name=c["nombre"], amount=c.get("saldo"))
                                      for c in morosos[:8]],
                                method={"key": "core.method.mora_total",
                                        "label": _t("core.method.mora_total", lang)}),
                ],
                assumptions=[ins.assumption(_t("core.prio.mora_sup", lang),
                                            if_wrong=_t("core.prio.mora_sup_if", lang))],
                risk=ins.risk(_t("core.prio.mora_risk", lang),
                              exposure=al["impacto_pesos"]),
                recommendation=ins.recommendation(
                    _t("core.prio.morosos_t", lang), navigate="cuentas",
                    chat=_t("core.prio.morosos_chat", lang)),
            ),
        ))
    atrasados = [c for c in cuentas.listar()
                 if c.get("en_mora") and (c.get("atraso_vs_promedio") or 0) >= 80]
    if atrasados:
        d = max(atrasados, key=lambda c: c.get("atraso_vs_promedio") or 0)
        prom = d.get("promedio_pago_dias") or 0
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
            insight=ins.build(
                pattern=ins.pattern(_t("core.prio.atraso_p", lang, nombre=d["nombre"],
                                       dias=_num(d["dias_sin_pagar"], lang),
                                       prom=_num(prom, lang)),
                                    scope={"kind": "client", "count": 1}),
                hypothesis=ins.hypothesis(_t("core.prio.atraso_hyp", lang,
                                             nombre=d["nombre"])),
                evidence=[
                    ins.metric("days_overdue",
                               label=_t("core.prio.atraso_r", lang,
                                        dias=_num(d["dias_sin_pagar"], lang),
                                        atraso=_num(d["atraso_vs_promedio"], lang)),
                               value=d["dias_sin_pagar"], unit="days", weight="primary",
                               baseline={"value": prom,
                                         "label": _t("core.method.prom_pago", lang)},
                               method={"key": "core.method.dias_mora",
                                       "label": _t("core.method.dias_mora", lang)},
                               records=[ins.record(kind="client", id=d.get("id"),
                                                   name=d["nombre"], amount=d.get("saldo"),
                                                   detail=_t("core.prio.atraso_i", lang,
                                                             dias=d["dias_sin_pagar"]))]),
                ],
                assumptions=[ins.assumption(_t("core.prio.mora_sup", lang),
                                            if_wrong=_t("core.prio.mora_sup_if", lang))],
                alternatives=[ins.caveat(_t("core.prio.atraso_alt", lang))],
                falsifiers=[ins.caveat(_t("core.prio.atraso_fals", lang))],
                risk=ins.risk(_t("core.prio.mora_risk", lang), exposure=d.get("saldo")),
                recommendation=ins.recommendation(
                    _t("core.prio.atraso_t", lang, nombre=d["nombre"]),
                    navigate="cuentas",
                    chat=_t("core.prio.atraso_chat", lang, nombre=d["nombre"])),
            ),
        ))
    return out


def _alerts_ventas(lang) -> list[dict]:
    from . import ventas, insight as ins
    pan = ventas.panorama(lang)
    if not pan.get("disponible"):
        return []
    q = pan.get("quiebre") or {}
    if not q.get("cantidad"):
        return []
    items = (q.get("items") or [])[:8]
    metodo = {"key": "core.method.quiebre_conteo",
              "label": _t("core.method.quiebre_conteo", lang)}
    return [_item(
        id="quiebre", tono="rojo", chip=_t("core.prio.chip_reponer", lang),
        titulo=_t("core.prio.quiebre_t", lang),
        resumen=_t("core.prio.quiebre_r", lang, n=_num(q["cantidad"], lang)),
        origen=["alerta:quiebre"], modulos=ALERT_MODULOS["quiebre"],
        cifra_texto=_num(q["cantidad"], lang),
        fuentes=[_t("core.prio.f_stock", lang), _t("core.prio.f_ventas", lang)],
        navegar="inventario",
        accion_chat=_t("core.prio.quiebre_chat", lang),
        insight=ins.build(
            pattern=ins.pattern(_t("core.prio.quiebre_p", lang,
                                   n=_num(q["cantidad"], lang)),
                                scope={"kind": "products", "count": q["cantidad"]}),
            hypothesis=ins.hypothesis(_t("core.prio.quiebre_hyp", lang)),
            evidence=[
                ins.metric("stockout_count", label=_num(q["cantidad"], lang),
                           value=q["cantidad"], unit="products", weight="primary",
                           method=metodo),
                ins.records("stockout_items", label=_t("core.prio.quiebre_t", lang),
                            weight="primary",
                            rows=[ins.record(kind="product", id=x.get("codigo"),
                                             name=x.get("descripcion") or "",
                                             detail=_t("core.prio.quiebre_i", lang,
                                                       dias=x.get("dias_cobertura") or 0))
                                  for x in items],
                            method=metodo),
            ],
            risk=ins.risk(_t("core.prio.quiebre_risk", lang)),
            recommendation=ins.recommendation(
                _t("core.prio.quiebre_t", lang), navigate="inventario",
                chat=_t("core.prio.quiebre_chat", lang)),
        ),
    )]


def _alerts_pagos(lang) -> list[dict]:
    from . import pagos, insight as ins
    pv = pagos.resumen()
    out = []
    if pv.get("pagos_vencidos"):
        items = pagos.pagos_vencidos()[:8]
        metodo = {"key": "core.method.payables_overdue",
                  "label": _t("core.method.payables_overdue", lang)}
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
            insight=ins.build(
                pattern=ins.pattern(_t("core.prio.pago_vencido_p", lang,
                                       n=_num(pv["pagos_vencidos"], lang)),
                                    scope={"kind": "payables", "count": pv["pagos_vencidos"]}),
                evidence=[
                    ins.metric("payables_overdue_total",
                               label=_pesos(pv["vencidos_total"], lang),
                               value=pv["vencidos_total"], unit="ars", weight="primary",
                               method=metodo),
                    ins.records("payables_overdue_rows",
                                label=_t("core.prio.pago_vencido_t", lang),
                                weight="primary",
                                rows=[ins.record(kind=None, id=None,
                                                 name=f"{x.get('proveedor') or ''} {x.get('numero') or ''}".strip(),
                                                 amount=x.get("monto"),
                                                 detail=_t("core.prio.pago_vencido_i", lang,
                                                           dias=x.get("dias_vencido") or 0))
                                      for x in items],
                                method=metodo),
                    ins.series("payables_overdue_chart",
                               label=_t("core.prio.pago_vencido_g", lang),
                               chart=_grafico(_t("core.prio.pago_vencido_g", lang),
                                             [{"x": x.get("proveedor") or "", "y": x.get("monto") or 0}
                                              for x in items], "$", False),
                               method=metodo),
                ],
                risk=ins.risk(_t("core.prio.pago_vencido_risk", lang),
                              exposure=pv["vencidos_total"]),
                recommendation=ins.recommendation(
                    _t("core.prio.pago_vencido_t", lang), navigate="finanzas",
                    chat=_t("core.prio.pago_vencido_chat", lang)),
            ),
        ))
    if pv.get("por_pagar_semana"):
        items = pagos.pagos_por_vencer(7)[:8]
        metodo = {"key": "core.method.payables_week",
                  "label": _t("core.method.payables_week", lang)}
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
            insight=ins.build(
                pattern=ins.pattern(_t("core.prio.pago_semana_p", lang,
                                       monto=_pesos(pv["por_pagar_semana"], lang))),
                evidence=[
                    ins.metric("payables_week_total",
                               label=_pesos(pv["por_pagar_semana"], lang),
                               value=pv["por_pagar_semana"], unit="ars", weight="primary",
                               method=metodo),
                    ins.records("payables_week_rows",
                                label=_t("core.prio.pago_semana_t", lang),
                                weight="primary",
                                rows=[ins.record(kind=None, id=None,
                                                 name=f"{x.get('proveedor') or ''} {x.get('numero') or ''}".strip(),
                                                 amount=x.get("monto"),
                                                 detail=_t("core.prio.pago_semana_i", lang,
                                                           dias=x.get("dias_restantes") or 0))
                                      for x in items],
                                method=metodo),
                    ins.series("payables_week_chart",
                               label=_t("core.prio.pago_semana_g", lang),
                               chart=_grafico(_t("core.prio.pago_semana_g", lang),
                                             [{"x": x.get("proveedor") or "", "y": x.get("monto") or 0}
                                              for x in items], "$", False),
                               method=metodo),
                ],
                risk=ins.risk(_t("core.prio.pago_semana_risk", lang),
                              exposure=pv["por_pagar_semana"]),
                recommendation=ins.recommendation(
                    _t("core.prio.pago_semana_t", lang), navigate="finanzas",
                    chat=_t("core.prio.pago_semana_chat", lang)),
            ),
        ))
    if pv.get("cheques_cartera"):
        items = pagos.cheques_en_cartera()[:8]
        metodo = {"key": "core.method.checks", "label": _t("core.method.checks", lang)}
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
            insight=ins.build(
                pattern=ins.pattern(_t("core.prio.cheques_p", lang,
                                       n=_num(pv["cheques_cartera"], lang),
                                       monto=_pesos(pv["cheques_total"], lang)),
                                    scope={"kind": "checks", "count": pv["cheques_cartera"]}),
                evidence=[
                    ins.metric("checks_total", label=_pesos(pv["cheques_total"], lang),
                               value=pv["cheques_total"], unit="ars", weight="primary",
                               method=metodo),
                    ins.records("checks_rows", label=_t("core.prio.cheques_t", lang),
                                weight="primary",
                                rows=[ins.record(kind=None, id=None,
                                                 name=f"{x.get('cliente') or ''} {x.get('numero') or ''}".strip(),
                                                 amount=x.get("monto"),
                                                 detail=_t("core.prio.cheques_i", lang,
                                                           banco=x.get("banco") or ""))
                                      for x in items],
                                method=metodo),
                    ins.series("checks_chart", label=_t("core.prio.cheques_g", lang),
                               chart=_grafico(_t("core.prio.cheques_g", lang),
                                             [{"x": x.get("cliente") or "", "y": x.get("monto") or 0}
                                              for x in items], "$", False),
                               method=metodo),
                ],
                risk=ins.risk(_t("core.prio.cheques_risk", lang), exposure=pv["cheques_total"]),
                recommendation=ins.recommendation(
                    _t("core.prio.cheques_t", lang), navigate="finanzas",
                    chat=_t("core.prio.cheques_chat", lang)),
            ),
        ))
    return out


def _alerts_deposito(lang) -> list[dict]:
    from . import deposito, vencimientos, insight as ins
    out = []
    dep = deposito.resumen()
    if dep.get("vencidos"):
        valuados = _deposito_lot_value(deposito.vencidos())
        total_valor = round(sum(x["valor"] for x in valuados), 2)
        lotes = sorted(valuados, key=lambda x: -x["valor"])[:8]
        metodo = {"key": "core.method.expired_lots", "label": _t("core.method.expired_lots", lang)}
        out.append(_item(
            id="dep_vencidos", tono="rojo", chip=_t("core.prio.chip_deposito", lang),
            titulo=_t("core.prio.dep_vencidos_t", lang),
            resumen=_t("core.prio.dep_vencidos_r", lang, n=_num(dep["vencidos"], lang)),
            origen=["alerta:dep_vencidos"], modulos=ALERT_MODULOS["dep_vencidos"],
            cifra_texto=_num(dep["vencidos"], lang),
            monto=total_valor,
            fuentes=[_t("core.prio.f_deposito", lang)],
            navegar="deposito",
            accion_chat=_t("core.prio.dep_vencidos_chat", lang),
            insight=ins.build(
                pattern=ins.pattern(_t("core.prio.dep_vencidos_p", lang, n=_num(dep["vencidos"], lang),
                                       monto=_pesos(total_valor, lang)),
                                    scope={"kind": "products", "count": dep["vencidos"]}),
                evidence=[
                    ins.metric("expired_lots_value", label=_pesos(total_valor, lang),
                               value=total_valor, unit="ars", weight="primary", method=metodo),
                    ins.records("expired_lots", label=_t("core.prio.dep_vencidos_t", lang),
                                weight="primary",
                                rows=[ins.record(kind="product", id=x.get("codigo"),
                                                 name=x.get("producto") or "", amount=x["valor"],
                                                 detail=_t("core.prio.dep_vencidos_i", lang,
                                                           dias=x.get("dias_vencido") or 0))
                                      for x in lotes],
                                method=metodo),
                    ins.series("expired_lots_chart", label=_t("core.prio.dep_vencidos_g", lang),
                               chart=_grafico(_t("core.prio.dep_vencidos_g", lang),
                                             [{"x": x.get("producto") or "", "y": x["valor"]}
                                              for x in lotes], "$", False),
                               method=metodo),
                ],
                assumptions=[ins.assumption(_t("core.prio.dep_vencidos_s", lang))],
                risk=ins.risk(_t("core.prio.dep_vencidos_risk", lang), exposure=total_valor),
                recommendation=ins.recommendation(
                    _t("core.prio.dep_vencidos_t", lang), navigate="deposito",
                    chat=_t("core.prio.dep_vencidos_chat", lang)),
            ),
        ))
    if dep.get("por_vencer"):
        valuados = _deposito_lot_value(deposito.vencimientos())
        total_valor = round(sum(x["valor"] for x in valuados), 2)
        lotes = sorted(valuados, key=lambda x: -x["valor"])[:8]
        metodo = {"key": "core.method.expiring_lots", "label": _t("core.method.expiring_lots", lang)}
        out.append(_item(
            id="dep_porvencer", tono="oro", chip=_t("core.prio.chip_deposito", lang),
            titulo=_t("core.prio.dep_porvencer_t", lang),
            resumen=_t("core.prio.dep_porvencer_r", lang, n=_num(dep["por_vencer"], lang)),
            origen=["alerta:dep_porvencer"], modulos=ALERT_MODULOS["dep_porvencer"],
            cifra_texto=_num(dep["por_vencer"], lang),
            monto=total_valor,
            fuentes=[_t("core.prio.f_deposito", lang)],
            navegar="deposito",
            accion_chat=_t("core.prio.dep_porvencer_chat", lang),
            insight=ins.build(
                pattern=ins.pattern(_t("core.prio.dep_porvencer_p", lang, n=_num(dep["por_vencer"], lang)),
                                    scope={"kind": "products", "count": dep["por_vencer"]}),
                hypothesis=ins.hypothesis(_t("core.prio.dep_porvencer_hyp", lang)),
                evidence=[
                    ins.metric("expiring_lots_value", label=_pesos(total_valor, lang),
                               value=total_valor, unit="ars", weight="primary", method=metodo),
                    ins.records("expiring_lots", label=_t("core.prio.dep_porvencer_t", lang),
                                weight="primary",
                                rows=[ins.record(kind="product", id=x.get("codigo"),
                                                 name=x.get("producto") or "", amount=x["valor"],
                                                 detail=_t("core.prio.dep_porvencer_i", lang,
                                                           dias=x.get("dias_restantes") or 0))
                                      for x in lotes],
                                method=metodo),
                    ins.series("expiring_lots_chart", label=_t("core.prio.dep_porvencer_g", lang),
                               chart=_grafico(_t("core.prio.dep_porvencer_g", lang),
                                             [{"x": x.get("producto") or "", "y": x["valor"]}
                                              for x in lotes], "$", False),
                               method=metodo),
                ],
                assumptions=[ins.assumption(_t("core.prio.dep_vencidos_s", lang))],
                risk=ins.risk(_t("core.prio.dep_porvencer_risk", lang), exposure=total_valor),
                recommendation=ins.recommendation(
                    _t("core.prio.dep_porvencer_t", lang), navigate="deposito",
                    chat=_t("core.prio.dep_porvencer_chat", lang)),
            ),
        ))
    if dep.get("discrepancias"):
        items = deposito.discrepancias()[:8]
        metodo = {"key": "core.method.dep_discrep", "label": _t("core.method.dep_discrep", lang)}
        out.append(_item(
            id="dep_discrep", tono="oro", chip=_t("core.prio.chip_deposito", lang),
            titulo=_t("core.prio.dep_discrep_t", lang),
            resumen=_t("core.prio.dep_discrep_r", lang, n=_num(dep["discrepancias"], lang)),
            origen=["alerta:dep_discrep"], modulos=ALERT_MODULOS["dep_discrep"],
            cifra_texto=_num(dep["discrepancias"], lang),
            fuentes=[_t("core.prio.f_deposito", lang)],
            navegar="deposito",
            accion_chat=_t("core.prio.dep_discrep_chat", lang),
            insight=ins.build(
                pattern=ins.pattern(_t("core.prio.dep_discrep_p", lang, n=_num(dep["discrepancias"], lang)),
                                    scope={"kind": "products", "count": dep["discrepancias"]}),
                evidence=[
                    ins.metric("discrepancy_count", label=_num(dep["discrepancias"], lang),
                               value=dep["discrepancias"], unit="products", weight="primary",
                               method=metodo),
                    ins.records("discrepancy_rows", label=_t("core.prio.dep_discrep_t", lang),
                                weight="primary",
                                rows=[ins.record(kind="product", id=x.get("codigo"),
                                                 name=x.get("descripcion") or "",
                                                 amount=x.get("diferencia"))
                                      for x in items],
                                method=metodo),
                ],
                recommendation=ins.recommendation(
                    _t("core.prio.dep_discrep_t", lang), navigate="deposito",
                    chat=_t("core.prio.dep_discrep_chat", lang)),
            ),
        ))
    venc = vencimientos.en_riesgo(30, lang)
    if venc.get("disponible") and venc.get("lotes_en_riesgo"):
        items = sorted(venc.get("items") or [], key=lambda x: -x["plata_en_riesgo"])[:8]
        top = items[0]
        metodo = {"key": "core.method.at_risk", "label": _t("core.method.at_risk", lang)}
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
            insight=ins.build(
                pattern=ins.pattern(_t("core.prio.venc_riesgo_p", lang,
                                       n=_num(venc["lotes_en_riesgo"], lang),
                                       monto=_pesos(venc.get("total_en_riesgo") or 0, lang)),
                                    scope={"kind": "products", "count": venc["lotes_en_riesgo"]}),
                evidence=[
                    ins.metric("at_risk_value", label=_pesos(venc.get("total_en_riesgo") or 0, lang),
                               value=venc.get("total_en_riesgo"), unit="ars", weight="primary",
                               method=metodo),
                    ins.records("at_risk_rows", label=_t("core.prio.venc_riesgo_t", lang,
                                                         n=_num(venc["lotes_en_riesgo"], lang)),
                                weight="primary",
                                rows=[ins.record(kind="product", id=x.get("codigo"),
                                                 name=x.get("producto") or "",
                                                 amount=x["plata_en_riesgo"],
                                                 detail=_t("core.prio.venc_riesgo_i", lang,
                                                           dias=x.get("dias_restantes") or 0))
                                      for x in items],
                                method=metodo),
                    ins.series("at_risk_chart", label=_t("core.prio.venc_riesgo_g", lang),
                               chart=_grafico(_t("core.prio.venc_riesgo_g", lang),
                                             [{"x": x.get("producto") or "", "y": x["plata_en_riesgo"]}
                                              for x in items], "$", False),
                               method=metodo),
                ],
                assumptions=[ins.assumption(_t("core.prio.venc_riesgo_s", lang))],
                risk=ins.risk(_t("core.prio.venc_riesgo_risk", lang),
                              exposure=venc.get("total_en_riesgo")),
                recommendation=ins.recommendation(
                    _t("core.prio.venc_riesgo_t", lang, n=_num(venc["lotes_en_riesgo"], lang)),
                    navigate="deposito",
                    chat=_t("core.prio.venc_riesgo_chat", lang)),
            ),
        ))
    return out


def _alerts_inventario(lang) -> list[dict]:
    from . import store
    pan = store.panorama()
    cv = (pan.get("alertas") or {}).get("costo_viejo") or {}
    if not cv.get("cantidad"):
        return []
    items = sorted(pan.get("grupos", {}).get("costo_viejo") or [],
                   key=lambda d: -(d.get("inmovilizado") or 0))[:8]
    return [_item(
        id="costo_viejo", tono="oro", chip=_t("core.prio.chip_precio", lang),
        titulo=_t("core.prio.costo_viejo_t", lang),
        resumen=_t("core.prio.costo_viejo_r", lang, n=_num(cv["cantidad"], lang)),
        origen=["alerta:costo_viejo"], modulos=ALERT_MODULOS["costo_viejo"],
        cifra_texto=_num(cv["cantidad"], lang),
        monto=cv.get("impacto_pesos"),
        fuentes=[_t("core.prio.f_costos", lang)],
        navegar="inventario",
        accion_chat=_t("core.prio.costo_viejo_chat", lang),
        drill={
            "porque": [_t("core.prio.costo_viejo_p", lang, n=_num(cv["cantidad"], lang))],
            "grafico": _grafico(_t("core.prio.costo_viejo_g", lang),
                                [{"x": d.get("descripcion") or "", "y": d.get("inmovilizado") or 0}
                                 for d in items], "$", False),
            "involucrados": [{"id": d.get("codigo"), "kind": "product",
                              "nombre": d.get("descripcion") or "",
                              "monto": d.get("inmovilizado") or 0,
                              "detalle": _t("core.prio.costo_viejo_i", lang,
                                            dias=d.get("antiguedad_costo_dias") or 0)}
                             for d in items],
            "supuestos": [],
        },
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
    grafico = _grafico(_t("core.prio.caja_g", lang),
                       [{"x": h["fecha"], "y": h["total"]} for h in hist] +
                       [{"x": _t("core.prio.caja_hoy", lang), "y": tot}],
                       "$", True)
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
        drill={"porque": [_t("core.prio.caja_p", lang, total=_pesos(tot, lang),
                             prom=_pesos(prom, lang), pct=round(desvio * 100))],
              "grafico": grafico, "involucrados": [],
              "supuestos": [_t("core.prio.caja_s", lang)]},
    )]


def _alerts_evolucion(lang) -> list[dict]:
    from . import evolucion
    pan = evolucion.panorama(lang)
    if pan.get("hay_datos") is False:
        return []
    out = []
    serie = pan.get("serie") or []
    grafico = _grafico(_t("core.prio.caida_g", lang),
                       [{"x": p["mes"], "y": p.get("real") if p.get("real") is not None
                        else p.get("nominal")} for p in serie],
                       "$", True) if serie else None
    for a in evolucion.alertas_de(pan, lang):
        out.append(_item(
            # tono=oro, not rojo: this id lives in WATCH_IDS (informational,
            # own heading) — rojo is reserved for items in `act` so the
            # section header color and the card's own accent never disagree.
            id="caida_interanual", tono="oro", chip=_t("core.prio.chip_riesgo", lang),
            titulo=a["titulo"],
            resumen=a["detalle"],
            origen=["alerta:caida_interanual"],
            modulos=ALERT_MODULOS["caida_interanual"],
            fuentes=[_t("core.prio.f_ventas", lang)],
            navegar="evolucion",
            accion_chat=_t("core.prio.caida_chat", lang),
            drill={"porque": [a["detalle"]], "grafico": grafico, "involucrados": [],
                  "supuestos": [_t("core.prio.caida_s", lang)]},
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
