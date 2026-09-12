# Odoo sales, stock, receipts, and forecast — design

Status: draft pending review
Date: 2026-08-27

This is a **new** spec. It extends
[`2026-08-27-odoo-ingestion-pipeline-design.md`](2026-08-27-odoo-ingestion-pipeline-design.md)
(contacts, products, vendors, purchase orders). It does not replace that
document, except for one explicit amendment to purchase-order status mapping
(see “Purchase-order status” below).

## Overview

PolPilot already computes rotación, margen real, quiebre, excedente,
inmovilizado, fantasmas, stock negativo, sin PVP, vencimientos, and
depósito discrepancies — against the synthetic `data-demo/` tenant. None of
those engines have a live Odoo feed for **demand**. Product ingest today
sends on-hand qty and list price only; it deliberately omits cost.

This spec makes Odoo the live source for:

1. Confirmed sales lines → `venta` (unlocks the existing sales engines).
2. Richer product qty/cost → on hand, free, incoming, outgoing, inmovilizado,
   ghosts, negatives, unpriced.
3. `stock.quant` + lots → `deposito` (locations, expiry, aging, counted vs
   system).
4. Done incoming pickings → `recepciones` (remito ↔ OC, without double-counting
   stock).
5. A new deterministic demand forecast per product, with optional confidence
   intervals.

Test/dev Odoo is the sibling **odoo-demo** repo (Odoo 17 + Postgres 15). That
seed must grow from a 10-SKU catalog with five undated orders into a small
electronics SME: ~60 SKUs, two warehouses, 24 months of confirmed history.

## Goals

- Confirmed Odoo sale-order lines ingest into PolPilot `venta` via the same
  two-tier sync already shipped (linked `source_id` auto-upserts; brand-new
  rows go to Staging).
- Re-sync is idempotent. Cancelled-or-unconfirmed lines disappear from
  Odoo-sourced `venta` rows; CSV rows are never deleted this way.
- Product ingest sends cost and free/incoming/outgoing qty. Odoo owns cost
  (`standard_price` → `costo_iva`) on linked products.
- Depósito and recepciones ingest follow the same two-tier + provenance
  pattern.
- `core/forecast.py` produces a 3-month seasonal monthly forecast per
  product. Ángela only narrates those numbers.
- odoo-demo can rebuild a dump that actually runs warehouse workflows
  (confirmed orders, validated receipts), not XML `state=` shortcuts.

## Non-goals

- Push PolPilot → Odoo.
- Scheduler / webhooks. Ingest stays a dueño-triggered button.
- Customer invoices / payments → `cuenta_corriente` (AR aging). Separate
  sub-project.
- Vendor bills → `compras`. Separate.
- Holt-Winters, Prophet, or any extra Python dependency for forecast.
- A sales-order **document** table (header + items). Consumers want flat
  `venta` lines.
- PolPilot as a WMS: no per-warehouse first-class stock dimension, no
  picking UI. Two Odoo warehouses roll up on the product; detail lives in
  `deposito`.
- Changing CSV venta/depósito/recepciones behaviour, except that Odoo
  ventas auto-confirm the amount validator (CSV still asks the dueño).
- Inventing a 21% IVA markup when mapping `standard_price` / `price_unit`.
  Untaxed Odoo amounts land in `costo_iva` / `precio`. Documented
  approximation.

## Decisions (locked)

| Topic | Choice |
|---|---|
| What is a sale | Confirmed `sale.order` lines only (`state` in `sale` / `done`). Draft, sent, cancel: preview tab only, never `venta`. |
| Qty on a sale line | Ordered (`product_uom_qty`), not delivered. |
| `source_id` for ventas | `sale.order.line` id, not the order id. |
| Cost on linked products | `standard_price` writes `costo_iva` on every sync. Hand-entered products untouched. |
| Amount validator | Auto-confirm when an Odoo `venta` batch is integrated. CSV unchanged. |
| Forecast | Seasonal monthly, 3-month horizon, residual ±1.96σ interval. |
| Stock model | Product rollup (`stock`, `free_qty`, `incoming_qty`, `outgoing_qty`); locations/lots in `deposito`. |
| Seed catalog | Keep electronics/office names; ~60 SKUs; two warehouses; 24 months ending 2026-07. |
| Seed history | Generator writes XML; `post_init_hook` confirms orders and validates pickings via ORM; then `dump-seed.sh`. |
| Receipts vs stock | Ingesting `recepciones` does **not** increment `product.stock`. Odoo already moved it. |
| Partial PO + receipt | PolPilot PO becomes `recibida` if Odoo is `done` **or** any line `qty_received > 0`. |
| New identifiers | English (`free_qty`, `counted_qty`, `in_date`, `po_number`, `source_id`, …). Existing Spanish keys stay (`fecha`, `cantidad`, `costo_iva`, `inmovilizado`, …). |
| Architecture | Extend the shipped ingest pipeline. No live-query shadow. No `sale_orders` SQL table. |

## Architecture

Same data flow as the first ingestion spec:

```
ConectorOdoo.pull_X()  →  split by (source, source_id)
        │
   ┌────┴────┐
   linked     unlinked
   auto-upsert    staging.crear_batch_odoo(tipo, rows)
   (Odoo-owned)   coerce → observe → dueño integrar()
```

New `pull_*` / `ingest_*` pairs:

| Connector method | Staging `tipo` | Target |
|---|---|---|
| `pull_ordenes_venta()` | `venta` | `esquema` apartado `venta` |
| `pull_productos()` (extended) | `producto` | `store` article dict |
| `pull_deposito()` | `deposito` | `esquema` apartado `deposito` |
| `pull_recepciones()` | `recepciones` | `esquema` apartado `recepciones` |

`crear_apartado` only **appends**. Re-sync of blob-backed tipos needs:

- `esquema.upsert_filas(tipo, filas)` — match `(source, source_id)`, insert or
  replace Odoo-owned keys on that row.
- `esquema.delete_odoo_missing(tipo, pulled_source_ids)` — delete rows with
  `source == "odoo"` whose `source_id` is not in the current pull. Never
  touches rows without `source`.

Shared resolver: Odoo `product.product` (variant) → `product.template` id →
PolPilot article with `source == "odoo"` and that `source_id` → `codigo`.
If unresolved: skip auto-upsert; Staging observation `producto_inexistente`
(already exists for CSV ventas/depósito). Operational copy: ingest products
first. Not a hard lock.

Malformed rows: reuse `_REQUERIDO_ODOO`. Skip and count
`omitidos_malformados`. Never abort the whole ingest.

Audit: one summary record per `ingest_*` call (counts + ids), matching
órdenes de compra.

### Product matching and variant ids

`ConectorOdoo.pull_productos` today stores `product.template` id as
`source_id`. Sale lines and stock moves reference `product.product`. Every
pull that has a variant must also read `product_tmpl_id` and match on the
template id. No second provenance key.

## 1. Sales → `venta`

**Pull filter:** `sale.order` with `state in ('sale', 'done')`. Include
locked confirmed orders (`state` remains `sale`). Preview (Conectores tab)
may still list draft/sent/cancel; ingest ignores them.

**Grain:** one `venta` row per `sale.order.line`.

| Field | Source | Notes |
|---|---|---|
| `fecha` | `date_order` date part | Existing Spanish key |
| `producto` | product display name | |
| `codigo` | resolved PolPilot article | Required for engines; unresolved → Staging |
| `cantidad` | `product_uom_qty` | Zero qty is a valid row |
| `precio` | `price_unit` | Untaxed; `evolucion._monto_fila` = qty × price |
| `source` | `"odoo"` | |
| `source_id` | `str(line.id)` | |
| `source_status` | order `state` | |

No `cliente` on the line: current `_coerce_venta` and the engines do not
use it.

**Required field:** `producto` (non-empty). `_REQUERIDO_ODOO["venta"] =
"producto"`.

**Coercer** `coerce_venta_odoo`: only the keys above. Do not emit dueño-only
or default-only fields.

**integrar():** upsert into apartado `venta`, then call
`ventas.confirmar_validacion(confirmar=True)` so `montos_confirmados()`
is true. CSV `venta` integrar still calls `iniciar_validacion()`.

**Re-sync:** update linked lines; delete Odoo-sourced rows whose line is
not in the confirmed pull (order moved to cancel, or no longer returned).

**i18n:** `core.esquema.venta` and `activa_venta_*` already exist. Add
Conectores / ingest copy only.

## 2. Product ingest extensions

Not a new tipo. Extends the shipped product pipeline.

`Articulo` (`core/models.py`) **drops unknown keys**. New optional fields
must be added there and to `store.upsert_desde_conector`'s copied-field
list, or they vanish.

| PolPilot | Odoo `product.template` |
|---|---|
| `stock` | `qty_available` (company-wide on hand, both warehouses) |
| `free_qty` | `free_qty` |
| `incoming_qty` | `incoming_qty` |
| `outgoing_qty` | `outgoing_qty` |
| `costo_iva` | `standard_price` |
| `pvp` | `list_price` (unchanged) |
| `estado` | `active` → `activo` / `anulado` |

`inmovilizado` stays `_recalcular_inmovilizado`: `stock × costo_iva`. Not
`free_qty`.

**Pull domain:** templates that are `active` **or** have on-hand qty ≠ 0.
Today’s `active = True` only would make fantasmas impossible.

**Coercer change:** `coerce_producto_odoo` **emits `costo_iva`**, reversing
the PR #8 omit, plus `free_qty`, `incoming_qty`, `outgoing_qty`, and
`estado`. Still omits `venta_x_peso`, scale limits — Odoo does not own
those.

Existing classifiers then just work: fantasma (anulado + stock), negativo,
sin_pvp.

## 3. Depósito → `deposito`

PolPilot is not a WMS. We ingest `stock.quant` on **internal** locations
only.

| Field | Source |
|---|---|
| `codigo` / `producto` | variant → template → article |
| `ubicacion` | location `complete_name` (`WH/Stock`, `WH2/Stock`) |
| `lote` | `stock.lot.name` or `""` |
| `vencimiento` | lot `expiration_date` (ISO date) or `""` |
| `cantidad` | `quant.quantity` (system on-hand at that location) |
| `counted_qty` | `inventory_quantity` when a count is in progress; **omit** the key otherwise |
| `in_date` | `quant.in_date` |
| `source` / `source_id` | `"odoo"` / `str(quant.id)` |

Skip qty-0 quants. Re-sync deletes Odoo-sourced rows not in the pull.

**Required:** `producto`.

**Aging:** new `deposito.aging()` — buckets from `in_date` vs `fechas.hoy()`:
0–90, 91–180, 181–365, 365+ days. Each bucket: units and inmovilizado
(qty × product `costo_iva`). Products with no `in_date` are omitted from
aging, not invented.

**Discrepancies:** today’s `deposito.discrepancias()` compares
`sum(cantidad)` vs `product.stock`. If both are Odoo on-hand, that is a
tautology. Change: when **any** depósito row for a product has
`counted_qty`, that product’s discrepancy is summed `counted_qty` vs
summed `cantidad` (counted vs system at location). When no `counted_qty`
is present on any row for that product, keep the CSV/WMS behaviour
(`sum(cantidad)` vs `product.stock`).

Existing `ubicacion_de`, `vencimientos`, `vencidos` need no new engine.

odoo-demo must depend on `product_expiry`.

## 4. Goods receipts → `recepciones`

**Pull:** `stock.picking` with `picking_type_code = 'incoming'` and
`state = 'done'`. Lines: `stock.move` with qty done.

**Do not** add to `product.stock`. Photo-remito remains the only path that
mutates stock because there PolPilot is the system of record.

| Field | Source |
|---|---|
| `fecha` | picking `date_done` |
| `codigo` / `producto` | variant → template → article |
| `proveedor` | picking partner name |
| `cantidad` | move qty done |
| `deposito` | destination location `complete_name` |
| `origen` | picking `name` (remito number, e.g. `WH/IN/00012`) |
| `po_number` | PO `name` via `move.purchase_line_id` or picking `origin` |
| `source` / `source_id` / `source_status` | `"odoo"` / move id / picking state |

**Required:** `producto`.

**Remito ↔ OC:** new helper in `core/` (English name, e.g.
`match_receipt_to_purchase_order(po_number)`). For a receipt with
`po_number`, compare received qty per `codigo` to that ingested PO’s
lines. Returns matches / short / extra. Same idea as
`comprobantes.cruzar_remito`, but **after** the fact. Do not persist a
second copy of the diff; compute on read. Do not suggest a vendor claim
from this path in v1 (photo-remito already does that).

### Purchase-order status (amendment)

The first spec mapped `purchase → aprobada` always. **This spec amends
that:**

| Odoo | PolPilot `status` |
|---|---|
| `draft`, `sent` | `borrador` |
| `cancel` | `cancelada` |
| `done` | `recibida` |
| `purchase` and all lines `qty_received == 0` | `aprobada` |
| `purchase` and any line `qty_received > 0` | `recibida` |

`source_status` still stores Odoo’s raw state (`purchase` vs `done`).
Receipt ingest updates the linked PO immediately with the same rule so
the UI is right before the next PO pull. PO auto-upsert must not
downgrade `recibida` back to `aprobada` while `qty_received > 0`.

PO ingest must read `qty_received` on `purchase.order.line` (add to the
existing line read).

## 5. Forecast

New module `backend/core/forecast.py`. No LLM. No extra dependencies.

**Input:** `esquema.filas("venta")` with a resolvable `codigo`. Horizon:
next **3 calendar months** from `fechas.hoy()`.

**Per product, per future month *m*:**

1. Aggregate monthly units and pesos (`cantidad × precio`, same as
   `evolucion._monto_fila`).
2. Point forecast: `same_month_last_year × trend`, with
   `trend = (sum of last 3 months) / (sum of the same 3 months a year ago)`.
   If last year’s month is 0, use trailing 3-month average. Never divide
   by zero. Never invent seasonality from an empty year.
3. Interval: residual = actual − that formula over the last 12 months that
   have a prior year. `low/high = max(0, point ± 1.96 × stdev(residuals))`.
   If fewer than 6 usable residuals, **omit** `qty_low` / `qty_high` and
   set `interval_ok = false`.
4. `confidence`: `"low"` if no interval; else `"high"` if residual CV <
   0.15, `"medium"` if CV < 0.35, else `"low"`.
5. Products with no sales in the last 12 months: `{available: false,
   reason: ...}`. Do not emit a flat fake series.

**Output keys (English):** `product_code`, `description`, `months` (list of
`period`, `qty`, `amount`, `qty_low`, `qty_high`, `interval_ok`),
`confidence`, `trend`.

**Quiebre:** existing quiebre keeps trailing run-rate. Forecast is a
**second** signal: if month-1 forecast qty > `stock + incoming_qty -
outgoing_qty`, flag the product. No purchase-qty optimizer in this spec.

**API:** `GET /api/forecast`, same feature gate as ventas/evolución.
Ángela tool: read-only, passes through the dict. Evolución (or ventas
panorama) shows a compact block. No new nav section.

**Tests:** frozen `fechas.hoy`; a fixture with a May spike must forecast
next May above a trend-only baseline; a 3-month-old SKU returns
`available: false` or `confidence: "low"` without an interval.

## 6. odoo-demo seed

Sibling repo. Do not hand-write 24 months of orders.

**Generator** `addons/test_seed_data/generate.py`: Python stdlib,
deterministic RNG, English identifiers. Writes XML for catalog (products,
second warehouse, lots, static extra partners if needed).

**Catalog:** ~60 products, electronics/office names. Mix of goods and a
few services. `standard_price` + `list_price`. One `list_price = 0`. One
`active = False` with leftover qty. One negative quant. Subset with lots
+ expiry (one expired, one inside 7 days). Two warehouses (`WH`, `WH2`).
Open inventory counts on a few quants (`inventory_quantity` ≠ `quantity`).

**Depends:** add `product_expiry`; ensure `sale_stock` and `purchase_stock`
are installed (usually via `sale_management` + `purchase` + `stock`).

**History:** module `post_init_hook` creates confirmed sale orders and
**validates** incoming pickings through the ORM so computed qty and stock
moves exist. XML `state = sale` is not enough. Frozen window: 24 months
ending **2026-07**. Mix of fast / medium / slow / seasonal movers (at
least one SKU with a May spike). About **2–4k confirmed SO lines**, not a
full 60×24 cartesian. Receipts thinner: include one complete vs PO and
one short. Keep a handful of draft/sent/cancel SOs and draft POs for
preview-tab filters (not ingested as `venta`).

**Rebuild:**

```text
python addons/test_seed_data/generate.py
./scripts/reset.sh && ./scripts/init.sh
./scripts/dump-seed.sh
```

Commit generated XML + `seed/odoo_seed.dump`. Document in odoo-demo
README.

PolPilot pytest **never** boots Docker. Connector tests mock `execute_kw`.
Optional live smoke against localhost:8069 is marked and skipped by
default.

## API

Alongside existing ingest routes:

- `POST /api/conectores/odoo/ingest-ventas`
- `POST /api/conectores/odoo/ingest-deposito`
- `POST /api/conectores/odoo/ingest-recepciones`

Each admin-only, same return shape as today’s ingest:
`{actualizados, nuevos_para_revisar, omitidos_malformados, batch_id}`.

Preview (sync) routes matching `pull_*`, same pattern as
`/api/conectores/odoo/sync-ordenes-compra`.

Product ingest/preview endpoints stay; their payloads grow the new fields.

`GET /api/forecast` — not admin-only; same feature as evolución/ventas.

## Frontend

`Conectores.jsx`: three tabs — Ventas, Recepciones, Depósito — cloning
`OdooTabCompras` (preview + ingest + result line). “Ver en Staging” calls
`onNavigate("saneamiento", "revision")`, never `<a href>`.

Productos tab: show cost / free / in / out when present; no fourth new
tab for those fields.

Evolución: compact forecast block behind the same “numbers available”
gate as ventas (auto-true after Odoo venta integrate).

Locales: `frontend/src/lib/locales/es.js` + `en.js`, and `backend/i18n.py`
for API-facing strings. Product UI copy may stay Spanish; all new code
identifiers are English.

## Error handling

- Odoo down / bad credentials: existing `ValueError` → HTTP 400. All reads
  for that entity finish before writes.
- Missing required field: skip row, increment `omitidos_malformados`.
- Unresolved product: Staging observation, not auto-upsert.
- Forecast with empty ventas: `{available: false}` at the collection
  level, not a 500.

## Testing (polpilot-app)

Mirror `test_odoo_ingest.py` / `test_conectores_odoo.py` / `test_staging.py`:

- Preview pull shape per new method.
- First ingest → Staging batch; re-sync linked → auto-upsert, no batch.
- Cancelled SO line dropped from `venta` on re-sync; CSV row untouched.
- `coerce_producto_odoo` writes `costo_iva`; `venta_x_peso` still omitted.
- Inactive + stock → fantasma after ingest.
- Odoo venta integrar sets `montos_confirmados()`.
- PO `purchase` + `qty_received > 0` → `recibida`; qty_received all 0 →
  `aprobada`.
- Receipt ingest does not change `product.stock`.
- `counted_qty` present → discrepancy; absent → legacy comparison.
- Aging buckets with frozen today.
- Forecast May-spike and young-SKU cases.

odoo-demo: generator test that two runs with the same seed write the same
XML (if the generator is unit-testable without Odoo).

## Implementation waves

One spec, sequential delivery so each wave is testable:

1. odoo-demo generator + hook + dump.
2. Product pull/upsert: cost, `free_qty` / `incoming_qty` / `outgoing_qty`,
   ghosts; `Articulo` + coercer.
3. Ventas pull, ingest, blob upsert/delete, Staging, tab, auto-confirm.
4. `core/forecast.py`, `GET /api/forecast`, Ángela tool, Evolución block.
5. Depósito ingest, aging, counted discrepancies, tab.
6. Recepciones ingest, PO status amendment, remito↔OC helper, tab.

Wave 1 can proceed in odoo-demo in parallel with wave 2 in polpilot-app.

## Out of scope (next specs)

- AR: `account.move` + payments → `cuenta_corriente`.
- Vendor bills → `compras`.
- Forecast-driven purchase quantity suggestions.
- Push to Odoo.
