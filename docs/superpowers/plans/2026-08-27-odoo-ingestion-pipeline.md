# Odoo Ingestion Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let pulled Odoo data (contacts, products, vendors, purchase orders) actually merge into PolPilot's real tables (`customer_accounts`, `inventory_working`, the `proveedores` apartado, `purchase_orders`) instead of only being previewed, while staying idempotent on re-sync and always traceable back to its source.

**Architecture:** Extend the existing Staging Area (`core/staging.py`) with a second entry point, `crear_batch_odoo`, that accepts pre-structured rows (skipping CSV parsing/Nivel-1 normalization) and reuses its review/resolve/audit/backup machinery. A new orchestration module, `core/odoo_ingest.py`, splits each pull into records already linked to a PolPilot row (by `source`+`source_id`, auto-upserted immediately) and genuinely new ones (routed into a Staging batch for dueño review before creation).

**Tech Stack:** FastAPI + SQLAlchemy/Postgres (Alembic migrations) backend, React/Vite frontend — same stack as the rest of the repo, no new dependencies.

**Spec:** `docs/superpowers/specs/2026-08-27-odoo-ingestion-pipeline-design.md`

## Global Constraints

- All new DB column names are in English (matches the existing `purchase_orders`/`customer_accounts` convention).
- Auto-upsert applies to already-linked records with no review card; only genuinely new (unlinked) records go through Staging Area review.
- No new scheduler/webhook — ingestion stays a manual, dueño-triggered action per entity.
- `core/ordenes.py`'s Ángela-prepares/dueño-approves workflow for PolPilot-originated orders is untouched; ingested Odoo POs are additional rows in the same `purchase_orders` table, distinguished by `origin='odoo'`/`source='odoo'`.
- Every new backend identifier, comment, and docstring is in English or Spanish following the existing per-file convention (`core/*.py` docstrings are Spanish, matching the rest of the file being edited); product-facing UI copy is Spanish (existing i18n convention).
- Run `cd backend && python -m pytest` after each task; run `git checkout -- data-demo/` afterward if the suite touched seed files (per `backend/CLAUDE.md`).

---

### Task 1: Schema migrations — provenance columns

**Files:**
- Create: `backend/migrations/versions/0035_customer_accounts_odoo_fields.py`
- Create: `backend/migrations/versions/0036_purchase_orders_odoo_fields.py`
- Test: `backend/tests/test_migrations.py` (existing RLS tests already cover both tables by name — no changes needed, just must keep passing)

**Interfaces:**
- Produces: `customer_accounts.vat/city/phone/email/source/source_id` (all `TEXT`, nullable), `purchase_orders.source/source_id/source_status` (all `TEXT`, nullable). Task 3 and Task 4 read/write these directly via SQL.

- [ ] **Step 1: Write migration 0035**

```python
"""add contact and source-tracking columns to customer_accounts

Revision ID: 0035
Revises: 0034
Create Date: 2026-08-27

customer_accounts has no contact fields today (id, name, balance,
credit_limit, payment_term_days, days_overdue, average_payment_days).
Odoo ingestion (core/odoo_ingest.py) needs vat/city/phone/email to store
what it pulls, plus source/source_id to track where a row came from and
find it again on re-sync. All nullable, additive — existing rows get
NULL, meaning "not from a connector".
"""
from alembic import op
import sqlalchemy as sa

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customer_accounts", sa.Column("vat", sa.Text, nullable=True))
    op.add_column("customer_accounts", sa.Column("city", sa.Text, nullable=True))
    op.add_column("customer_accounts", sa.Column("phone", sa.Text, nullable=True))
    op.add_column("customer_accounts", sa.Column("email", sa.Text, nullable=True))
    op.add_column("customer_accounts", sa.Column("source", sa.Text, nullable=True))
    op.add_column("customer_accounts", sa.Column("source_id", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("customer_accounts", "source_id")
    op.drop_column("customer_accounts", "source")
    op.drop_column("customer_accounts", "email")
    op.drop_column("customer_accounts", "phone")
    op.drop_column("customer_accounts", "city")
    op.drop_column("customer_accounts", "vat")
```

- [ ] **Step 2: Write migration 0036**

```python
"""add source-tracking columns to purchase_orders

Revision ID: 0036
Revises: 0035
Create Date: 2026-08-27

Odoo ingestion (core/odoo_ingest.py) needs to track which purchase orders
came from Odoo and stay idempotent on re-sync. source/source_id identify
the row's origin; source_status holds Odoo's own state string (e.g.
"confirmada") separately from `status`, which holds it mapped into
PolPilot's borrador/aprobada/recibida/cancelada workflow — so the mapping
never loses the original value. All nullable, additive.

No new unique index is needed: (tenant_id, number) is already this
table's primary key (see 0009_purchase_orders.py), and Odoo's own PO
numbers (e.g. "P00006") never collide with PolPilot-originated ones
(e.g. "OC-2026-0901"), so ON CONFLICT (tenant_id, number) is enough to
upsert idempotently by number.
"""
from alembic import op
import sqlalchemy as sa

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("purchase_orders", sa.Column("source", sa.Text, nullable=True))
    op.add_column("purchase_orders", sa.Column("source_id", sa.Text, nullable=True))
    op.add_column("purchase_orders", sa.Column("source_status", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("purchase_orders", "source_status")
    op.drop_column("purchase_orders", "source_id")
    op.drop_column("purchase_orders", "source")
```

- [ ] **Step 3: Apply migrations and verify**

Run: `cd backend && alembic upgrade head`
Expected: both migrations apply cleanly, ending at head `0036`.

Run: `cd backend && python -m pytest tests/test_migrations.py -v`
Expected: PASS (existing RLS checks for both tables still pass — ALTER TABLE doesn't touch RLS).

- [ ] **Step 4: Commit**

```bash
cd backend
git add migrations/versions/0035_customer_accounts_odoo_fields.py migrations/versions/0036_purchase_orders_odoo_fields.py
git commit -m "Add source-tracking columns for Odoo ingestion"
```

---

### Task 2: Products ingestion (establishes the shared mechanism)

This task also builds `staging.crear_batch_odoo` and `core/odoo_ingest.py` — the shared machinery Tasks 3-5 reuse — using products as the first, migration-free vertical slice (`inventory_working` is a JSON blob, so no schema change is needed here).

**Files:**
- Modify: `backend/core/models.py` (extend `Articulo`)
- Modify: `backend/core/store.py` (add `upsert_desde_conector`)
- Modify: `backend/core/staging.py` (add `crear_batch_odoo`, `coerce_producto_odoo`)
- Create: `backend/core/odoo_ingest.py` (new orchestration module)
- Modify: `backend/main.py` (add `POST /api/conectores/odoo/ingest-productos`)
- Modify: `backend/frontend` — actually `frontend/src/desktop/sections/Conectores.jsx`, `frontend/src/lib/api.js`, `frontend/src/lib/locales/en.js`, `frontend/src/lib/locales/es.js`
- Test: `backend/tests/test_staging.py`, `backend/tests/test_odoo_ingest.py` (new)

**Interfaces:**
- Consumes: `core.conectores.ConectorOdoo.pull_productos()` → `{"origen": "odoo", "modulo": "product.template", "total": N, "productos": [{"id": int, "codigo": str, "nombre": str, "categoria": str, "precio": float, "stock": float}, ...]}` (already exists, unchanged).
- Produces:
  - `staging.coerce_producto_odoo(p: dict) -> dict` — `{"descripcion": str, "stock": float, "costo_iva": None, "pvp": float|None, "sku": str, "source": "odoo", "source_id": str}`.
  - `staging.crear_batch_odoo(tipo: str, filas_odoo: list[dict], nombre: str | None = None, lang: str | None = None) -> dict` — same shape `staging.crear_batch()` returns (`_resumen(batch)`).
  - `store.upsert_desde_conector(fila: dict, actor: str) -> dict` — the coerced dict, `fila` must have `descripcion`, `source`, `source_id`; returns the written article dict.
  - `core.odoo_ingest.ingest_productos(actor: str = "dueño") -> dict` — `{"actualizados": int, "nuevos_para_revisar": int, "batch_id": str | None}`.

- [ ] **Step 1: Extend `Articulo` with provenance fields**

Read `backend/core/models.py` lines 50-79 first to confirm you're editing the current version, then apply:

```python
@dataclass
class Articulo:
    codigo: int
    descripcion: str
    estado: str  # "activo" | "anulado"
    stock: float = 0.0
    costo_iva: float | None = None
    pvp: float | None = None
    venta_x_peso: bool = False
    cota_inf: float | None = None
    cota_sup: float | None = None
    valor_peso: float | None = None
    antiguedad_costo_dias: float | None = None
    inmovilizado: float = 0.0
    sku: str | None = None
    source: str | None = None
    source_id: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "Articulo":
        return cls(
            codigo=int(d["codigo"]),
            descripcion=d["descripcion"],
            estado=d.get("estado", "activo"),
            stock=d.get("stock") or 0.0,
            costo_iva=d.get("costo_iva"),
            pvp=d.get("pvp"),
            venta_x_peso=bool(d.get("venta_x_peso")),
            cota_inf=d.get("cota_inf"),
            cota_sup=d.get("cota_sup"),
            valor_peso=d.get("valor_peso"),
            antiguedad_costo_dias=d.get("antiguedad_costo_dias"),
            inmovilizado=d.get("inmovilizado") or 0.0,
            sku=d.get("sku"),
            source=d.get("source"),
            source_id=d.get("source_id"),
        )
```

(Only the new three fields and their two corresponding `from_dict` lines are additions — everything else is unchanged, shown for context so the edit applies cleanly.)

- [ ] **Step 2: Write the failing test for `store.upsert_desde_conector`**

Add to `backend/tests/test_store.py` (if it doesn't exist, check `backend/tests/` for the actual filename of `core/store.py`'s existing tests first — likely `test_store.py` or `test_articulos.py`; use whichever already imports `from core import store` and follows its fixture pattern for resetting `store.resetear_actual()`):

```python
def test_upsert_desde_conector_crea_producto_nuevo():
    store.resetear_actual()
    antes = len(store.raw_actual())
    fila = {"descripcion": "Producto Odoo Nuevo", "stock": 10, "costo_iva": None,
            "pvp": 500, "sku": "ODOO-1", "source": "odoo", "source_id": "999"}
    r = store.upsert_desde_conector(fila, actor="test")
    assert len(store.raw_actual()) == antes + 1
    assert r["descripcion"] == "Producto Odoo Nuevo"
    assert r["sku"] == "ODOO-1"
    assert r["source"] == "odoo" and r["source_id"] == "999"


def test_upsert_desde_conector_actualiza_si_ya_vinculado():
    store.resetear_actual()
    fila = {"descripcion": "Producto Odoo", "stock": 10, "costo_iva": None,
            "pvp": 500, "sku": "ODOO-2", "source": "odoo", "source_id": "888"}
    store.upsert_desde_conector(fila, actor="test")
    antes = len(store.raw_actual())
    fila["stock"] = 25
    fila["pvp"] = 600
    r = store.upsert_desde_conector(fila, actor="test")
    assert len(store.raw_actual()) == antes  # no duplica
    assert r["stock"] == 25
    assert r["pvp"] == 600
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_store.py -k upsert_desde_conector -v`
Expected: FAIL with `AttributeError: module 'core.store' has no attribute 'upsert_desde_conector'`

- [ ] **Step 4: Implement `store.upsert_desde_conector`**

Add to `backend/core/store.py`, after `actualizar_articulo` (around line 119):

```python
def buscar_por_source(source: str, source_id: str) -> dict | None:
    return next((d for d in raw_actual()
                 if d.get("source") == source and d.get("source_id") == source_id), None)


def upsert_desde_conector(fila: dict, actor: str) -> dict:
    """Alta o actualización de un producto que llega de un conector externo
    (p.ej. Odoo), a diferencia de crear_articulo/actualizar_articulo
    (ediciones manuales del dueño): resuelve el código automáticamente y
    acepta los campos de procedencia (source, source_id, sku). Usado tanto
    para el auto-upsert de productos ya vinculados (core/odoo_ingest.py)
    como al integrar un batch de Staging con productos nuevos."""
    raw = raw_actual()
    existente = next((d for d in raw if d.get("source") == fila["source"]
                       and d.get("source_id") == fila["source_id"]), None)
    if existente:
        antes = dict(existente)
        for campo in ("descripcion", "sku", "stock", "costo_iva", "pvp"):
            if campo in fila:
                existente[campo] = fila[campo]
        _recalcular_inmovilizado(existente)
        guardar(raw)
        audit.record(actor, "actualizar_articulo_conector", antes, existente)
        return existente
    siguiente = max([d.get("codigo", 0) for d in raw] + [0]) + 1
    nuevo = {
        "codigo": siguiente, "descripcion": fila["descripcion"], "estado": "activo",
        "stock": fila.get("stock") or 0, "costo_iva": fila.get("costo_iva"),
        "pvp": fila.get("pvp"), "venta_x_peso": False,
        "sku": fila.get("sku"), "source": fila["source"], "source_id": fila["source_id"],
    }
    _recalcular_inmovilizado(nuevo)
    raw.append(nuevo)
    guardar(raw)
    audit.record(actor, "crear_articulo_conector", None, nuevo)
    return nuevo
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_store.py -k upsert_desde_conector -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd backend
git add core/models.py core/store.py tests/test_store.py
git commit -m "Add provenance-tracked product upsert for connector ingestion"
```

- [ ] **Step 7: Write the failing test for `staging.crear_batch_odoo` (products)**

Add to `backend/tests/test_staging.py`:

```python
def test_crear_batch_odoo_producto_nuevo_sin_observaciones_de_precio():
    store.resetear_actual()
    filas_odoo = [
        {"id": 501, "codigo": "ODOO-NEW-1", "nombre": "Producto Totalmente Nuevo",
         "categoria": "General", "precio": 999.0, "stock": 5.0},
    ]
    r = staging.crear_batch_odoo("producto", filas_odoo)
    assert r["tipo"] == "producto"
    assert r["total_filas"] == 1


def test_crear_batch_odoo_producto_detecta_duplicado_por_nombre():
    store.resetear_actual()
    existente = store.raw_actual()[0]
    filas_odoo = [
        {"id": 502, "codigo": "ODOO-DUP-1", "nombre": existente["descripcion"],
         "categoria": "General", "precio": 10.0, "stock": 1.0},
    ]
    r = staging.crear_batch_odoo("producto", filas_odoo)
    tipos = {o["tipo"] for o in r["observaciones"]}
    assert "duplicado" in tipos
```

- [ ] **Step 8: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_staging.py -k crear_batch_odoo -v`
Expected: FAIL with `AttributeError: module 'core.staging' has no attribute 'crear_batch_odoo'`

- [ ] **Step 9: Implement `coerce_producto_odoo` and `crear_batch_odoo`**

Add to `backend/core/staging.py`, after `_coerce_logistica` (around line 104):

```python
def coerce_producto_odoo(p: dict) -> dict:
    return {
        "codigo": None,
        "descripcion": str(p.get("nombre") or "").strip(),
        "estado": "activo",
        "stock": p.get("stock") or 0.0,
        "costo_iva": None,
        "pvp": p.get("precio"),
        "venta_x_peso": False,
        "sku": p.get("codigo") or "",
        "source": "odoo",
        "source_id": str(p["id"]),
    }
```

Add near the bottom of the file, after `descartar` (this is the new entry point — note it deliberately does not touch `normalizacion.normalizar_tabla` or `importer.inferir_mapeo`, both CSV-only concerns):

```python
_COERCERS_ODOO = {
    "producto": coerce_producto_odoo,
}

# Qué campo identifica una fila coercionada como "utilizable" por tipo — una
# fila de Odoo sin este campo (p.ej. un contacto sin nombre) se descarta en
# vez de crear un registro vacío; mismo criterio que el filtrado por CSV en
# _coerce_y_analizar (líneas "filas = [f for f in filas if f[...]]").
_REQUERIDO_ODOO = {"producto": "descripcion", "proveedor": "nombre",
                    "cliente": "nombre", "orden_compra": "numero"}


def crear_batch_odoo(tipo: str, filas_odoo: list[dict], nombre: str | None = None,
                      lang: str | None = None) -> dict:
    """Como crear_batch(), pero para filas que YA llegan estructuradas desde
    un conector (Odoo) en vez de un CSV crudo: sin parseo ni normalización
    Nivel 1 (eso es para texto ambiguo tipeado a mano; el conector ya
    entrega tipos correctos). Sólo debe recibir filas SIN vínculo todavía —
    core/odoo_ingest.py filtra antes las que ya tienen source_id conocido y
    esas se actualizan directo, sin pasar por acá."""
    coerce = _COERCERS_ODOO[tipo]
    filas = [coerce(f) for f in filas_odoo]
    filas = [f for f in filas if f.get(_REQUERIDO_ODOO[tipo])]
    if tipo == "producto":
        observaciones = _analizar(filas)
    else:
        raise ValueError(f"tipo sin coercer/analizador Odoo: {tipo}")
    batch = {
        "id": "b" + secrets.token_hex(3),
        "nombre": nombre or f"Odoo · {tipo}",
        "fecha": datetime.datetime.now().isoformat(timespec="seconds"),
        "estado": "revision",
        "tipo": tipo,
        "fuente": "odoo",
        "plan": esquema.plan_integracion(tipo, lang),
        "mapeo": {},
        "filas": filas,
        "observaciones": observaciones,
        "normalizaciones": None,
        "ambiguos": [],
        "crudo": None,
    }
    batches = _load()
    batches.append(batch)
    _save(batches)
    return _resumen(batch)
```

Note the `else: raise ValueError(...)` branch — Tasks 3-5 each add one `elif tipo == "...":` line plus one entry in `_COERCERS_ODOO`, so this task's slice is complete and testable on its own without a dangling unimplemented branch.

- [ ] **Step 10: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_staging.py -k crear_batch_odoo -v`
Expected: PASS

- [ ] **Step 11: Make `integrar()` route Odoo-sourced product batches through the new upsert path**

Read `backend/core/staging.py`'s `integrar()` function (around line 489-547) first. Its existing bottom block (the `# Productos: se suman al inventario oficial.` section) always does a plain manual-append — extend it to call `store.upsert_desde_conector` per row when the batch came from Odoo, so ingested products carry `sku`/`source`/`source_id` while CSV-imported ones keep the exact existing behavior unchanged:

Replace:

```python
    # Productos: se suman al inventario oficial.
    raw = store.raw_actual()
    backup = store.versiones.save({"articulos": raw}, motivo=f"Backup antes de integrar «{b['nombre']}»", autor=actor)
    siguiente = max([d.get("codigo", 0) for d in raw] + [0]) + 1
    nuevos = 0
    for f in a_integrar:
        codigo = f["codigo"] or siguiente
        siguiente = max(siguiente, codigo) + 1
        inmov = round((f["stock"] or 0) * (f["costo_iva"] or 0), 2) if (f["stock"] or 0) > 0 else 0.0
        raw.append({
            "codigo": codigo, "descripcion": f["descripcion"], "estado": f.get("estado", "activo"),
            "stock": f["stock"], "costo_iva": f.get("costo_iva"), "pvp": f.get("pvp"),
            "venta_x_peso": f.get("venta_x_peso", False), "inmovilizado": inmov,
        })
        nuevos += 1
    store.guardar(raw)
```

with:

```python
    # Productos: se suman al inventario oficial. Los que llegan de un
    # conector (b["fuente"] == "odoo") pasan por upsert_desde_conector para
    # que queden con sku/source/source_id; el resto (CSV) sigue igual.
    raw = store.raw_actual()
    backup = store.versiones.save({"articulos": raw}, motivo=f"Backup antes de integrar «{b['nombre']}»", autor=actor)
    if b.get("fuente") == "odoo":
        for f in a_integrar:
            store.upsert_desde_conector(f, actor)
        nuevos = len(a_integrar)
    else:
        siguiente = max([d.get("codigo", 0) for d in raw] + [0]) + 1
        nuevos = 0
        for f in a_integrar:
            codigo = f["codigo"] or siguiente
            siguiente = max(siguiente, codigo) + 1
            inmov = round((f["stock"] or 0) * (f["costo_iva"] or 0), 2) if (f["stock"] or 0) > 0 else 0.0
            raw.append({
                "codigo": codigo, "descripcion": f["descripcion"], "estado": f.get("estado", "activo"),
                "stock": f["stock"], "costo_iva": f.get("costo_iva"), "pvp": f.get("pvp"),
                "venta_x_peso": f.get("venta_x_peso", False), "inmovilizado": inmov,
            })
            nuevos += 1
        store.guardar(raw)
```

(`store.upsert_desde_conector` already calls `store.guardar` internally per row, so the `else` branch keeps the original single `store.guardar(raw)` call and the `if` branch doesn't need one.)

- [ ] **Step 12: Write the failing test for full integration**

Add to `backend/tests/test_staging.py`:

```python
def test_integrar_batch_odoo_usa_upsert_con_source():
    store.resetear_actual()
    filas_odoo = [
        {"id": 601, "codigo": "ODOO-INT-1", "nombre": "Producto Integrado Odoo",
         "categoria": "General", "precio": 42.0, "stock": 3.0},
    ]
    r = staging.crear_batch_odoo("producto", filas_odoo)
    res = staging.integrar(r["id"], actor="test")
    assert res["ok"] is True
    creado = next(d for d in store.raw_actual() if d.get("source_id") == "601")
    assert creado["source"] == "odoo"
    assert creado["sku"] == "ODOO-INT-1"
```

- [ ] **Step 13: Run the test to verify it fails, then implement, then pass**

Run: `cd backend && python -m pytest tests/test_staging.py -k integrar_batch_odoo -v`
Expected: FAIL before Step 11's edit is in place (if you're doing Steps 11-13 in order, apply Step 11 first, then this test should already PASS — run it now to confirm).
Expected after Step 11: PASS

- [ ] **Step 14: Commit**

```bash
cd backend
git add core/staging.py tests/test_staging.py
git commit -m "Add Odoo-sourced batch entry point to Staging Area (products)"
```

- [ ] **Step 15: Write the failing test for `core/odoo_ingest.py` (products)**

Create `backend/tests/test_odoo_ingest.py`:

```python
import xmlrpc.client

import pytest

from core import odoo_ingest, store
from core.db import odoo_connections_repo, tenant as _tenant


class _FakeCommon:
    def authenticate(self, db, user, pwd, ctx):
        return 7


class _FakeModels:
    def __init__(self):
        self.productos = [
            {"id": 1, "name": "Producto Ya Vinculado", "default_code": "SKU-1",
             "categ_id": [1, "General"], "list_price": 100.0, "qty_available": 50.0},
            {"id": 2, "name": "Producto Nuevo De Odoo", "default_code": "SKU-2",
             "categ_id": [1, "General"], "list_price": 200.0, "qty_available": 20.0},
        ]

    def execute_kw(self, db, uid, pwd, model, method, args, kwargs):
        if model == "product.template":
            if method == "search":
                return [p["id"] for p in self.productos]
            if method == "read":
                return self.productos
        raise NotImplementedError((model, method))


def _fake_server_proxy(url):
    return _FakeCommon() if url.endswith("/xmlrpc/2/common") else _FakeModels()


@pytest.fixture
def tenant_id():
    return _tenant.current_tenant_id()


@pytest.fixture(autouse=True)
def _setup(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "good-key")
    store.resetear_actual()
    yield
    odoo_connections_repo.delete(tenant_id)
    store.resetear_actual()


def test_ingest_productos_primera_vez_todo_va_a_revision():
    r = odoo_ingest.ingest_productos(actor="test")
    assert r["actualizados"] == 0
    assert r["nuevos_para_revisar"] == 2
    assert r["batch_id"] is not None


def test_ingest_productos_segunda_vez_actualiza_sin_batch():
    r1 = odoo_ingest.ingest_productos(actor="test")
    from core import staging
    staging.integrar(r1["batch_id"], actor="test")

    r2 = odoo_ingest.ingest_productos(actor="test")
    assert r2["actualizados"] == 2
    assert r2["nuevos_para_revisar"] == 0
    assert r2["batch_id"] is None
```

- [ ] **Step 16: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_odoo_ingest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.odoo_ingest'`

- [ ] **Step 17: Implement `core/odoo_ingest.py`**

Create `backend/core/odoo_ingest.py`:

```python
"""
core/odoo_ingest.py — orquesta el pull de Odoo hacia los datos reales de
PolPilot (a diferencia de conectores.ConectorOdoo.pull_*, que sólo trae el
preview de sólo lectura).

Two-tier: por cada fila que llega de Odoo, si ya está vinculada a un
registro de PolPilot (mismo source_id) se actualiza directo, sin revisión
— Odoo ya es dueño de ese dato. Si es nueva, entra a un batch de la
Staging Area (core/staging.py) para que el dueño la revise/apruebe antes
de crearla — nunca se crea un cliente/proveedor/producto/orden a ciegas.
"""
from __future__ import annotations

from . import conectores, staging, store
from .db import tenant as _tenant


def ingest_productos(actor: str = "dueño") -> dict:
    tenant_id = _tenant.current_tenant_id()
    conector = conectores.ConectorOdoo(tenant_id)
    pull = conector.pull_productos()

    vinculados = {d["source_id"] for d in store.raw_actual() if d.get("source") == "odoo"}
    nuevas, actualizadas = [], 0
    for p in pull["productos"]:
        if str(p["id"]) in vinculados:
            fila = staging.coerce_producto_odoo(p)
            store.upsert_desde_conector(fila, actor)
            actualizadas += 1
        else:
            nuevas.append(p)

    batch_id = None
    if nuevas:
        r = staging.crear_batch_odoo("producto", nuevas, nombre="Odoo · productos")
        batch_id = r["id"]

    return {"actualizados": actualizadas, "nuevos_para_revisar": len(nuevas), "batch_id": batch_id}
```

- [ ] **Step 18: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_odoo_ingest.py -v`
Expected: PASS

- [ ] **Step 19: Commit**

```bash
cd backend
git add core/odoo_ingest.py tests/test_odoo_ingest.py
git commit -m "Add core/odoo_ingest.py orchestration module (products)"
```

- [ ] **Step 20: Write the failing endpoint test**

Add to `backend/tests/test_odoo_endpoints.py` (it already has `_FakeModels`/`_fake_server_proxy`/`admin_token` fixtures — extend `_FakeModels.execute_kw`'s `product.template` branch, which today returns one hardcoded product for both `search` and `read`, to also handle being called twice across a sync — check the current fixture body first; if it already returns a fixed single-product list regardless of args, that's fine for this test since we only need "1 product, first sync"):

```python
def test_ingest_productos_primera_vez_crea_batch(admin_token, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    client.put("/api/conectores/odoo", headers=_h(admin_token),
               json={"url": "https://x.odoo.com", "database": "x",
                     "username": "admin", "api_key": "good-key"})
    r = client.post("/api/conectores/odoo/ingest-productos", headers=_h(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert body["nuevos_para_revisar"] == 1
    assert body["batch_id"] is not None


def test_ingest_productos_sin_conexion_da_400(admin_token):
    r = client.post("/api/conectores/odoo/ingest-productos", headers=_h(admin_token))
    assert r.status_code == 400
```

- [ ] **Step 21: Run the test to verify it fails**

Run: `cd backend && python -m pytest tests/test_odoo_endpoints.py -k ingest_productos -v`
Expected: FAIL with 404 (route doesn't exist yet)

- [ ] **Step 22: Add the route**

Add to `backend/main.py`, after the existing `odoo_sync_productos` route (around line 1550):

```python
@app.post("/api/conectores/odoo/ingest-productos")
def odoo_ingest_productos(_u: dict = Depends(require_admin)):
    """Ingesta real: los productos de Odoo ya vinculados se actualizan
    directo; los nuevos quedan en un batch de Staging para revisión."""
    from core import odoo_ingest
    try:
        return odoo_ingest.ingest_productos(actor=usuario_actual(_u))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

Check how other admin routes in this file obtain the acting user's name from `_u` (search `usuario_actual` usage nearby, e.g. in the `staging` routes) and match that exact call — the snippet above assumes `usuario_actual(_u)` returns the username string; adjust to match the established pattern if it differs.

- [ ] **Step 23: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_odoo_endpoints.py -k ingest_productos -v`
Expected: PASS

- [ ] **Step 24: Add to `test_authz.py`**

Add to the `CASOS_ADMIN` list in `backend/tests/test_authz.py`, next to the existing `odoo_sync_productos` entry:

```python
    ("odoo_ingest_productos", "POST", "/api/conectores/odoo/ingest-productos"),
```

Run: `cd backend && python -m pytest tests/test_authz.py -v`
Expected: PASS

- [ ] **Step 25: Commit**

```bash
cd backend
git add main.py tests/test_odoo_endpoints.py tests/test_authz.py
git commit -m "Add POST /api/conectores/odoo/ingest-productos endpoint"
```

- [ ] **Step 26: Frontend — API client and i18n**

Add to `frontend/src/lib/api.js`, next to `odooSyncProductos`:

```js
  odooIngestProductos: () => post("/api/conectores/odoo/ingest-productos", {}),
```

Add to `frontend/src/lib/locales/es.js`, in the `odoo.*` block:

```js
  "odoo.ingestar_productos": "Ingestar a PolPilot",
  "odoo.ingestando_productos": "Ingestando…",
  "odoo.ingesta_productos_resultado": "{actualizados} actualizados, {nuevos} nuevos para revisar en Staging.",
  "odoo.ingesta_productos_sin_novedades": "Todo tu catálogo de Odoo ya está al día en PolPilot.",
  "odoo.ver_en_staging": "Ver en Staging",
```

Add the English equivalents to `frontend/src/lib/locales/en.js`:

```js
  "odoo.ingestar_productos": "Ingest into PolPilot",
  "odoo.ingestando_productos": "Ingesting…",
  "odoo.ingesta_productos_resultado": "{actualizados} updated, {nuevos} new pending review in Staging.",
  "odoo.ingesta_productos_sin_novedades": "Your Odoo catalog is already up to date in PolPilot.",
  "odoo.ver_en_staging": "View in Staging",
```

- [ ] **Step 27: Frontend — button in `OdooTabProductos`**

Read `frontend/src/desktop/sections/Conectores.jsx`'s current `OdooTabProductos` component first (it has `sync`/`sincronizando`/`error` state and a `sincronizar` handler calling `api.odooSyncProductos()`). Add ingestion as a second, independent action with its own state, placed right after the existing "Traer productos" button:

```jsx
function OdooTabProductos({ t }) {
  const [sync, setSync] = useState(null);
  const [sincronizando, setSincronizando] = useState(false);
  const [error, setError] = useState(null);
  const [ingesta, setIngesta] = useState(null);
  const [ingestando, setIngestando] = useState(false);
  const [errorIngesta, setErrorIngesta] = useState(null);

  const sincronizar = async () => {
    setSincronizando(true);
    setError(null);
    try {
      setSync(await api.odooSyncProductos());
    } catch {
      setError(t("odoo.error_generico"));
    } finally {
      setSincronizando(false);
    }
  };

  const ingestar = async () => {
    setIngestando(true);
    setErrorIngesta(null);
    try {
      setIngesta(await api.odooIngestProductos());
    } catch {
      setErrorIngesta(t("odoo.error_generico"));
    } finally {
      setIngestando(false);
    }
  };

  return (
    <div className="space-y-3 pt-1">
      <div className="flex flex-wrap items-center gap-2">
        <button onClick={sincronizar} disabled={sincronizando}
          className="rounded-full border border-violeta bg-violeta px-3.5 py-1.5 text-[0.8rem]
                     font-semibold text-crema disabled:opacity-50">
          {sincronizando ? t("odoo.sincronizando_productos") : t("odoo.traer_productos")}
        </button>
        <button onClick={ingestar} disabled={ingestando}
          className="rounded-full border border-violeta px-3.5 py-1.5 text-[0.8rem]
                     font-semibold text-violeta disabled:opacity-50">
          {ingestando ? t("odoo.ingestando_productos") : t("odoo.ingestar_productos")}
        </button>
      </div>
      {error && <p className="text-[0.8rem] text-rojo">{error}</p>}
      {errorIngesta && <p className="text-[0.8rem] text-rojo">{errorIngesta}</p>}
      {ingesta && (
        <p className="text-[0.82rem] text-tinta-suave">
          {ingesta.actualizados > 0 || ingesta.nuevos_para_revisar > 0
            ? t("odoo.ingesta_productos_resultado", { actualizados: ingesta.actualizados, nuevos: ingesta.nuevos_para_revisar })
            : t("odoo.ingesta_productos_sin_novedades")}
          {ingesta.batch_id && (
            <> · <a href="/cargar" className="font-semibold text-violeta underline">{t("odoo.ver_en_staging")}</a></>
          )}
        </p>
      )}
      {sync && (
        <p className="text-[0.82rem] text-tinta-suave">
          {sync.total > 0 ? t("odoo.sync_productos_resultado", { n: sync.total }) : t("odoo.sync_productos_vacio")}
        </p>
      )}
      {sync?.total > 0 && (
        <ul className="max-h-48 space-y-1 overflow-y-auto rounded-xl border border-linea/60
                       bg-papel-hondo/30 p-2 text-[0.8rem]">
          {sync.productos.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-2 text-tinta">
              <span className="min-w-0 truncate">
                {p.codigo && <span className="text-tinta-suave">{p.codigo} · </span>}
                {p.nombre}
                {p.categoria && <span className="text-tinta-suave"> · {p.categoria}</span>}
              </span>
              <span className={`shrink-0 font-semibold ${p.stock > 0 ? "text-tinta" : "text-rojo"}`}>
                {t("odoo.stock_unidades", { n: p.stock })}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

(Verify `/cargar` is still the current route for the Staging review page — check `frontend/src/desktop/DesktopApp.jsx`'s route table before hardcoding it; use whatever it actually is if different.)

- [ ] **Step 28: Manual smoke test**

Start backend (`cd backend && POLPILOT_DEMO_TODAY=2026-07-07 python -m uvicorn main:app --port 8000`) and frontend (`cd frontend && npm run dev`), log in as an admin, go to Conectores → Odoo → Productos tab, click "Ingestar a PolPilot" twice in a row. First click should report N new-for-review with a Staging link; go integrate that batch in `/cargar`; second click should report N updated, 0 new.

- [ ] **Step 29: Commit**

```bash
git add frontend/src/desktop/sections/Conectores.jsx frontend/src/lib/api.js frontend/src/lib/locales/en.js frontend/src/lib/locales/es.js
git commit -m "Add product ingestion UI to Conectores"
```

---

### Task 3: Vendors ingestion

**Files:**
- Modify: `backend/core/proveedores.py` (extend `_CAMPOS`, add `upsert_desde_conector`)
- Modify: `backend/core/staging.py` (add `coerce_proveedor_odoo`, wire into `_COERCERS_ODOO`/`crear_batch_odoo`, add `integrar()` branch)
- Modify: `backend/core/odoo_ingest.py` (add `ingest_proveedores`)
- Modify: `backend/main.py` (add `POST /api/conectores/odoo/ingest-proveedores`)
- Modify: `frontend/src/desktop/sections/Conectores.jsx`, `frontend/src/lib/api.js`, locale files
- Test: `backend/tests/test_proveedores.py` (or wherever `core/proveedores.py`'s existing tests live — check first), `backend/tests/test_staging.py`, `backend/tests/test_odoo_ingest.py`, `backend/tests/test_odoo_endpoints.py`, `backend/tests/test_authz.py`

**Interfaces:**
- Consumes: `conector.pull_proveedores()` → `{"proveedores": [{"id": int, "nombre": str, "cuit": str, "localidad": str, "telefono": str, "email": str}, ...]}` (already exists).
- Produces: `proveedores.upsert_desde_conector(filas: list[dict], actor: str) -> {"nuevos": int, "actualizados": int}`; `staging.coerce_proveedor_odoo(p: dict) -> dict`; `odoo_ingest.ingest_proveedores(actor="dueño") -> {"actualizados": int, "nuevos_para_revisar": int, "batch_id": str|None}`.

- [ ] **Step 1: Read `core/proveedores.py` in full** (already read earlier in this session — `_CAMPOS = ("nombre", "contacto", "telefono", "email", "notas")`, `crear`/`actualizar`/`eliminar`/`listar` operate on the `"proveedores"` apartado via `esquema.filas`/`reemplazar_filas`).

- [ ] **Step 2: Write the failing test**

Find or create `backend/tests/test_proveedores.py` (check `backend/tests/` first for the existing file covering `core/proveedores.py` — follow its fixture pattern for clearing the apartado between tests):

```python
def test_upsert_desde_conector_crea_y_luego_actualiza():
    from core import proveedores
    r1 = proveedores.upsert_desde_conector([
        {"nombre": "Proveedor Odoo Uno", "cuit": "30-1-1", "contacto": "",
         "telefono": "11-0000", "email": "uno@example.com",
         "source": "odoo", "source_id": "701"},
    ], actor="test")
    assert r1 == {"nuevos": 1, "actualizados": 0}
    listado = proveedores.listar()
    creado = next(p for p in listado if p.get("source_id") == "701")
    assert creado["nombre"] == "Proveedor Odoo Uno"

    r2 = proveedores.upsert_desde_conector([
        {"nombre": "Proveedor Odoo Uno", "cuit": "30-1-1", "contacto": "",
         "telefono": "11-9999", "email": "uno@example.com",
         "source": "odoo", "source_id": "701"},
    ], actor="test")
    assert r2 == {"nuevos": 0, "actualizados": 1}
    actualizado = next(p for p in proveedores.listar() if p.get("source_id") == "701")
    assert actualizado["telefono"] == "11-9999"
```

- [ ] **Step 3: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_proveedores.py -k upsert_desde_conector -v`
Expected: FAIL with `AttributeError`

- [ ] **Step 4: Implement `_CAMPOS` extension and `upsert_desde_conector`**

In `backend/core/proveedores.py`, change:

```python
_CAMPOS = ("nombre", "contacto", "telefono", "email", "notas")
```

to:

```python
_CAMPOS = ("nombre", "contacto", "telefono", "email", "notas",
           "cuit", "source", "source_id")
```

Then add, after `eliminar` (end of file):

```python
def upsert_desde_conector(filas: list[dict], actor: str) -> dict:
    """Alta o actualización masiva de proveedores que llegan de un conector
    externo (Odoo), matcheados por (source, source_id) — a diferencia de
    crear()/actualizar() (una ficha a la vez, pensadas para el dueño
    tipeando), esto resuelve el match automáticamente."""
    actuales = esquema.filas(_TIPO)
    por_source = {(f.get("source"), f.get("source_id")): f
                  for f in actuales if f.get("source")}
    nuevos, actualizados = 0, 0
    for entrante in filas:
        key = (entrante.get("source"), entrante.get("source_id"))
        existente = por_source.get(key)
        if existente:
            existente.update({c: entrante.get(c, existente.get(c)) for c in _CAMPOS})
            actualizados += 1
        else:
            fila = {"id": uuid.uuid4().hex[:10], **{c: entrante.get(c, "") for c in _CAMPOS}}
            actuales.append(fila)
            por_source[key] = fila
            nuevos += 1
    esquema.reemplazar_filas(_TIPO, actuales)
    _audit.record(actor, "upsert_proveedores_conector", None,
                  {"nuevos": nuevos, "actualizados": actualizados})
    return {"nuevos": nuevos, "actualizados": actualizados}
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_proveedores.py -k upsert_desde_conector -v`
Expected: PASS. Also run the full file to confirm the `_CAMPOS` change didn't break `crear`/`actualizar`: `cd backend && python -m pytest tests/test_proveedores.py -v` → PASS.

- [ ] **Step 6: Commit**

```bash
cd backend
git add core/proveedores.py tests/test_proveedores.py
git commit -m "Add provenance-tracked vendor upsert for connector ingestion"
```

- [ ] **Step 7: Write the failing Staging test**

Add to `backend/tests/test_staging.py`:

```python
def test_crear_batch_odoo_proveedor_nuevo():
    r = staging.crear_batch_odoo("proveedor", [
        {"id": 801, "nombre": "Proveedor Staging Nuevo", "cuit": "30-2-2",
         "localidad": "Rosario", "telefono": "341-000", "email": "p@example.com"},
    ])
    assert r["tipo"] == "proveedor"
    assert r["total_filas"] == 1
```

- [ ] **Step 8: Run to verify failure, then implement**

Run: `cd backend && python -m pytest tests/test_staging.py -k crear_batch_odoo_proveedor -v`
Expected: FAIL with `ValueError: tipo sin coercer/analizador Odoo: proveedor`

In `backend/core/staging.py`, add after `coerce_producto_odoo`:

```python
def coerce_proveedor_odoo(p: dict) -> dict:
    return {
        "nombre": str(p.get("nombre") or "").strip(),
        "contacto": "",
        "telefono": p.get("telefono") or "",
        "email": p.get("email") or "",
        "notas": "",
        "cuit": p.get("cuit") or "",
        "source": "odoo",
        "source_id": str(p["id"]),
    }


def _analizar_proveedores(filas: list[dict], lang: str | None = None) -> list[dict]:
    from . import proveedores as proveedores_mod
    existentes = {_norm(p["nombre"]) for p in proveedores_mod.listar() if not p.get("source")}
    dups = [i for i, f in enumerate(filas) if _norm(f["nombre"]) in existentes]
    if not dups:
        return []
    return [{
        "id": "duplicado", "tipo": "duplicado",
        "titulo": _t("core.staging.obs_duplicado", lang),
        "descripcion": f"{len(dups)} proveedores parecen ya existir en tu sistema con el mismo nombre.",
        "items": len(dups), "indices": dups, "impacto_pesos": 0,
        "opciones": [{"label": "No agregarlos (ya existen)", "accion": "unificar", "params": {}},
                     {"label": "Agregarlos igual (son distintos)", "accion": "mantener", "params": {}}],
        "resuelta": False, "resolucion": None,
    }]
```

Update `_COERCERS_ODOO` and `crear_batch_odoo`'s branch:

```python
_COERCERS_ODOO = {
    "producto": coerce_producto_odoo,
    "proveedor": coerce_proveedor_odoo,
}
```

```python
    if tipo == "producto":
        observaciones = _analizar(filas)
    elif tipo == "proveedor":
        observaciones = _analizar_proveedores(filas, lang)
    else:
        raise ValueError(f"tipo sin coercer/analizador Odoo: {tipo}")
```

- [ ] **Step 9: Add the `integrar()` branch for vendors**

In `backend/core/staging.py`'s `integrar()`, the existing structure is:

```python
    if tipo != "producto":
        # Tipo nuevo (ventas, clientes, …): crea el apartado y arma las relaciones.
        res = esquema.crear_apartado(tipo, a_integrar)
        ...
```

Insert a new branch before that generic one, so `proveedor` (and, from Task 4/5, `cliente`/`orden_compra`) route to their real modules instead:

```python
    if tipo == "proveedor" and b.get("fuente") == "odoo":
        from . import proveedores as proveedores_mod
        res = proveedores_mod.upsert_desde_conector(a_integrar, actor)
        batches = [x for x in batches if x["id"] != batch_id]
        _save(batches)
        return {"ok": True, "nuevos": res["nuevos"], "tipo": tipo,
                "mensaje": f"{res['nuevos']} proveedores nuevos, {res['actualizados']} actualizados."}

    if tipo != "producto":
        # Tipo nuevo (ventas, clientes, …): crea el apartado y arma las relaciones.
        res = esquema.crear_apartado(tipo, a_integrar)
        ...
```

- [ ] **Step 10: Write the failing full-integration test**

Add to `backend/tests/test_staging.py`:

```python
def test_integrar_batch_odoo_proveedor():
    from core import proveedores
    r = staging.crear_batch_odoo("proveedor", [
        {"id": 802, "nombre": "Proveedor Integrado Odoo", "cuit": "30-3-3",
         "localidad": "", "telefono": "", "email": ""},
    ])
    res = staging.integrar(r["id"], actor="test")
    assert res["ok"] is True
    creado = next(p for p in proveedores.listar() if p.get("source_id") == "802")
    assert creado["nombre"] == "Proveedor Integrado Odoo"
```

- [ ] **Step 11: Run all new staging tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_staging.py -v`
Expected: PASS (all, including the pre-existing ones — confirms Step 9's insertion didn't disturb the generic apartado path used by `venta`/`deposito`/`logistica`).

- [ ] **Step 12: Commit**

```bash
cd backend
git add core/staging.py tests/test_staging.py
git commit -m "Add vendor coercer/analyzer and integrar() routing to Staging Area"
```

- [ ] **Step 13: Add `odoo_ingest.ingest_proveedores`**

Write the failing test first, in `backend/tests/test_odoo_ingest.py` (extend `_FakeModels` to also handle `res.partner` with `supplier_rank`, following the same pattern already used in `test_conectores_odoo.py` for distinguishing customer vs. vendor domains by inspecting the search domain's first element):

```python
def test_ingest_proveedores_primera_vez_todo_va_a_revision():
    r = odoo_ingest.ingest_proveedores(actor="test")
    assert r["nuevos_para_revisar"] >= 1
    assert r["batch_id"] is not None
```

(Extend `_FakeModels.execute_kw` in this file to handle `model == "res.partner"` returning a fixed vendor list for `search`/`read`, mirroring the fixture already built in `tests/test_conectores_odoo.py`'s `_FakeModels` — reuse that exact shape rather than inventing a new one.)

Implement in `backend/core/odoo_ingest.py`:

```python
def ingest_proveedores(actor: str = "dueño") -> dict:
    from . import proveedores as proveedores_mod

    tenant_id = _tenant.current_tenant_id()
    conector = conectores.ConectorOdoo(tenant_id)
    pull = conector.pull_proveedores()

    vinculados = {p["source_id"] for p in proveedores_mod.listar() if p.get("source") == "odoo"}
    nuevas, actualizadas_filas = [], []
    for p in pull["proveedores"]:
        if str(p["id"]) in vinculados:
            actualizadas_filas.append(staging.coerce_proveedor_odoo(p))
        else:
            nuevas.append(p)

    if actualizadas_filas:
        proveedores_mod.upsert_desde_conector(actualizadas_filas, actor)

    batch_id = None
    if nuevas:
        r = staging.crear_batch_odoo("proveedor", nuevas, nombre="Odoo · proveedores")
        batch_id = r["id"]

    return {"actualizados": len(actualizadas_filas), "nuevos_para_revisar": len(nuevas), "batch_id": batch_id}
```

Run: `cd backend && python -m pytest tests/test_odoo_ingest.py -v`
Expected: PASS

- [ ] **Step 14: Commit**

```bash
cd backend
git add core/odoo_ingest.py tests/test_odoo_ingest.py
git commit -m "Add vendor ingestion orchestration"
```

- [ ] **Step 15: Add the route, authz entry, and frontend wiring**

Follow Task 2 Steps 20-29 exactly, substituting `productos` → `proveedores` throughout: new route `POST /api/conectores/odoo/ingest-proveedores` in `main.py` calling `odoo_ingest.ingest_proveedores`, a `test_odoo_endpoints.py` pair of tests, a `test_authz.py` entry, `api.js`'s `odooIngestProveedores`, the four `odoo.ingestar_proveedores`/etc. i18n keys (es/en), and a second button in `OdooTabProveedores` mirroring Task 2 Step 27's JSX exactly (state variables renamed `ingesta`/`ingestando`/`errorIngesta`, same structure, calling `api.odooIngestProveedores()`).

Run: `cd backend && python -m pytest tests/test_odoo_endpoints.py tests/test_authz.py -v`
Expected: PASS

- [ ] **Step 16: Manual smoke test**

Same as Task 2 Step 28, on the Proveedores tab.

- [ ] **Step 17: Commit**

```bash
git add backend/main.py backend/tests/test_odoo_endpoints.py backend/tests/test_authz.py frontend/src/desktop/sections/Conectores.jsx frontend/src/lib/api.js frontend/src/lib/locales/en.js frontend/src/lib/locales/es.js
git commit -m "Add vendor ingestion endpoint and UI"
```

---

### Task 4: Customer accounts ingestion

**Files:**
- Modify: `backend/core/db/customer_accounts_repo.py` (extend columns)
- Modify: `backend/core/staging.py` (add `coerce_cliente_odoo`, `_analizar_clientes`, wire into `_COERCERS_ODOO`/`crear_batch_odoo`, add `integrar()` branch)
- Modify: `backend/core/odoo_ingest.py` (add `ingest_clientes`)
- Modify: `backend/main.py` (add `POST /api/conectores/odoo/ingest-contactos`)
- Modify: `frontend/src/desktop/sections/Conectores.jsx`, `frontend/src/lib/api.js`, locale files
- Test: `backend/tests/test_customer_accounts_repo.py` (check exact filename first), `backend/tests/test_staging.py`, `backend/tests/test_odoo_ingest.py`, `backend/tests/test_odoo_endpoints.py`, `backend/tests/test_authz.py`

**Interfaces:**
- Consumes: `conector.pull_data()` → `{"clientes": [{"id": int, "nombre": str, "cuit": str, "localidad": str, "telefono": str, "email": str}, ...]}` (already exists, this is the "Contactos" pull).
- Produces: `customer_accounts_repo.list_accounts`/`upsert_account` extended to carry `vat, city, phone, email, source, source_id`; `staging.coerce_cliente_odoo(c: dict) -> dict`; `odoo_ingest.ingest_clientes(actor="dueño") -> {"actualizados": int, "nuevos_para_revisar": int, "batch_id": str|None}`.

- [ ] **Step 1: Write the failing repo test**

Find `backend/tests/` for the file testing `core/db/customer_accounts_repo.py` (check filenames — likely `test_customer_accounts_repo.py`; read its existing fixture/cleanup pattern first) and add:

```python
def test_upsert_account_persiste_campos_de_contacto_y_source(tenant_id):
    from core.db import customer_accounts_repo
    customer_accounts_repo.upsert_account(tenant_id, {
        "id": "odoo-901", "nombre": "Cliente Odoo", "saldo": 0, "limite_credito": 0,
        "plazo_dias": 30, "dias_sin_pagar": 0, "promedio_pago_dias": None,
        "vat": "20-1-1", "city": "CABA", "phone": "11-0000", "email": "c@example.com",
        "source": "odoo", "source_id": "901",
    })
    cuentas = customer_accounts_repo.list_accounts(tenant_id)
    c = next(x for x in cuentas if x["id"] == "odoo-901")
    assert c["vat"] == "20-1-1"
    assert c["source"] == "odoo" and c["source_id"] == "901"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_customer_accounts_repo.py -k source -v`
Expected: FAIL (either `KeyError` on `account["vat"]` inside `upsert_account`, or the returned dict lacking `vat`/`source` keys — either way, a clear failure pointing at the missing columns).

- [ ] **Step 3: Extend `customer_accounts_repo.py`**

Replace the whole file's `_ACCOUNT_COLS`, `list_accounts`, and `upsert_account`:

```python
_ACCOUNT_COLS = ("id, name, balance, credit_limit, payment_term_days, days_overdue, "
                  "average_payment_days, vat, city, phone, email, source, source_id")


def list_accounts(tenant_id: str) -> list[dict]:
    with tenant_connection(tenant_id) as conn:
        accounts = conn.execute(
            text(f"SELECT {_ACCOUNT_COLS} FROM customer_accounts ORDER BY id")
        ).mappings().all()
        movements = conn.execute(
            text("SELECT customer_id, date, type, amount, description FROM account_movements ORDER BY date")
        ).mappings().all()

    by_account: dict[str, list[dict]] = {}
    for m in movements:
        by_account.setdefault(m["customer_id"], []).append({
            "fecha": m["date"].isoformat(),
            "tipo": m["type"],
            "monto": float(m["amount"]),
            "detalle": m["description"],
        })

    return [
        {
            "id": a["id"],
            "nombre": a["name"],
            "saldo": float(a["balance"]),
            "limite_credito": float(a["credit_limit"]),
            "plazo_dias": a["payment_term_days"],
            "dias_sin_pagar": a["days_overdue"],
            "promedio_pago_dias": a["average_payment_days"],
            "vat": a["vat"],
            "city": a["city"],
            "phone": a["phone"],
            "email": a["email"],
            "source": a["source"],
            "source_id": a["source_id"],
            "movimientos": by_account.get(a["id"], []),
        }
        for a in accounts
    ]


def upsert_account(tenant_id: str, account: dict) -> None:
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "INSERT INTO customer_accounts "
                "(tenant_id, id, name, balance, credit_limit, payment_term_days, days_overdue, "
                "average_payment_days, vat, city, phone, email, source, source_id) "
                "VALUES (:tid, :id, :name, :balance, :credit_limit, :payment_term_days, :days_overdue, "
                ":average_payment_days, :vat, :city, :phone, :email, :source, :source_id) "
                "ON CONFLICT (tenant_id, id) DO UPDATE SET "
                "name = EXCLUDED.name, balance = EXCLUDED.balance, credit_limit = EXCLUDED.credit_limit, "
                "payment_term_days = EXCLUDED.payment_term_days, days_overdue = EXCLUDED.days_overdue, "
                "average_payment_days = EXCLUDED.average_payment_days, "
                "vat = EXCLUDED.vat, city = EXCLUDED.city, phone = EXCLUDED.phone, "
                "email = EXCLUDED.email, source = EXCLUDED.source, source_id = EXCLUDED.source_id"
            ),
            {
                "tid": tenant_id,
                "id": account["id"],
                "name": account["nombre"],
                "balance": account["saldo"],
                "credit_limit": account.get("limite_credito", 0),
                "payment_term_days": account.get("plazo_dias", 30),
                "days_overdue": account.get("dias_sin_pagar", 0),
                "average_payment_days": account.get("promedio_pago_dias"),
                "vat": account.get("vat"),
                "city": account.get("city"),
                "phone": account.get("phone"),
                "email": account.get("email"),
                "source": account.get("source"),
                "source_id": account.get("source_id"),
            },
        )
```

(`add_movement` and `seed_if_empty` are unchanged — `_ACCOUNT_COLS` is now a plain string built with parens for readability, still interpolates the same way into the f-string `SELECT` calls.)

- [ ] **Step 4: Run to verify it passes, plus the full existing suite for this repo**

Run: `cd backend && python -m pytest tests/test_customer_accounts_repo.py -v`
Expected: PASS (all, including pre-existing tests — confirms `account.get("vat")` etc. defaulting to `None` doesn't break accounts created without those keys, e.g. the demo seed in `core/cuentas.py`'s `_SEED`).

Also run: `cd backend && python -m pytest tests/test_ver_como.py tests/test_p25.py -v` (or whichever existing suites exercise `core/cuentas.py` most — check `grep -rl "cuentas\." backend/tests/` if unsure which files to target) to confirm nothing that reads a customer account dict broke from the new keys always being present.

- [ ] **Step 5: Commit**

```bash
cd backend
git add core/db/customer_accounts_repo.py tests/test_customer_accounts_repo.py
git commit -m "Add contact and provenance columns to customer_accounts_repo"
```

- [ ] **Step 6: Staging coercer, analyzer, and `integrar()` branch — write failing tests first**

Add to `backend/tests/test_staging.py`:

```python
def test_crear_batch_odoo_cliente_nuevo():
    r = staging.crear_batch_odoo("cliente", [
        {"id": 901, "nombre": "Cliente Staging Nuevo", "cuit": "20-4-4",
         "localidad": "CABA", "telefono": "11-000", "email": "cl@example.com"},
    ])
    assert r["tipo"] == "cliente"
    assert r["total_filas"] == 1


def test_integrar_batch_odoo_cliente():
    from core import cuentas
    r = staging.crear_batch_odoo("cliente", [
        {"id": 902, "nombre": "Cliente Integrado Odoo", "cuit": "20-5-5",
         "localidad": "", "telefono": "", "email": ""},
    ])
    res = staging.integrar(r["id"], actor="test")
    assert res["ok"] is True
    creado = next(c for c in cuentas.listar() if c.get("source_id") == "902")
    assert creado["nombre"] == "Cliente Integrado Odoo"
    assert creado["saldo"] == 0
```

- [ ] **Step 7: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_staging.py -k "crear_batch_odoo_cliente or integrar_batch_odoo_cliente" -v`
Expected: FAIL with `ValueError: tipo sin coercer/analizador Odoo: cliente`

- [ ] **Step 8: Implement**

In `backend/core/staging.py`, add after `coerce_proveedor_odoo`/`_analizar_proveedores`:

```python
def coerce_cliente_odoo(c: dict) -> dict:
    return {
        "id": f"odoo-{c['id']}",
        "nombre": str(c.get("nombre") or "").strip(),
        "saldo": 0, "limite_credito": 0, "plazo_dias": 30,
        "dias_sin_pagar": 0, "promedio_pago_dias": None,
        "vat": c.get("cuit") or "", "city": c.get("localidad") or "",
        "phone": c.get("telefono") or "", "email": c.get("email") or "",
        "source": "odoo", "source_id": str(c["id"]),
    }


def _analizar_clientes(filas: list[dict], lang: str | None = None) -> list[dict]:
    from . import cuentas as cuentas_mod
    existentes = {_norm(c["nombre"]) for c in cuentas_mod.listar() if not c.get("source")}
    dups = [i for i, f in enumerate(filas) if _norm(f["nombre"]) in existentes]
    if not dups:
        return []
    return [{
        "id": "duplicado", "tipo": "duplicado",
        "titulo": _t("core.staging.obs_duplicado", lang),
        "descripcion": f"{len(dups)} clientes parecen ya existir en tu sistema con el mismo nombre.",
        "items": len(dups), "indices": dups, "impacto_pesos": 0,
        "opciones": [{"label": "No agregarlos (ya existen)", "accion": "unificar", "params": {}},
                     {"label": "Agregarlos igual (son distintos)", "accion": "mantener", "params": {}}],
        "resuelta": False, "resolucion": None,
    }]
```

Update `_COERCERS_ODOO` and `crear_batch_odoo`:

```python
_COERCERS_ODOO = {
    "producto": coerce_producto_odoo,
    "proveedor": coerce_proveedor_odoo,
    "cliente": coerce_cliente_odoo,
}
```

```python
    if tipo == "producto":
        observaciones = _analizar(filas)
    elif tipo == "proveedor":
        observaciones = _analizar_proveedores(filas, lang)
    elif tipo == "cliente":
        observaciones = _analizar_clientes(filas, lang)
    else:
        raise ValueError(f"tipo sin coercer/analizador Odoo: {tipo}")
```

In `integrar()`, add a branch alongside the `proveedor` one from Task 3 Step 9:

```python
    if tipo == "cliente" and b.get("fuente") == "odoo":
        from core.db import customer_accounts_repo
        for f in a_integrar:
            customer_accounts_repo.upsert_account(_tenant_id_actual(), f)
        batches = [x for x in batches if x["id"] != batch_id]
        _save(batches)
        return {"ok": True, "nuevos": len(a_integrar), "tipo": tipo,
                "mensaje": f"{len(a_integrar)} clientes nuevos."}
```

`customer_accounts_repo.upsert_account` needs a `tenant_id` — `core/staging.py` doesn't currently import `core.db.tenant`; add this small helper near the top of the file (after the existing imports) and use it here:

```python
def _tenant_id_actual() -> str:
    from core.db import tenant as _tenant
    return _tenant.current_tenant_id()
```

- [ ] **Step 9: Run to verify tests pass**

Run: `cd backend && python -m pytest tests/test_staging.py -v`
Expected: PASS (all)

- [ ] **Step 10: Commit**

```bash
cd backend
git add core/staging.py tests/test_staging.py
git commit -m "Add customer coercer/analyzer and integrar() routing to Staging Area"
```

- [ ] **Step 11: `odoo_ingest.ingest_clientes`, route, authz, frontend**

Same pattern as Task 3 Steps 13-17, substituting `proveedores`/`pull_proveedores` → `clientes`/`pull_data` (note: the *existing* preview endpoint for contacts is `sync`, not `sync-contactos` — the new ingestion endpoint should be `ingest-contactos` per the spec's API surface list, even though the underlying connector call is `pull_data()`). Add to `backend/core/odoo_ingest.py`:

```python
def ingest_clientes(actor: str = "dueño") -> dict:
    from core import cuentas

    tenant_id = _tenant.current_tenant_id()
    conector = conectores.ConectorOdoo(tenant_id)
    pull = conector.pull_data()

    vinculados = {c["source_id"] for c in cuentas.listar() if c.get("source") == "odoo"}
    nuevas, actualizadas_filas = [], []
    for c in pull["clientes"]:
        if str(c["id"]) in vinculados:
            actualizadas_filas.append(staging.coerce_cliente_odoo(c))
        else:
            nuevas.append(c)

    if actualizadas_filas:
        from core.db import customer_accounts_repo
        for f in actualizadas_filas:
            customer_accounts_repo.upsert_account(tenant_id, f)

    batch_id = None
    if nuevas:
        r = staging.crear_batch_odoo("cliente", nuevas, nombre="Odoo · contactos")
        batch_id = r["id"]

    return {"actualizados": len(actualizadas_filas), "nuevos_para_revisar": len(nuevas), "batch_id": batch_id}
```

Write the failing test in `test_odoo_ingest.py` first (extend `_FakeModels` for `res.partner` with `customer_rank`, reusing `test_conectores_odoo.py`'s existing fixture shape), then confirm it passes.

Add the route to `main.py`:

```python
@app.post("/api/conectores/odoo/ingest-contactos")
def odoo_ingest_contactos(_u: dict = Depends(require_admin)):
    """Ingesta real: los clientes de Odoo ya vinculados se actualizan
    directo; los nuevos quedan en un batch de Staging para revisión."""
    from core import odoo_ingest
    try:
        return odoo_ingest.ingest_clientes(actor=usuario_actual(_u))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

Add the `test_authz.py` entry (`("odoo_ingest_contactos", "POST", "/api/conectores/odoo/ingest-contactos")`), the `test_odoo_endpoints.py` pair of tests, `api.js`'s `odooIngestContactos`, the i18n keys, and the second button in `OdooTabContactos` — following Task 2 Steps 20-27 exactly.

Run: `cd backend && python -m pytest tests/test_odoo_ingest.py tests/test_odoo_endpoints.py tests/test_authz.py -v`
Expected: PASS

- [ ] **Step 12: Manual smoke test**

Same as Task 2 Step 28, on the Contactos tab.

- [ ] **Step 13: Commit**

```bash
git add backend/core/odoo_ingest.py backend/main.py backend/tests/test_odoo_ingest.py backend/tests/test_odoo_endpoints.py backend/tests/test_authz.py frontend/src/desktop/sections/Conectores.jsx frontend/src/lib/api.js frontend/src/lib/locales/en.js frontend/src/lib/locales/es.js
git commit -m "Add customer account ingestion endpoint and UI"
```

---

### Task 5: Purchase orders ingestion

**Files:**
- Modify: `backend/core/db/purchase_orders_repo.py` (extend `_COLS`, `_to_orden`, add `upsert_from_odoo`)
- Modify: `backend/core/staging.py` (add `coerce_orden_compra_odoo`, `_analizar_ordenes_compra`, wire into `_COERCERS_ODOO`/`crear_batch_odoo`, add `integrar()` branch)
- Modify: `backend/core/odoo_ingest.py` (add `ingest_ordenes_compra`)
- Modify: `backend/main.py` (add `POST /api/conectores/odoo/ingest-ordenes-compra`)
- Modify: `frontend/src/desktop/sections/Conectores.jsx`, `frontend/src/lib/api.js`, locale files
- Test: `backend/tests/test_purchase_orders_repo.py`, `backend/tests/test_staging.py`, `backend/tests/test_odoo_ingest.py`, `backend/tests/test_odoo_endpoints.py`, `backend/tests/test_authz.py`

**Interfaces:**
- Consumes: `conector.pull_ordenes_compra()` → `{"ordenes": [{"id": int, "numero": str, "proveedor": str, "estado": str, "fecha": str, "total": float, "items": [{"producto": str, "cantidad": float, "precio_unitario": float}, ...]}, ...]}` (already exists; `estado` is already the Spanish-mapped label — "borrador"/"enviada"/"confirmada"/"cerrada"/"cancelada" — per `ConectorOdoo.pull_ordenes_compra`'s existing `_ESTADOS` dict).
- Produces: `purchase_orders_repo.upsert_from_odoo(tenant_id: str, orden: dict) -> None`; `staging.coerce_orden_compra_odoo(o: dict) -> dict`; `odoo_ingest.ingest_ordenes_compra(actor="dueño") -> {"actualizados": int, "nuevos_para_revisar": int, "batch_id": str|None}`.

**Note on state mapping:** the spec calls for keeping "Odoo's raw state" in `source_status` alongside the mapped `status`. `ConectorOdoo.pull_ordenes_compra()` already translates Odoo's raw English state (draft/sent/purchase/done/cancel) into a Spanish label (borrador/enviada/confirmada/cerrada/cancelada) before this pipeline ever sees it — there's no separate raw-English value available without also changing the connector. This task stores that Spanish label as `source_status` (still fully traceable to what the connector reported, just not the pre-translation English word) and maps *that* into PolPilot's own workflow `status` — the mapping table below is unchanged in outcome.

- [ ] **Step 1: Write the failing repo test**

Add to `backend/tests/test_purchase_orders_repo.py`:

```python
def test_upsert_from_odoo_crea_y_luego_actualiza_por_number(tenant_id):
    from core.db import purchase_orders_repo
    orden = {
        "numero": "P00099", "fecha": "2026-08-20", "proveedor": "Proveedor Odoo",
        "estado": "borrador", "items": [{"producto": "X", "cantidad": 5, "precio_unitario": 10}],
        "source_id": "77", "source_status": "borrador",
    }
    purchase_orders_repo.upsert_from_odoo(tenant_id, orden)
    creada = purchase_orders_repo.find_by_number(tenant_id, "P00099")
    assert creada["estado"] == "borrador"
    assert creada["source"] == "odoo" and creada["source_id"] == "77"

    orden["estado"] = "aprobada"
    orden["source_status"] = "confirmada"
    purchase_orders_repo.upsert_from_odoo(tenant_id, orden)
    actualizada = purchase_orders_repo.find_by_number(tenant_id, "P00099")
    assert actualizada["estado"] == "aprobada"
    todas = purchase_orders_repo.list_orders(tenant_id)
    assert sum(1 for o in todas if o["numero"] == "P00099") == 1
```

(Check `test_purchase_orders_repo.py`'s existing fixtures for how `tenant_id` is provided — reuse that, don't invent a new fixture.)

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_purchase_orders_repo.py -k upsert_from_odoo -v`
Expected: FAIL with `AttributeError`

- [ ] **Step 3: Implement in `purchase_orders_repo.py`**

Change:

```python
_COLS = ("number", "date", "supplier", "status", "origin", "reason",
         "prepared_by", "approved_by", "prepared_at", "items", "location")
```

to:

```python
_COLS = ("number", "date", "supplier", "status", "origin", "reason",
         "prepared_by", "approved_by", "prepared_at", "items", "location",
         "source", "source_id", "source_status")
```

Update `_to_orden` to include the three new keys:

```python
def _to_orden(row) -> dict:
    return {
        "numero": row["number"],
        "fecha": row["date"].isoformat(),
        "proveedor": row["supplier"],
        "estado": row["status"],
        "origen": row["origin"],
        "motivo": row["reason"],
        "preparada_por": row["prepared_by"],
        "aprobada_por": row["approved_by"],
        "preparada": to_local_iso(row["prepared_at"]),
        "items": row["items"],
        "ubicacion_entrega": row["location"],
        "source": row["source"],
        "source_id": row["source_id"],
        "source_status": row["source_status"],
    }
```

Add, after `create`:

```python
def find_by_number(tenant_id: str, number: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(f"SELECT {', '.join(_COLS)} FROM purchase_orders WHERE number = :number"),
            {"number": number},
        ).mappings().first()
    return _to_orden(row) if row else None


def upsert_from_odoo(tenant_id: str, orden: dict) -> None:
    """Create-or-update a purchase order by its number — Odoo ingestion
    (core/odoo_ingest.py) uses this to stay idempotent across re-syncs.
    (tenant_id, number) is already this table's primary key (0009), and
    Odoo's own PO numbers (e.g. "P00006") never collide with
    PolPilot-originated ones (e.g. "OC-2026-0901"), so no extra index or
    lookup by source_id is needed — ON CONFLICT on number is enough."""
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "INSERT INTO purchase_orders "
                "(tenant_id, number, date, supplier, status, origin, reason, "
                "prepared_by, approved_by, prepared_at, items, location, "
                "source, source_id, source_status) "
                "VALUES (:tid, :number, :date, :supplier, :status, :origin, :reason, "
                ":prepared_by, :approved_by, :prepared_at, :items, :location, "
                ":source, :source_id, :source_status) "
                "ON CONFLICT (tenant_id, number) DO UPDATE SET "
                "status = EXCLUDED.status, source_status = EXCLUDED.source_status, "
                "supplier = EXCLUDED.supplier, items = EXCLUDED.items, date = EXCLUDED.date"
            ),
            {
                "tid": tenant_id,
                "number": orden["numero"],
                "date": orden["fecha"],
                "supplier": orden["proveedor"],
                "status": orden["estado"],
                "origin": "odoo",
                "reason": None,
                "prepared_by": "Odoo",
                "approved_by": "Odoo",
                "prepared_at": datetime.datetime.now().astimezone(),
                "items": json.dumps(orden["items"]),
                "location": None,
                "source": "odoo",
                "source_id": orden["source_id"],
                "source_status": orden["source_status"],
            },
        )
```

- [ ] **Step 4: Run to verify it passes, and the full existing file**

Run: `cd backend && python -m pytest tests/test_purchase_orders_repo.py -v`
Expected: PASS (all — confirms `create()` and `find_draft()`, which build/read `_COLS`-shaped rows without setting `source`/`source_id`/`source_status`, still work with those three columns defaulting to `NULL`).

- [ ] **Step 5: Commit**

```bash
cd backend
git add core/db/purchase_orders_repo.py tests/test_purchase_orders_repo.py
git commit -m "Add source-aware upsert-by-number to purchase_orders_repo"
```

- [ ] **Step 6: Staging coercer, analyzer, and `integrar()` branch**

Write the failing tests first, in `backend/tests/test_staging.py`:

```python
def test_crear_batch_odoo_orden_compra_nueva():
    r = staging.crear_batch_odoo("orden_compra", [
        {"id": 1001, "numero": "P00201", "proveedor": "Proveedor X", "estado": "confirmada",
         "fecha": "2026-08-20", "total": 500.0,
         "items": [{"producto": "Y", "cantidad": 2, "precio_unitario": 250.0}]},
    ])
    assert r["tipo"] == "orden_compra"
    assert r["total_filas"] == 1
    assert r["observaciones"] == []


def test_integrar_batch_odoo_orden_compra():
    from core.db import purchase_orders_repo, tenant as _tenant
    r = staging.crear_batch_odoo("orden_compra", [
        {"id": 1002, "numero": "P00202", "proveedor": "Proveedor Y", "estado": "cerrada",
         "fecha": "2026-08-15", "total": 300.0,
         "items": [{"producto": "Z", "cantidad": 1, "precio_unitario": 300.0}]},
    ])
    res = staging.integrar(r["id"], actor="test")
    assert res["ok"] is True
    creada = purchase_orders_repo.find_by_number(_tenant.current_tenant_id(), "P00202")
    assert creada["estado"] == "recibida"  # "cerrada" (Odoo) -> "recibida" (PolPilot)
    assert creada["source_status"] == "cerrada"
```

Run: `cd backend && python -m pytest tests/test_staging.py -k orden_compra -v`
Expected: FAIL with `ValueError: tipo sin coercer/analizador Odoo: orden_compra`

Implement in `backend/core/staging.py`, after `_analizar_clientes`:

```python
_ESTADO_ORDEN_COMPRA_ODOO = {
    "borrador": "borrador", "enviada": "borrador",
    "confirmada": "aprobada", "cerrada": "recibida", "cancelada": "cancelada",
}


def coerce_orden_compra_odoo(o: dict) -> dict:
    estado_odoo = o.get("estado") or "borrador"
    return {
        "numero": o.get("numero") or "",
        "proveedor": o.get("proveedor") or "",
        "fecha": o.get("fecha") or "",
        "total": o.get("total") or 0,
        "items": o.get("items") or [],
        "estado": _ESTADO_ORDEN_COMPRA_ODOO.get(estado_odoo, "borrador"),
        "source": "odoo",
        "source_id": str(o["id"]),
        "source_status": estado_odoo,
    }


def _analizar_ordenes_compra(filas: list[dict], lang: str | None = None) -> list[dict]:
    # Sin heurística de duplicado: una orden de compra de Odoo no colisiona
    # por nombre con nada hand-entered — el número de Odoo (source_id) ya es
    # la clave, y crear_batch_odoo sólo recibe filas sin ese vínculo todavía.
    return []
```

Update `_COERCERS_ODOO` and `crear_batch_odoo`:

```python
_COERCERS_ODOO = {
    "producto": coerce_producto_odoo,
    "proveedor": coerce_proveedor_odoo,
    "cliente": coerce_cliente_odoo,
    "orden_compra": coerce_orden_compra_odoo,
}
```

```python
    if tipo == "producto":
        observaciones = _analizar(filas)
    elif tipo == "proveedor":
        observaciones = _analizar_proveedores(filas, lang)
    elif tipo == "cliente":
        observaciones = _analizar_clientes(filas, lang)
    elif tipo == "orden_compra":
        observaciones = _analizar_ordenes_compra(filas, lang)
    else:
        raise ValueError(f"tipo sin coercer/analizador Odoo: {tipo}")
```

Add the `integrar()` branch, alongside `cliente`'s (Task 4 Step 8) and `proveedor`'s (Task 3 Step 9):

```python
    if tipo == "orden_compra" and b.get("fuente") == "odoo":
        from core.db import purchase_orders_repo
        tid = _tenant_id_actual()
        for f in a_integrar:
            purchase_orders_repo.upsert_from_odoo(tid, f)
        batches = [x for x in batches if x["id"] != batch_id]
        _save(batches)
        return {"ok": True, "nuevos": len(a_integrar), "tipo": tipo,
                "mensaje": f"{len(a_integrar)} órdenes de compra nuevas."}
```

- [ ] **Step 7: Run to verify they pass**

Run: `cd backend && python -m pytest tests/test_staging.py -v`
Expected: PASS (all)

- [ ] **Step 8: Commit**

```bash
cd backend
git add core/staging.py tests/test_staging.py
git commit -m "Add purchase order coercer and integrar() routing to Staging Area"
```

- [ ] **Step 9: `odoo_ingest.ingest_ordenes_compra`, route, authz, frontend**

Add to `backend/core/odoo_ingest.py`:

```python
def ingest_ordenes_compra(actor: str = "dueño") -> dict:
    from core.db import purchase_orders_repo, tenant as _tenant_db

    tenant_id = _tenant.current_tenant_id()
    conector = conectores.ConectorOdoo(tenant_id)
    pull = conector.pull_ordenes_compra()

    vinculadas = {o["source_id"] for o in purchase_orders_repo.list_orders(tenant_id)
                  if o.get("source") == "odoo"}
    nuevas, actualizadas = [], 0
    for o in pull["ordenes"]:
        if str(o["id"]) in vinculadas:
            purchase_orders_repo.upsert_from_odoo(tenant_id, staging.coerce_orden_compra_odoo(o))
            actualizadas += 1
        else:
            nuevas.append(o)

    batch_id = None
    if nuevas:
        r = staging.crear_batch_odoo("orden_compra", nuevas, nombre="Odoo · órdenes de compra")
        batch_id = r["id"]

    return {"actualizados": actualizadas, "nuevos_para_revisar": len(nuevas), "batch_id": batch_id}
```

(The `tenant as _tenant_db` import above is unused if `_tenant.current_tenant_id()` — already imported at module level — covers it; drop the redundant import when writing the file, keep only what's actually referenced.)

Write the failing test in `test_odoo_ingest.py` first (extend `_FakeModels` for `purchase.order`/`purchase.order.line`, reusing `test_conectores_odoo.py`'s existing fixture shape for those two models), then confirm it passes.

Add the route to `main.py`:

```python
@app.post("/api/conectores/odoo/ingest-ordenes-compra")
def odoo_ingest_ordenes_compra(_u: dict = Depends(require_admin)):
    """Ingesta real: las órdenes de compra de Odoo ya vinculadas se
    actualizan directo; las nuevas quedan en un batch de Staging."""
    from core import odoo_ingest
    try:
        return odoo_ingest.ingest_ordenes_compra(actor=usuario_actual(_u))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

Add the `test_authz.py` entry, the `test_odoo_endpoints.py` pair of tests, `api.js`'s `odooIngestOrdenesCompra`, the i18n keys, and the second button in `OdooTabCompras` — following Task 2 Steps 20-27's pattern (note `OdooTabCompras` renders a richer list with nested items than `OdooTabProductos`; add the ingest button/result block the same way, without altering the existing `<ul>` rendering block).

Run: `cd backend && python -m pytest tests/test_odoo_ingest.py tests/test_odoo_endpoints.py tests/test_authz.py -v`
Expected: PASS

- [ ] **Step 10: Manual smoke test**

Same as Task 2 Step 28, on the Compras tab — additionally verify a re-sync after manually changing an order's state in the odoo-demo instance (e.g. confirm a draft PO in Odoo's UI, then re-run ingestion) updates `estado` in PolPilot without creating a duplicate row.

- [ ] **Step 11: Full regression run**

Run: `cd backend && python -m pytest`
Expected: all pass except the pre-existing unrelated skips (per `backend/CLAUDE.md`'s note on `conftest.py`'s documented skips).

Run: `git checkout -- data-demo/` (tests write into the data dir — restore seeds per `backend/CLAUDE.md`).

- [ ] **Step 12: Commit**

```bash
git add backend/core/odoo_ingest.py backend/main.py backend/tests/test_odoo_ingest.py backend/tests/test_odoo_endpoints.py backend/tests/test_authz.py frontend/src/desktop/sections/Conectores.jsx frontend/src/lib/api.js frontend/src/lib/locales/en.js frontend/src/lib/locales/es.js
git commit -m "Add purchase order ingestion endpoint and UI"
```
