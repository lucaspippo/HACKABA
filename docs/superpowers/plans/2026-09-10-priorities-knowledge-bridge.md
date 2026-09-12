# Priorities Knowledge Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a `conocimiento` piece a real, citable, weighted piece of `insight.py` evidence — replacing two anti-patterns already live in production (`oportunidades_neg.py` citing knowledge as an `assumption`, which *lowers* confidence for having good business context, and a `metric()`-with-null-value workaround) — and give it a real node in `grafo.py` instead of flat metadata.

**Architecture:** Four PRs, stacked after `pr4-knowledge-decay` (this plan's first task hard-depends on `conocimiento.decay_score`/`freshness`/`needs_review` from the sibling plan's Task 4 — do not start Task 1 here before that lands). Continues the same `gh stack` chain.

**Tech Stack:** Same as the sibling plan — FastAPI, SQLAlchemy Core, pytest, React/TS.

**Spec:** `docs/superpowers/specs/2026-09-10-priorities-knowledge-bridge-design.md`

## Global Constraints

- Same English-identifiers rule as the sibling plan. Evidence `kind` value is `"knowledge"` (English, matching `"metric"`/`"records"`/`"series"`).
- Knowledge evidence counts toward `confidence.py`'s `data` axis only, never `hypothesis` — never appended to an insight's `assumptions`/`alternatives` list.
- No new confidence threshold constant — reuses `DATA_MEDIUM_RECORDS`/`DATA_HIGH_POINTS` already in `confidence.py`.
- `sources_stale` is `True` when **any** cited knowledge evidence is currently stale — never "all."
- This plan does not touch `insight.py`'s existing `metric()`/`records()`/`series()` constructors or their call sites, except the one documented case in Task 2 where an existing `metric()` call is a workaround being replaced by the new `knowledge()` constructor for the same citation.
- Run backend tests with `../.venv/Scripts/python.exe -m pytest` from `backend/`, never bare `python`.

## Stacking

```bash
gh stack checkout pr4-knowledge-decay   # base for this plan's first branch
gh stack add pr7-insight-knowledge-evidence   # after Task 1's commit
```

Continue `gh stack add pr8-...`, `pr9-...`, `pr10-...` after each subsequent task.

---

### Task 1: `insight.knowledge()` + `confidence.py` wiring

**Files:**
- Modify: `backend/core/insight.py` (new `knowledge()` constructor)
- Modify: `backend/core/confidence.py` (`_insight_record_count`, new `_sources_stale`, wire into `split_for`)
- Test: `backend/tests/test_confidence.py` (extend), new assertions in a new `backend/tests/test_insight_knowledge.py`

**Interfaces:**
- Consumes: `core.conocimiento.freshness(piece, *, today=None) -> str` and `core.conocimiento.needs_review(piece, *, today=None) -> bool` — both from the sibling plan's Task 4. **Do not start this task until those exist on the branch this stacks on.**
- Produces: `insight.knowledge(piece: dict, *, weight: str = "supporting") -> dict`. Used by Tasks 2-3.

- [ ] **Step 1: Failing test — `insight.knowledge()`'s shape**

```python
# backend/tests/test_insight_knowledge.py (new file)
import pytest

from core import conocimiento, insight
from tests.conftest import limpiar_tabla_tenant


@pytest.fixture(autouse=True)
def limpio():
    limpiar_tabla_tenant("business_knowledge_pieces")
    yield
    limpiar_tabla_tenant("business_knowledge_pieces")


def _pieza(**over):
    base = dict(texto="Tolerale 45 días", tipo="regla", ambito="cliente",
               nodo="clientes", efecto="ajusta_umbral", entidad="Doña Elsa")
    base.update(over)
    return conocimiento.crear(**base)


def test_knowledge_evidence_has_the_right_shape():
    p = _pieza()
    ev = insight.knowledge(p)
    assert ev["kind"] == "knowledge"
    assert ev["id"] == p["id"]
    assert ev["label"] == p["texto"]
    assert ev["weight"] == "supporting"
    assert ev["origen"] == p["origen"]
    assert ev["freshness"] in ("fresco", "atencion", "revisar")
    assert isinstance(ev["needs_review"], bool)


def test_knowledge_evidence_rejects_a_bad_weight():
    p = _pieza()
    with pytest.raises(ValueError):
        insight.knowledge(p, weight="load-bearing")


def test_knowledge_evidence_reflects_current_decay_not_build_time_decay():
    """freshness()/needs_review() are read from conocimiento at the moment
    knowledge() is called — this test just confirms the wiring calls
    through, the decay MATH itself is tested in test_conocimiento_decay.py."""
    p = _pieza()
    ev = insight.knowledge(p)
    assert ev["freshness"] == conocimiento.freshness(p)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_insight_knowledge.py -v`
Expected: FAIL — `AttributeError: module 'core.insight' has no attribute 'knowledge'`.

- [ ] **Step 3: Implement**

```python
# backend/core/insight.py — add after series() (after line 119)
def knowledge(piece: dict, *, weight: str = "supporting") -> dict:
    """A conocimiento piece cited as evidence. `piece` is the dict as
    returned by conocimiento.listar()/aplicables()/para()/detalle() — this
    function reads it, never mutates it. Freshness is derived HERE, not
    stored on the evidence item at build time, so it always reflects the
    piece's CURRENT decay state when this insight is read, not whenever it
    happened to be built."""
    from . import conocimiento
    if weight not in WEIGHTS:
        raise ValueError(f"weight must be one of {WEIGHTS}, got {weight!r}")
    return {
        "id": piece["id"], "kind": "knowledge", "label": piece["texto"],
        "value": None, "unit": None, "baseline": None, "deviation": None,
        "weight": weight, "method": {"source": "conocimiento", "tipo": piece["tipo"]},
        "records": [], "chart": None,
        "origen": piece.get("origen") or {},
        "freshness": conocimiento.freshness(piece),
        "needs_review": conocimiento.needs_review(piece),
    }
```

- [ ] **Step 4: Run to verify it passes**

Same command as Step 2. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/core/insight.py backend/tests/test_insight_knowledge.py
git commit -m "feat: add insight.knowledge() evidence constructor"
```

- [ ] **Step 6: Failing test — `confidence.py` counts knowledge evidence and computes `sources_stale`**

```python
# backend/tests/test_confidence.py — extend the _insight() helper and add tests
def _insight(*, points=0, records=0, assumptions=0, alternatives=0, knowledge=()):
    ev = []
    if points:
        ev.append(insight.series("s", label="l", chart=_chart(points),
                                 method={"key": "k", "label": "l"}))
    if records:
        ev.append(insight.records(
            "r", label="l",
            rows=[insight.record(kind="client", id=i, name=str(i)) for i in range(records)],
            method={"key": "k", "label": "l"}))
    for k in knowledge:
        ev.append(k)
    return insight.build(
        pattern=insight.pattern("p"),
        evidence=ev,
        assumptions=[insight.assumption(f"a{i}") for i in range(assumptions)],
        alternatives=[insight.caveat(f"c{i}") for i in range(alternatives)],
    )


def _knowledge_evidence(*, fresh: bool) -> dict:
    """A hand-built knowledge-kind evidence item, bypassing insight.knowledge()
    (which needs a real DB-backed piece) — confidence.py only needs the
    evidence dict's shape, not a live piece."""
    return {"id": "k01", "kind": "knowledge", "label": "x", "value": None,
            "unit": None, "baseline": None, "deviation": None, "weight": "supporting",
            "method": {"source": "conocimiento", "tipo": "regla"}, "records": [], "chart": None,
            "origen": {}, "freshness": "fresco" if fresh else "revisar",
            "needs_review": not fresh}


def test_knowledge_evidence_counts_toward_data_confidence():
    c = confidence.split_for(_insight(knowledge=[_knowledge_evidence(fresh=True),
                                                 _knowledge_evidence(fresh=True)]))
    assert c["data"]["level"] == "medium"  # 2 knowledge items == DATA_MEDIUM_RECORDS
    assert c["data"]["signals"]["record_count"] == 2


def test_knowledge_evidence_never_affects_hypothesis_confidence():
    c = confidence.split_for(_insight(knowledge=[_knowledge_evidence(fresh=True)]))
    assert c["hypothesis"]["level"] == "high"  # no assumptions/alternatives declared


def test_sources_stale_true_when_any_cited_knowledge_needs_review():
    c = confidence.split_for(_insight(
        knowledge=[_knowledge_evidence(fresh=True), _knowledge_evidence(fresh=False)]))
    assert c["data"]["signals"]["sources_stale"] is True


def test_sources_stale_false_with_no_stale_knowledge():
    c = confidence.split_for(_insight(knowledge=[_knowledge_evidence(fresh=True)]))
    assert c["data"]["signals"]["sources_stale"] is False


def test_sources_stale_false_with_no_knowledge_evidence_at_all():
    c = confidence.split_for(_insight(points=12))
    assert c["data"]["signals"]["sources_stale"] is False
```

- [ ] **Step 7: Run to verify it fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_confidence.py -v`
Expected: the five new tests FAIL — `record_count` doesn't count knowledge items yet, `sources_stale` is hardcoded `False`.

- [ ] **Step 8: Implement**

```python
# backend/core/confidence.py — replace _insight_record_count (lines 37-38)
def _insight_record_count(insight: dict) -> int:
    """Real rows give breadth; a cited knowledge piece is as much "a real
    thing behind this" as a database row, so it counts the same way."""
    from_records = sum(len(ev.get("records") or []) for ev in insight.get("evidence") or [])
    from_knowledge = sum(1 for ev in insight.get("evidence") or [] if ev.get("kind") == "knowledge")
    return from_records + from_knowledge


def _sources_stale(insight: dict) -> bool:
    """True when ANY cited knowledge evidence is due for review — errs
    toward surfacing the caveat, same "declare it and let confidence show
    it" philosophy as _hypothesis_level."""
    return any(ev.get("needs_review") for ev in insight.get("evidence") or []
              if ev.get("kind") == "knowledge")
```

```python
# backend/core/confidence.py — split_for() (lines 64-91), change the "sources_stale": False
# line inside the "data" dict's "signals" to:
                "signals": {"chart_points": points, "record_count": records,
                            "sources_stale": _sources_stale(insight),
                            "missing": []},
```

- [ ] **Step 9: Run to verify it passes**

Same command as Step 7. Expected: PASS (all `test_confidence.py` tests, old and new).

- [ ] **Step 10: Commit**

```bash
git add backend/core/confidence.py backend/tests/test_confidence.py
git commit -m "feat: knowledge evidence counts toward data confidence and drives sources_stale"
```

- [ ] **Step 11: Add to the stack**

```bash
gh stack add pr7-insight-knowledge-evidence
```

---

### Task 2: Wire the four `oportunidades_neg.py` call sites that already build insights

**Files:**
- Modify: `backend/core/oportunidades_neg.py` (four call sites: `_card_dormido` ~line 307, `_card_ventana_compra` ~line 389, the quiebre-inminente builder ~line 679-781, the concentración builder ~line 937)
- Test: extend whichever test file already covers these cards (`grep -rln "_card_dormido\|cobrar_morosos\|quiebre_inminente\|concentracion" backend/tests/` — likely `test_p27.py` and/or `test_oportunidades_ids.py`; add cases there rather than creating a new file, matching existing coverage organization)

**Interfaces:**
- Consumes: `insight.knowledge()` from Task 1.
- Produces: nothing new consumed elsewhere — this task only changes what these four cards' `insight.evidence` contains.

This task replaces two existing anti-patterns (grep-verified 2026-09-10, exact lines cited):

1. **`_card_dormido` (line 305-312):** a knowledge piece is currently appended to `assunciones` (assumptions) — which, per `confidence._hypothesis_level`, *lowers* confidence for having a taught exception on record. Fix: cite it as evidence instead.
2. **The quiebre-inminente builder (lines 774-780):** already avoids the assumptions anti-pattern, but works around the lack of a dedicated evidence kind by using `ins.metric(..., value=None, unit=None, ...)` — a generic metric with no actual value. Fix: use the real `ins.knowledge()` constructor, which also carries `origen`/`freshness` that the metric workaround couldn't.
3. **`_card_ventana_compra` (lines 385-403):** two pieces (`ctx_suba`, `regla_viernes`) currently appended to `supuestos` (assumptions) — same anti-pattern as #1.
4. **The concentración builder (lines 934-941):** one piece appended to `asunciones` (assumptions) — same anti-pattern as #1.

- [ ] **Step 1: Failing test — dormido card cites knowledge as evidence, not as an assumption**

```python
# add to whichever file already tests _card_dormido / the "despertar_dormido" card
# (check test_p27.py first)
def test_dormido_cites_the_cleanup_exception_as_evidence_not_assumption():
    from core import conocimiento
    conocimiento.crear(texto="El stock de limpieza fue compra por precio", tipo="contexto",
                       ambito="categoria", nodo="inventario", efecto="contexto_para_angela",
                       entidad="limpieza")
    # (use this test file's existing fixture/tenant setup to get a "dormido" card —
    # follow the same setup any neighboring passing test in this file already uses)
    card = ...  # obtain the despertar_dormido card the same way an existing test does
    evidence_kinds = [ev["kind"] for ev in card["insight"]["evidence"]]
    assumption_labels = [a["label"] for a in card["insight"]["assumptions"]]
    assert "knowledge" in evidence_kinds
    assert not any("limpieza" in (lbl or "") for lbl in assumption_labels)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest -k dormido_cites_the_cleanup -v`
Expected: FAIL — the piece is still in `assumptions`, not in `evidence`.

- [ ] **Step 3: Implement — `_card_dormido`**

```python
# backend/core/oportunidades_neg.py:305-312 — replace
    # Piece 14 — el dormido de limpieza fue una compra por precio, no un error:
    # el hallazgo lo distingue del resto, citado como evidencia (nunca como
    # assumption: una regla del dueño no es un salto interpretativo que baja
    # confianza, es una fuente más).
    k_dorm = [p for p in conocimiento.aplicables(nodo="inventario", efecto="contexto_para_angela")
              if "limpieza" in conocimiento._norm(p.get("entidad"))]
    if k_dorm:
        evidencia.append(ins.knowledge(k_dorm[0]))
        card["conocimiento_aplicado"] = [conocimiento.resumen_pieza(p) for p in k_dorm]
```

(Removes the `assunciones.append(ins.assumption(...))` call; `card["conocimiento_aplicado"]`, used by the frontend citation chip independent of `insight`, is unchanged. Confirm `evidencia` is already in scope at this point in the function — it is, per the existing `evidence=evidencia` in this function's `ins.build()` call at line 317.)

- [ ] **Step 4: Run to verify it passes**

Same command as Step 2. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/core/oportunidades_neg.py
git commit -m "fix: cite the dormant-stock exception as evidence, not an assumption"
```

- [ ] **Step 6: Failing test — quiebre-inminente cites knowledge via the dedicated constructor**

```python
# add near the dormido test
def test_quiebre_inminente_cites_knowledge_not_a_null_metric():
    from core import conocimiento
    conocimiento.crear(texto="GASEOSA COLA nunca puede quebrar", tipo="regla",
                       ambito="categoria", nodo="inventario", efecto="genera_alerta",
                       entidad="GASEOSA COLA LA RIBERA")
    card = ...  # obtain the quiebre_inminente card for that product, same setup pattern
    kinds = [ev["kind"] for ev in card["insight"]["evidence"]]
    assert kinds[0] == "knowledge"  # still first, same priority as before
    assert card["chip_conocimiento"]  # unchanged UI behavior
```

- [ ] **Step 7: Run to verify it fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest -k quiebre_inminente_cites_knowledge -v`
Expected: FAIL — `kinds[0] == "metric"`, not `"knowledge"`.

- [ ] **Step 8: Implement — the quiebre-inminente builder**

```python
# backend/core/oportunidades_neg.py:770-781 — replace
    if piezas_k:
        # chip "Regla de Aldo: crítico" + la regla PRIMERO en la evidencia (misma
        # jerarquía que el viejo porque.insert(0, ...)) + el nodo de conocimiento
        # para el camino en el mapa (E3). Antes esto era un ins.metric() con
        # value=None como workaround; ins.knowledge() es el constructor real,
        # y además carga origen/freshness que el workaround no podía.
        card["chip_conocimiento"] = _t("core.opn.qi_k_chip", lang)
        evidencia.insert(0, ins.knowledge(piezas_k[0], weight="primary"))
        card["conocimiento_aplicado"] = [conocimiento.resumen_pieza(p) for p in piezas_k]
```

- [ ] **Step 9: Run to verify it passes**

Same command as Step 7. Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add backend/core/oportunidades_neg.py
git commit -m "fix: quiebre-inminente cites knowledge via insight.knowledge(), not a null metric"
```

- [ ] **Step 11: Failing test — concentración cites knowledge as evidence, not an assumption**

```python
def test_concentracion_cites_knowledge_as_evidence():
    from core import conocimiento
    conocimiento.crear(texto="El riesgo es de concentración, no de cobro", tipo="contexto",
                       ambito="global", nodo="clientes", efecto="contexto_para_angela",
                       params={"marca": "concentracion"})
    card = ...  # obtain the "concentracion" card, same setup pattern as its existing tests
    kinds = [ev["kind"] for ev in card["insight"]["evidence"]]
    labels = [a["label"] for a in card["insight"]["assumptions"]]
    assert "knowledge" in kinds
    assert not any("concentrac" in (lbl or "").lower() for lbl in labels)
```

- [ ] **Step 12: Run to verify it fails, then implement**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest -k concentracion_cites_knowledge -v`
Expected: FAIL.

```python
# backend/core/oportunidades_neg.py:934-947 — replace
    # Piece 4 — el matiz de Aldo: son los que pagan en fecha, el riesgo es de
    # concentración, no de cobro. Reencuadra la card sin cambiar el número —
    # citado como evidencia, nunca como assumption.
    asunciones = []
    k_conc = [p for p in conocimiento.aplicables(nodo="clientes", efecto="contexto_para_angela")
              if p.get("ambito") == "global" and (p.get("params") or {}).get("marca") == "concentracion"]
    if k_conc:
        card["conocimiento_aplicado"] = [conocimiento.resumen_pieza(p) for p in k_conc]
    insight_val = ins.build(
        pattern=ins.pattern(_t("core.opn.conc_q1", lang, pct=f"{pct:.0f}",
                               monto=_pesos(monto, lang)),
                            scope={"kind": "clients", "count": 3}),
        evidence=[
            ins.metric("client_concentration_pct",
                       label=_t("core.opn.client_concentration_lbl", lang), value=round(pct, 1),
```

(Continue: after this `ins.metric(...)` entry and whatever else is already in that inline `evidence=[...]` list, add `*([ins.knowledge(k_conc[0])] if k_conc else []),` as the list's last element before its closing `]`. The exact remaining lines of this `evidence=[...]` list weren't re-quoted here — open `oportunidades_neg.py` at line 943 and extend the existing list literal; do not replace anything below what's shown above. Also remove `assumptions=asunciones` from this `ins.build()` call if `asunciones` is now always empty — check the rest of the function for any other assumption this card declares before deciding whether to drop the parameter entirely or just pass the now-shorter list.)

- [ ] **Step 13: Run to verify it passes**

Same command as Step 12. Expected: PASS.

- [ ] **Step 14: Commit**

```bash
git add backend/core/oportunidades_neg.py
git commit -m "fix: concentracion cites knowledge as evidence, not an assumption"
```

- [ ] **Step 15: Failing test — ventana_compra cites both pieces as evidence**

```python
def test_ventana_compra_cites_the_supplier_rules_as_evidence():
    from core import conocimiento
    conocimiento.crear(texto="No pedirle los viernes", tipo="regla", ambito="proveedor",
                       nodo="proveedores", efecto="contexto_para_angela",
                       entidad="<the fixture's supplier name>", params={"evitar_dia": "viernes"})
    card = ...  # obtain the ventana_compra card, same setup as its existing tests
    kinds = [ev["kind"] for ev in card["insight"]["evidence"]]
    assert "knowledge" in kinds
```

- [ ] **Step 16: Run to verify it fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest -k ventana_compra_cites -v`
Expected: FAIL.

- [ ] **Step 17: Implement — `_card_ventana_compra`**

```python
# backend/core/oportunidades_neg.py:385-403 — replace the assumption-building lines
    # Pieces 7+8 — lo que Aldo enseñó sobre este proveedor, citado como
    # evidencia (no como assumption: no es un salto interpretativo).
    piezas_prov = conocimiento.para(prov, nodo="proveedores")
    regla_viernes = next((p for p in piezas_prov
                          if (p.get("params") or {}).get("evitar_dia") == "viernes"), None)
    ctx_suba = next((p for p in piezas_prov if p["tipo"] == "contexto"), None)
    base_dia = hoy if dias_hasta <= 3 else proxima
    dia_pedido, movido = base_dia, False
    if regla_viernes and base_dia.weekday() == 4:  # 4 = viernes
        dia_pedido, movido = base_dia - datetime.timedelta(days=1), True  # al jueves
    conocimiento_evidencia = ([ins.knowledge(ctx_suba)] if ctx_suba else []) + \
                             ([ins.knowledge(regla_viernes)] if regla_viernes else [])
    aplicadas = ([conocimiento.resumen_pieza(ctx_suba)] if ctx_suba else []) + \
                ([conocimiento.resumen_pieza(regla_viernes)] if regla_viernes else [])
```

Then: `grep -n "ins.build(" backend/core/oportunidades_neg.py` to find `_card_ventana_compra`'s own build call (between this point and the function's `return`), and add `evidence=[..., *conocimiento_evidencia]` there — extend whatever `evidence` list/expression that call already passes rather than replacing it; if that call already passes a plain list variable (not inline), append `conocimiento_evidencia` to it right before the `ins.build()` call instead: `evidencia_ventana.extend(conocimiento_evidencia)` (name it to match whatever the existing variable is actually called there).

- [ ] **Step 18: Run to verify it passes**

Same command as Step 16. Expected: PASS.

- [ ] **Step 19: Commit**

```bash
git add backend/core/oportunidades_neg.py
git commit -m "fix: ventana_compra cites supplier rules as evidence, not assumptions"
```

- [ ] **Step 20: Add to the stack**

```bash
gh stack add pr8-oportunidades-knowledge-evidence
```

---

### Task 3: Wire `cuentas.py`'s tolerance rule into `cobrar_morosos`; confirm the remaining three call sites stay out of scope

**Files:**
- Modify: `backend/core/cuentas.py` (`_enriquecer`, ~line 105-126)
- Modify: `backend/core/oportunidades_neg.py` (`cobrar_morosos`'s insight builder, ~line 150-234)
- No change: `backend/core/conciliacion.py`, `backend/core/deposito.py`, `backend/core/pagos.py` — see rationale below
- Test: extend the `cobrar_morosos` test coverage (check `test_p25.py`/`test_oportunidades_ids.py` for existing cases)

**Why the other three sites are out of scope (confirmed 2026-09-10, not deferred by assumption):**

- **`conciliacion.py:72`** (`_umbral_tara`) — feeds `_hip()`, conciliación's OWN hypothesis shape (`{clase, confianza, acciones, evidencia, params}`, `confidence.py:56-67`), never `insight.py`. No insight exists here to attach evidence to.
- **`deposito.py:197-219`** (`discrepancias_conocimiento`) — returns `{visibles, suprimidas, reglas}`, a discrepancies list where each suppressed row already carries `"regla": conocimiento.resumen_pieza(regla)`. No `insight.py` object built here either.
- **`pagos.py:119-129`** (the cashflow `proyeccion`) — returns a plain dict (`supuestos` is a plain i18n STRING here, not a list of `insight.assumption()` objects) with `notas_conocimiento`/`conocimiento_aplicado` already citation-ready. No `insight.build()` call in this function.

None of these three currently have an `insight.py`-shaped card to extend. Forcing one into existence is out of scope for this plan (it would be new insight-adoption work for those surfaces, not "close the loop" work) — revisit if/when any of the three gets a proper insight.

- [ ] **Step 1: Failing test — `_enriquecer` also returns the raw tolerance pieces**

```python
# backend/tests/test_cruces.py or wherever cuentas._enriquecer already has
# coverage — check with: grep -rln "_enriquecer\|cuentas.listar" backend/tests/
def test_enriquecer_returns_raw_tolerance_pieces_when_exceso():
    from core import conocimiento, cuentas
    conocimiento.crear(texto="Tolerale 45 días", tipo="regla", ambito="cliente",
                       nodo="clientes", efecto="contexto_para_angela",
                       entidad="Despensa Doña Elsa", params={"tolerancia_dias": 45})
    # use this test file's existing fixture to get a client dict `c` for
    # "Despensa Doña Elsa" whose dias_sin_pagar exceeds 45, same as any
    # existing test exercising exceso_tolerancia
    enriquecido = cuentas._enriquecer(c)
    assert enriquecido.get("piezas_conocimiento")
    assert enriquecido["piezas_conocimiento"][0]["id"]  # a real piece dict, not resumen_pieza's trimmed shape
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest -k enriquecer_returns_raw -v`
Expected: FAIL — no `piezas_conocimiento` key.

- [ ] **Step 3: Implement — `cuentas.py`**

```python
# backend/core/cuentas.py:117-126 — replace the return statement
    return {
        **c,
        "en_mora": en_mora,
        "score": score,
        "disponible": max(0, c.get("limite_credito", 0) - c["saldo"]),
        "atraso_vs_promedio": atraso,
        **({"tolerancia_dias": tol, "exceso_tolerancia": exceso,
            "conocimiento": [conocimiento.resumen_pieza(p) for p in piezas_tol],
            "piezas_conocimiento": piezas_tol}
           if exceso is not None else {}),
    }
```

(Adds `piezas_conocimiento` — the raw piece dicts — alongside the existing `conocimiento` summarized list, which stays untouched for whatever already reads it.)

- [ ] **Step 4: Run to verify it passes**

Same command as Step 2. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/core/cuentas.py
git commit -m "feat: cuentas._enriquecer also returns raw tolerance pieces for insight evidence"
```

- [ ] **Step 6: Failing test — `cobrar_morosos` cites tolerance rules as evidence**

```python
def test_cobrar_morosos_cites_a_tolerance_rule_as_evidence():
    from core import conocimiento
    conocimiento.crear(texto="Tolerale 45 días", tipo="regla", ambito="cliente",
                       nodo="clientes", efecto="contexto_para_angela",
                       entidad="Despensa Doña Elsa", params={"tolerancia_dias": 45})
    card = ...  # obtain the cobrar_morosos card, same setup as its existing tests,
                # with Doña Elsa overdue past her taught tolerance
    kinds = [ev["kind"] for ev in card["insight"]["evidence"]]
    assert "knowledge" in kinds
```

- [ ] **Step 7: Run to verify it fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest -k cobrar_morosos_cites -v`
Expected: FAIL.

- [ ] **Step 8: Implement — `cobrar_morosos`'s builder**

`grep -n "def _card_morosos\|cobrar_morosos" backend/core/oportunidades_neg.py` to find this card's builder function name and where `morosos` (the list this card iterates, seen already carrying `.saldo`/`.dias_sin_pagar`/`.nombre` in the evidence already read at lines 200-219) is assembled — it comes from `cuentas.listar()` (now carrying `piezas_conocimiento` per Step 3) filtered to `en_mora`. Add, right before the `insight_val = ins.build(...)` call at line 227:

```python
    piezas_tolerancia = {
        p["id"]: p for c in morosos for p in (c.get("piezas_conocimiento") or [])
    }.values()  # de-duplicated across clients, in case two morosos share a piece
    for p in piezas_tolerancia:
        evidencia.append(ins.knowledge(p))
```

(Insert this immediately before `insight_val = ins.build(` at line 227, so `evidencia` already includes it when passed to `evidence=evidencia`.)

- [ ] **Step 9: Run to verify it passes**

Same command as Step 7. Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add backend/core/oportunidades_neg.py
git commit -m "fix: cobrar_morosos cites each debtor's tolerance rule as evidence"
```

- [ ] **Step 11: Add to the stack**

```bash
gh stack add pr9-cobrar-morosos-knowledge-evidence
```

---

### Task 4: `grafo.py` — knowledge pieces become real graph nodes

**Files:**
- Modify: `backend/core/grafo.py:468-481` (the conocimiento block inside `construir()`)
- Test: extend whichever test file exercises `grafo.construir()`'s node/edge output (the same file Task 1 of the sibling plan used or created for the pause-bug test)

**Interfaces:**
- Consumes: `conocimiento.needs_review()` (sibling plan Task 4), `conocimiento.listar(incluir_pausadas=False, incluir_archivadas=False)` (sibling plan Task 5 — **this task cannot start before that lands**, since `incluir_archivadas` doesn't exist before then).

**Scope decision carried from the spec's open question:** a piece with `ambito="global"` has no single entity to attach to. This task leaves global pieces exactly as they are today (not represented in the graph) — only entity-attached pieces gain a real node. Giving global pieces a synthetic anchor is explicitly deferred (YAGNI until a concrete need for it shows up), not silently dropped.

- [ ] **Step 1: Failing test — a knowledge piece is a real node with an edge**

```python
def test_knowledge_piece_is_a_real_node_with_an_edge_to_its_entity():
    from core import conocimiento, grafo
    pieza = conocimiento.crear(
        texto="Tolerale 45 días", tipo="regla", ambito="cliente",
        nodo="clientes", efecto="ajusta_umbral", entidad="Despensa Doña Elsa")
    g = grafo.construir()
    nid = f"conocimiento:{pieza['id']}"
    node = g["_indice"].get(nid)
    assert node is not None
    assert node["tipo"] == "conocimiento"
    cliente = next((n for n in g["nodos"] if n["tipo"] == "cliente"
                    and "Elsa" in n["nombre"]), None)
    arista = next((a for a in g["aristas"]
                  if a["source"] == nid and a["target"] == cliente["id"]), None)
    assert arista is not None
    assert arista["rel"] == "aplica_a"


def test_a_stale_knowledge_node_is_flagged_atencion():
    from core import conocimiento, grafo
    pieza = conocimiento.crear(
        texto="Vieja regla", tipo="regla", ambito="cliente", nodo="clientes",
        efecto="ajusta_umbral", entidad="Despensa Doña Elsa", half_life_days=1)
    g = grafo.construir()
    node = g["_indice"][f"conocimiento:{pieza['id']}"]
    # half_life_days=1 with last_reinforced_at=created_at=now means this
    # decays to "revisar" almost immediately at any realistic "today"
    assert node["riesgo"] == "atencion"


def test_archived_knowledge_produces_no_node():
    from core import conocimiento, grafo
    pieza = conocimiento.crear(
        texto="Retirada", tipo="regla", ambito="cliente", nodo="clientes",
        efecto="ajusta_umbral", entidad="Despensa Doña Elsa")
    conocimiento.archive(pieza["id"], actor="aldo")
    g = grafo.construir()
    assert f"conocimiento:{pieza['id']}" not in g["_indice"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest -k "knowledge_piece_is_a_real_node or stale_knowledge_node or archived_knowledge_produces" -v`
Expected: FAIL — no `conocimiento:*` nodes exist yet (today's code only sets a flat metadata list).

- [ ] **Step 3: Implement**

```python
# backend/core/grafo.py:468-481 — replace the entire block
    # --- lo que el dueño le enseñó a Ángela, como nodo real -------------------
    try:
        from . import conocimiento
        for p in conocimiento.listar(incluir_pausadas=False, incluir_archivadas=False):
            ent = (p.get("entidad") or "").strip()
            if not ent:
                continue  # global pieces: no single entity to attach to (see plan's scope note)
            objetivo = next((nid for nid, n in nodos.items()
                             if n["tipo"] in ("producto", "cliente", "proveedor")
                             and _norm(ent) in _norm(n["nombre"])), None)
            if not objetivo:
                continue
            kid = f"conocimiento:{p['id']}"
            nodos[kid] = _nodo(
                kid, "conocimiento", p["texto"][:80], seccion=p["nodo"],
                riesgo=("atencion" if conocimiento.needs_review(p) else None),
                texto=p.get("texto"), texto_en=p.get("texto_en"))
            add_arista(kid, objetivo, "aplica_a")
    except Exception:
        pass
```

- [ ] **Step 4: Run to verify it passes**

Same command as Step 2. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/core/grafo.py
git commit -m "feat: a knowledge piece is a real graph node with an aplica_a edge"
```

- [ ] **Step 6: Failing test — `caminos()` can seed from a knowledge node**

```python
def test_caminos_can_seed_from_a_knowledge_piece():
    from core import conocimiento, grafo
    pieza = conocimiento.crear(
        texto="Tolerale 45 días", tipo="regla", ambito="cliente", nodo="clientes",
        efecto="ajusta_umbral", entidad="Despensa Doña Elsa")
    g = grafo.construir()
    camino = grafo.caminos(g, semilla=f"conocimiento:{pieza['id']}")
    assert camino  # doesn't raise, returns something reachable from the knowledge node
```

(Confirm `caminos()`'s exact signature and semilla-handling first — `grep -n "def caminos" backend/core/grafo.py` — the test above assumes a `semilla` kwarg based on `_SEMILLA_CAMPOS`/`_resolver` already seen near line 494-499; adjust the call to match whatever the real signature is if it differs.)

- [ ] **Step 7: Run to verify it fails, then confirm it already passes**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest -k caminos_can_seed_from_a_knowledge -v`

If `caminos()` already treats any node type generically (likely, since it worked for `nota` nodes without special-casing — check `caminos()`'s body for any `tipo ==` branching before assuming special-casing is needed), this test may PASS immediately once Step 3's node exists, with no further code change — in that case, no Step 8 implementation is needed; only add the test and confirm it passes. If `caminos()` DOES special-case node types, add `"conocimiento"` alongside wherever `"nota"` is already allowed as a seed.

- [ ] **Step 8: Commit**

```bash
git add backend/core/grafo.py
git commit -m "test: confirm caminos() treats a knowledge node as a valid seed"
```

- [ ] **Step 9: Manually verify in the running app**

`python start_demo.py`, open the business map for a client with a taught tolerance rule, confirm the knowledge piece now appears as its own connected node (not just a metadata badge), and that archiving it (via the Task 5 archive action from the sibling plan) removes it from the map on next load.

- [ ] **Step 10: Add to the stack and submit**

```bash
gh stack add pr10-grafo-knowledge-node
gh stack submit
```

---

## Self-Review Notes

- **Spec coverage:** all four PRs (7-10) from the spec have a matching task. The spec's open question about global-piece graph representation is resolved in Task 4 as "leave unrepresented, as today" — the minimal, YAGNI-consistent choice, documented rather than silently decided.
- **Corrections found during planning, not anticipated in the spec:** the spec assumed builder-wiring (PR 8/9) was purely additive ("wrap whatever pieces came back"). Reading the actual code turned up that `oportunidades_neg.py` already cites knowledge at four sites, three of them as an `assumption` (an active bug under the new confidence model — it currently *lowers* confidence for citing a taught rule) and one as a `metric()` workaround. Task 2 fixes these three, not just adds a fourth. `cuentas.py`'s call site (originally listed in the spec as its own PR-9 target) turned out to require a small upstream change (`_enriquecer` returning raw pieces, not just `resumen_pieza`'s trimmed shape) before it could feed `cobrar_morosos` — captured in Task 3. `conciliacion.py`/`deposito.py`/`pagos.py` were confirmed (not assumed) to have no `insight.py` object at their call sites and are explicitly out of scope with the reason stated, rather than silently wired in incorrectly.
- **Type consistency:** `insight.knowledge()`'s returned dict shape (Task 1) matches exactly what Tasks 2-4's tests assert (`kind`, `id`, `label`, `weight`, `origen`, `freshness`, `needs_review`) — no drift between the constructor's definition and its call sites.
- **Known gap, flagged rather than hidden:** Task 2 and Task 3's tests use `card = ...  # obtain the X card, same setup as its existing tests` in four places. This plan verified the exact production code being changed (every line cited above was read directly from the file), but did not read the full existing test files (`test_p27.py`, `test_p25.py`, `test_oportunidades_ids.py`) to extract their tenant/fixture setup boilerplate — doing so for all four card types was out of budget for this planning pass. Whoever executes Task 2/3 should open the nearest existing passing test for that same card first, copy its fixture setup verbatim, and only then add the new assertions shown here. This is a real, bounded gap — not a placeholder for the *logic* being changed, which is fully specified above.
