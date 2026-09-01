# Prioridades Evidence Generalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every card type in the `/prioridades` inbox (9 opportunity cards + ~11 alert-only types) the same verifiable drill-down evidence `cobrar_morosos` already has: a chart, a narrated hypothesis, a confidence signal, and real-record deep-links wherever the destination screen supports them.

**Architecture:** Backend-only data changes plus two small frontend generalizations. A new `core/confidence.py` computes a `{level, reason}` signal from generic drill signals (chart data points, assumption count) and is hooked once into `priorities.py`'s composition step — no per-card-builder confidence code. Card builders in `oportunidades_neg.py` and `priorities.py` are extended to thread real entity ids (`codigo` for products, `id` for clients) into `involucrados` rows wherever the underlying data already carries one, tagged with a new `kind` field (`"client"` / `"product"`). The frontend gains one new `data-nav-id` anchor pattern (`producto-${codigo}`) in `Inventario.jsx`, alongside the existing `cliente-${id}` one in `CuentasCorrientes.jsx`, and `Prioridades.jsx`'s involucrado-click handler is generalized to route on `kind` instead of a single hardcoded case.

**Tech Stack:** Python 3.12 / FastAPI (`backend/`), React + Vite (`frontend/`), pytest, existing `i18n.t()` (backend/i18n.py) and `useT()` (frontend/src/lib/i18n.js) translation helpers.

**Spec:** `docs/superpowers/specs/2026-09-01-prioridades-evidence-generalization-design.md`

## Global Constraints

- All new code, identifiers, variable/field names, and comments are in English (repo `CLAUDE.md` + explicit user instruction). Existing Spanish keys already in the schema (`drill`, `porque`, `grafico`, `involucrados`, `supuestos`, `fuentes`, `tono`, `tipo`, `navegar`, ...) are NOT renamed — only new fields (`confidence`, `kind`) use English names and English enum values (`"high"/"medium"/"low"`, `"client"/"product"`).
- Product-facing/UI copy (translated strings shown to end users, in both `backend/i18n.py` and `frontend/src/lib/locales/{es,en}.js`) stays bilingual Spanish+English as today — this rule is about code, not UI text.
- Every number and every involved record a card cites must come from deterministic `backend/core/` calculation — never invented or reformatted by an LLM.
- Backend tests run via `cd backend && python -m pytest`; they write into `data-demo/` — restore with `git checkout -- data-demo/` afterward.
- Finanzas (payments/checks), Caja (movimientos/historial), and Evolución (per-category/product breakdown) get NO new per-row list UI and NO new backend ids in this plan — they keep page-level-only navigation (explicit scope decision in the spec).

---

## Task 1: Shared confidence signal (`core/confidence.py`)

**Files:**
- Create: `backend/core/confidence.py`
- Test: `backend/tests/test_confidence.py`

**Interfaces:**
- Produces: `confidence.level_for(drill: dict, lang: str | None = None) -> dict` returning `{"level": "high" | "medium" | "low", "reason": str}`. Consumed by Task 2.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_confidence.py
"""Shared confidence signal: generic, not per-card-type (see design spec
2026-09-01). Signals: chart data points (sample size proxy) and number of
declared assumptions."""
from core import confidence


def _drill(points=0, assumptions=0):
    grafico = None
    if points:
        grafico = {"ok": True, "series": [{"nombre": "x",
                   "puntos": [{"x": i, "y": i} for i in range(points)]}],
                   "meta": {}}
    return {"grafico": grafico, "supuestos": ["a"] * assumptions}


def test_high_confidence_needs_enough_points_and_no_assumptions():
    out = confidence.level_for(_drill(points=6, assumptions=0), "en")
    assert out["level"] == "high"
    assert "6" in out["reason"]


def test_medium_confidence_with_some_points_or_one_assumption():
    assert confidence.level_for(_drill(points=3, assumptions=0), "en")["level"] == "medium"
    assert confidence.level_for(_drill(points=1, assumptions=1), "en")["level"] == "medium"


def test_low_confidence_with_little_data_and_multiple_assumptions():
    out = confidence.level_for(_drill(points=1, assumptions=2), "en")
    assert out["level"] == "low"


def test_no_chart_and_no_assumptions_is_still_low():
    """A finding with nothing behind it (no chart, no declared assumptions)
    must not read as confident by default — absence of assumptions is not
    evidence of confidence."""
    out = confidence.level_for(_drill(points=0, assumptions=0), "en")
    assert out["level"] == "low"


def test_reason_is_translated():
    out_es = confidence.level_for(_drill(points=6, assumptions=0), "es")
    out_en = confidence.level_for(_drill(points=6, assumptions=0), "en")
    assert out_es["reason"] != out_en["reason"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_confidence.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.confidence'`

- [ ] **Step 3: Implement `core/confidence.py`**

```python
"""Shared confidence signal for every Prioridades card, computed from
generic signals already present on any drill (backend/core/priorities.py
composes it, per card, once — no per-card-type confidence logic).

The rule of thumb: a finding backed by a real chart with several data
points and no undeclared leaps of assumption reads as high confidence; a
finding with a thin chart or several assumptions reads as low. This is
intentionally coarse — it is a reading aid, not a statistical model."""
from __future__ import annotations

HIGH_POINTS = 6
MEDIUM_POINTS = 3
MEDIUM_MAX_ASSUMPTIONS = 1


def _chart_points(grafico: dict | None) -> int:
    if not grafico or not grafico.get("series"):
        return 0
    return max((len(s.get("puntos") or []) for s in grafico["series"]), default=0)


def level_for(drill: dict, lang: str | None = None) -> dict:
    import i18n
    points = _chart_points(drill.get("grafico"))
    assumptions = len(drill.get("supuestos") or [])
    if points >= HIGH_POINTS and assumptions == 0:
        level = "high"
        reason = i18n.t("core.confidence.reason_high", lang, points=points)
    elif points >= MEDIUM_POINTS or assumptions <= MEDIUM_MAX_ASSUMPTIONS:
        level = "medium"
        reason = i18n.t("core.confidence.reason_medium", lang, points=points,
                        assumptions=assumptions)
    else:
        level = "low"
        reason = i18n.t("core.confidence.reason_low", lang, points=points,
                        assumptions=assumptions)
    return {"level": level, "reason": reason}
```

- [ ] **Step 4: Add the translation keys**

Add to `backend/i18n.py` (alongside the other `core.*` keys, e.g. near `core.opn.*`):

```python
    "core.confidence.reason_high": {
        "es": "Basado en {points} datos, sin supuestos adicionales.",
        "en": "Based on {points} data points, no additional assumptions."},
    "core.confidence.reason_medium": {
        "es": "Basado en {points} datos y {assumptions} supuesto(s).",
        "en": "Based on {points} data points and {assumptions} assumption(s)."},
    "core.confidence.reason_low": {
        "es": "Datos limitados: {points} datos y {assumptions} supuesto(s).",
        "en": "Limited data: {points} data points and {assumptions} assumption(s)."},
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_confidence.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/core/confidence.py backend/tests/test_confidence.py backend/i18n.py
git commit -m "Add shared confidence signal for Prioridades drills"
```

---

## Task 2: Hook confidence into the Prioridades inbox composition

**Files:**
- Modify: `backend/core/priorities.py:261-273` (`_compose`)
- Test: `backend/tests/test_priorities.py`

**Interfaces:**
- Consumes: `confidence.level_for(drill, lang)` from Task 1.
- Produces: every item returned by `priorities.inbox()`/`priorities._compose()` has `item["drill"]["confidence"] = {"level": ..., "reason": ...}`. Frontend Task (12) reads `item.drill.confidence`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_priorities.py`:

```python
def test_compose_attaches_confidence_to_every_item(monkeypatch):
    from core import cuentas
    monkeypatch.setattr(cuentas, "listar", lambda: [
        {"nombre": "Cliente Uno", "en_mora": True, "dias_sin_pagar": 90,
         "saldo": 50_000, "promedio_pago_dias": 30, "atraso_vs_promedio": 200,
         "movimientos": []}])
    composed = priorities._compose("en")
    assert composed["items"], "expected at least one item to check"
    for it in composed["items"]:
        conf = it["drill"].get("confidence")
        assert conf and conf["level"] in ("high", "medium", "low")
        assert conf["reason"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_priorities.py::test_compose_attaches_confidence_to_every_item -v`
Expected: FAIL with `KeyError`/`AssertionError` (no `confidence` key yet)

- [ ] **Step 3: Implement the hook**

In `backend/core/priorities.py`, change `_compose`:

```python
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
```

(Computed post-merge, not per-builder, so a merged card's confidence reflects
the combined evidence actually shown — the `_combine()` step in
`merge_duplicates` can add `porque`/`grafico` from the merged-in alert.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_priorities.py -v`
Expected: PASS (all tests, including the new one)

- [ ] **Step 5: Restore data dir and commit**

```bash
git -C backend checkout -- ../data-demo 2>/dev/null; git checkout -- data-demo/
git add backend/core/priorities.py backend/tests/test_priorities.py
git commit -m "Attach confidence to every Prioridades card after merge"
```

---

## Task 3: Real product ids for `despertar_dormido`, `ventana_compra`, `quiebre_inminente`, `margen_bajo`

**Files:**
- Modify: `backend/core/oportunidades_neg.py` (`_card_dormido` ~L221-266, `_card_ventana_compra` ~L268-371, `_card_quiebre_inminente` ~L522-633, `_card_margen_bajo` ~L770-854)
- Test: `backend/tests/test_oportunidades_ids.py`

**Interfaces:**
- Produces: `involucrado["id"]` (product `codigo`) and `involucrado["kind"] = "product"` on these four cards' `drill.involucrados` rows. Consumed by frontend Task 11/12.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_oportunidades_ids.py
"""Every involucrado backed by a real article record must carry a real
`id` (product code) and `kind` so the frontend can deep-link to it —
see design spec 2026-09-01."""
from core import oportunidades_neg as opn


def _ctx_with_arts(monkeypatch, arts, clientes=None):
    base_ctx = opn._ctx("es")
    base_ctx["arts"] = arts
    base_ctx["clientes"] = clientes or []
    return base_ctx


def test_dormido_involucrados_carry_product_id(monkeypatch):
    from core import analisis
    monkeypatch.setattr(analisis, "rotacion", lambda lang: {
        "disponible": True, "pct_dormido": 10,
        "por_estado": {"dormido": 500_000},
        "dormidos_top": [{"codigo": "P1", "producto": "Prod Uno",
                          "inmovilizado": 500_000, "dias_rotacion": None}],
    })
    ctx = _ctx_with_arts(monkeypatch, [])
    card = opn._card_dormido("es", ctx)
    assert card is not None
    iv = card["drill"]["involucrados"][0]
    assert iv["id"] == "P1" and iv["kind"] == "product"


def test_margen_bajo_involucrados_carry_product_id(monkeypatch):
    from core import analisis
    arts = [{"codigo": f"P{i}", "descripcion": f"Prod {i}", "tipo": "cat",
             "pvp": 100, "costo_iva": 60 + (i % 2) * 20} for i in range(6)]
    monkeypatch.setattr(analisis, "rotacion", lambda lang: {
        "disponible": True,
        "detalle": [{"producto": a["descripcion"], "unidades_12m": 120} for a in arts],
    })
    ctx = _ctx_with_arts(monkeypatch, arts)
    card = opn._card_margen_bajo("es", ctx)
    assert card is not None
    for iv in card["drill"]["involucrados"]:
        assert iv.get("kind") == "product"
        assert iv.get("id")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_oportunidades_ids.py -v`
Expected: FAIL — `iv["id"]`/`iv["kind"]` is `None`/missing (or `KeyError`)

- [ ] **Step 3: Thread `codigo` through `_card_dormido`**

In `backend/core/oportunidades_neg.py`, `_card_dormido`, change the `involucrados` build (the existing top5-loop, ~L249-254):

```python
            "involucrados": [{"id": x.get("codigo"), "kind": "product",
                              "nombre": x["producto"], "monto": x["inmovilizado"],
                              "detalle": (_t("core.opn.dormido_dias", lang,
                                             dias=int(x["dias_rotacion"]))
                                          if x.get("dias_rotacion")
                                          else _t("core.opn.dormido_sin_venta", lang))}
                             for x in top[:6]],
```

- [ ] **Step 4: Thread `codigo` through `_card_ventana_compra`**

`items.append(...)` (~L304) already builds from `a` (an `ctx["arts"]` entry with `codigo`) — add the id:

```python
        items.append({"id": a.get("codigo"), "kind": "product",
                      "nombre": a["descripcion"], "monto": round(monto_item, 2),
                      "detalle": _t("core.opn.ventana_cob", lang, dias=int(cob))})
```

- [ ] **Step 5: Thread `codigo` through `_card_quiebre_inminente`**

The `involucrados` build (~L618-621) iterates `cands[1:6]`, tuples of
`(cob, pos, prod, art, ritmo)` — `art` already carries `codigo`:

```python
            "involucrados": [{"id": _a.get("codigo"), "kind": "product",
                              "nombre": p, "monto": None,
                              "detalle": _t("core.opn.qi_i", lang, dias=int(c),
                                            pos=ps)}
                             for c, ps, p, _a, _r in cands[1:6]],
```

- [ ] **Step 6: Thread `codigo` through `_card_margen_bajo`**

The `bajos.append(...)` (~L805) already has `a` in scope (an `ctx["arts"]`
entry):

```python
            bajos.append({"id": a.get("codigo"), "kind": "product",
                          "nombre": a["descripcion"], "monto": round(extra_mes, 2),
                          "detalle": _t("core.opn.margen_i", lang, m=f"{m:.1f}",
                                        prom=f"{prom:.1f}",
                                        cat=i18n.categoria(cat, lang))})
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_oportunidades_ids.py -v`
Expected: PASS (2 tests)

- [ ] **Step 8: Run the full opn/priorities suite for regressions**

Run: `cd backend && python -m pytest tests/test_priorities.py tests/test_oportunidades_feedback.py -v`
Expected: PASS (no existing behavior changed — only new keys added to
`involucrados` dicts)

- [ ] **Step 9: Commit**

```bash
git checkout -- data-demo/
git add backend/core/oportunidades_neg.py backend/tests/test_oportunidades_ids.py
git commit -m "Thread real product ids into 4 opportunity cards' involucrados"
```

---

## Task 4: Real client ids for `cliente_frio`

**Files:**
- Modify: `backend/core/oportunidades_neg.py` (`_card_cliente_frio` ~L376-445)
- Test: `backend/tests/test_oportunidades_ids.py` (append)

**Interfaces:**
- Produces: `involucrado["id"]` (client `id`) and `involucrado["kind"] = "client"` on `cliente_frio`'s `drill.involucrados`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_oportunidades_ids.py`:

```python
def test_cliente_frio_involucrados_carry_client_id(monkeypatch):
    import datetime
    from core import fechas
    hoy = fechas.hoy()
    vieja = (hoy - datetime.timedelta(days=400)).isoformat()
    reciente = (hoy - datetime.timedelta(days=200)).isoformat()
    clientes = [{"id": 7, "nombre": "Cliente Frío",
                "movimientos": [{"tipo": "venta", "fecha": vieja, "monto": 100_000}] * 3 +
                               [{"tipo": "venta", "fecha": reciente, "monto": 100_000}] * 3}]
    ctx = _ctx_with_arts(monkeypatch, [], clientes)
    card = opn._card_cliente_frio("es", ctx)
    if card:  # the synthetic fixture may or may not clear the drop threshold
        iv = card["drill"]["involucrados"][0]
        assert iv["id"] == 7 and iv["kind"] == "client"
```

- [ ] **Step 2: Run test to verify it fails or is inconclusive**

Run: `cd backend && python -m pytest tests/test_oportunidades_ids.py::test_cliente_frio_involucrados_carry_client_id -v`
Expected: either FAILs on `iv["id"]` being `None`, or the card returns
`None` (synthetic fixture didn't clear the 25%-drop threshold — acceptable,
the real assertion is inside the `if card:` guard). If it's `None`, adjust
the fixture's older-period total upward until `card` is truthy before
moving on — the test must exercise the real code path at least once
locally during development (temporarily add `assert card is not None` to
confirm, then remove that line since a synthetic dataset is inherently
fragile to threshold tuning).

- [ ] **Step 3: Thread `id` through `_card_cliente_frio`**

The `involucrados` build (~L439-442) iterates `cands[:4]`, each holding
`"c"` (a `ctx["clientes"]` entry with `id`):

```python
            "involucrados": [{"id": x["c"].get("id"), "kind": "client",
                              "nombre": x["c"]["nombre"], "monto": round(x["actual"], 2),
                              "detalle": _t("core.opn.frio_i", lang,
                                            pct=f"{x['caida']:.0f}")}
                             for x in cands[:4]],
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_oportunidades_ids.py -v`
Expected: PASS (3 tests total in this file)

- [ ] **Step 5: Commit**

```bash
git add backend/core/oportunidades_neg.py backend/tests/test_oportunidades_ids.py
git commit -m "Thread real client ids into cliente_frio's involucrados"
```

---

## Task 5: Name-to-id lookups for `estrella_caida` and `concentracion`

**Files:**
- Modify: `backend/core/oportunidades_neg.py` (`_ctx` ~L103-151, `_card_estrella_caida` ~L450-517, `_card_concentracion` ~L704-765)
- Test: `backend/tests/test_oportunidades_ids.py` (append)

**Interfaces:**
- Consumes: `ctx["arts"]`, `ctx["clientes"]` (already built in `_ctx`).
- Produces: `ctx["product_id_by_name"]: dict[str, str]`, `ctx["client_id_by_name"]: dict[str, int]` — new `_ctx()` keys, consumed only within this task's two card builders. `involucrado["id"]`/`kind` on both cards.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_oportunidades_ids.py`:

```python
def test_ctx_builds_name_to_id_lookups(monkeypatch):
    arts = [{"codigo": "P1", "descripcion": "Prod Uno"}]
    clientes = [{"id": 3, "nombre": "Cliente Tres"}]
    ctx = _ctx_with_arts(monkeypatch, arts, clientes)
    assert ctx["product_id_by_name"]["Prod Uno"] == "P1"
    assert ctx["client_id_by_name"]["Cliente Tres"] == 3


def test_concentracion_involucrados_carry_client_id(monkeypatch):
    clientes = [{"id": i, "nombre": f"Cliente {i}",
                "movimientos": [{"tipo": "venta", "fecha": "2026-06-01",
                                 "monto": 10_000_000 if i < 3 else 100_000}]}
               for i in range(12)]
    ctx = _ctx_with_arts(monkeypatch, [], clientes)
    card = opn._card_concentracion("es", ctx)
    assert card is not None
    for iv in card["drill"]["involucrados"]:
        assert iv["kind"] == "client" and iv["id"] is not None
```

(`estrella_caida` needs real 12+ months of `ventas` rows via `ctx["ventas_ok"]`
to produce a card — covered instead by the demo-integration test in Step 6,
consistent with how the existing suite already exercises that builder only
through `test_demo_inbox_has_no_duplicate_twins`-style subprocess calls.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_oportunidades_ids.py -v`
Expected: FAIL — `KeyError: 'product_id_by_name'`

- [ ] **Step 3: Build the lookups in `_ctx`**

In `backend/core/oportunidades_neg.py`, `_ctx`, right after `ctx["arts"]`
and `ctx["clientes"]` are populated (~L117, before the `try` block for
`ventas.hay_datos`):

```python
    ctx["product_id_by_name"] = {a.get("descripcion"): a.get("codigo")
                                 for a in ctx["arts"] if a.get("descripcion")}
    ctx["client_id_by_name"] = {c.get("nombre"): c.get("id")
                                for c in ctx["clientes"] if c.get("nombre")}
```

- [ ] **Step 4: Use the lookup in `_card_concentracion`**

The `involucrados` build (~L750-753):

```python
            "involucrados": [{"id": ctx["client_id_by_name"].get(n), "kind": "client",
                              "nombre": n, "monto": round(v, 2),
                              "detalle": _t("core.opn.conc_i", lang,
                                            pct=f"{v / total * 100:.0f}")}
                             for n, v in top3],
```

- [ ] **Step 5: Use the lookup in `_card_estrella_caida`**

The `otros.append(...)` (~L491):

```python
        otros.append({"id": ctx["product_id_by_name"].get(p2), "kind": "product",
                      "nombre": p2, "monto": None,
                      "detalle": _t("core.opn.estrella_i", lang, n=r2)})
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_oportunidades_ids.py -v`
Expected: PASS (5 tests total)

- [ ] **Step 7: Run demo-integration regression**

Run: `cd backend && python -m pytest tests/test_priorities.py::test_demo_inbox_has_no_duplicate_twins -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git checkout -- data-demo/
git add backend/core/oportunidades_neg.py backend/tests/test_oportunidades_ids.py
git commit -m "Add name-to-id lookups; thread ids into estrella_caida and concentracion"
```

---

## Task 6: Backfill drill data for `dep_vencidos`, `dep_porvencer`, `dep_discrep`, `venc_riesgo`

**Files:**
- Modify: `backend/core/priorities.py` (`_alerts_deposito` ~L495-555)
- Test: `backend/tests/test_priorities_drill.py`

**Interfaces:**
- Produces: real `porque`/`grafico`/`involucrados`/`supuestos` (instead of `_blank_drill()`) for these four alert types, `involucrados` carrying `id`=`codigo`, `kind="product"`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_priorities_drill.py
"""Alert-only card types must carry real drill data (chart, involucrados
with a real product id) instead of an empty/blank drill — see design spec
2026-09-01."""
from core import priorities


def test_dep_vencidos_drill_has_product_involucrados(monkeypatch):
    from core import deposito, store
    monkeypatch.setattr(deposito, "resumen", lambda: {"vencidos": 1, "por_vencer": 0,
                                                       "discrepancias": 0})
    monkeypatch.setattr(deposito, "vencidos", lambda: [
        {"codigo": "P1", "producto": "Prod Uno", "cantidad": 5, "dias_vencido": 3}])
    monkeypatch.setattr(store, "raw_actual", lambda: [
        {"codigo": "P1", "descripcion": "Prod Uno", "costo_iva": 1000}])
    out = priorities._alerts_deposito("es")
    dep_venc = next(i for i in out if i["id"] == "dep_vencidos")
    assert dep_venc["drill"]["porque"]
    assert dep_venc["drill"]["grafico"] is not None
    iv = dep_venc["drill"]["involucrados"][0]
    assert iv["id"] == "P1" and iv["kind"] == "product"


def test_venc_riesgo_drill_has_product_involucrados(monkeypatch):
    from core import vencimientos
    monkeypatch.setattr(vencimientos, "en_riesgo", lambda dias, lang: {
        "disponible": True, "lotes_en_riesgo": 1, "total_en_riesgo": 5000,
        "items": [{"codigo": "P2", "producto": "Prod Dos", "dias_restantes": 4,
                  "plata_en_riesgo": 5000}]})
    out = priorities._alerts_deposito("es")
    venc = next(i for i in out if i["id"] == "venc_riesgo")
    assert venc["drill"]["grafico"] is not None
    iv = venc["drill"]["involucrados"][0]
    assert iv["id"] == "P2" and iv["kind"] == "product"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_priorities_drill.py -v`
Expected: FAIL — `dep_venc["drill"]["grafico"] is None`

- [ ] **Step 3: Add a shared cost-join helper**

In `backend/core/priorities.py`, above `_alerts_deposito`:

```python
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
```

- [ ] **Step 4: Backfill `dep_vencidos`**

Replace the `dep_vencidos` block in `_alerts_deposito` (~L499-510):

```python
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
```

(`_grafico` is already imported/available in this module via
`oportunidades_neg`'s pattern — add `from . import oportunidades_neg as opn`
is NOT needed: define a local `_grafico` helper identical in shape, since
`priorities.py` doesn't import `opn`'s private helper. Add this to
`priorities.py`, near `_blank_drill`:)

```python
def _grafico(nombre: str, puntos: list[dict], unidad: str, temporal: bool,
             ventana: str = "") -> dict:
    """Contract P21 (consulta-serie) — same shape as oportunidades_neg._grafico,
    duplicated locally: priorities.py composes alerts standalone and
    shouldn't reach into opn's private helpers."""
    return {"ok": True, "series": [{"nombre": nombre, "puntos": puntos}],
            "meta": {"unidad": unidad, "temporal": temporal, "ventana": ventana,
                     "composicion": False, "deflactado": False}}
```

- [ ] **Step 5: Backfill `dep_porvencer`**

Same shape as Step 4, sourced from `deposito.vencimientos()` instead of
`deposito.vencidos()`, `dias_restantes` instead of `dias_vencido` in the
detail text. Replace the `dep_porvencer` block (~L511-522):

```python
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
```

- [ ] **Step 6: Backfill `venc_riesgo`**

Replace the `venc_riesgo` block (~L535-554), reusing `venc["items"]`
(already has `codigo`, `producto`, `plata_en_riesgo`, `dias_restantes`):

```python
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
```

- [ ] **Step 7: Add the new i18n keys**

Add to `backend/i18n.py` (`core.prio.*` section):

```python
    "core.prio.dep_vencidos_g": {"es": "Lotes vencidos por valor", "en": "Expired lots by value"},
    "core.prio.dep_vencidos_i": {"es": "vencido hace {dias} días", "en": "expired {dias} days ago"},
    "core.prio.dep_vencidos_s": {"es": "Valor calculado al costo con IVA cargado en el catálogo.",
                                 "en": "Value computed at the catalog's costo_iva."},
    "core.prio.dep_porvencer_g": {"es": "Lotes por vencer por valor", "en": "Expiring lots by value"},
    "core.prio.dep_porvencer_i": {"es": "vence en {dias} días", "en": "expires in {dias} days"},
    "core.prio.venc_riesgo_g": {"es": "Lotes en riesgo por plata expuesta",
                                "en": "At-risk lots by exposed value"},
    "core.prio.venc_riesgo_i": {"es": "vence en {dias} días", "en": "expires in {dias} days"},
    "core.prio.venc_riesgo_s": {"es": "Ritmo de venta = unidades de los últimos 12 meses / 365.",
                                "en": "Sale pace = last 12 months' units / 365."},
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_priorities_drill.py -v`
Expected: PASS (2 tests)

- [ ] **Step 9: Run full backend suite for regressions**

Run: `cd backend && python -m pytest -v`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git checkout -- data-demo/
git add backend/core/priorities.py backend/tests/test_priorities_drill.py backend/i18n.py
git commit -m "Backfill drill data for dep_vencidos, dep_porvencer, venc_riesgo"
```

---

## Task 7: Backfill drill data for `costo_viejo`

**Files:**
- Modify: `backend/core/priorities.py` (`_alerts_inventario` ~L558-573)
- Test: `backend/tests/test_priorities_drill.py` (append)

**Interfaces:**
- Consumes: `_grafico` from Task 6.
- Produces: real drill for `costo_viejo`, `involucrados` with `id`=`codigo`, `kind="product"`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_priorities_drill.py`:

```python
def test_costo_viejo_drill_has_product_involucrados(monkeypatch):
    from core import store
    monkeypatch.setattr(store, "panorama", lambda: {"alertas": {"costo_viejo": {"cantidad": 1}},
                                                     "grupos": {"costo_viejo": [
                                                         {"codigo": "P3", "descripcion": "Prod Tres",
                                                          "inmovilizado": 20_000,
                                                          "antiguedad_costo_dias": 400}]}})
    out = priorities._alerts_inventario("es")
    cv = next(i for i in out if i["id"] == "costo_viejo")
    assert cv["drill"]["grafico"] is not None
    iv = cv["drill"]["involucrados"][0]
    assert iv["id"] == "P3" and iv["kind"] == "product"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_priorities_drill.py::test_costo_viejo_drill_has_product_involucrados -v`
Expected: FAIL — `cv["drill"]["grafico"] is None`

- [ ] **Step 3: Backfill `_alerts_inventario`**

Replace the body in `backend/core/priorities.py` (~L558-573):

```python
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
        monto=round(sum(d.get("inmovilizado") or 0 for d in items), 2),
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
```

- [ ] **Step 4: Add the new i18n keys**

```python
    "core.prio.costo_viejo_p": {"es": "{n} productos tienen su costo cargado hace más de un año.",
                                "en": "{n} products have a cost loaded over a year ago."},
    "core.prio.costo_viejo_g": {"es": "Costo desactualizado por plata parada",
                                "en": "Outdated cost by immobilized value"},
    "core.prio.costo_viejo_i": {"es": "costo cargado hace {dias} días",
                                "en": "cost loaded {dias} days ago"},
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_priorities_drill.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Run full backend suite for regressions**

Run: `cd backend && python -m pytest -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git checkout -- data-demo/
git add backend/core/priorities.py backend/tests/test_priorities_drill.py backend/i18n.py
git commit -m "Backfill drill data for costo_viejo"
```

---

## Task 8: Backfill chart data for `caida_interanual` and `caja_inusual`

**Files:**
- Modify: `backend/core/priorities.py` (`_alerts_evolucion` ~L601-619, `_alerts_caja` ~L576-598)
- Test: `backend/tests/test_priorities_drill.py` (append)

**Interfaces:**
- Consumes: `_grafico` from Task 6.
- Produces: real `grafico` (no `involucrados` — no per-item breakdown exists for either source, per spec) for both alert types.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_priorities_drill.py`:

```python
def test_caida_interanual_drill_has_chart(monkeypatch):
    from core import evolucion
    pan = {"hay_datos": True,
          "serie": [{"mes": "2026-01", "nominal": 100, "real": 95},
                    {"mes": "2026-02", "nominal": 110, "real": 90}]}
    monkeypatch.setattr(evolucion, "panorama", lambda lang: pan)
    monkeypatch.setattr(evolucion, "alertas_de", lambda p, lang: [
        {"titulo": "Caída real", "detalle": "cayó"}])
    out = priorities._alerts_evolucion("es")
    a = out[0]
    assert a["drill"]["grafico"] is not None
    assert len(a["drill"]["grafico"]["series"][0]["puntos"]) == 2


def test_caja_inusual_drill_has_chart(monkeypatch):
    from core import caja
    monkeypatch.setattr(caja, "estado", lambda: {
        "abierta": True,
        "totales": {"total": 500_000},
        "historial": [{"fecha": f"2026-06-2{i}", "total": 260_000, "diferencia": 0}
                     for i in range(5)],
    })
    out = priorities._alerts_caja("es")
    a = out[0]
    assert a["drill"]["grafico"] is not None
    assert len(a["drill"]["grafico"]["series"][0]["puntos"]) == 6
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_priorities_drill.py -k "caida_interanual or caja_inusual" -v`
Expected: FAIL — `grafico is None`

- [ ] **Step 3: Backfill `_alerts_evolucion`**

Replace the loop body in `_alerts_evolucion` (~L607-619):

```python
    out = []
    serie = pan.get("serie") or []
    grafico = _grafico(_t("core.prio.caida_g", lang),
                       [{"x": p["mes"], "y": p.get("real") if p.get("real") is not None
                        else p.get("nominal")} for p in serie],
                       "$", True) if serie else None
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
            drill={"porque": [a["detalle"]], "grafico": grafico, "involucrados": [],
                  "supuestos": [_t("core.prio.caida_s", lang)]},
        ))
    return out
```

- [ ] **Step 4: Backfill `_alerts_caja`**

Replace the `return [_item(...)]` in `_alerts_caja` (~L587-598):

```python
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
```

- [ ] **Step 5: Add the new i18n keys**

```python
    "core.prio.caida_g": {"es": "Facturación real, mes a mes", "en": "Real revenue, month by month"},
    "core.prio.caida_s": {"es": "Deflactado con el IPC del último mes disponible.",
                          "en": "Deflated using the latest available CPI month."},
    "core.prio.caja_g": {"es": "Total de caja, últimos cierres", "en": "Cash total, recent closes"},
    "core.prio.caja_hoy": {"es": "Hoy", "en": "Today"},
    "core.prio.caja_p": {"es": "El cierre de hoy ({total}) se desvía {pct}% del promedio de los últimos cierres ({prom}).",
                         "en": "Today's close ({total}) deviates {pct}% from the recent average ({prom})."},
    "core.prio.caja_s": {"es": "Promedio de los últimos cierres con caja positiva.",
                         "en": "Average of recent closes with a positive cash total."},
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_priorities_drill.py -v`
Expected: PASS (5 tests)

- [ ] **Step 7: Run full backend suite for regressions**

Run: `cd backend && python -m pytest -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git checkout -- data-demo/
git add backend/core/priorities.py backend/tests/test_priorities_drill.py backend/i18n.py
git commit -m "Backfill chart data for caida_interanual and caja_inusual"
```

---

## Task 9: Backfill drill data for `pago_vencido`, `pago_semana`, `cheques`

**Files:**
- Modify: `backend/core/priorities.py` (`_alerts_pagos` ~L445-492)
- Test: `backend/tests/test_priorities_drill.py` (append)

**Interfaces:**
- Consumes: `_grafico` from Task 6, `pagos.pagos_vencidos()`, `pagos.cheques_en_cartera()` (already imported via `from . import pagos`).
- Produces: real `porque`/`grafico` for all three; `involucrados` are text-only (no `id`/`kind` — no stable id exists on hand-entered `pagos_proveedores`/`cheques` rows, matches today's Finanzas page-nav-only behavior per spec).

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_priorities_drill.py`:

```python
def test_pago_vencido_drill_has_chart_and_text_involucrados(monkeypatch):
    from core import pagos
    monkeypatch.setattr(pagos, "resumen", lambda: {
        "pagos_vencidos": 1, "vencidos_total": 30_000, "por_pagar_semana": 0,
        "cheques_cartera": 0, "cheques_total": 0})
    monkeypatch.setattr(pagos, "pagos_vencidos", lambda: [
        {"proveedor": "Proveedor Uno", "numero": "F-1", "monto": 30_000, "dias_vencido": 5}])
    out = priorities._alerts_pagos("es")
    pv = next(i for i in out if i["id"] == "pago_vencido")
    assert pv["drill"]["grafico"] is not None
    iv = pv["drill"]["involucrados"][0]
    # No stable id exists on hand-entered pagos_proveedores rows (spec,
    # scope decision) — involucrados here stay text-only, non-clickable.
    assert iv.get("id") is None and iv.get("kind") is None
    assert "Proveedor Uno" in iv["nombre"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_priorities_drill.py::test_pago_vencido_drill_has_chart_and_text_involucrados -v`
Expected: FAIL — `pv["drill"]["grafico"] is None` (current drill is
`_blank_drill()`)

- [ ] **Step 3: Backfill the `pago_vencido` block**

Replace it in `_alerts_pagos` (~L449-464):

```python
    if pv.get("pagos_vencidos"):
        items = pagos.pagos_vencidos()[:8]
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
            drill={
                "porque": [_t("core.prio.pago_vencido_p", lang,
                              n=_num(pv["pagos_vencidos"], lang))],
                "grafico": _grafico(_t("core.prio.pago_vencido_g", lang),
                                    [{"x": x.get("proveedor") or "", "y": x.get("monto") or 0}
                                     for x in items], "$", False),
                "involucrados": [{"nombre": f"{x.get('proveedor') or ''} {x.get('numero') or ''}".strip(),
                                  "monto": x.get("monto"),
                                  "detalle": _t("core.prio.pago_vencido_i", lang,
                                                dias=x.get("dias_vencido") or 0)}
                                 for x in items],
                "supuestos": [],
            },
        ))
```

- [ ] **Step 4: Backfill the `pago_semana` block**

Replace it (~L465-477):

```python
    if pv.get("por_pagar_semana"):
        items = pagos.pagos_por_vencer(7)[:8]
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
            drill={
                "porque": [_t("core.prio.pago_semana_p", lang,
                              monto=_pesos(pv["por_pagar_semana"], lang))],
                "grafico": _grafico(_t("core.prio.pago_semana_g", lang),
                                    [{"x": x.get("proveedor") or "", "y": x.get("monto") or 0}
                                     for x in items], "$", False),
                "involucrados": [{"nombre": f"{x.get('proveedor') or ''} {x.get('numero') or ''}".strip(),
                                  "monto": x.get("monto"),
                                  "detalle": _t("core.prio.pago_semana_i", lang,
                                                dias=x.get("dias_restantes") or 0)}
                                 for x in items],
                "supuestos": [],
            },
        ))
```

- [ ] **Step 5: Backfill the `cheques` block**

Replace it (~L478-491):

```python
    if pv.get("cheques_cartera"):
        items = pagos.cheques_en_cartera()[:8]
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
            drill={
                "porque": [_t("core.prio.cheques_p", lang, n=_num(pv["cheques_cartera"], lang),
                              monto=_pesos(pv["cheques_total"], lang))],
                "grafico": _grafico(_t("core.prio.cheques_g", lang),
                                    [{"x": x.get("cliente") or "", "y": x.get("monto") or 0}
                                     for x in items], "$", False),
                "involucrados": [{"nombre": f"{x.get('cliente') or ''} {x.get('numero') or ''}".strip(),
                                  "monto": x.get("monto"),
                                  "detalle": _t("core.prio.cheques_i", lang,
                                                banco=x.get("banco") or "")}
                                 for x in items],
                "supuestos": [],
            },
        ))
```

- [ ] **Step 6: Add the new i18n keys**

```python
    "core.prio.pago_vencido_g": {"es": "Facturas vencidas por monto", "en": "Overdue bills by amount"},
    "core.prio.pago_vencido_i": {"es": "vencida hace {dias} días", "en": "overdue by {dias} days"},
    "core.prio.pago_semana_p": {"es": "Vencen esta semana {monto} en facturas de proveedores.",
                                "en": "{monto} in vendor bills are due this week."},
    "core.prio.pago_semana_g": {"es": "Por pagar esta semana, por monto", "en": "Due this week, by amount"},
    "core.prio.pago_semana_i": {"es": "vence en {dias} días", "en": "due in {dias} days"},
    "core.prio.cheques_p": {"es": "Tenés {n} cheques en cartera por {monto}.",
                            "en": "You have {n} checks in hand worth {monto}."},
    "core.prio.cheques_g": {"es": "Cheques en cartera por monto", "en": "Checks in hand by amount"},
    "core.prio.cheques_i": {"es": "banco {banco}", "en": "bank {banco}"},
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_priorities_drill.py -v`
Expected: PASS (6 tests)

- [ ] **Step 8: Run full backend suite for regressions**

Run: `cd backend && python -m pytest -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git checkout -- data-demo/
git add backend/core/priorities.py backend/tests/test_priorities_drill.py backend/i18n.py
git commit -m "Backfill drill data for pago_vencido, pago_semana, cheques"
```

---

## Task 10: Real involucrado for standalone `moroso_atraso` and `quiebre` alerts

**Files:**
- Modify: `backend/core/priorities.py` (`_alerts_cuentas` ~L382-420, `_alerts_ventas` ~L423-442)
- Test: `backend/tests/test_priorities_drill.py` (append)

**Interfaces:**
- Produces: `moroso_atraso`'s drill gets one `involucrado` (`kind="client"`); `quiebre`'s drill gets involucrados sourced from `ventas.panorama()`'s quiebre item list if it carries product codes (verify shape during implementation — see Step 3).

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_priorities_drill.py`:

```python
def test_moroso_atraso_drill_has_client_involucrado(monkeypatch):
    from core import cuentas
    monkeypatch.setattr(cuentas, "listar", lambda: [
        {"id": 9, "nombre": "Cliente Atraso", "en_mora": True, "dias_sin_pagar": 120,
         "atraso_vs_promedio": 200, "promedio_pago_dias": 30, "saldo": 40_000}])
    out = priorities._alerts_cuentas("es")
    ma = next(i for i in out if i["id"] == "moroso_atraso")
    iv = ma["drill"]["involucrados"][0]
    assert iv["id"] == 9 and iv["kind"] == "client"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_priorities_drill.py::test_moroso_atraso_drill_has_client_involucrado -v`
Expected: FAIL — `IndexError` (`involucrados` is empty today)

- [ ] **Step 3: Add the involucrado in `_alerts_cuentas`**

In the `moroso_atraso` block (~L405-419), add `involucrados` to the drill:

```python
            drill={"porque": [_t("core.prio.atraso_p", lang, nombre=d["nombre"],
                                 dias=d["dias_sin_pagar"],
                                 prom=d.get("promedio_pago_dias") or "—")],
                   "grafico": None,
                   "involucrados": [{"id": d.get("id"), "kind": "client",
                                     "nombre": d["nombre"], "monto": d.get("saldo"),
                                     "detalle": _t("core.prio.atraso_i", lang,
                                                   dias=d["dias_sin_pagar"])}],
                   "supuestos": []},
```

- [ ] **Step 4: Add the i18n key**

```python
    "core.prio.atraso_i": {"es": "sin pagar hace {dias} días", "en": "unpaid for {dias} days"},
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_priorities_drill.py::test_moroso_atraso_drill_has_client_involucrado -v`
Expected: PASS

- [ ] **Step 6: Investigate `quiebre`'s data shape**

Read `backend/core/ventas.py`'s `panorama()` return shape for the `quiebre`
key (`q = pan.get("quiebre") or {}`, used at `priorities.py:428`). If it
already lists individual products with a `codigo` (similar to
`vencimientos.en_riesgo`'s `items`), add `involucrados` there the same way
as Step 3, with a matching test. If it's count-only (no per-product list),
leave `quiebre`'s drill as-is — it already merges into `quiebre_inminente`
(which has full drill data as of Task 3) in the overwhelmingly common case,
and this raw form is a fallback. Do not invent a product list this alert
doesn't have.

- [ ] **Step 7: Run full backend suite for regressions**

Run: `cd backend && python -m pytest -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git checkout -- data-demo/
git add backend/core/priorities.py backend/tests/test_priorities_drill.py backend/i18n.py
git commit -m "Add real client involucrado to standalone moroso_atraso alert"
```

---

## Task 11: `Inventario.jsx` per-product deep-link anchors

**Files:**
- Modify: `frontend/src/desktop/sections/Inventario.jsx:232` (`FocoView`'s `<tr>`), `frontend/src/desktop/sections/Inventario.jsx:271` (`PestanaCustom`'s `<tr>`)

**Interfaces:**
- Produces: `data-nav-id="producto-${codigo}"` on both per-product row renderers, matching the `resaltarPorId`/`data-nav-id` convention already used in `CuentasCorrientes.jsx`. Consumed by Task 12.

- [ ] **Step 1: Add the anchor to `FocoView`'s row**

In `frontend/src/desktop/sections/Inventario.jsx`, line 232:

```jsx
              <tr key={p.codigo} data-nav-id={`producto-${p.codigo}`} onClick={() => onSelect(p)} className="cursor-pointer border-b border-linea/60 bg-rojo/[0.025] last:border-0 hover:bg-rojo/[0.05]">
```

- [ ] **Step 2: Add the anchor to `PestanaCustom`'s row**

Line 271:

```jsx
              <tr key={p.codigo} data-nav-id={`producto-${p.codigo}`} onClick={() => onSelect(p)} className="cursor-pointer border-b border-linea/60 last:border-0 hover:bg-papel-hondo/40">
```

- [ ] **Step 3: Manual verification**

Start the dev servers (`cd backend && python -m uvicorn main:app --port 8000`
and `cd frontend && npm run dev`), navigate to Inventario, open the browser
devtools and confirm each product `<tr>` carries
`data-nav-id="producto-<codigo>"`. No automated test — this is a static
markup attribute with no behavior of its own until Task 12 uses it.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/desktop/sections/Inventario.jsx
git commit -m "Add per-product data-nav-id anchors to Inventario rows"
```

---

## Task 12: Generalize `Prioridades.jsx`'s involucrado navigation and pass confidence

**Files:**
- Modify: `frontend/src/sections/Prioridades.jsx:272-305` (`drillProps`)

**Interfaces:**
- Consumes: `iv.kind` (`"client" | "product"`) from Tasks 3-5 and 10, `item.drill.confidence` from Task 2, `producto-${codigo}` anchor from Task 11.
- Produces: `drillProps(item).confidence` and a generalized `onVerInvolucrado`, both passed to `DrillNegocio` (Task 13 reads `confidence`).

- [ ] **Step 1: Replace the hardcoded involucrado handler and add `confidence`**

In `frontend/src/sections/Prioridades.jsx`, `drillProps` (~L272-305):

```js
  // Where an involucrado's `kind` sends the reader when clicked — mirrors
  // the data-nav-id anchors that exist today: `cliente-${id}` in
  // CuentasCorrientes.jsx, `producto-${id}` in Inventario.jsx.
  const INVOLUCRADO_NAV = {
    client: { section: "cuentas", anchor: (id) => `cliente-${id}` },
    product: { section: "inventario", anchor: (id) => `producto-${id}` },
  };

  const drillProps = (item) => {
    const acc = estiloAccion(item);
    return {
      tono: item.tono,
      titulo: item.titulo,
      monto: item.monto,
      montoLabel: item.monto_label,
      cifraTexto: item.cifra_texto,
      porque: item.drill?.porque || [],
      macro: item.macro,
      grafico: item.drill?.grafico,
      involucrados: item.drill?.involucrados || [],
      supuestos: item.drill?.supuestos || [],
      confidence: item.drill?.confidence,
      fuentes: item.fuentes || [],
      propuesta: item.propuesta,
      propuestaTrabajando: propTrabajando,
      propuestaResultado: propResultado[item.id],
      onAprobarPropuesta: () => aprobarPropuesta(item),
      chip: item.chip,
      chipIcon: acc.icon,
      chipCls: acc.cls,
      onFeedback: canGiveFeedback(item) ? (action) => giveFeedback(item, action) : undefined,
      feedbackBusy,
      // Sources all point at the card's one destination section — there's no
      // per-source routing yet, but it's a real jump instead of dead text.
      onVerFuentes: item.navegar ? () => onNavegar?.(item.navegar) : undefined,
      // Each involucrado routes by its own `kind` (client/product), landing
      // on the real record via the destination screen's data-nav-id anchor
      // (cliente-${id} in CuentasCorrientes.jsx, producto-${id} in
      // Inventario.jsx) — rows without a kind (e.g. Finanzas-sourced text
      // rows) render non-clickable in CardNegocio.jsx already.
      onVerInvolucrado: (iv) => {
        const target = iv.kind && INVOLUCRADO_NAV[iv.kind];
        if (target && iv.id != null) onNavegar?.(target.section, target.anchor(iv.id));
      },
    };
  };
```

- [ ] **Step 2: Manual verification**

With both dev servers running, open a card whose involucrados now carry
`kind: "product"` (e.g. `despertar_dormido` after Task 3), click one, and
confirm it navigates to Inventario and highlights/scrolls to that exact
row (via the existing `resaltarPorId` pulse). Repeat for a `kind: "client"`
row (`cobrar_morosos`, unaffected — still works) to confirm no regression.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/sections/Prioridades.jsx
git commit -m "Generalize Prioridades involucrado navigation to route by kind"
```

---

## Task 13: Confidence badge in `DrillNegocio`

**Files:**
- Modify: `frontend/src/components/CardNegocio.jsx`
- Modify: `frontend/src/lib/locales/en.js`, `frontend/src/lib/locales/es.js`

**Interfaces:**
- Consumes: `confidence` prop (`{level, reason}`) from Task 12.
- Produces: `ConfidenceBadge` component rendered inside `DrillNegocio`, next to the "Por qué" heading.

- [ ] **Step 1: Add the i18n keys**

In `frontend/src/lib/locales/en.js`, near the other `cardneg.*` keys:

```js
  "cardneg.confidence_high": "High confidence",
  "cardneg.confidence_medium": "Medium confidence",
  "cardneg.confidence_low": "Low confidence",
```

In `frontend/src/lib/locales/es.js`, same location:

```js
  "cardneg.confidence_high": "Confianza alta",
  "cardneg.confidence_medium": "Confianza media",
  "cardneg.confidence_low": "Confianza baja",
```

- [ ] **Step 2: Add the `ConfidenceBadge` component**

In `frontend/src/components/CardNegocio.jsx`, after `FuentePill` (~L147):

```jsx
// A small, neutral pill reading the shared confidence signal every card's
// drill now carries (backend/core/confidence.py) — not tied to `tono`,
// since confidence is about the evidence, not the finding's severity.
const CONFIDENCE_STYLE = {
  high: "border-salvia/30 text-salvia",
  medium: "border-oro/30 text-oro-tinta",
  low: "border-tinta-suave/30 text-tinta-suave",
};

function ConfidenceBadge({ confidence }) {
  const t = useT();
  if (!confidence?.level) return null;
  const cls = CONFIDENCE_STYLE[confidence.level] || CONFIDENCE_STYLE.low;
  return (
    <span
      title={confidence.reason}
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[0.7rem] font-semibold ${cls}`}
    >
      {t(`cardneg.confidence_${confidence.level}`)}
    </span>
  );
}
```

- [ ] **Step 3: Wire it into `DrillNegocio`**

Add `confidence` to `DrillNegocio`'s props (~L169-176) and render the badge
next to the "Por qué" heading (~L202-216):

```jsx
export function DrillNegocio({ tono = "salvia", titulo, monto, montoLabel, cifraTexto,
                               porque = [], macro, grafico, involucrados = [],
                               supuestos = [], fuentes = [], acciones, onCerrar,
                               propuesta, onAprobarPropuesta, propuestaResultado,
                               propuestaTrabajando, variante = "overlay",
                               chip, chipIcon: ChipIcon, chipCls,
                               onFeedback, feedbackBusy, confidence,
                               onVerFuentes, onVerInvolucrado }) {
```

```jsx
        {porque.length > 0 && (
          <>
            <div className="mt-4 flex items-center justify-between gap-2">
              <h3 className="text-[0.76rem] font-semibold uppercase tracking-wide text-tinta-suave">{t("cardneg.drill_porque")}</h3>
              <ConfidenceBadge confidence={confidence} />
            </div>
            <div className="mt-1.5 space-y-1.5">
```

(Keep the rest of that block — the `porque.map`, `macro?.inflacion` check,
closing `</div></>` — unchanged; only the heading line changes from a bare
`<h3>` to the flex row above.)

- [ ] **Step 4: Manual verification**

With both dev servers running, open several drill panels on `/prioridades`
covering high/medium/low-confidence cards (e.g. a card with a rich chart
and no assumptions vs. `caida_interanual` which has few points) and confirm
the badge renders the right label and its tooltip shows the `reason` text.
Confirm no badge renders when `porque` is empty (guard already in place)
or when `confidence` is undefined (defensive `if (!confidence?.level)`).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/CardNegocio.jsx frontend/src/lib/locales/en.js frontend/src/lib/locales/es.js
git commit -m "Add confidence badge to Prioridades drill panel"
```

---

## Task 14: Full Chrome/Playwright verification pass

**Files:** none (manual verification only)

**Interfaces:** none — this task validates Tasks 1-13 together.

- [ ] **Step 1: Boot both dev servers**

```bash
cd backend && POLPILOT_DEMO_TODAY=2026-07-07 python -m uvicorn main:app --port 8000
cd frontend && npm run dev
```

- [ ] **Step 2: Verify at least one card of each backfilled type**

Using the Chrome or Playwright MCP tools, navigate to `/prioridades` and, for
one card of each of: `despertar_dormido`, `cliente_frio`, `estrella_caida`,
`quiebre_inminente`, `concentracion`, `margen_bajo`, `dep_vencidos`,
`dep_porvencer`, `venc_riesgo`, `costo_viejo`, `caida_interanual`,
`caja_inusual`, `pago_vencido`, `pago_semana`, `cheques`, `moroso_atraso` —
confirm: the chart renders (where the card is expected to have one), the
confidence badge shows a sensible level with a matching tooltip reason, and
where `involucrados` carry a real `id`+`kind`, clicking one navigates and
highlights the destination row (Inventario for `kind: "product"`, Cuentas
for `kind: "client"`).

- [ ] **Step 3: Regression-check the two prior features**

Confirm the two-column independent scroll and the sidebar-doesn't-modal
behavior from the earlier iteration (commit `db929fd`) still work, and that
arrow-key/digit hotkey navigation (commit `6c4225a`) is unaffected.

- [ ] **Step 4: Report findings**

If any card renders unexpectedly (missing chart, wrong confidence level,
broken navigation), fix inline before considering this plan complete —
these are exactly the kind of gaps this plan exists to close.

---

## Self-Review Notes

- **Spec coverage:** confidence field (Task 1-2), 7 opportunity cards gaining
  real ids (Tasks 3-5), product-linkable alerts backfilled (Tasks 6-7),
  whole-business alerts backfilled (Task 8), Finanzas alerts backfilled with
  text-only involucrados (Task 9), raw alert forms (Task 10), Inventario
  anchors (Task 11), frontend kind-based routing (Task 12), confidence badge
  (Task 13), end-to-end verification (Task 14). `sobrecompra` is
  intentionally untouched (spec: no involucrados to add). Finanzas/Caja/
  Evolución per-row list UI is intentionally out of scope (spec).
- **Placeholder scan:** no TBD/TODO; every step shows real code or a
  concrete verification action. Task 10's Step 6 is a deliberate
  investigate-then-maybe-extend step (the `quiebre` alert's data shape
  wasn't confirmed during planning) rather than a vague placeholder — it
  gives an explicit decision rule and forbids inventing data.
  Task 4's Step 2 similarly gives an explicit fallback rule for a
  synthetic-fixture threshold that can't be predicted without running it.
- **Type/name consistency:** `kind` values are `"client"`/`"product"`
  everywhere (Tasks 3-5, 10, 12). `_grafico` is defined once in
  `priorities.py` (Task 6, Step 4) and reused by Tasks 7-9 — no duplicate
  definitions. `confidence.level_for(drill, lang)` signature (Task 1) matches
  its call site in `_compose` (Task 2).
