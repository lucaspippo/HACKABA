# Priorities bridge: knowledge as citable evidence

Date: 2026-09-10
Status: approved design — ready for implementation planning

## Why

The first spec in this pair
(`docs/superpowers/specs/2026-09-10-knowledge-lifecycle-design.md`) fixes
how a `conocimiento` piece ages, gets edited, and gets archived. This spec
is the other half of "closing the loop": today a knowledge piece can
*produce* a finding (`pattern_feedback.learn()`), and a builder's
*calculation* can already consult one (`conocimiento.aplicables()`/`para()`
adjusting a threshold or suppressing an alert) — but the resulting
`insight` never *declares* that a taught rule participated. The product's
own pitch ("cada hallazgo tiene trazabilidad: qué regla del dueño
participó") is only half true until this closes. Full background and
code citations: `PolPilot/Memoria de Angela - Investigacion y Propuesta.md`
in the vault, §3.

## Dependency on the sibling spec

This spec's freshness signal (see below) reads `core/conocimiento.py`'s
`decay_score()`/`needs_review()`, both introduced in the knowledge-lifecycle
spec's PR 4. **PR 7 below cannot start before that PR lands** (or, at
minimum, before those two functions exist — the rest of PR 4's migration
isn't required, just the pure decay function). PRs 8-10 have no such
dependency beyond PR 7.

## Goals

- A knowledge piece consulted while computing a finding becomes citable,
  weighted evidence inside that finding's `insight`, not flat metadata
  beside the card.
- `confidence.split_for`'s `data` axis reflects that evidence (more
  sources = more confidence, same as chart points/records already do).
- `confidence.split_for`'s `sources_stale` signal — hardcoded `False`
  today — becomes real when the cited knowledge is due for review.
- A knowledge piece becomes a first-class node in `core/grafo.py`, with a
  real edge to the entity it's about, instead of a flat id list — usable
  as a seed in `caminos()`, same as a floor note already is.

## Non-goals

- No change to `insight.py`'s existing `metric()`/`records()`/`series()`
  constructors or their callers — `knowledge()` is additive.
- No change to how a finding gets *promoted into* a knowledge piece
  (`pattern_feedback.learn()`) — that direction already works.
- No LLM-judged relevance scoring of which knowledge applies — reuses
  `aplicables()`/`para()`'s existing deterministic filtering exactly as
  builders already call it today.
- Global pieces (`ambito="global"`) getting a graph anchor is flagged as
  an open question for the implementation plan to resolve, not decided
  here (see PR 10).

## Language rule

Same as the sibling spec: new identifiers in English
(`insight.knowledge()`, not a Spanish name), existing Spanish identifiers
in `insight.py`/`confidence.py`/`grafo.py` untouched. The new evidence
`kind` value is `"knowledge"` (English), consistent with the existing
kinds (`"metric"`, `"records"`, `"series"`) already being English.

## Design decisions (confirmed with the user)

1. **Knowledge evidence counts toward `data` confidence, never toward
   `hypothesis`.** It is evidence *for* the finding, never a declared
   assumption that should lower confidence — restated from the original
   research because it's the crux of this spec.
2. **No new confidence lever.** A knowledge-evidence item counts toward
   `confidence.py`'s existing `_insight_record_count()` tally — same
   `DATA_MEDIUM_RECORDS`/`DATA_HIGH_POINTS` thresholds, no new constant to
   tune. Matches the module's own stated philosophy ("deliberately coarse
   ... no per-card-type logic").
3. **`sources_stale` is `True` when ANY cited knowledge evidence is
   currently `needs_review()`** (not "all") — errs toward surfacing the
   caveat, consistent with `hypothesis_level`'s existing "more declared
   leaps → lower confidence, never higher" rule.
4. **Graph node-ification is in scope here, as its own PR (PR 10)** —
   confirmed with the user despite being the most invasive piece (touches
   `grafo.py`'s node model and `caminos()`), rather than deferring to a
   third spec.

## `insight.knowledge()` (`core/insight.py`, PR 7)

```python
def knowledge(piece: dict, *, weight: str = "supporting") -> dict:
    """A conocimiento piece cited as evidence. `piece` is the dict as
    returned by conocimiento.listar()/aplicables()/para() — this function
    reads it, never mutates it. `weight` follows the same contract as
    metric()/records()/series() (must be "primary" or "supporting").
    Freshness is derived here (not stored) via conocimiento.freshness(),
    so the evidence item always reflects the CURRENT decay state, not
    the state at insight-build time."""
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

Three fields (`origen`, `freshness`, `needs_review`) are new relative to
the existing `_evidence()` shape — additive, so `metric()`/`records()`/
`series()` callers and every existing reader of an evidence item are
unaffected (they simply won't see these keys on non-knowledge evidence).

## `confidence.py` changes (PR 7)

```python
def _insight_record_count(insight: dict) -> int:
    # existing records() count, PLUS one per knowledge() evidence item —
    # a taught rule is as much "a real thing behind this" as a database row
    return sum(len(ev.get("records") or []) for ev in insight.get("evidence") or []) \
        + sum(1 for ev in insight.get("evidence") or [] if ev.get("kind") == "knowledge")

def _sources_stale(insight: dict) -> bool:
    return any(ev.get("needs_review") for ev in insight.get("evidence") or []
               if ev.get("kind") == "knowledge")
```

`split_for()`'s `data.signals.sources_stale` becomes `_sources_stale(insight)`
instead of the literal `False`. `missing` (also hardcoded `[]` today)
is **not** addressed by this spec — it's a different signal (absent data
sources, not stale knowledge) and out of scope here.

## Builder wiring (PRs 8-9)

Every call site that already does `conocimiento.aplicables(...)` or
`conocimiento.para(...)` gets a one-line addition: wrap whatever pieces
came back with `insight.knowledge(p)` and append to that card's
`evidence` list, at `weight="supporting"` unless the builder's author
judges the rule load-bearing enough for `"primary"` (matches how
`metric()`'s weight is already a per-call judgment, not automatic).

Known call sites today (grep-verified 2026-09-10):

| File | Call | PR |
|---|---|---|
| `oportunidades_neg.py:307` | `aplicables(nodo="inventario", efecto="contexto_para_angela")` | 8 |
| `oportunidades_neg.py:389` | `para(prov, nodo="proveedores")` | 8 |
| `oportunidades_neg.py:679` | `para(prod, nodo="inventario", efecto="genera_alerta", tipo="regla")` | 8 |
| `oportunidades_neg.py:937` | `aplicables(nodo="clientes", efecto="contexto_para_angela")` | 8 |
| `conciliacion.py:72` | `aplicables(nodo="deposito", efecto="suprime_alerta")` | 9 |
| `deposito.py:203` | `aplicables(nodo="deposito", efecto="suprime_alerta")` | 9 |
| `pagos.py:121` | `aplicables(nodo="caja")` | 9 |
| `cuentas.py:110` | `para(c.get("nombre"), nodo="clientes", tipo="regla")` | 9 |

PR 9 additionally confirms, per site, whether that call's result actually
feeds an `insight.py`-shaped card today (some of these may back an alert
or a caja computation that doesn't build a full insight yet) — where it
doesn't, this spec doesn't force one into existence; it's noted and left
for whoever eventually gives that surface a proper insight.

## `grafo.py` — knowledge as a real node (PR 10)

Replaces `grafo.py`'s current
`nodos[objetivo].setdefault("conocimiento", []).append(p.get("id"))`
(the flat metadata list) with the same treatment `core/notas.py` entries
already get:

```python
nid = f"conocimiento:{p['id']}"
nodos[nid] = _nodo(nid, "conocimiento", p["texto"][:80], seccion=p["nodo"],
                    texto=p.get("texto"), texto_en=p.get("texto_en"),
                    riesgo="atencion" if conocimiento.needs_review(p) else None)
add_arista(nid, objetivo, "aplica_a")
```

This also carries forward PR 1's pause-bug fix (already applied in the
sibling spec) — the call here must pass `incluir_pausadas=False` and,
since PR 5 of the sibling spec exists by the time this lands,
`incluir_archivadas=False` too, so a paused/archived rule doesn't show as
a live node on the map.

Open question for the implementation plan (not decided in this spec, per
the non-goals above): a piece with `ambito="global"` has no single
`objetivo` entity to attach to — whether it gets a synthetic "global
knowledge" anchor node, is grouped under its `nodo` (business-map domain)
instead of an entity, or is simply left off the graph as today, is left
to be decided when PR 10 is actually implemented, informed by whatever
the panel/UI work from the sibling spec's PR 1-3 already settled about
displaying global pieces.

## Testing

- PR 7: table-driven tests for `insight.knowledge()`'s shape (weight
  validation, freshness/needs_review passthrough) and
  `confidence.split_for()`'s new record-count and `sources_stale`
  behavior, against hand-built insight dicts — no DB, no tenant fixture
  needed, matching how `test_confidence.py` already tests `split_for()`.
- PR 8-9: extend each touched builder's existing test file with a case
  asserting the resulting card's `insight.evidence` includes a
  `kind="knowledge"` item when a matching piece exists for the fixture
  tenant, and doesn't when none does.
- PR 10: extend `grafo.py`'s existing test coverage for the new node
  type/edge, including a `caminos()` case where a knowledge piece is the
  seed, and a case confirming a paused/archived piece produces no node.

## Rollout sequence

Continues the stack from the sibling spec's PR 6:

7. `insight.knowledge()` + `confidence.py` wiring (depends on sibling PR 4)
8. Wire the four clearest `oportunidades_neg.py` call sites
9. Wire the remaining four call sites (`conciliacion.py`, `deposito.py`,
   `pagos.py`, `cuentas.py`), confirming each actually feeds an insight
10. `grafo.py`: knowledge pieces become real graph nodes
