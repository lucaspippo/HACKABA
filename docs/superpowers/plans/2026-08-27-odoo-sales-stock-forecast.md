# Odoo Sales, Stock, Receipts, and Forecast Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ingest confirmed Odoo sales lines, richer product qty/cost, depósito quants, and done incoming receipts into PolPilot, and add a deterministic 3-month seasonal forecast.

**Architecture:** Extend the shipped two-tier Odoo ingest (`ConectorOdoo.pull_*` → `odoo_ingest.ingest_*` → Staging / auto-upsert). Blob-backed tipos (`venta`, `deposito`, `recepciones`) get `esquema.upsert_filas` / `delete_odoo_missing`. Forecast is a new `core/forecast.py` that only reads `venta` rows. odoo-demo (sibling repo) grows a generator + `post_init_hook` so warehouse computed fields exist.

**Tech Stack:** FastAPI, JSON-blob apartados / inventory, React/Vite, Odoo 17 XML-RPC. No new Python dependencies.

**Spec:** `docs/superpowers/specs/2026-08-27-odoo-sales-stock-forecast-design.md`

## Global Constraints

- All new code identifiers, variables, and columns are in English. Existing Spanish keys stay (`fecha`, `cantidad`, `costo_iva`, `inmovilizado`, `producto`, `codigo`).
- Two-tier sync: linked `(source, source_id)` auto-upserts; unlinked rows go to Staging.
- Coercers emit only Odoo-owned keys (except `costo_iva` on products, which Odoo now owns).
- Receipt ingest must not increment `product.stock`.
- Odoo venta integrar auto-confirms the amount validator; CSV path unchanged.
- No push to Odoo, no scheduler, no AR/`cuenta_corriente`, no vendor bills/`compras`.
- PolPilot pytest mocks `execute_kw`; never boot Docker.
- `cd backend && python -m pytest` after each task; `git checkout -- data-demo/` if seeds were touched.
- Product-facing UI copy may stay Spanish; add keys in `es.js` and `en.js` plus `backend/i18n.py` when the API returns copy.

## File structure

| File | Responsibility |
|---|---|
| `backend/core/esquema.py` | `upsert_filas`, `delete_odoo_missing` |
| `backend/core/models.py` + `store.py` | `free_qty`, `incoming_qty`, `outgoing_qty` on `Articulo` / connector upsert |
| `backend/core/conectores.py` | `pull_ordenes_venta`, `pull_deposito`, `pull_recepciones`; extend `pull_productos` / PO lines |
| `backend/core/staging.py` | `coerce_*_odoo` for venta/deposito/recepciones; integrar branches; auto-confirm |
| `backend/core/odoo_ingest.py` | `ingest_ventas`, `ingest_deposito`, `ingest_recepciones` |
| `backend/core/forecast.py` | Seasonal monthly forecast |
| `backend/core/deposito.py` | `aging()`; `discrepancias()` counted_qty branch |
| `backend/core/receipts.py` | `match_receipt_to_purchase_order` |
| `backend/core/staging.py` `coerce_orden_compra_odoo` | PO status: `purchase` + any `qty_received` → `recibida` |
| `backend/main.py` + `frontend/src/lib/api.js` | sync/ingest/forecast routes |
| `frontend/src/desktop/sections/Conectores.jsx` | Ventas, Recepciones, Depósito tabs |
| `odoo-demo/addons/test_seed_data/` | Generator + hook (sibling repo) |

---

### Task 1: Blob upsert and delete-missing helpers

**Files:**
- Modify: `backend/core/esquema.py` (after `reemplazar_filas`)
- Test: `backend/tests/test_esquema.py`

**Interfaces:**
- Produces: `upsert_filas(tipo: str, filas: list[dict]) -> dict` with `{"tipo", "upserted", "inserted"}`. Match on `(source, source_id)` when both are set; otherwise append.
- Produces: `delete_odoo_missing(tipo: str, pulled_source_ids: set[str] | list[str]) -> int` — deletes rows with `source == "odoo"` whose `source_id` is not in the pull. Returns count deleted. Leaves rows with no `source` alone.

- [ ] **Step 1: Write failing tests**

```python
def test_upsert_filas_inserts_then_updates_by_source_id():
    esquema.upsert_filas("venta", [
        {"fecha": "2026-01-01", "producto": "A", "codigo": 1, "cantidad": 2,
         "precio": 10, "source": "odoo", "source_id": "L1"},
    ])
    assert len(esquema.filas("venta")) == 1
    esquema.upsert_filas("venta", [
        {"fecha": "2026-01-02", "producto": "A", "codigo": 1, "cantidad": 5,
         "precio": 10, "source": "odoo", "source_id": "L1"},
    ])
    filas = esquema.filas("venta")
    assert len(filas) == 1
    assert filas[0]["cantidad"] == 5
    assert filas[0]["fecha"] == "2026-01-02"


def test_delete_odoo_missing_keeps_csv_rows():
    esquema.reemplazar_filas("venta", [
        {"fecha": "2026-01-01", "producto": "CSV", "cantidad": 1, "precio": 1},
        {"fecha": "2026-01-01", "producto": "Odoo", "cantidad": 1, "precio": 1,
         "source": "odoo", "source_id": "L1"},
        {"fecha": "2026-01-01", "producto": "Gone", "cantidad": 1, "precio": 1,
         "source": "odoo", "source_id": "L2"},
    ])
    n = esquema.delete_odoo_missing("venta", {"L1"})
    assert n == 1
    ids = {f.get("source_id") for f in esquema.filas("venta")}
    assert ids == {None, "L1"}
```

- [ ] **Step 2: Run tests — expect FAIL** (`upsert_filas` not defined)

Run: `cd backend && python -m pytest tests/test_esquema.py::test_upsert_filas_inserts_then_updates_by_source_id tests/test_esquema.py::test_delete_odoo_missing_keeps_csv_rows -v`

- [ ] **Step 3: Implement**

```python
def upsert_filas(tipo: str, filas: list[dict]) -> dict:
    """Create-or-update rows of an apartado by (source, source_id).
    Rows without provenance are appended (CSV path)."""
    data = _load()
    bucket = data.setdefault(tipo, {"nombre": TIPOS.get(tipo, {}).get("nombre", tipo), "filas": []})
    existentes = bucket["filas"]
    por_source = {(f.get("source"), f.get("source_id")): i
                  for i, f in enumerate(existentes)
                  if f.get("source") and f.get("source_id")}
    inserted = 0
    upserted = 0
    for fila in filas:
        key = (fila.get("source"), fila.get("source_id"))
        if key[0] and key[1] and key in por_source:
            existentes[por_source[key]] = {**existentes[por_source[key]], **fila}
            upserted += 1
        else:
            existentes.append(dict(fila))
            if key[0] and key[1]:
                por_source[key] = len(existentes) - 1
            inserted += 1
    _save(data)
    return {"tipo": tipo, "upserted": upserted, "inserted": inserted}


def delete_odoo_missing(tipo: str, pulled_source_ids) -> int:
    """Drop Odoo-sourced rows whose source_id is no longer in the pull."""
    keep = {str(x) for x in pulled_source_ids}
    data = _load()
    bucket = data.get(tipo)
    if not bucket:
        return 0
    antes = len(bucket["filas"])
    bucket["filas"] = [
        f for f in bucket["filas"]
        if not (f.get("source") == "odoo" and str(f.get("source_id") or "") not in keep)
    ]
    deleted = antes - len(bucket["filas"])
    if deleted:
        _save(data)
    return deleted
```

- [ ] **Step 4: Re-run tests — expect PASS**
- [ ] **Step 5: Commit** `feat: upsert and delete Odoo-sourced apartado rows by provenance`

---

### Task 2: Product pull/coercer — cost, qty fields, ghosts

**Files:**
- Modify: `backend/core/models.py` (`Articulo`)
- Modify: `backend/core/store.py` (`upsert_desde_conector` copied fields)
- Modify: `backend/core/conectores.py` (`pull_productos`)
- Modify: `backend/core/staging.py` (`coerce_producto_odoo`)
- Modify: `backend/tests/test_conectores_odoo.py`, `backend/tests/test_odoo_ingest.py`, `backend/tests/test_store.py`

**Interfaces:**
- `pull_productos` returns each product with `costo` (`standard_price`), `free_qty`, `incoming_qty`, `outgoing_qty`, `activo` (bool). Search: `active_test=False` context; domain `| (active=True) (qty_available != 0)`.
- `coerce_producto_odoo` emits `costo_iva`, `free_qty`, `incoming_qty`, `outgoing_qty`, `estado` (`activo`/`anulado`). Still omits `venta_x_peso`.
- **Breaks** `test_reingest_productos_no_pisa_costo_editado_por_el_dueño` — replace it: Odoo **owns** cost on linked products; re-sync writes `standard_price` onto `costo_iva`.

- [ ] **Step 1: Extend fake products in tests** with `standard_price`, `free_qty`, `incoming_qty`, `outgoing_qty`, `active`. Add one archived product with qty.

- [ ] **Step 2: Tests**

```python
def test_pull_productos_incluye_costo_y_qty_desglosada(tenant_id, monkeypatch):
    # after wiring fake: assert producto["costo"] == 80, free_qty, incoming_qty, outgoing_qty

def test_coerce_producto_odoo_emite_costo_y_omite_venta_x_peso():
    fila = staging.coerce_producto_odoo({
        "id": 1, "nombre": "X", "codigo": "SKU", "stock": 4, "precio": 10,
        "costo": 8, "free_qty": 3, "incoming_qty": 1, "outgoing_qty": 0, "activo": True,
    })
    assert fila["costo_iva"] == 8
    assert fila["free_qty"] == 3
    assert "venta_x_peso" not in fila
    assert fila["estado"] == "activo"

def test_reingest_productos_odoo_pisa_costo_iva():
    # ingest+integrar, dueño sets costo 77, re-ingest → costo_iva is Odoo's standard_price
```

- [ ] **Step 3: Implement pull + coercer + Articulo fields + upsert_desde_conector loop** (`descripcion`, `sku`, `stock`, `costo_iva`, `pvp`, `free_qty`, `incoming_qty`, `outgoing_qty`, `estado`). Recalc inmovilizado already runs.

- [ ] **Step 4: Pytest those files — PASS.** Update `test_store.py` Articulo round-trip if needed.
- [ ] **Step 5: Commit** `feat: ingest Odoo cost and free/incoming/outgoing qty on products`

---

### Task 3: `pull_ordenes_venta`

**Files:**
- Modify: `backend/core/conectores.py`
- Test: `backend/tests/test_conectores_odoo.py`

**Interfaces:**
- Produces: `ConectorOdoo.pull_ordenes_venta(**kwargs) -> dict` with `origen`, `modulo="sale.order"`, `total`, `ordenes` (preview, all states) and the ingest path will filter.
- Spec ingest filter is confirmed only; preview may include draft/sent/cancel like PO preview includes draft.
- Each order: `id`, `numero`, `cliente`, `estado` (Spanish: borrador/enviada/confirmada/cancelada), `fecha`, `total`, `items` with `id` (line id), `producto`, `product_tmpl_id`, `cantidad`, `precio_unitario`.
- Search `sale.order` limit 200 (or kwargs `limite`). Lines via `sale.order.line` `order_id in`. Read `product_id`, `product_uom_qty`, `price_unit`, `order_id`. For `product_tmpl_id`, read `product.product` ids if needed, or include `product_template_id` if the field exists on the line in Odoo 17 (`product_template_id` is on `sale.order.line` in v17).

Odoo 17 `sale.order.line` has `product_template_id`. Use it.

State map for preview: `draft→borrador`, `sent→enviada`, `sale→confirmada`, `done→confirmada`, `cancel→cancelada`.

- [ ] **Step 1: Fake models** for `sale.order` / `sale.order.line` (one sale, one draft, one cancel; lines with `product_template_id`).
- [ ] **Step 2: Test** `test_pull_ordenes_venta_trae_ordenes_con_items` — confirmed + draft present; line has `id` and `product_tmpl_id`.
- [ ] **Step 3: Implement `pull_ordenes_venta`.**
- [ ] **Step 4: Pytest — PASS**
- [ ] **Step 5: Commit** `feat: pull Odoo sale orders with lines for preview`

---

### Task 4: Coerce + ingest ventas

**Files:**
- Modify: `backend/core/staging.py` — `coerce_venta_odoo`, `_COERCERS_ODOO`, `_REQUERIDO_ODOO`, `crear_batch_odoo` analyzer (`_analizar_ventas` on coerced rows), `integrar` branch
- Modify: `backend/core/odoo_ingest.py` — `ingest_ventas`
- Modify: `backend/core/store.py` — helper `codigo_por_source_id(source, source_id)` or resolve in ingest via `store.buscar_por_source`
- Test: `backend/tests/test_staging.py`, `backend/tests/test_odoo_ingest.py`

**Interfaces:**
- `coerce_venta_odoo(line: dict) -> dict` where `line` is a **flat ingest row** produced by ingest (not the nested preview order): `id` (line id), `nombre` (product name), `fecha`, `cantidad`, `precio`, `product_tmpl_id`, `estado` (order state).
- Better: `ingest_ventas` flattens confirmed orders (`estado == "confirmada"`) into line dicts, resolves `codigo` via `store.buscar_por_source("odoo", str(product_tmpl_id))`, then coerce.

```python
def coerce_venta_odoo(p: dict) -> dict:
    return {
        "fecha": str(p.get("fecha") or "")[:10],
        "producto": str(p.get("nombre") or p.get("producto") or "").strip(),
        "codigo": p.get("codigo"),
        "cantidad": p.get("cantidad") or 0.0,
        "precio": p.get("precio"),
        "source": "odoo",
        "source_id": str(p["id"]),
        "source_status": p.get("estado") or "",
    }
```

`_REQUERIDO_ODOO["venta"] = "producto"`.

`ingest_ventas`:
1. `pull_ordenes_venta()`
2. Flatten lines where order `estado == "confirmada"`
3. Resolve codigo from product `source_id == str(product_tmpl_id)`
4. Linked by line `source_id` → auto-upsert via `esquema.upsert_filas`; skip if no producto
5. Unlinked → `crear_batch_odoo("venta", ...)`
6. `delete_odoo_missing("venta", pulled_confirmed_line_ids)` — only ids from the confirmed flatten, so cancelled lines drop
7. Audit summary

`integrar` for `tipo == "venta"` and `fuente == "odoo"`: `esquema.upsert_filas("venta", a_integrar)` then `ventas.confirmar_validacion(confirmar=True, actor=actor)`. Do **not** go through `iniciar_validacion`. CSV venta path unchanged (generic `crear_apartado` + `iniciar_validacion`).

Analyzer for Odoo venta: reuse `_analizar_ventas` (orphan products).

- [ ] **Step 1: Tests** — first ingest stages; after integrate, `ventas.montos_confirmados()`; second ingest auto-upserts; cancelled line deleted; CSV row kept; empty name skipped (`omitidos_malformados`).
- [ ] **Step 2: Implement flatten + coerce + ingest + integrar branch**
- [ ] **Step 3: Pytest — PASS**
- [ ] **Step 4: Commit** `feat: ingest confirmed Odoo sale lines into venta`

---

### Task 5: API + Conectores Ventas tab

**Files:**
- Modify: `backend/main.py` — `POST .../sync-ventas`, `POST .../ingest-ventas`
- Modify: `backend/tests/test_odoo_endpoints.py`, `backend/tests/test_authz.py`
- Modify: `frontend/src/lib/api.js`
- Modify: `frontend/src/desktop/sections/Conectores.jsx`
- Modify: `frontend/src/lib/locales/es.js`, `en.js`

**Interfaces:** Same admin gate and return shape as ingest-ordenes-compra.

Clone `OdooTabCompras` → `OdooTabVentas`. “Ver en Staging” → `onNavigate("saneamiento", "revision")`.

- [ ] **Step 1: Endpoint tests** (admin 200, non-admin 403) + fake XML-RPC
- [ ] **Step 2: Implement routes + UI + i18n keys** (`odoo.tab_ventas`, `traer_ventas`, `ingestar_ventas`, `ingesta_ventas_resultado`, `sync_ventas_resultado`, `estado_venta_*`)
- [ ] **Step 3: Pytest authz/endpoints — PASS**
- [ ] **Step 4: Commit** `feat: Ventas Odoo tab and ingest API`

---

### Task 6: Forecast engine

**Files:**
- Create: `backend/core/forecast.py`
- Test: `backend/tests/test_forecast.py`

**Interfaces:**
- `forecast_demand(lang: str | None = None) -> dict`
- Returns `{available: bool, as_of: str, items: list[dict]}`. If no venta rows: `available: false`, `reason` via i18n key `core.forecast.sin_ventas`.
- Each item: `product_code`, `description`, `months` (3 dicts: `period` YYYY-MM, `qty`, `amount`, `qty_low`, `qty_high`, `interval_ok`), `confidence` (`low`/`medium`/`high`), `trend` (float), `available` (per product).
- Math per spec §5. Use `statistics.stdev` / `pstdev`. Horizon: next 3 calendar months from `fechas.hoy()`.
- Flag `stockout_risk: bool` if month-1 `qty > stock + incoming_qty - outgoing_qty` (missing qty fields treat as 0).

- [ ] **Step 1: Tests with monkeypatched `fechas.hoy` = 2026-07-07**
  - Empty ventas → collection `available: false`
  - May spike 2024-05 and 2025-05 high, other months low → 2026-05 is not in horizon (horizon is Aug-Oct 2026 if today is Jul 7). Use today=2026-04-15 so horizon includes 2026-05, OR test January spike with today=2026-12-01.
  - **Use `fechas.hoy` = 2026-04-07** so horizon is 2026-05, 2026-06, 2026-07. Seed 24 months with May qty 100 and other months 10. Expect May forecast well above 10.
  - SKU with only 3 months of data → `available: false` or `confidence: low` and `interval_ok: false`.

- [ ] **Step 2: Implement `forecast.py`**
- [ ] **Step 3: Pytest — PASS**
- [ ] **Step 4: Commit** `feat: seasonal monthly demand forecast per product`

---

### Task 7: Forecast API, Ángela tool, Evolución block

**Files:**
- Modify: `backend/main.py` — `GET /api/forecast` with `require_feature("evolucion")` (same as evolución)
- Modify: `backend/tests/test_authz.py`
- Modify: `backend/angela.py` — add tool `consultar_pronostico` that returns `forecast.forecast_demand(lang)` JSON (narrate only)
- Modify: `frontend/src/lib/api.js` — `forecast: () => get("/api/forecast")`
- Modify: Evolución desktop section to show a compact list when `available`

Find the Evolución component (`frontend/src/desktop/sections/` or `frontend/src/sections/`) and add a block: product, next month qty, interval if `interval_ok`.

- [ ] **Step 1: Authz test + empty forecast 200**
- [ ] **Step 2: Wire API + tool + UI**
- [ ] **Step 3: Pytest — PASS**
- [ ] **Step 4: Commit** `feat: expose demand forecast on API, Ángela, and Evolución`

---

### Task 8: Depósito pull + ingest

**Files:**
- Modify: `conectores.py` — `pull_deposito`
- Modify: `staging.py` — `coerce_deposito_odoo`; analyzer reuse depósito orphan check
- Modify: `odoo_ingest.py` — `ingest_deposito`
- Tests: `test_conectores_odoo.py`, `test_odoo_ingest.py`, `test_staging.py`

**Interfaces:**
- Pull `stock.quant` with `quantity != 0` and location `usage = internal`. Fields: `product_id`, `location_id`, `quantity`, `lot_id`, `in_date`, `inventory_quantity`, `inventory_quantity_set` (if present). Resolve location `complete_name`, lot name + `expiration_date`, `product.product` → `product_tmpl_id`.
- Coercer: existing Spanish keys + `counted_qty` only if inventory set, `in_date`, `source`, `source_id` (quant id).
- Same two-tier + `delete_odoo_missing("deposito", ...)`.
- Required: `producto`.

- [ ] Tests for preview, stage, re-sync, qty-0 not pulled, missing product → observation
- [ ] Implement
- [ ] Commit `feat: ingest Odoo stock quants into deposito`

---

### Task 9: Aging + counted discrepancies

**Files:**
- Modify: `backend/core/deposito.py`
- Test: `backend/tests/test_wms_tms.py` or `backend/tests/test_deposito.py`

**Interfaces:**
- `aging(as_of=None) -> list[dict]` buckets `0_90`, `91_180`, `181_365`, `365_plus` with `units`, `inmovilizado`. Skip rows without parseable `in_date`.
- `discrepancias()`: group by `codigo`. If any row has `counted_qty` not None, compare sum(counted_qty) vs sum(cantidad); else sum(cantidad) vs product.stock.

- [ ] Tests with frozen `hoy`
- [ ] Implement
- [ ] Commit `feat: inventory aging and counted-vs-system discrepancies`

---

### Task 10: Recepciones + PO status amendment

**Files:**
- Modify: `conectores.py` — `pull_recepciones`; PO line read adds `qty_received`
- Modify: `staging.py` — `coerce_recepcion_odoo`, `_ESTADO_ORDEN_COMPRA_ODOO` logic via a function `map_purchase_status(odoo_state, qty_received_any: bool)`
- Modify: `odoo_ingest.py` — `ingest_recepciones` (no stock increment); after upsert, update linked POs with the status rule
- Modify: `purchase_orders_repo` only if needed (upsert already sets status from coercer)
- Create: `backend/core/receipts.py` — `match_receipt_to_purchase_order(po_number: str) -> dict`
- Tests

**Interfaces:**
- Pull done incoming pickings + moves. Row: fecha, producto, product_tmpl_id, proveedor, cantidad, deposito, origen (picking name), po_number, id (move id), estado.
- `map_purchase_status`: draft/sent→borrador, cancel→cancelada, done→recibida, purchase + any qty_received→recibida, else aprobada.
- `ingest_recepciones` must not change `store` stock.
- `match_receipt_to_purchase_order`: load PO items vs sum of recepciones with that `po_number` per codigo.

- [ ] Tests: stock unchanged; PO purchase+qty_received→recibida; short receipt diffs
- [ ] Implement
- [ ] Commit `feat: ingest Odoo goods receipts and map partial POs to recibida`

---

### Task 11: Depósito + Recepciones API and tabs

**Files:** `main.py`, `api.js`, `Conectores.jsx`, locales, `test_odoo_endpoints.py`, `test_authz.py`

Clone Ventas tab twice. Staging link `onNavigate("saneamiento", "revision")`.

- [ ] Implement + authz tests
- [ ] Commit `feat: Odoo tabs for deposito and recepciones`

---

### Task 12: odoo-demo seed generator (sibling repo)

**Files (odoo-demo repo):**
- Create: `addons/test_seed_data/generate.py`
- Modify: `__manifest__.py` (depends `product_expiry`; `post_init_hook`)
- Create: `addons/test_seed_data/hooks.py` — confirm SOs / validate incoming pickings
- Modify: `README.md` rebuild loop
- Generated XML under `addons/test_seed_data/data/`

**Constraints:** deterministic RNG seed `20260707`; ~60 electronics SKUs; two warehouses; 24 months ending 2026-07; 2–4k confirmed SO lines; one unpriced, one archived+qty, one negative quant, lots+expiry, open inventory counts; draft/sent/cancel leftovers; one short receipt.

This repo is `../odoo-demo` relative to polpilot-app. Commit there separately.

- [ ] Generator writes catalog XML
- [ ] Hook builds history via ORM
- [ ] Document rebuild; dump-seed after a local init
- [ ] Commit in odoo-demo `feat: SME-scale seed with 24-month sales and receipts`

---

## Spec coverage checklist

| Spec section | Task |
|---|---|
| upsert/delete blob rows | 1 |
| Product cost/qty/ghosts | 2 |
| Sales mapping + two-tier + auto-confirm | 3–5 |
| Forecast math + API | 6–7 |
| Depósito + aging + counted | 8–9, 11 |
| Recepciones + PO status + remito↔OC | 10–11 |
| odoo-demo seed | 12 |
| English new identifiers | all |
| No AR / compras / push | out of plan |
