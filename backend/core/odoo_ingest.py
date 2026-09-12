"""
core/odoo_ingest.py — orchestrates the pull from Odoo into PolPilot's real
data (unlike conectores.ConectorOdoo.pull_*, which only fetches the
read-only preview).

Two-tier: for every row coming from Odoo, if it is already linked to a
PolPilot record (same source_id) it is updated directly, with no review —
Odoo already owns that data. If it is new, it goes into a Staging Area
batch (core/staging.py) so the dueño reviews/approves it before it is
created — a customer/vendor/product/order is never created blindly.
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


def ingest_ordenes_compra(actor: str = "dueño") -> dict:
    from core.db import purchase_orders_repo

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
