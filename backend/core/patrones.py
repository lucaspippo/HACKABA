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
  3. cruce_no_programado   — different in kind from the two above: 1 and 2
                              each answer a hypothesis a developer chose in
                              advance (products×products, one weekday×the
                              rest). This one tags every order with whatever
                              generic attributes it carries (customer,
                              weekday, product category) and searches EVERY
                              cross-dimension pair for the same statistical
                              signal — no developer declares which pair to
                              look for. See docs/auto-learn-knowledge-brain.md.

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
        # Identifies THIS specific pair across requests, so feedback on it
        # (see record_feedback) survives even after other numbers on the
        # card change; a different pair firing later is a different finding.
        "fingerprint": f"{anchor}:{partner}",
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
        # Identifies THIS weekday: if a different weekday becomes the
        # outlier later, that's a different finding worth surfacing again.
        "fingerprint": f"weekday:{weekday}",
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


# --- 3 · cruce_no_programado: generic cross-dimension discovery ---------------
#
# combo_no_percibido and faltante_caja_patron above each answer ONE hypothesis
# a developer picked in advance. This one doesn't know in advance WHICH
# dimensions matter: it tags every order with whatever generic attributes it
# happens to carry, then searches every CROSS-dimension pair of tags for the
# same lift/support signal combo_no_percibido looks for in one pre-chosen
# pair (same-dimension pairs, e.g. product×product, are combo_no_percibido's
# job already — skipped here to stay a genuinely different finding). Adding a
# new dimension later (salesperson, payment method, once that data exists)
# is a one-line addition to `_tags_de_pedido`, not a new hypothesis function.

_DIMENSIONES_CRUCE = ("cliente", "dia_semana", "categoria")


def _tags_de_pedido(order: dict) -> set[tuple[str, str]]:
    """The generic (dimension, value) tags this ONE order carries. Nobody
    hardcodes which pair of these matters — `_cruces_por_lift` tries all of
    them."""
    from . import fechas
    tags: set[tuple[str, str]] = set()
    cliente = order.get("cliente")
    if cliente:
        tags.add(("cliente", cliente))
    fecha = fechas.parse_fecha(order.get("fecha"))
    if fecha:
        tags.add(("dia_semana", str(fecha.weekday())))
    for item in order.get("items") or []:
        categoria = item.get("categoria")
        if categoria:
            tags.add(("categoria", categoria))
    return tags


def _cruces_por_lift(orders: list[dict]) -> list[dict]:
    """Every cross-dimension tag pair that co-occurs far more than chance
    would explain — the generic version of `_pairs_by_lift`, run over
    whatever dimensions `_tags_de_pedido` produced instead of one hardcoded
    pair. Same statistical bar as combo_no_percibido on purpose: this is a
    different SEARCH, not a looser one."""
    n = len(orders)
    conteo: dict[tuple, int] = collections.Counter()
    clientes_por_tag: dict[tuple, set] = collections.defaultdict(set)
    conteo_par: dict[tuple, int] = collections.Counter()
    clientes_por_par: dict[tuple, set] = collections.defaultdict(set)
    for order in orders:
        tags = _tags_de_pedido(order)
        cliente_id = order.get("cliente_id")
        for tag in tags:
            conteo[tag] += 1
            clientes_por_tag[tag].add(cliente_id)
        for a, b in itertools.combinations(sorted(tags), 2):
            if a[0] == b[0]:
                continue  # same-dimension pairs: combo_no_percibido's job
            conteo_par[(a, b)] += 1
            clientes_por_par[(a, b)].add(cliente_id)
    out = []
    for (a, b), cnt in conteo_par.items():
        if cnt < MIN_COOCCURRENCES or n == 0:
            continue
        clientes = clientes_por_par[(a, b)]
        if len(clientes) < MIN_DISTINCT_CUSTOMERS:
            continue
        lift = (cnt / n) / ((conteo[a] / n) * (conteo[b] / n))
        if lift < MIN_LIFT:
            continue
        out.append({"a": a, "b": b, "cnt": cnt, "lift": lift, "clientes": len(clientes)})
    out.sort(key=lambda x: (-x["lift"], -x["cnt"]))
    return out


def _etiqueta_tag(tag: tuple[str, str], lang: str | None) -> str:
    dim, valor = tag
    if dim == "dia_semana":
        import i18n
        return i18n.weekday_name(int(valor), lang)
    return valor  # cliente/categoria: ya son texto de dato, no vocabulario


def _cruce_no_programado_card(lang) -> dict | None:
    from . import ventas_cliente
    orders = ventas_cliente.all_orders()
    if len(orders) < MIN_TOTAL_ORDERS:
        return None
    cruces = _cruces_por_lift(orders)
    if not cruces:
        return None
    top = cruces[0]
    a_label, b_label = _etiqueta_tag(top["a"], lang), _etiqueta_tag(top["b"], lang)
    a_dim = _t(f"core.pat.cruce_dim_{top['a'][0]}", lang)
    b_dim = _t(f"core.pat.cruce_dim_{top['b'][0]}", lang)
    lift = round(top["lift"], 1)
    return {
        "id": "cruce_no_programado", "tipo": "revisar",
        # Identifies THIS specific dimension pair+values; a different cross
        # firing later (a different weekday, a different category) is a
        # different finding, same convention as combo_no_percibido.
        "fingerprint": f"{top['a'][0]}:{top['a'][1]}|{top['b'][0]}:{top['b'][1]}",
        "titulo": _t("core.pat.cruce_t", lang, a=a_label, b=b_label),
        "monto": None, "monto_label": None,
        "datos": {"dimension_a": top["a"][0], "valor_a": top["a"][1],
                  "dimension_b": top["b"][0], "valor_b": top["b"][1],
                  "coocurrencias": top["cnt"], "clientes": top["clientes"], "lift": lift},
        "resumen": _t("core.pat.cruce_r", lang, a_dim=a_dim, a=a_label, b_dim=b_dim,
                     b=b_label, n=top["cnt"], clientes=top["clientes"], lift=lift),
        "accion_chat": _t("core.pat.cruce_chat", lang, a=a_label, b=b_label),
        "navegar": "cuentas",
        "fuentes": [_t("core.opn.f_cuentas", lang)],
        "drill": {
            "porque": [_t("core.pat.cruce_q1", lang, clientes=top["clientes"],
                          n=top["cnt"], lift=lift)],
            "grafico": None,
            "involucrados": [],
            "supuestos": [_t("core.pat.cruce_s1", lang)],
        },
    }


# --- the set ---------------------------------------------------------------

# Values match the shared vocabulary already established by
# oportunidades_neg.NATURALEZA / priorities._is_watch — "riesgo" is what
# priorities.py checks for to route a card into the watch band.
NATURE_BY_ID = {
    "combo_no_percibido": "accionable",
    "faltante_caja_patron": "riesgo",
    "cruce_no_programado": "accionable",
}

# Same module-gating convention as oportunidades_neg.DOMINIO: a card only
# shows up for a role that has ALL the listed modules enabled.
MODULES_BY_ID = {
    "combo_no_percibido": ("cuentas", "oportunidades"),
    "faltante_caja_patron": ("caja",),
    "cruce_no_programado": ("cuentas", "oportunidades"),
}

_CARD_BUILDERS = (_unnoticed_combo_card, _cash_shortfall_weekday_card,
                  _cruce_no_programado_card)


def cards(lang: str | None = None) -> list[dict]:
    from . import pattern_feedback
    out = []
    for build in _CARD_BUILDERS:
        try:
            card = build(lang)
        except Exception:  # noqa: BLE001 — one broken pattern must not kill the section
            card = None
        if card:
            card["naturaleza"] = NATURE_BY_ID.get(card["id"], "accionable")
            out.append(card)
    out = pattern_feedback.drop_handled(out)
    out.sort(key=lambda c: -(c.get("monto") or 0))
    return out


def record_feedback(card_id: str, action: str, *, actor: str,
                    note: str | None = None, lang: str | None = None) -> dict:
    """Thin wrapper over core/pattern_feedback.py, the mechanism this module
    shares with core/oportunidades_neg.py's fixed rule set."""
    from . import pattern_feedback
    return pattern_feedback.record(lambda: cards(lang), card_id, action,
                                   actor=actor, note=note)


def record_learn(card_id: str, *, actor: str, tipo: str, ambito: str, nodo: str,
                 efecto: str, entidad: str | None = None, texto: str | None = None,
                 texto_en: str | None = None, params: dict | None = None,
                 note: str | None = None, lang: str | None = None) -> dict:
    """"Enseñar a Ángela": thin wrapper over pattern_feedback.learn(), the
    generic engine this module shares with core/oportunidades_neg.py."""
    from . import pattern_feedback
    return pattern_feedback.learn(
        lambda: cards(lang), card_id, actor=actor, tipo=tipo, ambito=ambito,
        nodo=nodo, efecto=efecto, entidad=entidad, texto=texto, texto_en=texto_en,
        params=params, note=note)
