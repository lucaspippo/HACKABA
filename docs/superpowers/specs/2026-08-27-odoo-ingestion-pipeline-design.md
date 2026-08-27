# Odoo ingestion pipeline — design

Status: approved for implementation planning
Date: 2026-08-27

## Overview

The Odoo connector (`core/conectores.ConectorOdoo`) currently only pulls data
for preview: contacts, products+stock, vendors, and purchase orders show up
in the Conectores UI but never touch PolPilot's real data (`core/cuentas.py`,
`core/store.py`, `core/proveedores.py`, `core/ordenes.py`). This spec covers
the first half of making that connection bidirectional: **ingestion**
(Odoo → PolPilot). Pushing PolPilot-originated changes back out to Odoo is
explicitly out of scope here — a separate spec once this direction is proven.

## Goals

- Pulled Odoo data for all four entities (contacts, products, vendors,
  purchase orders) can be folded into PolPilot's real tables, not just
  previewed.
- Re-running a sync is idempotent: a record already ingested from Odoo gets
  updated in place, never duplicated.
- Every ingested record carries its provenance (`source`, `source_id`) so
  it's always traceable back to where it came from.
- Genuinely new records still go through dueño review before they're
  created — ingestion never silently creates a new customer/vendor/product
  PolPilot didn't know about. Updates to records *already* linked to Odoo
  apply automatically, since Odoo already owns that data.

## Non-goals

- Push direction (PolPilot → Odoo). Not built here.
- Real-time/webhook sync. Ingestion stays a manual, dueño-triggered action
  (same UX pattern as today's "Traer X" buttons), no scheduler.
- Any change to `core/ordenes.py`'s Ángela-prepares/dueño-approves flow for
  PolPilot-originated orders — ingested Odoo purchase orders are additional
  rows in the same table (see "Purchase orders" below), not a replacement
  for that workflow.

## Architecture

Extend the existing Staging Area (`core/staging.py`) rather than build a
parallel ingestion system. It already has the review/resolve/audit/backup
machinery this needs (observation cards, dueño-resolved policies, versioned
backups) — built for CSV imports, but the batch shape doesn't care where
rows came from.

Two alternatives considered and rejected:

- **Direct upsert on click, no review step.** Simpler, but lets a stale or
  wrong Odoo pull silently overwrite dueño-edited data (e.g. a manually
  adjusted credit limit) with no chance to catch it — breaks the "Ángela
  proposes, dueño approves" rule the Staging Area exists to enforce.
- **Permanent "Odoo shadow" tables, never merged into real data.** Avoids
  merge conflicts entirely, but doesn't ingest anything — it's a second
  preview mode. Existing analyses (`reponer`, `cobranza`, etc.) still
  wouldn't see the data.

### Two-tier sync

Triggering ingestion for an entity (e.g. "Ingestar productos") does two
things, in order:

1. **Auto-upsert already-linked records.** For every pulled Odoo row whose
   `(source="odoo", source_id=<odoo id>)` already matches an existing
   PolPilot record, update that record's fields in place. No review card —
   Odoo already owns this data, and the dueño already accepted the link the
   first time it was created.
2. **Stage genuinely new records.** Any pulled row with no existing
   `source_id` match creates (or joins) a Staging batch of `tipo="cliente"`
   / `"proveedor"` / `"producto"` / `"orden_compra"`, running through the
   *existing* dedup/observation flow (e.g. "duplicado" if the name matches
   an unlinked, hand-entered record) before the dueño integrates it. This is
   what catches the case where a customer already exists in PolPilot without
   a `source_id` (hand-entered) and a new Odoo row would otherwise create a
   second row for the same business.

## Schema changes

Two storage shapes exist today, so the mechanism to add `source`/`source_id`
differs:

**JSON-blob-backed data — no migration needed:**
- **Products** (`inventory_working`, one JSON blob per tenant). Add `sku`,
  `source`, `source_id` to the article dict shape. `Articulo` is a strict
  dataclass (`core/models.py`) that silently drops unknown dict keys on
  load — add these three as optional fields there too (default `None`) so
  they survive the round-trip.
- **Vendors** (`proveedores`, a JSON-blob "apartado" via `core/esquema.py`).
  Extend `_CAMPOS` in `core/proveedores.py` to include `cuit`, `source`,
  `source_id`.

**Fixed-column SQL tables — migration required:**
- **Customer accounts** (`customer_accounts`). Currently
  `id, name, balance, credit_limit, payment_term_days, days_overdue,
  average_payment_days` — no contact fields at all. New migration adds
  `vat, city, phone, email, source, source_id` (all nullable; existing rows
  get `source = NULL`, meaning "not from a connector").
- **Purchase orders** (`purchase_orders`). New migration adds `source,
  source_id, source_status` (nullable). `source_status` holds Odoo's raw
  state (draft/sent/purchase/done/cancel) *alongside* the `status` column,
  which stores it mapped into PolPilot's own vocabulary
  (borrador/aprobada/recibida/cancelada) — so mapping never loses the
  original value.

All new columns are named in English, matching the existing convention in
both of these tables.

`source`/`source_id` together are the idempotency key: `WHERE source =
'odoo' AND source_id = :id` finds the linked record on re-sync, if any.
No separate mapping table.

## Per-entity mapping

| Odoo entity | PolPilot target | Match key | New fields on target |
|---|---|---|---|
| `res.partner` (customer_rank>0) | `core/cuentas.py` / `customer_accounts` | `source_id` = Odoo partner id | `vat, city, phone, email, source, source_id` |
| `product.template` | `core/store.py` / `inventory_working` article dict | `source_id` = Odoo product id | `sku, source, source_id` |
| `res.partner` (supplier_rank>0) | `core/proveedores.py` apartado | `source_id` = Odoo partner id | `cuit, source, source_id` |
| `purchase.order` | `core/ordenes.py` / `purchase_orders` | `source_id` = Odoo PO id | `source, source_id, source_status` |

Purchase order state mapping (per earlier decision): `draft/sent → borrador`,
`purchase → aprobada`, `done → recibida`, `cancel → cancelada`. On
auto-upsert of an already-linked PO, if `source_status` changed, `status` is
re-derived from the new Odoo state via this same mapping.

## Data flow (per entity, per sync click)

```
ConectorOdoo.pull_X()  →  rows (already shaped by the connector, Spanish keys)
        │
        ▼
split by source_id lookup against the target table/blob
        │
   ┌────┴────┐
   ▼         ▼
linked     unlinked
   │         │
   ▼         ▼
auto-    staging.crear_batch_odoo(tipo, rows)
upsert       │
   │         ▼
   │     existing coerce → analyze → dueño resolves → integrar()
   │         │
   └────┬────┘
        ▼
   target table/blob updated, audit logged
```

`staging.crear_batch_odoo(tipo, filas)` is a new entry point alongside
`crear_batch()` (CSV): it skips CSV parsing and Nivel-1 normalization
(rows are already structured, not raw text) and goes straight into
`_coerce_y_analizar`-equivalent logic for the new `tipo` values
(`cliente`, `proveedor`, `orden_compra` — `producto` already exists).
New coercers are mostly pass-through, since `ConectorOdoo`'s pull methods
already produce PolPilot-shaped field names; they add `source="odoo"` and
`source_id` to each row.

`integrar()` gains a branch per new tipo, routing to the entity's real
write path instead of the generic `esquema.crear_apartado` used for
`deposito`/`logistica`:
- `producto` → existing `store.guardar` path (unchanged).
- `cliente` → `customer_accounts_repo.upsert_account`.
- `proveedor` → `core/proveedores.py`'s existing blob write, extended for
  the new fields.
- `orden_compra` → `purchase_orders_repo`, with a new create-or-update path
  (currently `create()` always inserts; needs a `source`+`source_id`-aware
  upsert) and the state mapping above.

## API surface

New endpoints, one per entity, alongside the existing preview-only
`sync-*` routes (which stay unchanged):

- `POST /api/conectores/odoo/ingest-contactos`
- `POST /api/conectores/odoo/ingest-productos`
- `POST /api/conectores/odoo/ingest-proveedores`
- `POST /api/conectores/odoo/ingest-ordenes-compra`

Each admin-only (`require_admin`, same as today's routes), calls
`pull_X()` then the split/auto-upsert/stage flow above, and returns
`{"actualizados": N, "batch_id": "..." | null}` — `batch_id` is set only
when there were unlinked rows staged for review, so the frontend can offer
"Ver en Staging" when relevant.

## Frontend UX

Each Odoo tab (Contactos/Productos/Proveedores/Compras) gets a second
button next to "Traer X": "Ingestar a PolPilot". Clicking it calls the new
`ingest-*` endpoint and shows a short result line ("12 actualizados, 3
nuevos para revisar" with a link to `/cargar` → Staging when `batch_id` is
present). The existing "Traer X" preview button and its list are untouched.

## Error handling

- Odoo unreachable or credentials rejected mid-sync → same `ValueError` →
  HTTP 400 pattern the connector already uses. All reads happen before any
  writes for that entity's sync, so a failure never leaves a partial
  auto-upsert.
- A single malformed row (e.g. a contact with no name) is skipped and
  counted, not a hard failure for the whole sync — matches how CSV staging
  already tolerates row-level issues (`_coerce_*` functions already filter
  out rows missing their required field).

## Testing

- Unit tests per new coercer/analyzer in `test_staging.py`, following its
  existing per-tipo test structure.
- Endpoint tests per entity in a new `test_odoo_ingest.py` (mirrors
  `test_odoo_endpoints.py`'s fake-XML-RPC pattern), covering: first sync
  (all new, batch created), re-sync with no changes (no-op), re-sync with a
  changed field (auto-upsert, no batch), and a new-but-name-colliding row
  (surfaces as `duplicado` in the batch, same as CSV today).
- Migration tests: extend `test_migrations.py`'s existing parametrized RLS
  check to cover the two altered tables (no new tables are created, so no
  new RLS policy needed — the ALTER TABLE additions inherit the existing
  policy).

## Open questions for the implementation plan

- Exact shape of the "what changed" auto-upsert diff for audit logging
  (full before/after per field, or just a count) — leave to the plan.
- Whether `ingest-*` should be rate-limited or otherwise guarded against
  being clicked repeatedly in quick succession — likely unnecessary given
  it's an admin-only manual action, but worth a decision in the plan.
