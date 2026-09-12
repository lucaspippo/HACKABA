# Prioridades: a structured insight contract

Date: 2026-09-01
Status: approved, pending implementation plan

## Context

Every Prioridades card explains itself through `drill.porque` — a flat
`list[str]` of prose sentences rendered one `<p>` each. A real payload from
`/api/prioridades` today:

```json
[
  "3 clientes en mora suman $85.700.000 vencidos.",
  "Despensa Doña Elsa lleva 66 días sin pagar cuando su promedio histórico es 31 — el desvío es la señal.",
  "3 clientes en mora por $85.700.000.",
  "Despensa Doña Elsa lleva 66 días; su promedio era 31."
]
```

Two defects are visible in those four lines:

1. **Every fact appears twice.** `_combine` (`core/priorities.py:203-227`)
   concatenates `porque` from merged twins and de-duplicates on *exact string
   equality*. `"3 clientes en mora suman $85.700.000 vencidos."` and
   `"3 clientes en mora por $85.700.000."` are different strings for the same
   fact, so both survive the merge of `morosos` into `cobrar_morosos`.
2. **The reasoning has no shape.** Observation, interpretation, supporting
   number and caveat are all the same type — a string in a list — so nothing
   downstream can tell them apart, order them, or act on them.

The consequences are not only cosmetic:

- The UI cannot highlight which data point actually drives the conclusion,
  cannot let the owner expand a claim to the records behind it, and cannot
  explain how any metric was computed.
- Ángela's `listar_prioridades` tool (`backend/angela.py:1950-1966`) returns a
  *slimmed* card with no reasoning at all. The agent therefore has no evidence
  to reason over — the richest part of the deterministic core never reaches it.
- Confidence is a single coarse level (`core/confidence.py`) that mixes a data
  signal (chart points) with a hypothesis signal (assumption count) into one
  number, so a finding backed by twelve months of data but resting on three
  assumptions is indistinguishable from its opposite.

This spec replaces `drill` with a structured `insight` object built on a fixed
shape: **Pattern → Hypothesis → Evidence → Assumptions → Risk → Recommended
action → Owner → Deadline**, with confidence split along the data/hypothesis
seam and explicit "alternative explanations" and "what would change this
conclusion" fields.

Per the deterministic-core invariant (repo `CLAUDE.md`), every value in the
insight is computed in `backend/core/` from real data. The LLM narrates and
cites it; it never produces or reformats a number.

## Prior art in this repo

Three earlier specs are **implemented**, and this one builds on them rather
than revisiting their decisions:

- `2026-08-27-prioridades-design.md` — the inbox itself: merge policy,
  `act`/`watch` bands, ranking, `GET /api/prioridades` as the single payload
  for desktop, mobile, the sidebar badge and Ángela.
- `2026-09-01-prioridades-evidence-generalization-design.md` —
  `drill.confidence` (`core/confidence.py`) and real record ids on
  `involucrados` (`id` + `kind`, deep-linking into `CuentasCorrientes.jsx` and
  `Inventario.jsx`).
- `2026-09-01-angela-proposal-pattern-design.md` — `action_taken` derived from
  the `purchase_orders` table, `components/AngelaProposal.jsx`, executed cards
  sinking in rank and dropping from the badge. Its central decision — *state of
  record is derived from the domain table, never mirrored into a parallel
  ledger* — is the reason the action workflow is deferred here (see
  "Deferred" below).

## Decisions taken

Four forks were resolved before design:

1. **Scope: contract and UI now; action workflow and lifecycle later.** The
   stateful layer (status, assignment, tracking) needs the first stored
   per-priority state in the product and reverses a deliberate architectural
   decision. It gets its own spec, on top of this shape.
2. **Migration: hard cutover across all ~25 builders.** `drill.porque` is
   deleted from the contract and the UI. Rejected: an additive `insight`
   alongside `porque` with incremental migration — it would keep two card
   qualities on one page indefinitely, and the prose path may never actually
   die.
3. **Owner and Deadline are computed suggestions.** Both have a deterministic
   basis today (module ownership; supplier lead times, ageing curves, lot
   expiry dates), so both ship now, labelled as suggestions. The follow-on
   spec adds override and tracking without reshaping the fields.
4. **i18n: data plus a server-rendered label.** Every evidence item carries
   both machine-readable fields (value, unit, baseline, record refs) and a
   rendered sentence in the caller's language. See "i18n direction" below for
   why this is the right call here and what it costs.

### Rejected shapes

- **`insight` beside `drill`.** Assumptions would live in `drill.supuestos`
  while the structure calls them `insight.assumptions`, and evidence would
  split across two sibling objects joined by id — shipping the same conceptual
  duplication this spec exists to remove, permanently.
- **Chart as an evidence item.** Purer evidence-first model (a chart attached
  to the claim it supports, multiple charts per card), but every card today
  carries exactly one chart. It buys generality nothing needs and relocates the
  P21 renderer. YAGNI.

## The contract

`_item()` (`core/priorities.py:146-173`) keeps every field it has today except
one: `drill` is replaced by `insight`. The card envelope — `id`, `tono`,
`chip`, `titulo`, `resumen`, `monto`, `monto_label`, `cifra_texto`, `fuentes`,
`origen`, `navegar`, `accion_chat`, `propuesta`, `piso`, `macro`,
`naturaleza`, `tipo`, `modulos`, `reportes`, `band`, `action_taken` — is
untouched.

New identifiers are English per the repo coding standard. Replacing `drill`
wholesale means renaming its Spanish sub-keys (`porque`, `grafico`,
`involucrados`, `supuestos`), which the standard permits: this work is
substantially inside those files, so it is a migration, not a blanket rewrite
as a side effect.

### `insight.pattern`

The observation, stated as fact with no interpretation. This field does not
exist today; it is what makes cards comparable, because every card now opens
with *what was observed* before *what it means*.

```
{ "label": "3 clientes concentran el 71% de la mora",
  "since": "2026-04-01" | null,          # when the pattern becomes visible
  "scope": { "kind": "clients", "count": 3 } }
```

### `insight.hypothesis`

The interpretive leap, explicitly separated from the pattern.

```
{ "label": "Despensa Doña Elsa cambió su comportamiento de pago, no su capacidad" }
```

`null` when the card has no defensible hypothesis. The UI says so rather than
inventing one — honest for the thinner alerts, and preferable to prose that
implies an interpretation nobody computed.

### `insight.evidence[]`

The load-bearing part.

```
{ "id": "days_overdue",                  # stable; drives merge union and UI keys
  "kind": "metric" | "records" | "series",
  "label": "66 días sin pagar, contra 31 de promedio histórico",
  "value": 66,
  "unit": "days",
  "baseline": { "value": 31, "label": "promedio histórico del cliente" } | null,
  "deviation": { "pct": 113, "direction": "up" } | null,
  "weight": "primary" | "supporting",
  "method": { "key": "core.method.dias_mora",
              "label": "Días entre la última cobranza registrada y hoy…" },
  "records": [ { "kind": "client", "id": "c-142", "name": "…",
                 "amount": 0, "detail": "…" } ],
  "chart": <P21 chart> | null }
```

- **`weight`** implements "highlight the data points that materially affect the
  conclusion": the UI renders `primary` expanded and `supporting` collapsed.
  It defaults to `supporting`, so a builder must opt in to claiming primacy.
- **`method`** implements "how was this calculated?" as a real field on every
  metric rather than a tooltip someone remembers to write.
- **`records`** is today's `involucrados`, moved to hang off the claim it
  supports. The `kind`/`id` deep-link mechanism (`INVOLUCRADO_NAV` in
  `sections/Prioridades.jsx:301-304`) carries over unchanged.
- **`deviation`** is derived by `insight.metric()` from `value` and `baseline`;
  no builder hand-writes a percentage. It is `null` when there is no baseline,
  or when the baseline is zero (no meaningful percentage exists).

### `insight.assumptions[]`

Today's `supuestos`, upgraded from bare strings so the consequence of being
wrong is stated:

```
{ "label": "Asumo que no hubo pagos en efectivo sin registrar",
  "if_wrong": "La mora real sería menor" }
```

### `insight.alternatives[]` and `insight.falsifiers[]`

`[{ "label": … }]` each. Two lists, not one, because they answer different
questions: *what else could explain this* versus *what evidence would kill it*.

### `insight.risk`

```
{ "level": "high" | "medium" | "low", "label": "…", "exposure": 85700000 | null }
```

`exposure` is the money at stake if nothing is done, which is not always
`monto`: for `dep_porvencer`, `monto` is total lot value while exposure is the
fraction that will actually expire.

### `insight.recommendation`

Consolidates what is scattered across `titulo` / `chip` / `propuesta` /
`navegar` / `accion_chat` today:

```
{ "label": "…", "detail": "…", "proposal": {…} | null,
  "navigate": "cuentas" | null, "chat": "…" | null }
```

The card-level fields stay for the list row and for `estiloAccion` /
`FiltrosAccion` (`lib/prioridadAccion.js`); `recommendation` is the drill's
single source.

### `insight.owner` and `insight.deadline`

```
"owner":    { "suggested": "Marina", "role": "cobranzas",
              "reason": "cuentas corrientes" } | null
"deadline": { "date": "2026-07-14", "basis": "lead time 7d",
              "urgency": "overdue" | "today" | "this_week" | "later" } | null
```

### `insight.confidence`

The split, replacing today's single level:

```
{ "data":       { "level": …, "reason": …,
                  "signals": { "chart_points": 12, "record_count": 3,
                               "sources_stale": false, "missing": [] } },
  "hypothesis": { "level": …, "reason": …,
                  "signals": { "assumptions": 3, "alternatives": 1 } } }
```

Two badges that can disagree ("datos: alta · hipótesis: baja") are the single
most informative thing on the card, and are impossible to express today.

## How this fixes the duplication

With `evidence[]` keyed by a stable `id`, `_combine` unions by `id` instead of
concatenating prose. `morosos` and `cobrar_morosos` both emit
`evidence.id = "overdue_total"`; the merged card carries it once. Duplication
stops being something to police in prose and becomes structurally impossible.

Merge rules:
- `evidence` — union by `id`; on collision `primary` wins over `supporting`,
  and the canonical card's copy is kept.
- `assumptions` / `alternatives` / `falsifiers` — union by `label`.
- `pattern` / `hypothesis` — the canonical card's, never concatenated.
- `origen` union, `tono` escalation to `rojo`: unchanged from today.

## Backend production

### Authored versus derived

The split keeps ~25 builders from each growing sixty lines.

**Authored per builder** (only the builder knows the domain): `pattern`,
`hypothesis`, `evidence[]`, `assumptions[]`, `alternatives[]`, `falsifiers[]`,
`risk.label`, `risk.exposure`, `deadline.date` and `deadline.basis`. Only
`_card_quiebre_inminente` knows the deadline is supplier lead time; only
`_alerts_cuentas` knows the baseline for days-overdue is the client's own
payment average.

**Derived by the constructor** (`core/insight.py`, at build time):
`evidence[].deviation` from `value` and `baseline`.

**Derived centrally** in `_compose` (after every builder has run, because these
read the finished insight): `confidence` (both axes), `owner`,
`deadline.urgency` from `deadline.date` against the dataset's today, and
`risk.level` from `risk.exposure` and the card's band.

### `core/insight.py` (new)

The constructor and its vocabulary:

```python
def build(*, pattern, hypothesis=None, evidence=(), assumptions=(),
          alternatives=(), falsifiers=(), risk=None, recommendation=None,
          deadline=None) -> dict
def metric(id, *, label, value, unit, baseline=None, method,
           weight="supporting", records=(), chart=None) -> dict
def records(id, *, label, rows, method, weight="supporting") -> dict
def series(id, *, label, chart, method, weight="supporting") -> dict
```

Builders call `insight.build(...)` instead of writing a dict literal.

### `core/confidence.py` (rewritten in place)

`level_for(insight, lang)` returns the split object. The seam already exists in
the current 37 lines — chart points are a data signal, assumption count is a
hypothesis signal — they are simply mixed today.

- **data**: chart points (as today) plus `record_count`, source staleness, and
  any declared `missing` inputs.
- **hypothesis**: `len(assumptions)` and `len(alternatives)`. More declared
  alternatives lowers confidence, which is the honest direction.

Thresholds stay coarse, and the docstring keeps its current posture: a reading
aid, not a statistical model.

### `core/insight_owner.py` (new)

`suggest(modulos)` reverses the module → feature mapping to the team member
whose role owns that domain. `perfiles` exposes `features_efectivas(username)`
(forward only), so this either reuses an existing reverse helper or adds one —
to be verified during implementation.

Returns `None` for a tenant with no team, a single user, or an ambiguous match.
A real DB-backed tenant may have nobody assigned, and the UI must render that
as "sin dueño sugerido" rather than a guess.

### `core/priorities.py`

- `_blank_drill()` → `_blank_insight()`; `_item(drill=…)` → `_item(insight=…)`.
- `_combine` implements the merge rules above.
- `_compose` attaches `confidence`, `owner`, `risk.level` and
  `deadline.urgency` in the loop that attaches confidence today (`:321-322`).

### Caching

`insight` is fully deterministic, so it is built **inside** `_compose` and
therefore inside `analisis_cache` — like `confidence` today. `action_taken`
stays outside the cache, unchanged; the comment at `priorities.py:274-282`
explaining the freeze bug still applies and stays.

### The ~25 builders

14 inline alert builders in `priorities.py`, 10 finding builders in
`oportunidades_neg.py`, 2 in `patrones.py`, plus `piso.propuestas()`.

Each builder's existing `porque` prose is the source material: the sentence
that states an observation becomes `pattern`, the sentence that interprets it
becomes `hypothesis`, and the numbers currently interpolated into those strings
(`n=`, `monto=`, `dias=`, `prom=`) become evidence metrics carrying their raw
values. Most i18n keys survive as `label` templates; new keys are needed for
`method`, `alternatives` and `falsifiers`, which have no prose today.

Two consequences worth stating rather than discovering:

- **`dep_discrep` has no `porque` at all today** (`priorities.py:670`, blank
  drill). It needs a genuinely new `pattern` and `evidence`, not a translation.
- **Thin alerts will read as low confidence on both axes** — no chart, no
  records, no declared alternatives. That is accurate, and now visible where it
  was not. It may prompt a follow-up to enrich them; it is not a regression.

## i18n direction

Evidence carries raw typed data (`value`, `unit`, `baseline`, `deviation`,
record refs) formatted client-side with `Intl`, plus a server-rendered `label`
and `method.label` from `backend/i18n.py`.

The mainstream default for a web app is frontend translation — the server ships
keys and params, the client renders. That is not what this repo does, for two
reasons that are real rather than historical: Ángela and external MCP clients
consume finished sentences and will never run the frontend locale files, and
the narrative templates are coupled to the calculations they explain
(`"Vendés ~{u} {unidad} por mes de {producto}…"` is authored next to the code
that computes `u`).

The cost, stated plainly: plural and grammar edge cases stay in hand-rolled
Python. This spec contains that cost to narrative sentences instead of letting
it spread to every label.

**A `TODO` block is added at the top of `backend/i18n.py`** recording the
agreed direction — UI-facing labels should migrate to
`frontend/src/lib/locales/` with the server shipping keys and params — and
naming the blocker, so a future session does not relitigate it from scratch.

## Frontend

### `components/CardNegocio.jsx`

`DrillNegocio` renders the insight in its declared order, replacing today's
sequence (why → fuentes → chart → metrics → involucrados → proposal →
supuestos → origins → feedback):

1. **Pattern** — the observation, plainly, at the top.
2. **Hypothesis** with the two confidence badges beside it, labelled *datos*
   and *hipótesis*.
3. **Evidence** — `primary` expanded, `supporting` collapsed behind a count.
   Each metric shows its value formatted client-side, its baseline and
   deviation, and a disclosure for `method.label` ("¿Cómo se calculó?").
   Record lists keep `InvolucradoRow`'s click-through to `cuentas` /
   `inventario`.
4. **Risk**, then **Recommendation** — which owns `AngelaProposal`. That
   component is unchanged: its `{proposal, onApprove, working, actionTaken,
   onDismiss}` contract already takes what `recommendation.proposal` provides.
5. **Assumptions**, then **Alternatives** and **Falsifiers** in a collapsed
   "¿Qué cambiaría esta conclusión?" section.
6. Owner and deadline as a footer line; sources and `FindingFeedback` stay.

### `sections/Prioridades.jsx`

`drillProps()` (`:306-348`) is rewritten to pass the insight through.
`WorkRow` gains a deadline chip when `deadline.urgency` is `overdue` or
`today`. Keyboard navigation, overlay behaviour, master-detail layout and
`_cachePrio` are untouched.

### `mobile/InsightsMobile.jsx`

`rowOf()` (`:26-53`) maps the same shape. Both screens share `CardNegocio`, so
the drill work lands once.

Visual design of the evidence disclosure is handled during implementation with
the `impeccable` skill; this spec fixes structure and information hierarchy,
not styling.

## Ángela and MCP

`listar_prioridades` returning full insights for twenty cards would be a large
payload on every "¿qué hago ahora?". So:

- **`listar_prioridades` stays slim**, gaining only `deadline.urgency` and
  `risk.level` so Ángela can speak about urgency without inventing it.
- **New tool `explicar_prioridad(id)`** returns one card's complete insight.

This matches how the owner actually talks — "¿qué hago ahora?" then "¿por qué
esa?" — and it is what makes better agent analysis possible: evidence arrives
as typed data with baselines and methods rather than prose to re-parse.

The new tool needs an entry in `TOOL_FEATURE` or the same special case as
`listar_prioridades` (`angela.py:124-134`); adding it to `READ_ONLY_TOOLS`
(`mcp_server.py:44-53`) exposes it over MCP with no further work.

The prompt rule is unchanged: Ángela cites, never re-ranks, never computes.

## Testing

Backend (`cd backend && python -m pytest`; restore seeds afterward with
`git checkout -- data-demo/`):

- `core/insight.py` — `deviation` derived correctly from value and baseline,
  including the zero-baseline case; `weight` defaults to `supporting`.
- `core/confidence.py` — the axes move independently: a card with a rich chart
  and three assumptions reads `data: high, hypothesis: low`. This assertion is
  impossible to write before the split.
- `core/insight_owner.py` — `None` for no team, single-user tenant, and
  ambiguous match.
- `priorities._combine` — the regression guard for the duplication above:
  merging `morosos` into `cobrar_morosos` yields exactly one evidence item per
  `id`, and `primary` survives over `supporting`.
- `test_priorities_drill.py` — its 8 per-alert-type tests change from
  "`drill.porque` is non-empty" to "carries a `pattern` and at least one
  evidence item", a stronger claim.
- A contract test asserting **no card anywhere still emits `drill`** — the
  cutover's completeness check across all ~25 builders.
- `test_api.py:163-169` asserts `badge == len(act)`, which already contradicts
  `badge_of`'s semantics (`priorities.py:256-259`) and breaks the day a fixture
  card has `action_taken`. Pre-existing and unrelated, but fixed here rather
  than left as a known-wrong assertion in a file this work touches.

Frontend has no test runner configured, so verification is `npx vite build`
plus a Chrome pass over one card of each type.

## Deferred: action workflow and insight lifecycle

Recorded here so a future session inherits the intent rather than re-deriving
it. **Not implemented by this spec.**

**Action workflow** — recommendations become trackable actions with:
status (`Suggested`, `Accepted`, `In progress`, `Completed`, `Dismissed`),
owner (assigned, overriding `insight.owner.suggested`), due date (overriding
`insight.deadline.date`), expected impact, and actual outcome measured after
the fact. Expired and time-sensitive recommendations surface prominently.

**Insight lifecycle** — each insight tracks whether it is `New`, `Confirmed`,
`Acted upon`, `Resolved`, `Proven wrong`, or `Still being monitored`, so the
system can learn which patterns are actually useful. `Proven wrong` is the
valuable one: it is the feedback signal that tells the deterministic core which
hypotheses to stop generating.

Two things the implementing session must know:

1. It requires the **first stored per-priority state** in the product. Today
   the only priority state is derived — `action_taken` from `purchase_orders`,
   feedback from `pattern_feedback` (which means "the owner's opinion of this
   finding", not "this was executed").
2. It **reverses the decision** taken in
   `2026-09-01-angela-proposal-pattern-design.md` §"Decisions taken" (1):
   state of record is derived from the domain table, never mirrored, so nothing
   can drift. A stored lifecycle is a deliberate exception to that rule and
   must justify itself — most likely by scoping stored state to facts no domain
   table can answer (was this *seen*, *assigned*, *judged wrong*) while leaving
   "was this executed" derived where it already is.

`insight.owner` and `insight.deadline` are shaped so assignment and tracking
layer on top without reshaping them.

## Out of scope

- Any stored state (see Deferred).
- Renaming card-envelope fields (`titulo`, `resumen`, `tono`, `origen`,
  `propuesta`) — only `drill` is replaced.
- Changes to ranking, merge *policy*, `recuperable`, or `autonomia`.
- The i18n migration itself — the TODO records the direction only.
- A frontend test harness.

## Files touched

| File | Change |
|---|---|
| `backend/core/insight.py` | new — constructor and evidence vocabulary |
| `backend/core/confidence.py` | rewritten — split data/hypothesis confidence |
| `backend/core/insight_owner.py` | new — owner suggestion from modules |
| `backend/core/priorities.py` | `_item`/`_blank_insight`/`_combine`/`_compose`; 14 alert builders |
| `backend/core/oportunidades_neg.py` | 10 finding builders emit `insight` |
| `backend/core/patrones.py` | 2 builders emit `insight` |
| `backend/core/piso.py` | `propuestas()` emits `insight` |
| `backend/i18n.py` | new `method`/`alternatives`/`falsifiers` keys; i18n-direction TODO |
| `backend/angela.py` | slim card gains urgency/risk; new `explicar_prioridad` tool |
| `backend/mcp_server.py` | expose `explicar_prioridad` |
| `frontend/src/components/CardNegocio.jsx` | `DrillNegocio` restructured around the insight |
| `frontend/src/sections/Prioridades.jsx` | `drillProps`; deadline chip on `WorkRow` |
| `frontend/src/mobile/InsightsMobile.jsx` | `rowOf` maps the new shape |
| `frontend/src/lib/locales/{es,en}.js` | section headings, confidence labels, disclosure copy |
| `backend/tests/` | the cases above |
| `PRODUCT.md` | insight structure and lifecycle as a product principle |
