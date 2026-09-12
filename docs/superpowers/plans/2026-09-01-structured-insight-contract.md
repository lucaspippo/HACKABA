# Structured Insight Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Prioridades' flat prose `drill.porque` with a structured `insight` object — Pattern, Hypothesis, Evidence, Assumptions, Risk, Recommended action, Owner, Deadline — with split data/hypothesis confidence, across every card builder, the drill UI, and Ángela's tool projection.

**Architecture:** Three new/rewritten `core/` modules supply the vocabulary (`insight.py`), the derived confidence split (`confidence.py`) and owner suggestion (`insight_owner.py`). `priorities.py` composes: builders author domain fields, `_compose` derives the rest, `_combine` merges evidence by stable id (which is what kills today's duplicate-prose bug). Consumers — the shared `DrillNegocio` component and Ángela's `_slim` projection — read the finished insight. A temporary one-way `insight → drill` shim keeps the app runnable mid-plan and is deleted in Task 13.

**Tech Stack:** Python 3.12 + FastAPI (`backend/`), React 18 + Vite + Tailwind (`frontend/`), pytest.

**Spec:** `docs/superpowers/specs/2026-09-01-structured-insight-contract-design.md`

## Global Constraints

- **All new code, identifiers, comments and docstrings are in English.** Product-facing UI copy stays Spanish-first (bilingual via `backend/i18n.py` and `frontend/src/lib/locales/`). Do not blanket-rename pre-existing Spanish identifiers outside the files this plan substantially rewrites.
- **The deterministic invariant:** every number comes from `backend/core/` calculation. The LLM narrates and cites; it never computes, reformats or invents a figure. `_slim` selects — it never recomputes.
- **Card envelope is untouched:** `id`, `tono`, `chip`, `titulo`, `resumen`, `monto`, `monto_label`, `cifra_texto`, `fuentes`, `origen`, `navegar`, `accion_chat`, `propuesta`, `piso`, `macro`, `naturaleza`, `tipo`, `modulos`, `reportes`, `band`, `action_taken`. Only `drill` is replaced.
- **Every new user-visible string is born bilingual** — added to `backend/i18n.py` `CATALOGO` with both `"es"` and `"en"` on the same commit (house rule, `i18n.py:1-20`).
- **Tests write into `data-demo/`.** After any `pytest` run: `git checkout -- data-demo/`.
- Run backend tests from `backend/`: `python -m pytest`. Dataset "today" is **2026-07-07**.
- **Pre-existing failures, not to be "fixed": 7 of them**, confirmed pre-existing on the branch tip by `git stash` during Task 4. They live in `tests/test_cruces.py`, `tests/test_p27.py` and `tests/test_patrones.py`, and are `cliente_frio` / count mismatches against the real `data-demo/` dataset. A full-suite run should read **1377 passed / 7 failed / 36 skipped**. If your run shows more than 7 failures, you broke something; if it shows fewer, say so rather than assuming you fixed one.

## Runnability during the plan

The cutover is hard, but the branch stays runnable. Task 4 adds `_legacy_drill(insight)` — a **one-way, derived** shim that renders an insight back into the old `{porque, grafico, involucrados, supuestos, confidence}` shape so the untouched frontend keeps working. Nothing is dual-authored: builders only ever write insights. Task 13 deletes the shim and its test.

## File structure

| File | Responsibility |
|---|---|
| `backend/core/insight.py` | **new** — the insight constructor and evidence vocabulary. Pure functions, no I/O, no tenant. |
| `backend/core/confidence.py` | **rewritten** — derives the data/hypothesis confidence split from a finished insight. |
| `backend/core/insight_owner.py` | **new** — suggests an owner from a card's modules via `perfiles.matriz()`. |
| `backend/core/priorities.py` | composer: `_item`, `_blank_insight`, `_combine` merge-by-id, `_compose` derivation loop, 14 alert builders. |
| `backend/core/oportunidades_neg.py` | 10 finding builders emit insights. |
| `backend/core/patrones.py` | 2 pattern builders emit insights. |
| `backend/core/piso.py` | `propuestas()` emits insights. |
| `backend/angela.py` | `_slim` widens to the trimmed insight projection. |
| `frontend/src/components/CardNegocio.jsx` | `DrillNegocio` restructured around the insight; `Metrics` retired. |
| `frontend/src/sections/Prioridades.jsx` | `drillProps`; deadline chip on `WorkRow`. |
| `frontend/src/mobile/InsightsMobile.jsx` | `rowOf` maps the new shape. |

---

### Task 1: `core/insight.py` — the constructor and evidence vocabulary

**Files:**
- Create: `backend/core/insight.py`
- Test: `backend/tests/test_insight.py`

**Interfaces:**
- Consumes: nothing (pure, leaf module).
- Produces:
  - `build(*, pattern, hypothesis=None, evidence=(), assumptions=(), alternatives=(), falsifiers=(), risk=None, recommendation=None, deadline=None) -> dict`
  - `pattern(label, *, since=None, scope=None) -> dict`
  - `metric(id, *, label, value, unit, method, baseline=None, weight="supporting", records=(), chart=None) -> dict`
  - `records(id, *, label, rows, method, weight="supporting") -> dict`
  - `series(id, *, label, chart, method, weight="supporting") -> dict`
  - `record(*, kind, id, name, amount=None, detail=None) -> dict`
  - `assumption(label, *, if_wrong=None) -> dict`
  - `risk(label, *, exposure=None) -> dict`
  - `recommendation(label, *, detail=None, proposal=None, navigate=None, chat=None) -> dict`
  - `deadline(date, *, basis) -> dict`
  - `EMPTY -> dict` (module-level constant factory `blank()`)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_insight.py`:

```python
"""core/insight.py — the constructor vocabulary every card builder uses."""
import pytest

from core import insight


def test_metric_derives_deviation_from_baseline():
    m = insight.metric(
        "days_overdue", label="66 días contra 31", value=66, unit="days",
        baseline={"value": 31, "label": "promedio histórico"},
        method={"key": "core.method.dias_mora", "label": "Días desde la última cobranza"},
    )
    assert m["deviation"] == {"pct": 113, "direction": "up"}


def test_metric_deviation_direction_is_down_when_below_baseline():
    m = insight.metric(
        "margin", label="12% contra 20%", value=12, unit="pct",
        baseline={"value": 20, "label": "margen objetivo"},
        method={"key": "core.method.margen", "label": "Margen sobre costo"},
    )
    assert m["deviation"] == {"pct": 40, "direction": "down"}


@pytest.mark.parametrize("baseline", [None, {"value": 0, "label": "cero"}])
def test_metric_deviation_is_none_without_a_usable_baseline(baseline):
    """No baseline, or a zero baseline: no meaningful percentage exists."""
    m = insight.metric(
        "count", label="3 clientes", value=3, unit="clients", baseline=baseline,
        method={"key": "core.method.conteo", "label": "Conteo"},
    )
    assert m["deviation"] is None


def test_evidence_weight_defaults_to_supporting():
    """A builder must OPT IN to claiming an item is load-bearing."""
    m = insight.metric("x", label="x", value=1, unit="u",
                       method={"key": "k", "label": "l"})
    assert m["weight"] == "supporting"


def test_build_fills_every_contract_key():
    i = insight.build(pattern=insight.pattern("3 clientes concentran la mora"))
    assert set(i) == {
        "pattern", "hypothesis", "evidence", "assumptions", "alternatives",
        "falsifiers", "risk", "recommendation", "owner", "deadline", "confidence",
    }
    assert i["hypothesis"] is None
    assert i["evidence"] == []
    assert i["owner"] is None          # derived later, in _compose
    assert i["confidence"] is None     # derived later, in _compose


def test_records_carries_rows_and_kind():
    r = insight.records(
        "debtors", label="Clientes en mora",
        rows=[insight.record(kind="client", id="c-142", name="Doña Elsa", amount=1000)],
        method={"key": "k", "label": "l"}, weight="primary",
    )
    assert r["kind"] == "records"
    assert r["records"][0] == {"kind": "client", "id": "c-142",
                              "name": "Doña Elsa", "amount": 1000, "detail": None}


def test_blank_is_a_fresh_object_each_call():
    """Shared mutable default would leak evidence between cards."""
    a, b = insight.blank(), insight.blank()
    a["evidence"].append({"id": "x"})
    assert b["evidence"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_insight.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.insight'`

- [ ] **Step 3: Write the implementation**

Create `backend/core/insight.py`:

```python
"""The structured insight every Prioridades card carries.

One fixed shape for every finding, so cards are comparable and the UI,
Ángela and the tests all read the same thing:

    Pattern → Hypothesis → Evidence → Assumptions → Risk
            → Recommended action → Owner → Deadline

This module is pure vocabulary: constructors that validate shape and derive
what can be derived locally (a deviation from a value and its baseline).
It performs no I/O, resolves no tenant and reads no dataset — builders in
priorities.py / oportunidades_neg.py / patrones.py / piso.py supply the
domain values, and core/priorities.py::_compose fills the fields that can
only be derived once the whole insight exists (owner, confidence, risk
level, deadline urgency).

Per the deterministic-core invariant (repo CLAUDE.md), every value that
lands here was calculated upstream. Nothing in this file invents a number.
"""
from __future__ import annotations

WEIGHTS = ("primary", "supporting")


def blank() -> dict:
    """An insight with no content. A fresh object every call — a shared
    default would leak evidence from one card into the next."""
    return build(pattern=None)


def build(*, pattern=None, hypothesis=None, evidence=(), assumptions=(),
          alternatives=(), falsifiers=(), risk=None, recommendation=None,
          deadline=None) -> dict:
    """Assemble one card's insight.

    `owner`, `confidence` and the derived halves of `risk`/`deadline` are
    left for _compose: they need the finished insight (and, for owner, the
    tenant's team) and cannot be known here.
    """
    return {
        "pattern": pattern,
        "hypothesis": hypothesis,
        "evidence": list(evidence),
        "assumptions": list(assumptions),
        "alternatives": list(alternatives),
        "falsifiers": list(falsifiers),
        "risk": risk,
        "recommendation": recommendation,
        "owner": None,
        "deadline": deadline,
        "confidence": None,
    }


def pattern(label: str, *, since: str | None = None,
            scope: dict | None = None) -> dict:
    """The observation, with no interpretation in it."""
    return {"label": label, "since": since, "scope": scope}


def hypothesis(label: str) -> dict:
    """The interpretive leap, kept separate from the observation."""
    return {"label": label}


def _deviation(value, baseline: dict | None) -> dict | None:
    """Percentage gap between a value and its baseline.

    None when there is no baseline, or the baseline is zero — no meaningful
    percentage exists, and a divide-by-zero guard that returned 0 or inf
    would be a made-up number on a card that promises calculated ones.
    """
    if not baseline:
        return None
    base = baseline.get("value")
    if not base:  # None or 0
        return None
    delta = (float(value) - float(base)) / abs(float(base))
    return {"pct": round(abs(delta) * 100), "direction": "up" if delta >= 0 else "down"}


def _evidence(id, kind, *, label, method, weight, value=None, unit=None,
              baseline=None, deviation=None, records=(), chart=None) -> dict:
    if weight not in WEIGHTS:
        raise ValueError(f"weight must be one of {WEIGHTS}, got {weight!r}")
    return {
        "id": id, "kind": kind, "label": label,
        "value": value, "unit": unit, "baseline": baseline,
        "deviation": deviation, "weight": weight, "method": method,
        "records": list(records), "chart": chart,
    }


def metric(id: str, *, label: str, value, unit: str, method: dict,
           baseline: dict | None = None, weight: str = "supporting",
           records=(), chart=None) -> dict:
    """One number that supports the conclusion, with how it was computed.

    `weight` defaults to "supporting": a builder must opt in to calling an
    item load-bearing, which is what the UI expands and what Ángela sees.
    """
    return _evidence(id, "metric", label=label, method=method, weight=weight,
                     value=value, unit=unit, baseline=baseline,
                     deviation=_deviation(value, baseline),
                     records=records, chart=chart)


def records(id: str, *, label: str, rows, method: dict,
            weight: str = "supporting") -> dict:
    """The real rows behind a claim — the owner can click through to them."""
    return _evidence(id, "records", label=label, method=method, weight=weight,
                     records=rows)


def series(id: str, *, label: str, chart: dict, method: dict,
           weight: str = "supporting") -> dict:
    """A Contract P21 chart as evidence for a claim."""
    return _evidence(id, "series", label=label, method=method, weight=weight,
                     chart=chart)


def record(*, kind: str, id, name: str, amount=None, detail: str | None = None) -> dict:
    """One clickable row. `kind` drives navigation ("client" → cuentas,
    "product" → inventario); an id with no kind has nowhere to land."""
    return {"kind": kind, "id": id, "name": name, "amount": amount, "detail": detail}


def assumption(label: str, *, if_wrong: str | None = None) -> dict:
    """A declared leap, and what it would mean for the finding to be wrong."""
    return {"label": label, "if_wrong": if_wrong}


def caveat(label: str) -> dict:
    """One alternative explanation, or one thing that would falsify this."""
    return {"label": label}


def risk(label: str, *, exposure=None) -> dict:
    """`exposure` is the money at stake if nothing is done — not always the
    card's `monto` (for dep_porvencer, monto is total lot value while only a
    fraction actually expires). `level` is derived in _compose."""
    return {"level": None, "label": label, "exposure": exposure}


def recommendation(label: str, *, detail: str | None = None, proposal=None,
                   navigate: str | None = None, chat: str | None = None) -> dict:
    """The move. Consolidates what the card envelope scatters across
    titulo/chip/propuesta/navegar/accion_chat."""
    return {"label": label, "detail": detail, "proposal": proposal,
            "navigate": navigate, "chat": chat}


def deadline(date: str, *, basis: str) -> dict:
    """`basis` says WHY this is the date (supplier lead time, lot expiry,
    ageing curve). `urgency` is derived in _compose against the dataset's
    today."""
    return {"date": date, "basis": basis, "urgency": None}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_insight.py -v`
Expected: PASS (8 tests, including the 2 parametrized cases)

- [ ] **Step 5: Commit**

```bash
git add backend/core/insight.py backend/tests/test_insight.py
git commit -m "Add core/insight.py — the structured insight vocabulary"
```

---

### Task 2: `core/confidence.py` — split data and hypothesis confidence

**Files:**
- Modify (rewrite): `backend/core/confidence.py`
- Modify: `backend/i18n.py` (six new `core.confidence.*` keys)
- Test: `backend/tests/test_confidence.py`

**Interfaces:**
- Consumes: `insight.build()` output (Task 1).
- Produces: `confidence.split_for(insight: dict, lang: str | None = None) -> dict` returning `{"data": {level, reason, signals}, "hypothesis": {level, reason, signals}}`. Replaces `level_for(drill, lang)`, which is deleted.

**Why this shape:** the current 37-line `level_for` already mixes the two axes — chart points are a *data* signal, assumption count is a *hypothesis* signal — and collapses them into one level. Separating them is the whole point: a finding backed by twelve months of history but resting on three assumptions must read `data: high, hypothesis: low`, which today is inexpressible.

- [ ] **Step 1: Write the failing test**

**Append** to `backend/tests/test_confidence.py`, keeping the existing `level_for`
tests — that function is still live until Task 4:

```python
"""core/confidence.py — the two axes must move independently."""
from core import confidence, insight


def _chart(points: int) -> dict:
    return {"ok": True,
            "series": [{"nombre": "s", "puntos": [{"x": i, "y": i} for i in range(points)]}],
            "meta": {}}


def _insight(*, points=0, records=0, assumptions=0, alternatives=0):
    ev = []
    if points:
        ev.append(insight.series("s", label="l", chart=_chart(points),
                                 method={"key": "k", "label": "l"}))
    if records:
        ev.append(insight.records(
            "r", label="l",
            rows=[insight.record(kind="client", id=i, name=str(i)) for i in range(records)],
            method={"key": "k", "label": "l"}))
    return insight.build(
        pattern=insight.pattern("p"),
        evidence=ev,
        assumptions=[insight.assumption(f"a{i}") for i in range(assumptions)],
        alternatives=[insight.caveat(f"c{i}") for i in range(alternatives)],
    )


def test_rich_data_and_many_assumptions_disagree():
    """The assertion that was impossible before the split."""
    c = confidence.split_for(_insight(points=12, assumptions=3))
    assert c["data"]["level"] == "high"
    assert c["hypothesis"]["level"] == "low"


def test_thin_data_and_no_assumptions_disagree_the_other_way():
    c = confidence.split_for(_insight(points=0, assumptions=0))
    assert c["data"]["level"] == "low"
    assert c["hypothesis"]["level"] == "high"


def test_records_count_toward_data_confidence_without_a_chart():
    """An alert with no chart but eight real rows is not low-data."""
    c = confidence.split_for(_insight(points=0, records=8))
    assert c["data"]["level"] == "medium"


def test_declared_alternatives_lower_hypothesis_confidence():
    """More competing explanations means LESS certainty, not more."""
    few = confidence.split_for(_insight(points=6, alternatives=0))
    many = confidence.split_for(_insight(points=6, alternatives=3))
    order = {"low": 0, "medium": 1, "high": 2}
    assert order[many["hypothesis"]["level"]] < order[few["hypothesis"]["level"]]


def test_signals_are_exposed_for_the_ui():
    c = confidence.split_for(_insight(points=12, records=3, assumptions=1))
    assert c["data"]["signals"]["chart_points"] == 12
    assert c["data"]["signals"]["record_count"] == 3
    assert c["hypothesis"]["signals"]["assumptions"] == 1


def test_both_axes_always_carry_a_reason_string():
    c = confidence.split_for(_insight())
    assert c["data"]["reason"] and c["hypothesis"]["reason"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_confidence.py -v`
Expected: FAIL — `AttributeError: module 'core.confidence' has no attribute 'split_for'`

- [ ] **Step 3: Add the six i18n keys**

**Add** these to `backend/i18n.py`. Do **not** remove the existing three
`core.confidence.reason_*` entries — `level_for` still renders them until Task 4
deletes it (see Step 4's note). Task 4 removes the orphaned keys.

```python
    "core.confidence.data_high": {
        "es": "Basado en {points} puntos de historia y {records} registros.",
        "en": "Based on {points} data points and {records} records.",
    },
    "core.confidence.data_medium": {
        "es": "Basado en {points} puntos y {records} registros — alcanza para la señal, no para el detalle.",
        "en": "Based on {points} points and {records} records — enough for the signal, not the detail.",
    },
    "core.confidence.data_low": {
        "es": "Poca evidencia detrás: {points} puntos, {records} registros.",
        "en": "Thin evidence behind this: {points} points, {records} records.",
    },
    "core.confidence.hyp_high": {
        "es": "No apoya en supuestos: la lectura sale directo de los datos.",
        "en": "Rests on no assumptions — the reading comes straight from the data.",
    },
    "core.confidence.hyp_medium": {
        "es": "Apoya en {assumptions} supuesto(s) y {alternatives} explicación(es) alternativa(s).",
        "en": "Rests on {assumptions} assumption(s) with {alternatives} alternative explanation(s).",
    },
    "core.confidence.hyp_low": {
        "es": "Lectura frágil: {assumptions} supuesto(s) y {alternatives} explicación(es) alternativa(s).",
        "en": "Fragile reading: {assumptions} assumption(s) and {alternatives} alternative explanation(s).",
    },
```

- [ ] **Step 4: Add `split_for` alongside the existing `level_for`**

**Keep `level_for` exactly as it is.** `priorities._compose:322` still calls it, and
deleting it here would break the import until Task 4 rewrites that call site. Task 4
deletes `level_for`, its three `core.confidence.reason_*` keys, and the old tests
together. Add the new module content below the existing `level_for`, sharing the
module docstring:

```python
"""Confidence for a Prioridades card, split along the seam that matters.

Two questions the owner asks separately, and that a single level cannot
answer:

  data       — how much evidence is behind this? (chart points, real
               records, freshness)
  hypothesis — how big is the interpretive leap? (declared assumptions,
               competing explanations)

They can disagree, and when they do that IS the information: twelve months
of clean history read through three assumptions is high-data,
low-hypothesis, and the owner should see both.

Deliberately coarse — a reading aid, not a statistical model. Computed once
per card, centrally, in priorities._compose; no per-card-type logic.
"""
from __future__ import annotations

HIGH_POINTS = 6
MEDIUM_POINTS = 3
HIGH_RECORDS = 5
MEDIUM_RECORDS = 2


def _chart_points(insight: dict) -> int:
    """Longest series across every piece of evidence carrying a chart."""
    best = 0
    for ev in insight.get("evidence") or []:
        chart = ev.get("chart")
        if not chart or not chart.get("series"):
            continue
        best = max(best, max((len(s.get("puntos") or [])
                              for s in chart["series"]), default=0))
    return best


def _record_count(insight: dict) -> int:
    return sum(len(ev.get("records") or []) for ev in insight.get("evidence") or [])


def _data_level(points: int, records: int) -> str:
    if points >= HIGH_POINTS or records >= HIGH_RECORDS:
        return "high"
    if points >= MEDIUM_POINTS or records >= MEDIUM_RECORDS:
        return "medium"
    return "low"


def _hypothesis_level(assumptions: int, alternatives: int) -> str:
    """Both signals push the same way: every declared assumption and every
    competing explanation is a reason to trust the reading less. Declaring
    them is honest, and honesty should show as lower confidence, not
    higher."""
    leaps = assumptions + alternatives
    if leaps == 0:
        return "high"
    if leaps <= 2:
        return "medium"
    return "low"


def split_for(insight: dict, lang: str | None = None) -> dict:
    import i18n
    points = _chart_points(insight)
    records = _record_count(insight)
    assumptions = len(insight.get("assumptions") or [])
    alternatives = len(insight.get("alternatives") or [])

    data_level = _data_level(points, records)
    hyp_level = _hypothesis_level(assumptions, alternatives)
    hyp_key = {"high": "hyp_high", "medium": "hyp_medium", "low": "hyp_low"}[hyp_level]

    return {
        "data": {
            "level": data_level,
            "reason": i18n.t(f"core.confidence.data_{data_level}", lang,
                             points=points, records=records),
            "signals": {"chart_points": points, "record_count": records,
                        "sources_stale": False, "missing": []},
        },
        "hypothesis": {
            "level": hyp_level,
            "reason": i18n.t(f"core.confidence.{hyp_key}", lang,
                             assumptions=assumptions, alternatives=alternatives),
            "signals": {"assumptions": assumptions, "alternatives": alternatives},
        },
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_confidence.py -v`
Expected: PASS (6 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/core/confidence.py backend/tests/test_confidence.py backend/i18n.py
git commit -m "Split confidence into data and hypothesis axes"
git checkout -- data-demo/
```

---

### Task 3: `core/insight_owner.py` — suggest an owner from a card's modules

**Files:**
- Create: `backend/core/insight_owner.py`
- Test: `backend/tests/test_insight_owner.py`

**Interfaces:**
- Consumes: `perfiles.matriz()` → `list[{username, nombre, rol, es_admin, color, modulos: {module: bool}}]` (`core/perfiles.py:373-386`).
- Produces: `insight_owner.suggest(modulos: tuple[str, ...]) -> dict | None` returning `{"suggested": nombre, "role": rol, "reason": module_label}`.

**The rule:** among non-admin team members, find those whose effective modules cover **all** of the card's modules. Exactly one match → suggest them. Zero or more than one → `None`. Admins are excluded because the owner sees every module and would match every card, making every suggestion ambiguous.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_insight_owner.py`:

```python
"""core/insight_owner.py — a suggestion, or an honest None."""
from unittest.mock import patch

from core import insight_owner


def _row(username, nombre, rol, modulos, es_admin=False):
    return {"username": username, "nombre": nombre, "rol": rol,
            "es_admin": es_admin, "modulos": modulos}


def test_suggests_the_single_person_who_covers_the_modules():
    matriz = [
        _row("marina", "Marina", "Cobranzas", {"cuentas": True, "inventario": False}),
        _row("beto", "Beto", "Depósito", {"cuentas": False, "inventario": True}),
    ]
    with patch("core.perfiles.matriz", return_value=matriz):
        assert insight_owner.suggest(("cuentas",)) == {
            "suggested": "Marina", "role": "Cobranzas", "reason": "cuentas"}


def test_none_when_two_people_both_cover_the_modules():
    """Ambiguous is not a coin flip — the UI says 'sin dueño sugerido'."""
    matriz = [
        _row("marina", "Marina", "Cobranzas", {"cuentas": True}),
        _row("ana", "Ana", "Administración", {"cuentas": True}),
    ]
    with patch("core.perfiles.matriz", return_value=matriz):
        assert insight_owner.suggest(("cuentas",)) is None


def test_none_when_nobody_covers_the_modules():
    matriz = [_row("beto", "Beto", "Depósito", {"cuentas": False, "inventario": True})]
    with patch("core.perfiles.matriz", return_value=matriz):
        assert insight_owner.suggest(("cuentas",)) is None


def test_none_for_an_empty_team():
    """A fresh DB-backed tenant may have nobody assigned yet."""
    with patch("core.perfiles.matriz", return_value=[]):
        assert insight_owner.suggest(("cuentas",)) is None


def test_admins_are_excluded_from_the_candidate_set():
    """The owner sees every module; counting them would make every card
    ambiguous and no card would ever get a suggestion."""
    matriz = [
        _row("aldo", "Aldo", "Dueño", {"cuentas": True}, es_admin=True),
        _row("marina", "Marina", "Cobranzas", {"cuentas": True}),
    ]
    with patch("core.perfiles.matriz", return_value=matriz):
        assert insight_owner.suggest(("cuentas",))["suggested"] == "Marina"


def test_requires_every_module_not_just_one():
    matriz = [
        _row("marina", "Marina", "Cobranzas", {"cuentas": True, "inventario": False}),
    ]
    with patch("core.perfiles.matriz", return_value=matriz):
        assert insight_owner.suggest(("cuentas", "inventario")) is None


def test_none_for_the_no_domain_sentinel():
    """`__sin_dominio__` means the card declared no module — not that
    everyone owns it."""
    matriz = [_row("marina", "Marina", "Cobranzas", {"cuentas": True})]
    with patch("core.perfiles.matriz", return_value=matriz):
        assert insight_owner.suggest(("__sin_dominio__",)) is None


def test_a_perfiles_failure_yields_none_not_an_exception():
    """One broken lookup must not take down the whole inbox."""
    with patch("core.perfiles.matriz", side_effect=RuntimeError("db down")):
        assert insight_owner.suggest(("cuentas",)) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_insight_owner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.insight_owner'`

- [ ] **Step 3: Write the implementation**

Create `backend/core/insight_owner.py`:

```python
"""Suggest who on the team should own a Prioridades card.

A suggestion, never an assignment: the card says "Marina" because Marina is
the only person whose access covers cuentas corrientes, not because anybody
decided. Assignment (and overriding this) belongs to the deferred action-
workflow spec.

Returns None readily and on purpose. A tenant with no team, one person, or
two equally-plausible candidates gets no suggestion, and the UI says "sin
dueño sugerido" — which is honest, and better than a name nobody chose.
"""
from __future__ import annotations

NO_DOMAIN = "__sin_dominio__"


def suggest(modulos) -> dict | None:
    """The one non-admin teammate whose access covers every module this card
    needs, or None when that person is not unique."""
    needed = {m for m in (modulos or ()) if m != NO_DOMAIN}
    if not needed:
        return None
    try:
        from . import perfiles
        matriz = perfiles.matriz()
    except Exception:  # noqa: BLE001 — a lookup failure must not kill the inbox
        return None

    candidates = [
        row for row in matriz
        if not row.get("es_admin")
        and needed <= {m for m, has in (row.get("modulos") or {}).items() if has}
    ]
    if len(candidates) != 1:
        # Zero: nobody covers it. More than one: a coin flip, so say nothing.
        return None
    row = candidates[0]
    return {"suggested": row["nombre"], "role": row.get("rol") or "",
            "reason": sorted(needed)[0]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_insight_owner.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/core/insight_owner.py backend/tests/test_insight_owner.py
git commit -m "Add insight_owner.suggest — owner suggestion from card modules"
```

---

### Task 4: `priorities.py` composer — `insight` replaces `drill`, merge by evidence id

**Files:**
- Modify: `backend/core/priorities.py:118-119` (`_blank_drill`), `:146-173` (`_item`), `:203-227` (`_combine`), `:313-329` (`_compose`)
- Modify: `backend/i18n.py` (one new key)
- Test: `backend/tests/test_priorities.py` (extend)

**Interfaces:**
- Consumes: `insight.build/blank` (Task 1), `confidence.split_for` (Task 2), `insight_owner.suggest` (Task 3).
- Produces:
  - `_item(..., insight=None, ...)` — the `drill=` keyword is gone; the returned card has an `"insight"` key and **also** a `"drill"` key produced by the shim below.
  - `_blank_insight() -> dict` (delegates to `insight.blank()`).
  - `_legacy_drill(ins: dict) -> dict` — **temporary**, deleted in Task 13.
  - `_derive(item, lang)` — fills `insight.owner`, `insight.confidence`, `insight.risk.level`, `insight.deadline.urgency`.

**Note on `_compose` and the cache:** `insight` is fully deterministic, so derivation happens inside `_compose` (which `analisis_cache` memoizes), exactly where `confidence` is attached today at `:321-322`. `action_taken` stays outside the cache — do not move it; the comment at `:274-282` explains why.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_priorities.py`:

```python
# --- structured insight contract ------------------------------------------

from core import insight as _ins


def _with_insight(cid, ins, **kw):
    return _item(cid, **kw) | {"insight": ins}


def test_merge_unions_evidence_by_id_instead_of_concatenating_prose():
    """The duplicate-prose bug: `morosos` and `cobrar_morosos` both state the
    same fact in different words, so string de-dup kept both. Keyed evidence
    makes the duplicate structurally impossible."""
    ev = lambda w: _ins.metric("overdue_total", label="3 clientes por $85.700.000",
                               value=85700000, unit="ars", weight=w,
                               method={"key": "k", "label": "l"})
    a = _with_insight("cobrar_morosos", _ins.build(pattern=_ins.pattern("p"),
                                                   evidence=[ev("supporting")]))
    b = _with_insight("morosos", _ins.build(pattern=_ins.pattern("otra redaccion"),
                                            evidence=[ev("primary")]))
    out = priorities.merge_duplicates([a, b])
    assert len(out) == 1
    evidence = out[0]["insight"]["evidence"]
    assert len(evidence) == 1
    assert evidence[0]["weight"] == "primary", "primary must win over supporting"


def test_merge_keeps_the_canonical_pattern_and_never_concatenates():
    a = _with_insight("cobrar_morosos", _ins.build(pattern=_ins.pattern("canonica")))
    b = _with_insight("morosos", _ins.build(pattern=_ins.pattern("la del alerta")))
    out = priorities.merge_duplicates([a, b])
    assert out[0]["insight"]["pattern"]["label"] == "canonica"


def test_merge_unions_assumptions_by_label():
    a = _with_insight("cobrar_morosos", _ins.build(
        pattern=_ins.pattern("p"), assumptions=[_ins.assumption("mismo supuesto")]))
    b = _with_insight("morosos", _ins.build(
        pattern=_ins.pattern("p"),
        assumptions=[_ins.assumption("mismo supuesto"), _ins.assumption("otro")]))
    out = priorities.merge_duplicates([a, b])
    assert len(out[0]["insight"]["assumptions"]) == 2


def test_compose_derives_confidence_owner_and_urgency_on_every_card():
    inbox = priorities.inbox("es", None)
    for card in inbox["act"] + inbox["watch"]:
        ins = card["insight"]
        assert ins["confidence"]["data"]["level"] in ("high", "medium", "low")
        assert ins["confidence"]["hypothesis"]["level"] in ("high", "medium", "low")
        assert "owner" in ins           # may be None; must be resolved, not missing
        if ins["deadline"]:
            assert ins["deadline"]["urgency"] in (
                "overdue", "today", "this_week", "later")


def test_every_card_carries_a_pattern():
    inbox = priorities.inbox("es", None)
    for card in inbox["act"] + inbox["watch"]:
        assert card["insight"]["pattern"]["label"], f"{card['id']} has no pattern"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_priorities.py -k "insight or evidence or pattern or urgency" -v`
Expected: FAIL — `KeyError: 'insight'`

- [ ] **Step 3: Add the deadline-urgency i18n key**

In `backend/i18n.py`:

```python
    "core.prio.owner_reason": {
        "es": "es quien ve {modulo}",
        "en": "owns {modulo}",
    },
```

- [ ] **Step 4: Rewrite the composer pieces**

In `backend/core/priorities.py`, replace `_blank_drill` (`:118-119`):

```python
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
```

Add the reverse shim next to `_legacy_drill`. **Without it, this task breaks every
one of the ~25 builders the moment it lands** — they all still pass `drill=` until
Tasks 5–9 migrate them:

```python
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
```

Change `_item`'s signature (`:146-149`): keep `drill=None` **and** add `insight=None`.
`insight=` is the real keyword; `drill=` is transitional. Replace the `"drill"` dict
entry (`:169`) with:

```python
        "insight": insight or (_insight_from_legacy_drill(drill) if drill
                               else _blank_insight()),
        "drill": _legacy_drill(insight or (_insight_from_legacy_drill(drill) if drill
                                           else _blank_insight())),  # TEMPORARY, Task 13
```

Extract that repeated expression into a local before the return rather than writing
it twice.

Also **delete `level_for` from `core/confidence.py`** and its three
`core.confidence.reason_*` keys from `i18n.py` — this task replaces its only call
site, and Task 2 deliberately left it alive for exactly this long. Delete its tests
from `tests/test_confidence.py` in the same commit.

Replace `_combine` (`:203-227`) — the merge rules are the fix for the duplication bug:

```python
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
```

Replace the derivation loop in `_compose` (`:321-322`):

```python
    for it in merged:
        _derive(it, lang)
```

and add, above `_compose`:

```python
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
```

**On `fechas.hoy()`:** verified to exist (`backend/core/fechas.py:33`) and to return a `datetime.date`, frozen to `POLPILOT_DEMO_TODAY` when that env var is set (`:41`). Use it — never `datetime.date.today()`, which would make urgency drift off the dataset's 2026-07-07 and break every date-sensitive assertion in the suite.

- [ ] **Step 5: Run the new tests**

Run: `cd backend && python -m pytest tests/test_priorities.py -k "insight or evidence or pattern or urgency" -v`
Expected: the three merge tests PASS. The two `inbox()` tests still FAIL — no builder emits an insight yet (Tasks 5–9). This is expected; leave them failing and note it in the commit.

- [ ] **Step 6: Run the full priorities suite for regressions**

Run: `cd backend && python -m pytest tests/test_priorities.py tests/test_priorities_drill.py tests/test_api.py -v`
Expected: everything that passed before still passes. The two shims are what make this true: unmigrated builders still pass `drill=` and `_insight_from_legacy_drill` wraps it, then `_legacy_drill` renders it back, so `drill` stays present and populated for the untouched frontend and the existing drill tests.

**If any test fails with `TypeError: _item() got an unexpected keyword argument 'drill'`, the `drill=` keyword was dropped — re-add it.** Removing it is Task 13's job, not this one.

- [ ] **Step 7: Commit**

```bash
git add backend/core/priorities.py backend/tests/test_priorities.py backend/i18n.py
git commit -m "Compose insights: merge evidence by id, derive confidence/owner/urgency

Two inbox-level tests fail until the builders migrate (Tasks 5-9).
_legacy_drill is a temporary one-way shim so the frontend keeps working;
Task 13 deletes it."
git checkout -- data-demo/
```

---

### Tasks 5–7: migrate the 14 alert builders in `priorities.py`

These three tasks share one mechanical transformation, shown in full in Task 5 and applied per the tables in Tasks 6 and 7. The rule for splitting a builder's existing prose:

- The sentence stating **what was counted or observed** → `pattern`.
- The sentence **interpreting** it ("el desvío es la señal") → `hypothesis`, or `None` if the builder never interpreted anything.
- Each **number interpolated into those strings** (`n=`, `monto=`, `dias=`, `prom=`) → an `insight.metric` carrying the raw value, its unit and its `method`.
- The existing `involucrados` list → `insight.records(...)` with `insight.record(...)` rows.
- The existing `grafico` → `insight.series(...)`.
- `supuestos` → `insight.assumption(...)`.

Every new `method.label`, `alternatives` and `falsifiers` string is new copy and must be added to `i18n.py` bilingually in the same commit.

---

### Task 5: alert builders — cuentas and ventas

**Files:**
- Modify: `backend/core/priorities.py:438-511` (`_alerts_cuentas`, `_alerts_ventas`)
- Modify: `backend/i18n.py`
- Test: `backend/tests/test_priorities_drill.py`

**Interfaces:**
- Consumes: `insight.*` (Task 1), `_item(insight=…)` (Task 4).
- Produces: cards `morosos`, `moroso_atraso`, `quiebre` carrying insights whose evidence ids are `overdue_total`, `overdue_clients`, `days_overdue`, `stockout_count`, `stockout_items`. **These ids are the merge keys** — `cobrar_morosos` (Task 8) must reuse `overdue_total`/`overdue_clients`, and `quiebre_inminente` must reuse `stockout_count`/`stockout_items`, or the twins will not de-duplicate.

- [ ] **Step 1: Write the failing test**

Replace the `morosos`/`moroso_atraso`/`quiebre` tests in `backend/tests/test_priorities_drill.py`:

```python
import json
import os
import subprocess
import sys

_DEMO_INBOX = None


def _demo_inbox():
    """The real demo dataset's inbox, fetched once per module.

    This suite's fixture pins tenant `piloto` over a near-empty scratch dataset
    (tests/conftest.py), so an in-process `inbox()` returns almost no cards and
    every per-card assertion below would pass vacuously or skip. Card-shape
    assertions only mean anything against the seeded dataset, so this follows
    the repo's established subprocess pattern (test_priorities.py::_en_demo).
    Fetched once and cached — the subprocess costs seconds and every test here
    reads the same payload.
    """
    global _DEMO_INBOX
    if _DEMO_INBOX is None:
        backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_demo = os.path.join(os.path.dirname(backend), "data-demo")
        env = {**os.environ, "POLPILOT_TENANT": "demo",
               "POLPILOT_DATA_DIR": data_demo,
               "POLPILOT_DEMO_TODAY": "2026-07-07", "PYTHONIOENCODING": "utf-8"}
        env.pop("ANTHROPIC_API_KEY", None)
        expr = ("__import__('core.priorities', fromlist=['x']).inbox('es', "
                "['alertas','oportunidades','cuentas','inventario','deposito',"
                "'finanzas','caja','evolucion'])")
        r = subprocess.run(
            [sys.executable, "-c", f"import json; print(json.dumps({expr}))"],
            cwd=backend, env=env, capture_output=True, text=True, timeout=180)
        assert r.returncode == 0, r.stderr[-800:]
        _DEMO_INBOX = json.loads(r.stdout.strip().splitlines()[-1])
    return _DEMO_INBOX


def _card(cid):
    d = _demo_inbox()
    return next((c for c in d["act"] + d["watch"] if c["id"] == cid), None)


def test_moroso_atraso_states_the_deviation_as_a_metric():
    c = _card("moroso_atraso") or _card("cobrar_morosos")
    assert c, "expected a debtor card in the demo dataset"
    ins = c["insight"]
    assert ins["pattern"]["label"]
    days = next(e for e in ins["evidence"] if e["id"] == "days_overdue")
    assert days["unit"] == "days"
    assert days["baseline"]["value"] > 0, "the client's own payment average"
    assert days["deviation"]["direction"] == "up"
    assert days["method"]["label"], "every metric explains how it was computed"


def test_debtor_card_links_real_client_records():
    c = _card("moroso_atraso") or _card("cobrar_morosos")
    rows = [r for e in c["insight"]["evidence"] for r in e["records"]]
    assert rows, "the debtors must be listed as clickable records"
    assert all(r["kind"] == "client" and r["id"] is not None for r in rows)


def test_stockout_card_lists_products_as_records():
    c = _card("quiebre") or _card("quiebre_inminente")
    assert c, "expected a stockout card in the demo dataset"
    rows = [r for e in c["insight"]["evidence"] for r in e["records"]]
    assert all(r["kind"] == "product" and r["id"] is not None for r in rows)


def test_no_alert_card_emits_an_empty_pattern():
    d = _demo_inbox()
    for c in d["act"] + d["watch"]:
        assert c["insight"]["pattern"] and c["insight"]["pattern"]["label"], c["id"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_priorities_drill.py -v`
Expected: FAIL — the debtor card's insight has no evidence yet.

- [ ] **Step 3: Add the i18n keys**

In `backend/i18n.py`:

```python
    "core.method.mora_total": {
        "es": "Suma de saldos vencidos de clientes con al menos un comprobante impago pasada su fecha.",
        "en": "Sum of overdue balances for clients with at least one unpaid invoice past its due date.",
    },
    "core.method.dias_mora": {
        "es": "Días entre la última cobranza registrada del cliente y hoy.",
        "en": "Days between the client's last recorded payment and today.",
    },
    "core.method.prom_pago": {
        "es": "Promedio de días entre cobranzas de ese cliente en su historia.",
        "en": "That client's historical average days between payments.",
    },
    "core.method.quiebre_conteo": {
        "es": "Artículos cuya cobertura proyectada, al ritmo de venta actual, es menor al lead time del proveedor.",
        "en": "Items whose projected coverage at the current sales rate is below supplier lead time.",
    },
    "core.prio.morosos_hyp": {
        "es": "La mora está concentrada: son pocos clientes, no una caída general de la cobranza.",
        "en": "The overdue balance is concentrated — a few clients, not a general collections slump.",
    },
    "core.prio.atraso_hyp": {
        "es": "{nombre} cambió su comportamiento de pago, no necesariamente su capacidad.",
        "en": "{nombre}'s payment behaviour changed — not necessarily their ability to pay.",
    },
    "core.prio.atraso_alt": {
        "es": "Puede haber un pago hecho y todavía no registrado.",
        "en": "There may be a payment made but not yet recorded.",
    },
    "core.prio.atraso_fals": {
        "es": "Un comprobante de pago posterior a la última cobranza registrada.",
        "en": "A payment receipt dated after the last recorded collection.",
    },
    "core.prio.mora_sup": {
        "es": "Asumo que no hubo pagos en efectivo sin registrar.",
        "en": "I assume there were no unrecorded cash payments.",
    },
    "core.prio.mora_sup_if": {
        "es": "La mora real sería menor.",
        "en": "The real overdue figure would be lower.",
    },
    "core.prio.quiebre_hyp": {
        "es": "El faltante es de reposición, no de demanda: se vende igual que siempre.",
        "en": "This is a restocking gap, not a demand drop — sales are unchanged.",
    },
    "core.prio.quiebre_risk": {
        "es": "Venta perdida mientras el artículo no esté en góndola.",
        "en": "Lost sales for as long as the item is off the shelf.",
    },
    "core.prio.mora_risk": {
        "es": "Capital inmovilizado en la calle.",
        "en": "Working capital stuck with customers.",
    },
```

- [ ] **Step 4: Rewrite `_alerts_cuentas` and `_alerts_ventas`**

In `backend/core/priorities.py`, replace lines 438-511:

```python
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
```

- [ ] **Step 5: Run the tests**

Run: `cd backend && python -m pytest tests/test_priorities_drill.py -v`
Expected: the three debtor/stockout tests PASS. `test_no_alert_card_emits_an_empty_pattern` still FAILS (Tasks 6–9 remain).

- [ ] **Step 6: Verify the shim keeps the app coherent**

Run: `cd backend && python -m pytest tests/test_priorities.py tests/test_api.py -v`
Expected: PASS — `_legacy_drill` renders these insights back into `drill.porque`, so nothing downstream broke.

- [ ] **Step 7: Commit**

```bash
git add backend/core/priorities.py backend/i18n.py backend/tests/test_priorities_drill.py
git commit -m "Migrate cuentas and ventas alerts to structured insights"
git checkout -- data-demo/
```

---

### Task 6: alert builders — pagos and deposito

**Files:**
- Modify: `backend/core/priorities.py:514-700` (`_alerts_pagos`, `_alerts_deposito`)
- Modify: `backend/i18n.py`
- Test: `backend/tests/test_priorities_drill.py`

**Interfaces:**
- Consumes: the same `insight.*` vocabulary and the transformation rule stated before Task 5.
- Produces: cards `pago_vencido`, `pago_semana`, `cheques`, `dep_vencidos`, `dep_porvencer`, `dep_discrep`, `venc_riesgo`.

**Per-card content.** Apply the Task 5 transformation with these values. `method` keys are new and need bilingual `i18n.py` entries; `records` rows use `insight.record(kind=…, id=…)` where an id exists.

| Card | pattern (existing key) | hypothesis | evidence ids | records | risk exposure |
|---|---|---|---|---|---|
| `pago_vencido` | `core.prio.pago_vencido_p` | none — a due date passing needs no interpretation, so `hypothesis=None` | `payables_overdue_total` (ars, primary), `payables_overdue_rows` (records) | supplier rows from `pagos.pagos_vencidos()[:8]`, **no `id`/`kind`** — `pagos.py` has no stable per-row id (see spec's prior-art note); pass `kind=None, id=None` so rows render as plain text | `pv["vencidos_total"]` |
| `pago_semana` | `core.prio.pago_semana_p` | none | `payables_week_total` (ars, primary), `payables_week_rows` (records) | same, no ids | week total |
| `cheques` | `core.prio.cheques_p` | none | `checks_total` (ars, primary), `checks_rows` (records) | same, no ids | checks total |
| `dep_vencidos` | `core.prio.dep_vencidos_p` | none | `expired_lots_value` (ars, primary), `expired_lots` (records) | `deposito.vencidos()` rows via `_deposito_lot_value()`, `kind="product"`, `id=row["codigo"]` | summed `valor` |
| `dep_porvencer` | `core.prio.dep_porvencer_p` | `core.prio.dep_porvencer_hyp` (new) — "es rotación, no compra de más: el lote entró y no salió a tiempo" | `expiring_lots_value` (ars, primary), `expiring_lots` (records) | `deposito.vencimientos()` via `_deposito_lot_value()`, `kind="product"` | summed `valor` **of the expiring fraction only**, not total lot value |
| `dep_discrep` | **new** `core.prio.dep_discrep_p` (see below) | none | `discrepancy_count` (products, primary), `discrepancy_rows` (records) | `deposito.discrepancias()`, `kind="product"`, `id=row["codigo"]` | none |
| `venc_riesgo` | `core.prio.venc_riesgo_p` | none | `at_risk_value` (ars, primary), `at_risk_rows` (records) | `kind="product"` | at-risk total |

**`dep_discrep` has no `porque` today** (`priorities.py:670` returns a blank drill), so its pattern is genuinely new copy, not a translation:

```python
    "core.prio.dep_discrep_p": {
        "es": "{n} artículo(s) tienen diferencia entre el stock del sistema y el del depósito.",
        "en": "{n} item(s) differ between system stock and warehouse stock.",
    },
    "core.method.dep_discrep": {
        "es": "Comparación entre la existencia registrada y el último conteo de depósito.",
        "en": "Recorded stock compared against the latest warehouse count.",
    },
    "core.prio.dep_porvencer_hyp": {
        "es": "Es un problema de rotación, no de compra de más: el lote entró y no salió a tiempo.",
        "en": "A turnover problem, not over-buying — the lot came in and did not move in time.",
    },
```

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_priorities_drill.py`:

```python
import pytest


@pytest.mark.parametrize("cid", ["pago_vencido", "pago_semana", "cheques",
                                 "dep_vencidos", "dep_porvencer", "dep_discrep",
                                 "venc_riesgo"])
def test_finance_and_warehouse_alerts_carry_pattern_and_evidence(cid):
    c = _card(cid)
    if c is None:
        pytest.skip(f"{cid} not present in the demo dataset")
    ins = c["insight"]
    assert ins["pattern"]["label"], f"{cid} has no pattern"
    assert ins["evidence"], f"{cid} has no evidence"
    assert all(e["method"]["label"] for e in ins["evidence"]), \
        f"{cid} has a metric with no 'how was this calculated'"


@pytest.mark.parametrize("cid", ["dep_vencidos", "dep_porvencer", "dep_discrep",
                                 "venc_riesgo"])
def test_warehouse_alerts_link_real_products(cid):
    c = _card(cid)
    if c is None:
        pytest.skip(f"{cid} not present in the demo dataset")
    rows = [r for e in c["insight"]["evidence"] for r in e["records"]]
    assert rows, f"{cid} lists no products"
    assert all(r["kind"] == "product" and r["id"] is not None for r in rows)


@pytest.mark.parametrize("cid", ["pago_vencido", "pago_semana", "cheques"])
def test_finance_alert_rows_are_plain_text_not_fake_links(cid):
    """pagos.py has no stable per-row id. A row that looks clickable and
    silently no-ops is worse than plain text."""
    c = _card(cid)
    if c is None:
        pytest.skip(f"{cid} not present in the demo dataset")
    rows = [r for e in c["insight"]["evidence"] for r in e["records"]]
    assert all(r["id"] is None and r["kind"] is None for r in rows)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_priorities_drill.py -k "finance or warehouse" -v`
Expected: FAIL — no evidence on these cards yet.

- [ ] **Step 3: Add the i18n keys above, plus one `core.method.*` key per evidence id in the table**

Each `method` label states the calculation in one sentence, in both languages, following the wording style of the `core.method.*` keys added in Task 5.

- [ ] **Step 4: Rewrite the two builders** following Task 5's structure and the table above, keeping every existing `_item(...)` envelope argument (`id`, `tono`, `chip`, `titulo`, `resumen`, `origen`, `modulos`, `monto`, `fuentes`, `navegar`, `accion_chat`) exactly as it is today and replacing only the `drill={...}` argument with `insight=ins.build(...)`.

- [ ] **Step 5: Run the tests**

Run: `cd backend && python -m pytest tests/test_priorities_drill.py -v`
Expected: the finance and warehouse tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/core/priorities.py backend/i18n.py backend/tests/test_priorities_drill.py
git commit -m "Migrate pagos and deposito alerts to structured insights"
git checkout -- data-demo/
```

---

### Task 7: alert builders — inventario, caja, evolucion, pico

**Files:**
- Modify: `backend/core/priorities.py:700-825` (`_alerts_inventario`, `_alerts_caja`, `_alerts_evolucion`, `_alerts_pico`)
- Modify: `backend/i18n.py`
- Test: `backend/tests/test_priorities_drill.py`

**Interfaces:**
- Produces: cards `costo_viejo`, `caja_inusual`, `caida_interanual`, `pico`.

| Card | pattern | hypothesis | evidence ids | records |
|---|---|---|---|---|
| `costo_viejo` | `core.prio.costo_viejo_p` | `core.prio.costo_viejo_hyp` (new) — "el precio quedó viejo frente al costo, no es un problema de demanda" | `stale_cost_value` (ars, primary), `stale_cost_rows` (records) | `store.panorama()["alertas"]["costo_viejo"]`, `kind="product"`, `id=row["codigo"]` |
| `caja_inusual` | `core.prio.caja_p` | `core.prio.caja_hyp` (new) — "un movimiento puntual, no un cambio de nivel" | `cash_today` (ars, primary, `baseline` = the trailing average that triggered the alert), `cash_history` (series, chart from `historial`) | none — `caja.py` history rows have no stable id |
| `caida_interanual` | reuse `a["detalle"]` from `evolucion.alertas_de` as the pattern label | `core.prio.caida_hyp` (new) — "la caída es de volumen, no de precio" | `yoy_change` (pct, primary, `baseline` = last year's value), `yoy_series` (series, from `evolucion.panorama()`'s monthly comparison) | none — `evolucion.py` has no per-category breakdown |
| `pico` | `core.prio.pico_p` | none | `peak_multiplier` (`×`, primary) | none |

`caja_inusual` and `caida_interanual` deliberately carry **no records**. That is an honest reflection of what the data supports, not a gap: neither module has a per-row list UI to land on, and inventing a link that goes nowhere is worse than none (spec's out-of-scope section).

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_priorities_drill.py`:

```python
@pytest.mark.parametrize("cid", ["costo_viejo", "caja_inusual",
                                 "caida_interanual", "pico"])
def test_remaining_alerts_carry_pattern_and_evidence(cid):
    c = _card(cid)
    if c is None:
        pytest.skip(f"{cid} not present in the demo dataset")
    ins = c["insight"]
    assert ins["pattern"]["label"]
    assert ins["evidence"]


def test_whole_business_alerts_carry_a_chart_instead_of_records():
    """No per-row UI exists for caja/evolución, so these prove themselves
    with a series rather than fake links."""
    for cid in ("caja_inusual", "caida_interanual"):
        c = _card(cid)
        if c is None:
            continue
        ev = c["insight"]["evidence"]
        assert any(e["kind"] == "series" and e["chart"] for e in ev), cid
        assert not [r for e in ev for r in e["records"]], cid
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_priorities_drill.py -k "remaining or whole_business" -v`
Expected: FAIL.

- [ ] **Step 3: Add the three new hypothesis keys and one `core.method.*` key per evidence id, bilingually.**

- [ ] **Step 4: Rewrite the four builders** following Task 5's structure and the table above. Build the two charts with the existing local `_grafico(nombre, puntos, unidad, temporal, ventana)` helper (`priorities.py:122-129`) and wrap them in `ins.series(...)`.

- [ ] **Step 5: Run the full alert suite**

Run: `cd backend && python -m pytest tests/test_priorities_drill.py -v`
Expected: PASS — including `test_no_alert_card_emits_an_empty_pattern` from Task 5, since every alert builder has now migrated.

- [ ] **Step 6: Commit**

```bash
git add backend/core/priorities.py backend/i18n.py backend/tests/test_priorities_drill.py
git commit -m "Migrate inventario, caja, evolucion and pico alerts to insights"
git checkout -- data-demo/
```

---

### Task 8: migrate the 10 finding builders in `oportunidades_neg.py`

**Files:**
- Modify: `backend/core/oportunidades_neg.py` — `_card_morosos:205`, `_card_dormido:249`, `_card_ventana_compra:372`, `_card_cliente_frio:438`, `_card_estrella_caida:514`, `_card_quiebre_inminente:589`, `_card_pre_pico:714`, `_card_concentracion:770`, `_card_margen_bajo:867`, `_card_sobrecompra:979`
- Modify: `backend/i18n.py`
- Test: `backend/tests/test_priorities_drill.py`, `backend/tests/test_priorities.py`

**Interfaces:**
- Consumes: `insight.*`, and the evidence ids Task 5 established.
- Produces: each `_card_*` returns its dict with `"insight"` instead of `"drill"`. `_opportunity_items` (`priorities.py:350-372`) changes `drill=c.get("drill") or _blank_drill()` to `insight=c.get("insight") or _blank_insight()`.

**Critical — merge keys.** `MERGE_INTO` (`priorities.py:15-20`) merges `morosos`+`moroso_atraso` → `cobrar_morosos`, `quiebre` → `quiebre_inminente`, `pico` → `pre_pico`. For de-duplication to work, the merge targets must reuse the twins' evidence ids:

- `_card_morosos` (id `cobrar_morosos`) → `overdue_total`, `overdue_clients`, `days_overdue`
- `_card_quiebre_inminente` → `stockout_count`, `stockout_items`
- `_card_pre_pico` → `peak_multiplier`

**`metrics` is retired.** `_card_quiebre_inminente` currently returns a separate `drill["metrics"]` list (`:638-647`) of `{label, value}` day-counts, rendered by a dedicated `Metrics` component precisely because they do not share the chart's x-axis. Each becomes an `insight.metric` with `weight="supporting"` and its own `method`, so the special case disappears: `days_of_coverage` (unit `days`), `supplier_lead_time` (unit `days`), `negotiating_window` (unit `days`).

**The knowledge-rule prepend** at `:654` (`porque.insert(0, _t("core.opn.qi_k_por", …))`) becomes an additional `insight.metric` with `weight="primary"` placed first in the evidence list — same emphasis, no string surgery.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_priorities_drill.py`:

```python
OPPORTUNITY_IDS = ["cobrar_morosos", "despertar_dormido", "ventana_compra",
                   "cliente_frio", "estrella_caida", "quiebre_inminente",
                   "pre_pico", "concentracion", "margen_bajo", "sobrecompra"]


@pytest.mark.parametrize("cid", OPPORTUNITY_IDS)
def test_opportunity_cards_carry_structured_insight(cid):
    c = _card(cid)
    if c is None:
        pytest.skip(f"{cid} not present in the demo dataset")
    ins = c["insight"]
    assert ins["pattern"]["label"]
    assert ins["evidence"]
    assert any(e["weight"] == "primary" for e in ins["evidence"]), \
        f"{cid} declares nothing load-bearing"
    assert ins["recommendation"]["label"]


def test_restock_card_keeps_its_day_counts_as_supporting_metrics():
    """The retired `metrics` strip: same numbers, now first-class evidence."""
    c = _card("quiebre_inminente")
    if c is None:
        pytest.skip("quiebre_inminente not present")
    ids = {e["id"] for e in c["insight"]["evidence"]}
    assert {"days_of_coverage", "supplier_lead_time"} <= ids


def test_no_card_anywhere_still_carries_metrics_on_the_insight():
    d = _demo_inbox()
    for c in d["act"] + d["watch"]:
        assert "metrics" not in c["insight"], c["id"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_priorities_drill.py -k "opportunity or restock or metrics" -v`
Expected: FAIL.

- [ ] **Step 3: Migrate the ten builders**

Apply the transformation rule stated before Task 5 to each `_card_*`, and change `_opportunity_items` in `priorities.py` to pass `insight=` instead of `drill=`. Each builder keeps every other key it returns (`id`, `titulo`, `resumen`, `monto`, `monto_label`, `fuentes`, `navegar`, `accion_chat`, `propuesta`, `macro`, `naturaleza`, `tipo`) unchanged.

Set `recommendation` on every card from what it already has: `label=c["titulo"]`, `proposal=c.get("propuesta")`, `navigate=c.get("navegar")`, `chat=c.get("accion_chat")`.

Set `deadline` where a real clock exists — and only there:
- `quiebre_inminente`: `ins.deadline(date=<today + supplier lead time>, basis=<lead-time label>)`
- `ventana_compra`: the closing date of the buying window already computed in the builder
- `pre_pico`: the peak's start date
- every other card: `deadline=None`. Do not invent a date; the UI renders no chip when there is none.

- [ ] **Step 4: Run the tests**

Run: `cd backend && python -m pytest tests/test_priorities_drill.py tests/test_priorities.py -v`
Expected: PASS, including `test_merge_unions_evidence_by_id_instead_of_concatenating_prose` now exercising real merged cards.

- [ ] **Step 5: Verify the canonical demo numbers did not move**

Run: `cd backend && python -m pytest tests/test_p27.py tests/test_cobranza.py tests/test_reponer.py -v`
Expected: the two known `test_p27.py` failures listed in Global Constraints, and nothing else. `recuperable` is unchanged by this work — if a `recuperable` assertion moves, an envelope field was edited by mistake.

- [ ] **Step 6: Commit**

```bash
git add backend/core/oportunidades_neg.py backend/core/priorities.py backend/i18n.py backend/tests/
git commit -m "Migrate the ten opportunity builders to structured insights"
git checkout -- data-demo/
```

---

### Task 9: migrate `patrones.py` and `piso.py`

**Files:**
- Modify: `backend/core/patrones.py:184`, `:255`
- Modify: `backend/core/piso.py` (`propuestas()`)
- Modify: `backend/core/priorities.py:375-422` (`_pattern_items`, `_piso_items`)
- Test: `backend/tests/test_patrones.py`

**Interfaces:**
- Produces: pattern and floor-report cards carrying insights; `_pattern_items` and `_piso_items` pass `insight=` instead of `drill=`.

Pattern cards are correlations rather than single numbers, so their `hypothesis` is the interpretation of the correlation and their `alternatives` should name the obvious confounder — a correlation card with no declared alternative reads as high hypothesis-confidence, which for a correlation is rarely honest.

Floor reports (`piso`) are a team member's report, not a computed finding: `pattern` is what was reported, `hypothesis` is `None`, and the single piece of evidence is the report itself as a `records` item.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_patrones.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_patrones.py -k "alternative or floor" -v`
Expected: FAIL — `KeyError: 'insight'`.

- [ ] **Step 3: Migrate both modules** per the transformation rule, adding bilingual `i18n.py` keys for each new `alternatives` and `method` string.

- [ ] **Step 4: Run the tests**

Run: `cd backend && python -m pytest tests/test_patrones.py tests/test_priorities.py -v`
Expected: PASS, including Task 4's `test_every_card_carries_a_pattern` and `test_compose_derives_confidence_owner_and_urgency_on_every_card` — every builder has now migrated.

- [ ] **Step 5: Run the whole backend suite**

Run: `cd backend && python -m pytest -q`
Expected: only the two known `test_p27.py` failures.

- [ ] **Step 6: Commit**

```bash
git add backend/core/patrones.py backend/core/piso.py backend/core/priorities.py backend/i18n.py backend/tests/
git commit -m "Migrate pattern and floor-report cards to structured insights"
git checkout -- data-demo/
```

---

### Task 10: widen Ángela's `_slim` projection

**Files:**
- Modify: `backend/angela.py:1950-1966`
- Test: `backend/tests/test_angela_slim.py` (new)

**Interfaces:**
- Consumes: the finished card with its `insight` (Tasks 4–9).
- Produces: `_slim(item) -> dict` — the eight existing keys plus `insight`, trimmed. `listar_prioridades` keeps its name, empty input schema and permission special-case (`angela.py:124-134`); `mcp_server.py` is untouched.

**What the projection carries** (spec §"What `_slim` carries"): pattern label, hypothesis label, `primary` evidence only (label, value, unit, baseline, deviation, method label), first 3 records per item plus `records_total`, assumption/alternative/falsifier labels, both confidence levels, risk level and exposure, deadline urgency and date, owner name. **Dropped:** charts, `supporting` evidence, `confidence.*.signals`, `assumptions[].if_wrong`, `recommendation` (already on the envelope as `titulo`/`accion_chat`).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_angela_slim.py`:

```python
"""angela._slim — a projection, never a second computation."""
from core import insight as ins

import angela


def _card():
    chart = {"ok": True, "series": [{"nombre": "s", "puntos": [{"x": 1, "y": 2}]}],
             "meta": {}}
    return {
        "id": "cobrar_morosos", "chip": "Cobrar", "titulo": "t", "resumen": "r",
        "monto": 85700000, "cifra_texto": None, "tono": "rojo", "band": "act",
        "insight": ins.build(
            pattern=ins.pattern("3 clientes concentran la mora"),
            hypothesis=ins.hypothesis("cambió el comportamiento de pago"),
            evidence=[
                ins.metric("overdue_total", label="$85.700.000", value=85700000,
                           unit="ars", weight="primary",
                           baseline={"value": 40000000, "label": "mes pasado"},
                           method={"key": "k", "label": "Suma de saldos vencidos"},
                           records=[ins.record(kind="client", id=i, name=f"c{i}")
                                    for i in range(9)]),
                ins.series("hist", label="serie", chart=chart,
                           method={"key": "k", "label": "l"}, weight="supporting"),
            ],
            assumptions=[ins.assumption("sin pagos en efectivo", if_wrong="menor")],
            risk=ins.risk("capital en la calle", exposure=85700000),
        ) | {"confidence": {"data": {"level": "high", "reason": "r", "signals": {"x": 1}},
                            "hypothesis": {"level": "low", "reason": "r", "signals": {}}},
             "owner": {"suggested": "Marina", "role": "Cobranzas", "reason": "cuentas"},
             "deadline": {"date": "2026-07-14", "basis": "b", "urgency": "this_week"}},
    }


def test_only_primary_evidence_reaches_the_model():
    s = angela._slim(_card())
    assert [e["id"] for e in s["insight"]["evidence"]] == ["overdue_total"]


def test_charts_are_dropped():
    """Series points are for rendering, not reasoning."""
    s = angela._slim(_card())
    assert all("chart" not in e for e in s["insight"]["evidence"])


def test_records_are_capped_but_the_total_is_reported():
    s = angela._slim(_card())
    ev = s["insight"]["evidence"][0]
    assert len(ev["records"]) == 3
    assert ev["records_total"] == 9


def test_values_are_passed_through_untouched_never_reformatted():
    """The deterministic invariant: the projection selects, it does not
    compute or format. A pesos string here would be Angela's number, not
    core's."""
    card = _card()
    s = angela._slim(card)
    src = card["insight"]["evidence"][0]
    out = s["insight"]["evidence"][0]
    assert out["value"] == src["value"] and out["value"] == 85700000
    assert out["baseline"] == src["baseline"]
    assert out["deviation"] == src["deviation"]


def test_confidence_levels_survive_but_signals_do_not():
    s = angela._slim(_card())["insight"]["confidence"]
    assert s["data"] == "high" and s["hypothesis"] == "low"


def test_envelope_keys_are_unchanged():
    s = angela._slim(_card())
    for k in ("id", "chip", "titulo", "resumen", "monto", "cifra_texto", "tono", "band"):
        assert k in s
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_angela_slim.py -v`
Expected: FAIL — `_slim` is a local closure inside the handler, not module-level.

- [ ] **Step 3: Implement**

In `backend/angela.py`, lift `_slim` to module level (just above the tool handler) and widen it:

```python
_SLIM_KEYS = ("id", "chip", "titulo", "resumen", "monto", "cifra_texto", "tono", "band")
_SLIM_MAX_RECORDS = 3


def _slim(item: dict) -> dict:
    """One priority, trimmed for the model.

    Carries the REASONING and drops the BULK: charts and supporting evidence
    are for the screen, not for a prompt, and twenty cards' worth of series
    points would crowd out the answer.

    This SELECTS from the finished insight — it never recomputes or
    reformats a value. Every number Ángela says traces back to core/.
    """
    out = {k: item.get(k) for k in _SLIM_KEYS}
    ins = item.get("insight") or {}
    conf = ins.get("confidence") or {}
    risk = ins.get("risk") or {}
    deadline = ins.get("deadline") or {}
    owner = ins.get("owner") or {}
    labels = lambda rows: [r["label"] for r in (rows or [])]

    out["insight"] = {
        "pattern": (ins.get("pattern") or {}).get("label"),
        "hypothesis": (ins.get("hypothesis") or {}).get("label"),
        "evidence": [_slim_evidence(e) for e in (ins.get("evidence") or [])
                     if e.get("weight") == "primary"],
        "assumptions": labels(ins.get("assumptions")),
        "alternatives": labels(ins.get("alternatives")),
        "falsifiers": labels(ins.get("falsifiers")),
        "confidence": {"data": (conf.get("data") or {}).get("level"),
                       "hypothesis": (conf.get("hypothesis") or {}).get("level")},
        "risk": {"level": risk.get("level"), "exposure": risk.get("exposure")},
        "deadline": {"date": deadline.get("date"), "urgency": deadline.get("urgency")},
        "owner": owner.get("suggested"),
    }
    return out


def _slim_evidence(e: dict) -> dict:
    rows = e.get("records") or []
    return {
        "id": e.get("id"), "label": e.get("label"), "value": e.get("value"),
        "unit": e.get("unit"), "baseline": e.get("baseline"),
        "deviation": e.get("deviation"),
        "method": (e.get("method") or {}).get("label"),
        "records": [{"name": r.get("name"), "amount": r.get("amount"),
                     "detail": r.get("detail")} for r in rows[:_SLIM_MAX_RECORDS]],
        "records_total": len(rows),
    }
```

Then delete the inner `def _slim(...)` from the `listar_prioridades` handler, leaving its two `[_slim(i) for i in ...]` calls pointing at the module-level function.

- [ ] **Step 4: Run the tests**

Run: `cd backend && python -m pytest tests/test_angela_slim.py tests/test_mcp_server.py -v`
Expected: PASS — `mcp_server.py` validates tool names against `angela.TOOLS` at import, and the catalog is unchanged.

- [ ] **Step 5: Commit**

```bash
git add backend/angela.py backend/tests/test_angela_slim.py
git commit -m "Widen Angela's _slim to carry the trimmed insight"
git checkout -- data-demo/
```

---

### Task 11: `DrillNegocio` reads the insight

**Files:**
- Modify: `frontend/src/components/CardNegocio.jsx:136-380`
- Modify: `frontend/src/lib/locales/es.js`, `frontend/src/lib/locales/en.js`

**Interfaces:**
- Consumes: `insight` from the API.
- Produces: `DrillNegocio` takes a single `insight` prop in place of `porque`, `grafico`, `involucrados`, `supuestos`, `confidence` and `metrics`. Every other prop (`tono`, `titulo`, `monto`, `montoLabel`, `cifraTexto`, `macro`, `fuentes`, `acciones`, `onCerrar`, `propuesta`, `onAprobarPropuesta`, `actionTaken`, `propuestaTrabajando`, `variante`, `chip`, `chipIcon`, `chipCls`, `onFeedback`, `feedbackBusy`, `origins`, `onVerFuentes`, `onVerInvolucrado`) is unchanged. Callers are updated in Task 12.

**Render order** (replacing the current sequence at `:289-374`):

1. **Pattern** — `insight.pattern.label`, prominent, directly under the title.
2. **Hypothesis** — `insight.hypothesis.label` with the two confidence badges beside it, labelled *datos* and *hipótesis*. When `hypothesis` is `null`, render neither the block nor the hypothesis badge.
3. **Evidence** — `primary` items expanded; `supporting` collapsed behind a "+N más" toggle. Each item shows `label`, and where present a formatted `value`/`unit`, its `baseline.label` and `deviation` as a delta, a `<details>` disclosure holding `method`, its `chart` (through the existing `CuerpoConsulta` renderer), and its `records` through the existing `InvolucradoRow`.
4. **Risk**, then **Recommendation** — the latter wrapping the unchanged `AngelaProposal`.
5. **Assumptions**, then a collapsed "¿Qué cambiaría esta conclusión?" holding `alternatives` and `falsifiers`.
6. Owner and deadline as a footer line; `fuentes` pills, `BasedOn`, `FindingFeedback` unchanged.

`Metrics` (`:198-210`) and its call site (`:344`) are **deleted** — those day-counts are now ordinary `supporting` evidence, so the special case that existed only because they did not share the chart's x-axis no longer applies.

`ConfidenceBadge` (`:145-157`) gains an `axis` prop so it can render either level with the right label. `InvolucradoRow` (`:212-233`) keeps its logic but reads `record` field names (`name`/`amount`/`detail` instead of `nombre`/`monto`/`detalle`).

**Formatting numbers:** `value` is raw. Format with the existing `peso`/`pesoCorto` helpers already imported in this file when `unit === "ars"`, and with `Intl.NumberFormat` otherwise. Never render a raw float.

- [ ] **Step 1: Add the locale keys**

In both `frontend/src/lib/locales/es.js` and `en.js`, under the existing `cardneg` namespace:

```
cardneg.drill_pattern      "Qué observamos" / "What we observed"
cardneg.drill_hypothesis   "Qué creemos que significa" / "What we think it means"
cardneg.drill_evidence     "Evidencia" / "Evidence"
cardneg.drill_risk         "Riesgo" / "Risk"
cardneg.drill_recommend    "Qué conviene hacer" / "Recommended action"
cardneg.drill_assumptions  "Supuestos" / "Assumptions"
cardneg.drill_caveats      "¿Qué cambiaría esta conclusión?" / "What would change this?"
cardneg.drill_alternatives "Otras explicaciones posibles" / "Other possible explanations"
cardneg.drill_method       "¿Cómo se calculó?" / "How was this calculated?"
cardneg.drill_more         "+{n} más" / "+{n} more"
cardneg.conf_data          "datos" / "data"
cardneg.conf_hypothesis    "hipótesis" / "hypothesis"
cardneg.drill_owner        "Sugerido: {name}" / "Suggested: {name}"
cardneg.drill_no_owner     "Sin dueño sugerido" / "No suggested owner"
cardneg.drill_due          "Para el {date}" / "Due {date}"
cardneg.drill_vs           "contra {baseline}" / "vs. {baseline}"
```

- [ ] **Step 2: Restructure `DrillNegocio`** per the render order above.

- [ ] **Step 3: Verify it builds**

Run: `cd frontend && npx vite build`
Expected: build succeeds. It will still fail at runtime until Task 12 passes `insight` — that is the next task.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/CardNegocio.jsx frontend/src/lib/locales/
git commit -m "Restructure DrillNegocio around the insight contract"
```

---

### Task 12: wire both screens to the insight

**Files:**
- Modify: `frontend/src/sections/Prioridades.jsx:45-81` (`WorkRow`), `:306-348` (`drillProps`)
- Modify: `frontend/src/mobile/InsightsMobile.jsx:26-53` (`rowOf`), `:55-84` (`Fila`)
- Modify: `frontend/src/lib/locales/{es,en}.js`

**Interfaces:**
- Consumes: `DrillNegocio`'s `insight` prop (Task 11).
- Produces: both screens pass `insight={item.insight}` and stop passing `porque`, `grafico`, `involucrados`, `supuestos`, `confidence`, `metrics`.

`WorkRow` and `Fila` gain a deadline chip rendered **only** when `insight.deadline?.urgency` is `"overdue"` or `"today"` — a chip on every card would be noise, and `later` is not news. Reuse the existing "Hecho" pill styling with the `rojo`/`oro` accent.

`INVOLUCRADO_NAV` (`Prioridades.jsx:301-304`) and `INVOLVED_NAV` (`InsightsMobile.jsx:21-24`) are unchanged — they key on `kind`, which `insight.record` preserves.

Add locale keys `prioridades.due_today` ("Vence hoy" / "Due today") and `prioridades.overdue` ("Vencido" / "Overdue") to both files.

- [ ] **Step 1: Update `drillProps` and `rowOf`** to pass the insight through and drop the six removed props.

- [ ] **Step 2: Add the deadline chip** to `WorkRow` and `Fila`.

- [ ] **Step 3: Verify it builds**

Run: `cd frontend && npx vite build`
Expected: success.

- [ ] **Step 4: Run the app and check one card of each family**

```bash
cd backend && POLPILOT_DEMO_TODAY=2026-07-07 python -m uvicorn main:app --port 8000 &
cd frontend && npm run dev
```

Open `http://localhost:5173/prioridades` and confirm, for one debtor card, one stockout card, one warehouse card and one whole-business card (`caida_interanual`):
- Pattern reads as an observation; hypothesis reads as an interpretation.
- Both confidence badges render, and at least one card shows them **disagreeing**.
- Primary evidence is expanded, supporting is collapsed.
- "¿Cómo se calculó?" opens on every metric.
- Clicking a client record lands on `cuentas` with the row highlighted; a product record lands on `inventario`.
- No card shows a duplicated fact.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/sections/Prioridades.jsx frontend/src/mobile/InsightsMobile.jsx frontend/src/lib/locales/
git commit -m "Wire Prioridades and InsightsMobile to the insight contract"
```

---

### Task 13: delete the shim, add the completeness guard and the docs

**Files:**
- Modify: `backend/core/priorities.py` (delete `_legacy_drill` and its three call sites)
- Modify: `backend/i18n.py` (the i18n-direction TODO)
- Modify: `PRODUCT.md`
- Modify: `backend/tests/test_api.py:163-169`
- Test: `backend/tests/test_priorities.py`

**Interfaces:**
- Produces: cards with **no** `drill` key anywhere.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_priorities.py`:

```python
def test_no_card_anywhere_still_emits_a_drill():
    """The cutover's completeness check: `drill` is gone from the contract,
    not merely unused by the current frontend."""
    inbox = priorities.inbox("es", None)
    for c in inbox["act"] + inbox["watch"]:
        assert "drill" not in c, f"{c['id']} still emits the legacy drill"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_priorities.py -k no_card_anywhere -v`
Expected: FAIL — the shim is still populating `drill`.

- [ ] **Step 3: Delete the shim**

**First migrate the consumers Task 8 discovered.** `core/grafo.py` reads the drill
directly in two shallow places — both trivially expressible against the insight:

- `grafo.py:538` — `(card.get("drill") or {}).get("involucrados")`, used only for
  each row's `nombre` to seed graph nodes. Becomes: iterate
  `insight["evidence"]`, then each item's `records`, taking `r["name"]`.
- `grafo.py:629` — `(origen.get("drill") or {}).get("porque")`, exposed as the
  node's `porque` list. Becomes the same projection `_legacy_drill` performs:
  `pattern.label`, then `hypothesis.label` if present, then the `label` of each
  `primary` evidence item.

Then update the four test files that read a card's `drill` directly, bypassing
`priorities.py` entirely — which is why the shims never covered them:
`tests/test_p27.py`, `tests/test_p25.py`, `tests/test_oportunidades_ids.py` (all
reading `oportunidades_neg.cards()["drill"]`) and `tests/test_p39.py` (reading a
piso proposal's `drill`). Point each at `["insight"]`.

Only once those six files are migrated, remove **all four** shims — the two in
`priorities.py`, `_project_drill` in `oportunidades_neg.py`, and `_project_drill`
in `piso.py`:
- `_legacy_drill` and its three call sites: the `"drill":` entry in `_item`, the `out["drill"] =` line in `_combine`, and the `item["drill"] =` line in `_derive`.
- `_insight_from_legacy_drill` **and the `drill=` keyword on `_item`**. Every builder passes `insight=` by now (Tasks 5–9), so nothing calls it.
- `_project_drill` in `oportunidades_neg.py` (added in Task 8 to keep `grafo.py` and three tests working) and `_project_drill` in `piso.py` (added in Task 9 for `test_p39.py`), along with the `"drill"` key each populates.

Verify with `grep -rn "drill" backend/core/ backend/angela.py backend/tests/` — the only surviving hits should be in comments or unrelated identifiers. **`_blank_drill` also goes**: Task 4 kept it because unmigrated builders still called it; by now nothing does.

The `drill`-free guard test below checks the payload, not the keyword; the grep is what confirms the keyword is gone.

- [ ] **Step 4: Fix the stale badge assertion**

`backend/tests/test_api.py:168` asserts `body["badge"] == len(body["act"])`, which contradicts `badge_of` (`priorities.py:256-259` — executed cards are excluded) and breaks whenever a fixture card has `action_taken`. Replace with:

```python
    assert body["badge"] == sum(1 for c in body["act"] if not c.get("action_taken"))
```

- [ ] **Step 5: Add the i18n-direction TODO**

At the top of `backend/i18n.py`, after the module docstring:

```python
# TODO(i18n direction) — UI-facing copy should move to the frontend.
#
# The mainstream shape for a web app is: the server ships keys + params, the
# client renders with Intl (plurals, dates, currency are locale rules the
# browser already implements, and this module hand-rolls them in Python).
#
# What blocks a straight migration: Ángela and external MCP clients consume
# FINISHED sentences and will never run frontend/src/lib/locales/. The
# narrative templates here are also coupled to the calculations they explain
# (see core.opn.qi_q1b), so they are authored next to the code that computes
# their numbers, not as UI chrome.
#
# The agreed split (docs/superpowers/specs/2026-09-01-structured-insight-
# contract-design.md, §"i18n direction"):
#   - narrative sentences (pattern, hypothesis, method labels) stay here;
#   - raw numbers ship as typed data and are formatted client-side;
#   - section headings, badge labels and button copy belong in the frontend
#     locales — move them as they are touched.
```

- [ ] **Step 6: Document the product principle**

Add to `PRODUCT.md` a short section, "Insight structure", stating: every analysis the product presents follows Pattern → Hypothesis → Evidence → Assumptions → Risk → Recommended action → Owner → Deadline; confidence is always reported on two axes; every metric explains how it was calculated; every claim can be expanded to the records behind it. Note that the lifecycle (New / Confirmed / Acted upon / Resolved / Proven wrong / Monitoring) and the action workflow are the planned next step, and point at the spec's "Deferred" section.

- [ ] **Step 7: Run the whole suite**

Run: `cd backend && python -m pytest -q`
Expected: only the two known `test_p27.py` failures from Global Constraints.

- [ ] **Step 8: Verify the frontend still builds and runs**

Run: `cd frontend && npx vite build`, then re-check one card end-to-end as in Task 12 Step 4.

- [ ] **Step 9: Commit**

```bash
git add backend/ PRODUCT.md
git commit -m "Delete the legacy drill shim; guard the cutover; document the contract"
git checkout -- data-demo/
```

---

## Self-review

**Spec coverage.** Every section maps to a task: contract → Tasks 1, 4; confidence split → Task 2; owner/deadline → Tasks 3, 4, 8; merge fix → Task 4; the ~25 builders → Tasks 5–9; `_slim` → Task 10; frontend → Tasks 11–12; i18n TODO, `PRODUCT.md`, the `drill`-free guard and the stale `test_api.py` assertion → Task 13.

**Known gaps, deliberate.** Tasks 6, 7, 8, 9 and 11 specify content through per-card tables and an explicit render order rather than full code for all twenty-five builders. The transformation is shown in full in Task 5 and is mechanical thereafter; the tables carry the real decisions (evidence ids, which cards get records, which get deadlines, where a hypothesis is honestly `None`). An implementer needs Task 5 in front of them for those tasks.

**Type consistency.** `insight.build/pattern/hypothesis/metric/records/series/record/assumption/caveat/risk/recommendation/deadline` are used with the same names and signatures in Tasks 4–10. `confidence.split_for` (not `level_for`) is used in Task 4. `insight_owner.suggest` returns `{suggested, role, reason}`, consumed as `owner.suggested` in Tasks 10 and 11. Evidence ids established in Task 5 are reused in Task 8 — that reuse is what makes the merge de-duplicate.
