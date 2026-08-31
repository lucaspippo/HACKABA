"""
Continuous learning — patterns nobody asked to have calculated.

Everything else in `core/` answers a question someone already knew to ask
(who owes me money? what's about to run out?). This module looks for the
opposite: behavior that already lives in the everyday operational data
(orders, cash-register closes) but that no standard ERP report summarizes,
because it isn't ONE number — it's a correlation between two things nobody
ever put side by side.

The set (small on purpose — grows only once a new pattern proves itself in
production, never before):

  1. combo_no_percibido    — two products that travel together in the same
                              order far more than chance would explain
  2. faltante_caja_patron  — a weekday where the till comes up short far
                              more often than the rest, hidden by the
                              overall average

Same rule as `oportunidades_neg`: without the minimum statistical support
(volume, distinct customers, effect size) the card doesn't exist — it drops
silently, never forced out of two loose coincidences.
"""
from __future__ import annotations

import collections
import datetime
import itertools

# --- combo_no_percibido: cross-purchase thresholds -----------------------------
MIN_TOTAL_ORDERS = 40           # without enough order volume, the basket says nothing
MIN_COOCCURRENCES = 5           # the pair has to repeat, not be two one-off customers
MIN_LIFT = 6.0                  # how many times more often they appear together than chance predicts
MIN_DISTINCT_CUSTOMERS = 3      # so it isn't just one customer's habit

# --- faltante_caja_patron: weekday shortfall thresholds ------------------------
MIN_CASH_CLOSES = 20            # minimum history before calling a weekday "typical"
MIN_SAMPLES_PER_WEEKDAY = 4     # closes for THAT weekday, minimum, so one bad day doesn't decide it
SHORTFALL_RATIO_THRESHOLD = 2.5 # the flagged weekday has to fall short this many times more than the rest
MIN_SHORTFALL_PESOS = 500       # and not be a few pesos of noise


def _t(key: str, lang: str | None = None, **params) -> str:
    import i18n
    return i18n.t(key, lang, **params)


def _money(n, lang) -> str:
    import i18n
    return i18n.pesos(n or 0, lang)


def _chart(name: str, points: list[dict], unit: str, is_time_series: bool,
           window: str = "") -> dict:
    return {"ok": True, "series": [{"nombre": name, "puntos": points}],
            "meta": {"unidad": unit, "temporal": is_time_series, "ventana": window,
                     "composicion": False, "deflactado": False}}


# --- 1 · combo_no_percibido -----------------------------------------------------

def _pairs_by_lift(orders: list[dict]) -> tuple[list[dict], dict[int, str]]:
    """Every code pair that shows up together in the SAME order far more
    often than chance would explain (lift = P(a∩b) / (P(a)·P(b))), with real
    support behind it."""
    n = len(orders)
    product_count: dict[int, int] = collections.Counter()
    product_customers: dict[int, set] = collections.defaultdict(set)
    pair_count: dict[tuple, int] = collections.Counter()
    pair_customers: dict[tuple, set] = collections.defaultdict(set)
    names: dict[int, str] = {}
    for order in orders:
        codes = set()
        for line in order.get("items") or []:
            code = line.get("codigo")
            if code is None:
                continue
            code = int(code)
            codes.add(code)
            names[code] = line.get("producto")
        for code in codes:
            product_count[code] += 1
            product_customers[code].add(order.get("cliente_id"))
        for a, b in itertools.combinations(sorted(codes), 2):
            pair_count[(a, b)] += 1
            pair_customers[(a, b)].add(order.get("cliente_id"))
    out = []
    for (a, b), cnt in pair_count.items():
        if cnt < MIN_COOCCURRENCES or n == 0:
            continue
        customers = pair_customers[(a, b)]
        if len(customers) < MIN_DISTINCT_CUSTOMERS:
            continue
        lift = (cnt / n) / ((product_count[a] / n) * (product_count[b] / n))
        if lift < MIN_LIFT:
            continue
        out.append({"a": a, "b": b, "cnt": cnt, "lift": lift,
                    "customers": len(customers),
                    "count_a": product_count[a], "count_b": product_count[b]})
    out.sort(key=lambda x: (-x["lift"], -x["cnt"]))
    return out, names


def _unnoticed_combo_card(lang) -> dict | None:
    from . import ventas_cliente
    orders = ventas_cliente.all_orders()
    if len(orders) < MIN_TOTAL_ORDERS:
        return None
    pairs, names = _pairs_by_lift(orders)
    if not pairs:
        return None
    top = pairs[0]
    # The anchor is the rarer of the two: "when THIS shows up, the other one
    # almost always comes along" tells a story; the other way around doesn't.
    if top["count_a"] <= top["count_b"]:
        anchor, partner, n_anchor = top["a"], top["b"], top["count_a"]
    else:
        anchor, partner, n_anchor = top["b"], top["a"], top["count_b"]
    anchor_name, partner_name = names[anchor], names[partner]

    combined_revenue = 0.0
    partner_amounts: list[float] = []
    both_count = 0
    missed: list[dict] = []
    both_present: list[dict] = []
    for order in orders:
        by_code = {int(line["codigo"]): line for line in (order.get("items") or [])
                   if line.get("codigo") is not None}
        if anchor not in by_code:
            continue
        if partner in by_code:
            both_count += 1
            combined_revenue += float(by_code[anchor].get("monto") or 0)
            combined_revenue += float(by_code[partner].get("monto") or 0)
            partner_amounts.append(float(by_code[partner].get("monto") or 0))
            both_present.append({"nombre": order.get("cliente"),
                                 "monto": round(float(by_code[partner].get("monto") or 0), 2),
                                 "detalle": _t("core.pat.combo_i_conjunto", lang,
                                               fecha=order.get("fecha"))})
        else:
            missed.append({"nombre": order.get("cliente"), "fecha": order.get("fecha"),
                           "detalle": _t("core.pat.combo_i_falta", lang,
                                         a=anchor_name, fecha=order.get("fecha"), b=partner_name)})
    attach_pct = round(both_count / n_anchor * 100) if n_anchor else 0
    has_gap = bool(missed) and partner_amounts
    if has_gap:
        amount = round(len(missed) * (sum(partner_amounts) / len(partner_amounts)), 2)
        amount_label = _t("core.pat.combo_monto_label_potencial", lang)
        summary = _t("core.pat.combo_r_falta", lang, pct=attach_pct, a=anchor_name,
                     b=partner_name, n=len(missed))
        why_2 = _t("core.pat.combo_q2_falta", lang, n=len(missed))
        involved = [{"nombre": m["nombre"], "monto": None, "detalle": m["detalle"]}
                   for m in missed[:6]]
    else:
        amount = round(combined_revenue, 2)
        amount_label = _t("core.pat.combo_monto_label_conjunto", lang)
        summary = _t("core.pat.combo_r_conjunto", lang, pct=attach_pct, a=anchor_name, b=partner_name)
        why_2 = _t("core.pat.combo_q2_conjunto", lang)
        involved = both_present[:6]
    if amount <= 0:
        return None
    chart = _chart(
        _t("core.pat.combo_g", lang, a=anchor_name),
        [{"x": _t("core.pat.combo_g_con", lang, b=partner_name), "y": both_count},
         {"x": _t("core.pat.combo_g_sin", lang, b=partner_name), "y": len(missed)}],
        "#", False)
    return {
        "id": "combo_no_percibido", "tipo": "vender",
        "titulo": _t("core.pat.combo_t", lang, a=anchor_name, b=partner_name),
        "monto": amount, "monto_label": amount_label,
        "datos": {"producto_ancla": anchor_name, "producto_pareja": partner_name,
                  "attach_pct": attach_pct, "coocurrencias": both_count,
                  "pedidos_sin_pareja": len(missed), "clientes": top["customers"],
                  "lift": round(top["lift"], 2)},
        "resumen": summary,
        "accion_chat": _t("core.pat.combo_chat", lang, a=anchor_name, b=partner_name),
        "navegar": "cuentas",
        "fuentes": [_t("core.opn.f_cuentas", lang)],
        "drill": {
            "porque": [
                _t("core.pat.combo_q1", lang, n=n_anchor, clientes=top["customers"],
                   a=anchor_name, b=partner_name, pct=attach_pct),
                why_2,
            ],
            "grafico": chart,
            "involucrados": involved,
            "supuestos": [_t("core.pat.combo_s1", lang)],
        },
    }


# --- 2 · faltante_caja_patron: weekday shortfall pattern -----------------------

def _cash_shortfall_weekday_card(lang) -> dict | None:
    import i18n
    from . import caja
    history = [h for h in (caja.historial() or []) if h.get("total")]
    if len(history) < MIN_CASH_CLOSES:
        return None
    by_weekday: dict[int, list[tuple[str, float]]] = collections.defaultdict(list)
    for h in history:
        try:
            weekday = datetime.date.fromisoformat(h["fecha"]).weekday()
        except (KeyError, ValueError, TypeError):
            continue
        by_weekday[weekday].append((h["fecha"], float(h.get("diferencia") or 0)))
    candidates = []
    for weekday, samples in by_weekday.items():
        if len(samples) < MIN_SAMPLES_PER_WEEKDAY:
            continue
        rest = [d for wd2, ss in by_weekday.items() if wd2 != weekday for _, d in ss]
        if not rest:
            continue
        diffs = [d for _, d in samples]
        shortfall_day = sum(-d for d in diffs if d < 0) / len(diffs)
        shortfall_rest = sum(-d for d in rest if d < 0) / len(rest)
        candidates.append((weekday, shortfall_day, shortfall_rest, samples, rest))
    if not candidates:
        return None
    weekday, shortfall_day, shortfall_rest, samples, rest = max(candidates, key=lambda c: c[1])
    if shortfall_day < MIN_SHORTFALL_PESOS:
        return None
    if shortfall_rest > 0 and shortfall_day < shortfall_rest * SHORTFALL_RATIO_THRESHOLD:
        return None

    diffs = [d for _, d in samples]
    shortfalls = [(f, d) for f, d in samples if d < 0]
    pct = round(len(shortfalls) / len(diffs) * 100)
    pct_rest = round(sum(1 for d in rest if d < 0) / len(rest) * 100)
    total = round(sum(-d for d in diffs if d < 0), 2)
    weekday_name = i18n.weekday_name(weekday, lang)
    chart = _chart(_t("core.pat.caja_g", lang),
                   [{"x": f, "y": round(-d, 2) or 0.0} for f, d in sorted(samples)],
                   "$", True)
    return {
        "id": "faltante_caja_patron", "tipo": "revisar",
        "titulo": _t("core.pat.caja_t", lang, dia=weekday_name),
        "monto": total,
        "datos": {"dia_semana": weekday, "dia_nombre": weekday_name, "pct_faltante": pct,
                  "pct_faltante_resto": pct_rest, "cierres_analizados": len(diffs),
                  "total_faltante": total},
        "resumen": _t("core.pat.caja_r", lang, pct=pct, dia=weekday_name, pct_resto=pct_rest,
                      total=_money(total, lang), n=len(diffs)),
        "accion_chat": _t("core.pat.caja_chat", lang, dia=weekday_name),
        "navegar": "caja",
        "fuentes": [_t("core.prio.f_caja", lang)],
        "drill": {
            "porque": [
                _t("core.pat.caja_q1", lang, n=len(diffs), faltan=len(shortfalls),
                   dia=weekday_name, pct=pct, pct_resto=pct_rest),
                _t("core.pat.caja_q2", lang, total=_money(total, lang), dia=weekday_name),
            ],
            "grafico": chart,
            "involucrados": [{"nombre": f, "monto": round(-d, 2),
                              "detalle": _t("core.pat.caja_i", lang, fecha=f,
                                            monto=_money(-d, lang))}
                             for f, d in sorted(shortfalls, key=lambda x: x[1])[:6]],
            "supuestos": [_t("core.pat.caja_s1", lang)],
        },
    }


# --- the set ---------------------------------------------------------------

# Values match the shared vocabulary already established by
# oportunidades_neg.NATURALEZA / priorities._is_watch — "riesgo" is what
# priorities.py checks for to route a card into the watch band.
NATURE_BY_ID = {
    "combo_no_percibido": "accionable",
    "faltante_caja_patron": "riesgo",
}

# Same module-gating convention as oportunidades_neg.DOMINIO: a card only
# shows up for a role that has ALL the listed modules enabled.
MODULES_BY_ID = {
    "combo_no_percibido": ("cuentas", "oportunidades"),
    "faltante_caja_patron": ("caja",),
}

_CARD_BUILDERS = (_unnoticed_combo_card, _cash_shortfall_weekday_card)


def cards(lang: str | None = None) -> list[dict]:
    out = []
    for build in _CARD_BUILDERS:
        try:
            card = build(lang)
        except Exception:  # noqa: BLE001 — one broken pattern must not kill the section
            card = None
        if card:
            card["naturaleza"] = NATURE_BY_ID.get(card["id"], "accionable")
            out.append(card)
    out.sort(key=lambda c: -(c.get("monto") or 0))
    return out
