# Prioridades: generalize verifiable evidence across all card types

Date: 2026-09-01
Status: approved, pending implementation plan

## Context

A prior iteration (commit `6c4225a`) redesigned `DrillNegocio` (the drill-down
panel in `frontend/src/components/CardNegocio.jsx`, used on `/prioridades`) to
fix buried action buttons and information hierarchy, and made evidence
clickable for one card type (`cobrar_morosos`): its `involucrados` (debtors)
carry a real `id` and deep-link into `CuentasCorrientes.jsx` via the existing
`data-nav-id`/`resaltarPorId` mechanism.

This spec generalizes that pattern — verifiable, drillable evidence (chart,
data sources, hypothesis, confidence, real-record links) — across every card
type in the Prioridades inbox: the 9 `oportunidades_neg.py` opportunity cards
and the ~11 alert-only types composed in `priorities.py` (`dep_vencidos`,
`dep_porvencer`, `dep_discrep`, `venc_riesgo`, `costo_viejo`, `caja_inusual`,
`caida_interanual`, `pago_vencido`, `pago_semana`, `cheques`, `moroso_atraso`,
`quiebre`).

Per the deterministic-core invariant (repo `CLAUDE.md`), every number and
every "involved record" a card cites must come from `backend/core/`
calculation over real data — never invented or reformatted by an LLM.

## Survey findings that shaped scope

- 8 of the 9 opportunity cards already have `porque`/`grafico`/`involucrados`/
  `supuestos`/`fuentes`, but only `cobrar_morosos`'s `involucrados` carry a
  real `id` — the other 8 have `nombre`/`monto`/`detalle` only, no
  deep-link target.
- ~11 alert-only types return `_blank_drill()` or a near-empty drill (no
  chart, no involucrados, sometimes no `porque`) — the biggest
  hierarchy/verifiability gap today.
- Real per-entity destination anchors (the `data-nav-id` pattern) exist today
  only in `CuentasCorrientes.jsx` (`cliente-${id}`). `Inventario.jsx` renders
  per-product rows keyed by `codigo` but has no anchors yet — straightforward
  to add.
- `deposito.py` (`vencidos()`, `vencimientos()`, `discrepancias()`) and
  `store.py` (`panorama()["alertas"]["costo_viejo"]`) all expose a stable
  product `codigo` on every row already — so every product-linkable alert can
  deep-link into `Inventario.jsx` with no new backend id plumbing.
- `pagos.py` (payments/checks) has no universal stable id (hand-entered rows
  have neither `id` nor `source_id`); `caja.py`'s `historial` entries have no
  id (only `fecha`, not guaranteed unique); `evolucion.py` has no
  per-category/product breakdown at all. None of these have a per-row list UI
  in their destination screens today either (`Finanzas.jsx`, `Caja.jsx`,
  `Evolucion.jsx` are aggregate-only).

Building three new per-row list UIs (Finanzas, Caja, Evolución) to support
real-record links there is a materially larger, separate project. **Decision
(user-approved): out of scope for this pass.** Those card types keep today's
page-level navigation only.

## Data contract additions

Two additive fields on the existing drill/involucrado shape. Existing keys
(`drill`, `porque`, `grafico`, `involucrados`, `supuestos`, `fuentes`, `tono`,
`tipo`, `navegar`, ...) are untouched — this is the established schema and
the coding-standard rule ("all new code, identifiers, comments in English")
applies to what's being added, not a rename of existing Spanish keys.

```
drill.confidence: {
  "level": "high" | "medium" | "low",
  "reason": <i18n string, e.g. "Based on 12 months of history">
}

involucrado.kind: "client" | "product"   # new, alongside existing id/nombre/monto/detalle
```

### Confidence computation (shared, generic — not per-card-type)

Computed **once**, centrally, in `priorities.py`'s `_item()` (the single
function every card — opportunity, pattern, alert, piso — already passes
through before reaching the frontend). No per-builder work needed.

Signals used, both already present on every drill for free:
- number of data points in `drill.grafico` (proxy for sample size behind the
  finding)
- number of entries in `drill.supuestos` (how many assumptions the finding
  leans on)

Rule of thumb: `points >= 6 and assumptions == 0` → `high`;
`points >= 3 or assumptions <= 1` → `medium`; otherwise → `low`. A card with
no chart and multiple assumptions reads as low confidence, which is honest —
that's exactly the case for some of today's thinnest alerts pre-backfill.

New function: `backend/core/confidence.py` — `level_for(drill: dict) -> dict`.
Small and independently testable in isolation from the ~20 card builders.

## Backend backfill, by card type

**8 opportunity cards gaining real involucrado ids** (in
`oportunidades_neg.py`): `despertar_dormido`, `ventana_compra`,
`cliente_frio`, `estrella_caida`, `quiebre_inminente`, `concentracion`,
`margen_bajo`. (`sobrecompra` has no involucrados today and none are added —
it's a single-item finding, nothing to list.)

- `ventana_compra`, `quiebre_inminente`, `margen_bajo`: items already come
  from `ctx["arts"]`, which carries `codigo` — just thread it through into
  each involucrado dict as `id`, `kind="product"`.
- `cliente_frio`: items come from `ctx["clientes"]`, which carries `id` —
  same treatment, `kind="client"`.
- `estrella_caida`, `concentracion`: currently reference products/clients by
  name only. Add a small `name -> id` lookup built once in `_ctx()`
  (`product_id_by_name`, `client_id_by_name`) so these two builders can
  resolve ids without re-scanning.
- `despertar_dormido`: sourced from `analisis.rotacion()`'s `dormidos_top`,
  which is keyed by product description, not `codigo`. Verify during
  implementation whether `codigo` is already available on those rows; if
  not, thread it through from `analisis.py` (one extra field on an existing
  dict, not a new computation).

**Product-linkable alerts gaining full drill data** (in `priorities.py`):
`dep_vencidos`, `dep_porvencer`, `dep_discrep`, `venc_riesgo`, `costo_viejo`.
Each replaces its current `_blank_drill()`/thin drill with:
- `porque`: narrated from the same underlying numbers already used for the
  summary text (no new calculation, just carried into the drill).
- `grafico`: a bar chart of the top items by the relevant magnitude (days
  overdue, amount at risk, immobilized cost) — contract P21, same renderer
  as every other chart.
- `involucrados`: sourced from `deposito.vencidos()` / `deposito.vencimientos()`
  / `deposito.discrepancias()` / `store.panorama()`'s `costo_viejo` group,
  each row already carrying `codigo` → `id`, `kind="product"`.
- `supuestos`: same assumption-declaration pattern as existing cards.

**Whole-business alerts gaining partial drill data** (no per-item
involucrados — that's an honest reflection of what the data supports, not a
gap):
- `caida_interanual`: `grafico` built from the existing `serie`/`interanual`
  monthly comparison already computed in `evolucion.panorama()`.
- `caja_inusual`: `grafico` built from `historial` (today's total vs. the
  trailing average that triggered the alert).

**Finanzas alerts gaining narrative + chart, involucrados stay text-only**
(no stable id exists, and no per-row UI to land on — matches today's
page-nav behavior): `pago_vencido`, `pago_semana`, `cheques`. `porque` and
`grafico` backfilled from `pagos.pagos_vencidos()` /
`pagos.cheques_en_cartera()`; involucrado rows show `proveedor` + `numero` as
plain text (no `id`/`kind`), which `InvolucradoRow` already renders as
non-clickable when those are absent.

**Raw alert forms gaining one real involucrado**: `moroso_atraso`, `quiebre`
— these mostly disappear by merging into `cobrar_morosos`/`quiebre_inminente`
(`MERGE_INTO`), but surface standalone when the owner has dismissed the
merged-into card. Add the one relevant client/product as an involucrado with
a real id, for that standalone case.

## Frontend changes

- `Inventario.jsx`: add `data-nav-id={`producto-${p.codigo}`}` to the two
  per-product row renderers (`FocoView` ~L231, `PestanaCustom` ~L270).
- `Prioridades.jsx`: generalize the current single-purpose
  `onVerInvolucrado` (hardcoded to `item.navegar === "cuentas"`) to branch on
  `iv.kind`: `"client"` → navigate to `cuentas` + `cliente-${id}`;
  `"product"` → navigate to `inventario` + `producto-${id}`.
- `CardNegocio.jsx`:
  - `DrillNegocio` renders a small `ConfidenceBadge` near the "Por qué"
    heading, reading `drill.confidence` (translated label per `level`,
    tooltip/caption from `reason`).
  - `InvolucradoRow` becomes clickable whenever `iv.id && iv.kind` are both
    present (today's check is implicitly cuentas-only via the caller); falls
    back to plain text otherwise (unchanged for Finanzas-sourced rows).
- New i18n keys (`en.js`/`es.js`) for the three confidence level labels and
  the new `porque`/`supuestos` copy introduced by the backfilled alerts. UI
  copy stays Spanish-first per the repo's coding standard (English is for
  code/identifiers/comments, not end-user text); new identifiers (functions,
  fields, components) are English.

## Testing

- `backend/core/confidence.py`: unit tests for the three thresholds and edge
  cases (no chart, no assumptions; many assumptions; large chart).
  `pytest tests/test_confidence.py`.
- Existing `oportunidades_neg`/`priorities` tests extended to assert
  `id`/`kind` presence on the involucrados that should now carry them, and
  `drill.confidence` presence on every returned card.
  `cd backend && python -m pytest` (restore `data-demo/` afterward per repo
  convention).
- Frontend: Chrome/Playwright manual verification pass — for at least one
  card of each backfilled type, confirm chart renders, confidence badge
  shows a sensible level, and (where applicable) clicking an involucrado
  navigates + highlights the real Inventario/Cuentas row.

## Explicitly out of scope

- Finanzas (payments/checks), Caja (movimientos/historial), and Evolución
  (per-category/product breakdown) do not get new per-row list UI or new
  backend ids in this pass — they keep today's page-level-only navigation.
  Revisit as a separate, later-scoped project if the owner wants true
  record-level links there too.
