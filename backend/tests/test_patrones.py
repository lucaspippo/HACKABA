"""core/patrones.py — continuous learning: unnoticed combos and cash
shortfalls with a weekday pattern.

Synthetic tests (this file) exercise the thresholds precisely with
constructed fixtures — no demo dataset needed, same pattern as
test_priorities.py. The canonical numbers on the DEMO dataset (the injected
yerba/sugar combo, the Saturday shortfall) run in a subprocess, same
pattern as test_p38 / test_cruces.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from core import patrones


def _order(customer_id, date, items):
    return {"cliente_id": customer_id, "cliente": customer_id, "fecha": date,
            "monto": sum(it["monto"] for it in items), "items": items}


def _line(code, product, amount=1000.0):
    return {"codigo": code, "producto": product, "categoria": "test",
            "cantidad": 1, "precio": amount, "monto": amount}


# --- no data, no card --------------------------------------------------------

def test_piloto_has_no_orders_or_cash_history_so_nothing_shows():
    """The piloto tenant has no ventas_por_cliente.json and no long-enough
    cash history: neither card gets forced without its minimum support."""
    assert patrones.cards("es") == []


# --- 1 · combo_no_percibido ---------------------------------------------------

def _combo_orders(n_both, n_anchor_only, n_partner_only=0, n_customers=4):
    """`n_both` orders with A(mate)+B(sugar), `n_anchor_only` with A but no B
    (the gap), `n_partner_only` with B but no A (so B stays MORE frequent
    than A — the algorithm anchors on the less frequent one, same as in the
    real demo: yerba is the rare one, sugar the everyday staple). Plus filler
    noise (unrelated products) so lift has something to compare against: the
    bigger the total population, the rarer it is for A and B to cross by
    chance, so the filler count is sized to leave lift comfortably above
    MIN_LIFT."""
    orders = []
    for i in range(n_both):
        customer = f"customer_{i % n_customers}"
        items = [_line(1, "YERBA X", 2000.0), _line(2, "AZUCAR X", 1500.0)]
        orders.append(_order(customer, f"2026-0{1 + i % 6}-01", items))
    for i in range(n_anchor_only):
        customer = f"customer_gap_{i}"
        orders.append(_order(customer, f"2026-0{1 + i % 6}-15",
                             [_line(1, "YERBA X", 2000.0)]))
    for i in range(n_partner_only):
        orders.append(_order(f"customer_sugar_only_{i}", "2026-01-20",
                             [_line(2, "AZUCAR X", 1500.0)]))
    total = n_both + n_anchor_only + n_partner_only
    filler = max(patrones.MIN_TOTAL_ORDERS, int(patrones.MIN_LIFT * total * 3))
    for i in range(filler):
        orders.append(_order(f"noise_{i}", "2026-01-01",
                             [_line(100 + i, f"FILLER {i}", 500.0)]))
    return orders


def test_combo_no_percibido_sizes_the_gap_when_one_exists(monkeypatch):
    from core import ventas_cliente
    orders = _combo_orders(n_both=8, n_anchor_only=2, n_partner_only=3)
    monkeypatch.setattr(ventas_cliente, "all_orders", lambda: orders)
    c = next(x for x in patrones.cards("es") if x["id"] == "combo_no_percibido")
    assert c["datos"]["producto_ancla"] == "YERBA X"     # the less frequent one: 10 < 11
    assert c["datos"]["producto_pareja"] == "AZUCAR X"
    assert c["datos"]["attach_pct"] == 80                # 8 out of 10
    assert c["datos"]["pedidos_sin_pareja"] == 2
    # the gap is money left on the counter: 2 orders * the pair's $1500 line
    assert c["monto"] == 3000.0
    assert c["monto_label"] == "venta cruzada sin aprovechar"
    assert c["naturaleza"] == "accionable"
    assert "YERBA X" in c["titulo"] and "AZUCAR X" in c["titulo"]


def test_combo_no_percibido_sizes_the_combined_revenue_when_theres_no_gap(monkeypatch):
    from core import ventas_cliente
    orders = _combo_orders(n_both=6, n_anchor_only=0)
    monkeypatch.setattr(ventas_cliente, "all_orders", lambda: orders)
    c = next(x for x in patrones.cards("es") if x["id"] == "combo_no_percibido")
    assert c["datos"]["attach_pct"] == 100
    assert c["datos"]["pedidos_sin_pareja"] == 0
    # no gap: the amount is the ALREADY-flowing combined revenue, not a loss
    assert c["monto"] == round(6 * (2000.0 + 1500.0), 2)
    assert c["monto_label"] == "facturación conjunta ya detectada"


def test_combo_no_percibido_is_not_forced_with_thin_support(monkeypatch):
    """Only one customer, or too few coincidences: not enough to claim a
    pattern — the card doesn't exist."""
    from core import ventas_cliente
    orders = _combo_orders(n_both=2, n_anchor_only=0, n_customers=1)
    monkeypatch.setattr(ventas_cliente, "all_orders", lambda: orders)
    ids = [c["id"] for c in patrones.cards("es")]
    assert "combo_no_percibido" not in ids


# --- 3 · cruce_no_programado (generic cross-dimension discovery) --------------

def _cruce_orders(n_both, n_customers=4):
    """`n_both` orders that fall on a Monday AND carry an "importado" line —
    the cross the scanner should find is (dia_semana:Monday, categoria:
    importado), a pair NOBODY hardcodes anywhere in core/patrones.py, unlike
    combo_no_percibido's product-vs-product search. Filler orders spread
    across the other six weekdays with a UNIQUE category each, so no filler
    (weekday, category) pair can ever repeat and accidentally clear
    MIN_COOCCURRENCES — the only real signal in the data is the injected one."""
    import datetime as _dt
    monday = _dt.date(2026, 1, 5)
    assert monday.weekday() == 0
    orders = []
    for i in range(n_both):
        customer = f"customer_{i % n_customers}"
        fecha = (monday + _dt.timedelta(weeks=i)).isoformat()
        orders.append(_order(customer, fecha,
                             [{"codigo": 900 + i, "producto": "IMPORTADO X",
                               "categoria": "importado", "cantidad": 1,
                               "precio": 1000.0, "monto": 1000.0}]))
    filler = max(patrones.MIN_TOTAL_ORDERS, int(patrones.MIN_LIFT * n_both * 3))
    for i in range(filler):
        fecha = (monday + _dt.timedelta(days=1 + (i % 6), weeks=i)).isoformat()
        orders.append(_order(f"noise_{i}", fecha,
                             [{"codigo": 1000 + i, "producto": f"FILLER {i}",
                               "categoria": f"filler_cat_{i}", "cantidad": 1,
                               "precio": 500.0, "monto": 500.0}]))
    return orders


def test_cruce_no_programado_finds_a_cross_dimension_pattern(monkeypatch):
    """No developer told this detector to compare weekdays against product
    categories — it tried every cross-dimension pair the data offered and
    this is the one that cleared the bar."""
    from core import ventas_cliente
    monkeypatch.setattr(ventas_cliente, "all_orders", lambda: _cruce_orders(n_both=8))
    c = next(x for x in patrones.cards("es") if x["id"] == "cruce_no_programado")
    assert {c["datos"]["dimension_a"], c["datos"]["dimension_b"]} == {"dia_semana", "categoria"}
    valores = {c["datos"]["valor_a"], c["datos"]["valor_b"]}
    assert valores == {"0", "importado"}
    assert c["datos"]["coocurrencias"] == 8
    assert c["datos"]["clientes"] == 4
    assert c["naturaleza"] == "accionable"
    assert c["monto"] is None


def test_cruce_no_programado_is_not_forced_with_thin_support(monkeypatch):
    from core import ventas_cliente
    monkeypatch.setattr(ventas_cliente, "all_orders", lambda: _cruce_orders(n_both=2))
    ids = [c["id"] for c in patrones.cards("es")]
    assert "cruce_no_programado" not in ids


def test_cruce_no_programado_does_not_fire_on_same_dimension_pairs(monkeypatch):
    """cliente×cliente or categoria×categoria pairs are combo_no_percibido's
    job, not this scanner's — same-dimension pairs must never surface here
    even if they'd otherwise clear the statistical bar."""
    from core import ventas_cliente
    orders = _cruce_orders(n_both=8)
    monkeypatch.setattr(ventas_cliente, "all_orders", lambda: orders)
    c = next(x for x in patrones.cards("es") if x["id"] == "cruce_no_programado")
    assert c["datos"]["dimension_a"] != c["datos"]["dimension_b"]


def test_cruce_no_programado_supports_the_teach_angela_loop(monkeypatch, db_tenant):
    """The generic finding plugs into the SAME shared feedback/learn
    mechanism as the two hand-coded patterns — no special-casing needed for
    a genuinely discovered finding to become durable knowledge."""
    from core import conocimiento, ventas_cliente
    _patch_tenant(monkeypatch, db_tenant)
    monkeypatch.setattr(ventas_cliente, "all_orders", lambda: _cruce_orders(n_both=8))

    pieza = patrones.record_learn(
        "cruce_no_programado", actor="aldo", tipo="contexto", ambito="global",
        nodo="ventas", efecto="contexto_para_angela", lang="es")
    assert pieza["origen"]["hallazgo_id"] == "cruce_no_programado"
    assert conocimiento.detalle(pieza["id"]) == pieza

    ids = [c["id"] for c in patrones.cards("es")]
    assert "cruce_no_programado" not in ids  # handled — durable knowledge took over


def test_combo_no_percibido_ignores_pairs_without_lift(monkeypatch):
    """Two popular products that often appear together only because both are
    popular (low lift) don't count as a combo."""
    from core import ventas_cliente
    orders = []
    # A and B each show up in roughly half the orders, independently of one
    # another (mod 2 vs mod 3) — they cross barely more than chance already
    # predicts.
    for i in range(120):
        items = [_line(1, "POPULAR A", 1000.0)] if i % 2 == 0 else []
        items += [_line(2, "POPULAR B", 1000.0)] if i % 3 == 0 else []
        items += [_line(3 + i, f"FILLER {i}", 200.0)]
        orders.append(_order(f"customer_{i % 5}", "2026-01-01", items))
    monkeypatch.setattr(ventas_cliente, "all_orders", lambda: orders)
    ids = [c["id"] for c in patrones.cards("es")]
    assert "combo_no_percibido" not in ids


# --- 2 · faltante_caja_patron: weekday shortfall pattern ----------------------

def _cash_history(normal_days=30, saturdays_short=6, saturdays_ok=2):
    """Monday to Friday: no shortfall. Saturdays: most closes come up short
    by a lot. Dates anchored to real weeks (2026 starts on a Thursday)."""
    import datetime
    history = []
    base = datetime.date(2026, 1, 5)  # a Monday
    week = 0
    while len([d for d in history
              if datetime.date.fromisoformat(d["fecha"]).weekday() < 5]) < normal_days:
        monday = base + datetime.timedelta(weeks=week)
        for wd in range(5):  # Monday to Friday: healthy
            history.append({"fecha": (monday + datetime.timedelta(days=wd)).isoformat(),
                            "total": 100000, "diferencia": 0})
        week += 1
    saturday = base + datetime.timedelta(days=5)
    for i in range(saturdays_short):
        history.append({"fecha": (saturday + datetime.timedelta(weeks=i)).isoformat(),
                        "total": 100000, "diferencia": -4000})
    for i in range(saturdays_ok):
        history.append({"fecha": (saturday + datetime.timedelta(weeks=saturdays_short + i)).isoformat(),
                        "total": 100000, "diferencia": 0})
    return history


def test_faltante_caja_patron_finds_the_flagged_weekday(monkeypatch):
    from core import caja
    history = _cash_history()
    monkeypatch.setattr(caja, "historial", lambda: history)
    c = next(x for x in patrones.cards("es") if x["id"] == "faltante_caja_patron")
    assert c["datos"]["dia_semana"] == 5             # Saturday
    assert c["datos"]["dia_nombre"] == "sábado"
    assert c["datos"]["pct_faltante_resto"] == 0     # Monday through Friday, healthy
    assert c["monto"] == 6 * 4000.0
    assert c["naturaleza"] == "riesgo"


def test_faltante_caja_patron_is_not_forced_when_evenly_spread(monkeypatch):
    """Shortfalls spread evenly across every weekday: no single day stands
    out — there's no pattern worth flagging."""
    from core import caja
    import datetime
    history = []
    base = datetime.date(2026, 1, 5)
    for i in range(35):
        diff = -1000 if i % 3 == 0 else 0
        history.append({"fecha": (base + datetime.timedelta(days=i)).isoformat(),
                        "total": 100000, "diferencia": diff})
    monkeypatch.setattr(caja, "historial", lambda: history)
    ids = [c["id"] for c in patrones.cards("es")]
    assert "faltante_caja_patron" not in ids


def test_faltante_caja_patron_is_not_forced_with_thin_history(monkeypatch):
    from core import caja
    history = _cash_history(normal_days=5, saturdays_short=2, saturdays_ok=0)
    monkeypatch.setattr(caja, "historial", lambda: history)
    ids = [c["id"] for c in patrones.cards("es")]
    assert "faltante_caja_patron" not in ids


# --- bilingual, like everything that reaches a human --------------------------

def test_everything_new_is_bilingual(monkeypatch):
    from core import ventas_cliente, caja
    monkeypatch.setattr(ventas_cliente, "all_orders",
                        lambda: _combo_orders(n_both=8, n_anchor_only=2, n_partner_only=3))
    monkeypatch.setattr(caja, "historial", lambda: _cash_history())
    es = {c["id"]: c for c in patrones.cards("es")}
    en = {c["id"]: c for c in patrones.cards("en")}
    assert set(es) == set(en) == {"combo_no_percibido", "faltante_caja_patron"}
    for cid in es:
        assert es[cid]["titulo"] != en[cid]["titulo"], cid
        assert es[cid]["resumen"] != en[cid]["resumen"], cid
        assert es[cid]["monto"] == en[cid]["monto"], cid   # language doesn't move a number


# --- they enter the Prioridades inbox as one more source ----------------------

def test_they_enter_the_priorities_inbox(monkeypatch):
    from core import ventas_cliente, caja, priorities
    monkeypatch.setattr(ventas_cliente, "all_orders",
                        lambda: _combo_orders(n_both=8, n_anchor_only=2, n_partner_only=3))
    monkeypatch.setattr(caja, "historial", lambda: _cash_history())
    inbox = priorities.inbox("es", features=("caja", "cuentas", "oportunidades"))
    act_ids = [i["id"] for i in inbox["act"]]
    watch_ids = [i["id"] for i in inbox["watch"]]
    assert "combo_no_percibido" in act_ids       # actionable: competes for "do this"
    assert "faltante_caja_patron" in watch_ids   # risk/process: to watch, not to collect
    # and it respects the module filter: without "caja" enabled, the card is hidden
    without_caja = priorities.inbox("es", features=("cuentas", "oportunidades"))
    assert "faltante_caja_patron" not in [i["id"] for i in without_caja["watch"]]


# --- 3 · closing the loop: feedback on a finding -------------------------------

def _patch_tenant(monkeypatch, tenant_id):
    from core.db import tenant as tenant_module
    monkeypatch.setattr(tenant_module, "current_tenant_id", lambda: tenant_id)


def test_feedback_invalidates_the_priorities_inbox_cache(monkeypatch, db_tenant):
    """priorities.inbox() caches its compose (core/analisis_cache.py) — a
    regression here means the owner keeps seeing a finding they just gave
    feedback on until something ELSE happens to bust the cache first."""
    from core import ventas_cliente, priorities, analisis_cache
    _patch_tenant(monkeypatch, db_tenant)
    monkeypatch.setattr(ventas_cliente, "all_orders",
                        lambda: _combo_orders(n_both=8, n_anchor_only=2, n_partner_only=3))
    analisis_cache.limpiar()
    before = priorities.inbox("es", features=("caja", "cuentas", "oportunidades"))
    assert "combo_no_percibido" in [i["id"] for i in before["act"]]

    patrones.record_feedback("combo_no_percibido", "dismissed", actor="aldo", lang="es")

    after = priorities.inbox("es", features=("caja", "cuentas", "oportunidades"))
    assert "combo_no_percibido" not in [i["id"] for i in after["act"]]


def test_feedback_hides_the_exact_finding_it_was_given_on(monkeypatch, db_tenant):
    from core import ventas_cliente
    _patch_tenant(monkeypatch, db_tenant)
    monkeypatch.setattr(ventas_cliente, "all_orders",
                        lambda: _combo_orders(n_both=8, n_anchor_only=2, n_partner_only=3))
    before = [c["id"] for c in patrones.cards("es")]
    assert "combo_no_percibido" in before

    patrones.record_feedback("combo_no_percibido", "dismissed", actor="aldo", lang="es")

    after = [c["id"] for c in patrones.cards("es")]
    assert "combo_no_percibido" not in after


def test_learn_creates_a_knowledge_piece_and_hides_the_finding(monkeypatch, db_tenant):
    """"Enseñar a Ángela": the confirmed finding becomes a durable
    core/conocimiento.py piece (with the owner-chosen efecto, not an
    inferred one), and stops resurfacing under its old shape."""
    from core import conocimiento, ventas_cliente
    _patch_tenant(monkeypatch, db_tenant)
    monkeypatch.setattr(ventas_cliente, "all_orders",
                        lambda: _combo_orders(n_both=8, n_anchor_only=2, n_partner_only=3))
    before = [c["id"] for c in patrones.cards("es")]
    assert "combo_no_percibido" in before

    pieza = patrones.record_learn(
        "combo_no_percibido", actor="aldo", tipo="contexto", ambito="global",
        nodo="ventas", efecto="contexto_para_angela", lang="es")

    assert pieza["tipo"] == "contexto"
    assert pieza["efecto"] == "contexto_para_angela"
    assert pieza["origen"]["quien"] == "Ángela"
    assert pieza["origen"]["hallazgo_id"] == "combo_no_percibido"
    assert conocimiento.detalle(pieza["id"]) == pieza

    after = [c["id"] for c in patrones.cards("es")]
    assert "combo_no_percibido" not in after


def test_learn_on_a_card_that_is_not_live_raises(monkeypatch, db_tenant):
    from core import ventas_cliente
    _patch_tenant(monkeypatch, db_tenant)
    monkeypatch.setattr(ventas_cliente, "all_orders", lambda: [])
    import pytest
    with pytest.raises(KeyError):
        patrones.record_learn("combo_no_percibido", actor="aldo", tipo="contexto",
                              ambito="global", nodo="ventas",
                              efecto="contexto_para_angela", lang="es")


def test_feedback_does_not_hide_a_different_instance_of_the_same_pattern(monkeypatch, db_tenant):
    """Dismissing the yerba/sugar combo shouldn't silence a LATER, genuinely
    different pair that happens to trip the same detector — the fingerprint,
    not the pattern id, is what "already handled" is keyed on."""
    from core import ventas_cliente
    _patch_tenant(monkeypatch, db_tenant)
    monkeypatch.setattr(ventas_cliente, "all_orders",
                        lambda: _combo_orders(n_both=8, n_anchor_only=2, n_partner_only=3))
    patrones.record_feedback("combo_no_percibido", "dismissed", actor="aldo", lang="es")
    assert "combo_no_percibido" not in [c["id"] for c in patrones.cards("es")]

    # A different pair (different codes) now becomes the top finding.
    other_pair_orders = _combo_orders(n_both=8, n_anchor_only=2, n_partner_only=3)
    for order in other_pair_orders:
        for item in order["items"]:
            item["codigo"] += 100  # a different SKU pair -> a different fingerprint
    monkeypatch.setattr(ventas_cliente, "all_orders", lambda: other_pair_orders)
    assert "combo_no_percibido" in [c["id"] for c in patrones.cards("es")]


def test_feedback_on_a_card_that_is_not_live_raises(monkeypatch, db_tenant):
    from core import ventas_cliente
    _patch_tenant(monkeypatch, db_tenant)
    monkeypatch.setattr(ventas_cliente, "all_orders", lambda: [])
    import pytest
    with pytest.raises(KeyError):
        patrones.record_feedback("combo_no_percibido", "dismissed", actor="aldo", lang="es")


def test_feedback_rejects_an_unknown_action(monkeypatch, db_tenant):
    from core import ventas_cliente
    _patch_tenant(monkeypatch, db_tenant)
    monkeypatch.setattr(ventas_cliente, "all_orders",
                        lambda: _combo_orders(n_both=8, n_anchor_only=2, n_partner_only=3))
    import pytest
    with pytest.raises(ValueError):
        patrones.record_feedback("combo_no_percibido", "not_a_real_action", actor="aldo", lang="es")


def test_feedback_history_snapshots_the_finding_even_after_it_stops_firing(monkeypatch, db_tenant):
    from core import ventas_cliente
    _patch_tenant(monkeypatch, db_tenant)
    monkeypatch.setattr(ventas_cliente, "all_orders",
                        lambda: _combo_orders(n_both=8, n_anchor_only=2, n_partner_only=3))
    recorded = patrones.record_feedback("combo_no_percibido", "already_knew",
                                        actor="aldo", note="ya lo veníamos haciendo", lang="es")
    assert recorded["action"] == "already_knew"
    assert recorded["note"] == "ya lo veníamos haciendo"
    assert "YERBA X" in recorded["snapshot"]["titulo"]

    # The finding is gone from the live feed, but the history still has it.
    monkeypatch.setattr(ventas_cliente, "all_orders", lambda: [])
    from core import pattern_feedback
    hist = pattern_feedback.history()
    assert len(hist) == 1
    assert hist[0]["pattern_id"] == "combo_no_percibido"
    assert "YERBA X" in hist[0]["snapshot"]["titulo"]


def test_a_broken_feedback_lookup_does_not_hide_every_card(monkeypatch, db_tenant):
    """core/patrones.py's own house rule (a broken signal must not kill the
    section) applies to the feedback lookup too — a Postgres hiccup should
    fail open (show the cards), not fail closed (hide everything)."""
    from core import ventas_cliente
    from core.db import tenant as tenant_module

    def _boom():
        raise RuntimeError("db is down")
    monkeypatch.setattr(tenant_module, "current_tenant_id", _boom)
    monkeypatch.setattr(ventas_cliente, "all_orders",
                        lambda: _combo_orders(n_both=8, n_anchor_only=2, n_partner_only=3))
    assert "combo_no_percibido" in [c["id"] for c in patrones.cards("es")]


# --- the DEMO numbers, in a subprocess (same pattern as test_p38) -------------

def _demo(expr: str):
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_demo = os.path.join(os.path.dirname(backend), "data-demo")
    env = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": data_demo,
           "POLPILOT_DEMO_TODAY": "2026-07-07", "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)
    r = subprocess.run(
        [sys.executable, "-c", f"import json; print(json.dumps({expr}))"],
        cwd=backend, env=env, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_demo_finds_the_yerba_and_sugar_combo():
    cards = _demo("__import__('core.patrones', fromlist=['x']).cards('es')")
    combo = next(c for c in cards if c["id"] == "combo_no_percibido")
    assert "YERBA" in combo["datos"]["producto_ancla"]
    assert "AZUCAR" in combo["datos"]["producto_pareja"]
    assert combo["datos"]["clientes"] >= 3
    assert combo["datos"]["lift"] >= patrones.MIN_LIFT


def test_demo_finds_the_saturday_shortfall():
    cards = _demo("__import__('core.patrones', fromlist=['x']).cards('es')")
    cash_card = next(c for c in cards if c["id"] == "faltante_caja_patron")
    assert cash_card["datos"]["dia_semana"] == 5
    assert cash_card["datos"]["pct_faltante"] > cash_card["datos"]["pct_faltante_resto"]
    assert cash_card["monto"] > 0


def test_pattern_cards_declare_an_alternative_explanation():
    """A correlation with no declared confounder is not high-confidence."""
    from core import patrones
    for c in patrones.cards("es"):
        ins = c["insight"]
        assert ins["pattern"]["label"]
        assert ins["alternatives"], f"{c['id']} states a correlation with no alternative"


def test_floor_reports_have_no_hypothesis():
    """A team member's report is an observation, not an inference."""
    from core import piso
    for c in piso.propuestas("es"):
        assert c["insight"]["pattern"]["label"]
        assert c["insight"]["hypothesis"] is None


def test_demo_does_not_move_the_oportunidades_canonicals():
    """The new module adds a source to the inbox; it does NOT rewrite the 10
    closed opportunities_neg findings or their recoverable total (test_p27/p38)."""
    out = _demo(
        "{'n': len(__import__('core.oportunidades_neg', fromlist=['x']).cards('es')),"
        " 'recuperable': __import__('core.oportunidades_neg', fromlist=['x']).recuperable("
        "__import__('core.oportunidades_neg', fromlist=['x']).cards('es'), 'es')['total']}")
    assert out["n"] == 10
    assert round(out["recuperable"]) == 156324231
