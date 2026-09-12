"""
core/odoo_ingest.py — orchestrates the pull from Odoo into PolPilot's real
data (unlike conectores.ConectorOdoo.pull_*, which only fetches the
read-only preview).

Two-tier: for every row coming from Odoo, if it is already linked to a
PolPilot record (same source_id) it is updated directly, with no review —
Odoo already owns that data. If it is new, it goes into a Staging Area
batch (core/staging.py) so the dueño reviews/approves it before it is
created — a customer/vendor/product/order is never created blindly.

Malformed-row protection on the auto-upsert tier: `staging.crear_batch_odoo`
already drops any staged row missing its `_REQUERIDO_ODOO` field before it
can be created. The auto-upsert tier (already-linked records, this module)
reuses that same mapping so a row that lost its required field in Odoo
(e.g. an emptied-out name) is skipped — not written — instead of blanking
the PolPilot record. Skipped rows are counted, never hard-failed, matching
the staging tier's tolerance.
"""
from __future__ import annotations

from . import conectores, staging, store
from .audit import AuditLog
from .db import tenant as _tenant

_audit = AuditLog()


def ingest_productos(actor: str = "dueño") -> dict:
    tenant_id = _tenant.current_tenant_id()
    conector = conectores.ConectorOdoo(tenant_id)
    pull = conector.pull_productos()

    vinculados = {d["source_id"] for d in store.raw_actual() if d.get("source") == "odoo"}
    nuevas, actualizadas, omitidas = [], 0, 0
    for p in pull["productos"]:
        if str(p["id"]) in vinculados:
            fila = staging.coerce_producto_odoo(p)
            if not fila.get(staging._REQUERIDO_ODOO["producto"]):
                omitidas += 1
                continue
            store.upsert_desde_conector(fila, actor)
            actualizadas += 1
        else:
            nuevas.append(p)

    batch_id = None
    if nuevas:
        r = staging.crear_batch_odoo("producto", nuevas, nombre="Odoo · productos")
        batch_id = r["id"]

    return {"actualizados": actualizadas, "nuevos_para_revisar": len(nuevas),
            "omitidos_malformados": omitidas, "batch_id": batch_id}


def ingest_proveedores(actor: str = "dueño") -> dict:
    from . import proveedores as proveedores_mod

    tenant_id = _tenant.current_tenant_id()
    conector = conectores.ConectorOdoo(tenant_id)
    pull = conector.pull_proveedores()

    vinculados = {p["source_id"] for p in proveedores_mod.listar() if p.get("source") == "odoo"}
    nuevas, actualizadas_filas, omitidas = [], [], 0
    for p in pull["proveedores"]:
        if str(p["id"]) in vinculados:
            fila = staging.coerce_proveedor_odoo(p)
            if not fila.get(staging._REQUERIDO_ODOO["proveedor"]):
                omitidas += 1
                continue
            actualizadas_filas.append(fila)
        else:
            nuevas.append(p)

    if actualizadas_filas:
        proveedores_mod.upsert_desde_conector(actualizadas_filas, actor)

    batch_id = None
    if nuevas:
        r = staging.crear_batch_odoo("proveedor", nuevas, nombre="Odoo · proveedores")
        batch_id = r["id"]

    return {"actualizados": len(actualizadas_filas), "nuevos_para_revisar": len(nuevas),
            "omitidos_malformados": omitidas, "batch_id": batch_id}


def ingest_clientes(actor: str = "dueño") -> dict:
    from core import cuentas

    tenant_id = _tenant.current_tenant_id()
    conector = conectores.ConectorOdoo(tenant_id)
    pull = conector.pull_data()

    vinculados = {c["source_id"] for c in cuentas.listar() if c.get("source") == "odoo"}
    nuevas, actualizadas_filas, omitidas = [], [], 0
    for c in pull["clientes"]:
        if str(c["id"]) in vinculados:
            fila = staging.coerce_cliente_odoo(c)
            if not fila.get(staging._REQUERIDO_ODOO["cliente"]):
                omitidas += 1
                continue
            actualizadas_filas.append(fila)
        else:
            nuevas.append(c)

    if actualizadas_filas:
        from core.db import customer_accounts_repo
        for f in actualizadas_filas:
            # Re-sync of an already-linked account: use the Odoo-owned-columns
            # variant so a dueño-edited balance/credit_limit/etc. isn't
            # reverted to the coercer's insert-time defaults (C1 fix).
            customer_accounts_repo.upsert_account_from_odoo(tenant_id, f)

    batch_id = None
    if nuevas:
        r = staging.crear_batch_odoo("cliente", nuevas, nombre="Odoo · contactos")
        batch_id = r["id"]

    return {"actualizados": len(actualizadas_filas), "nuevos_para_revisar": len(nuevas),
            "omitidos_malformados": omitidas, "batch_id": batch_id}


def ingest_ordenes_compra(actor: str = "dueño") -> dict:
    from core.db import purchase_orders_repo

    tenant_id = _tenant.current_tenant_id()
    conector = conectores.ConectorOdoo(tenant_id)
    pull = conector.pull_ordenes_compra()

    vinculadas = {o["source_id"] for o in purchase_orders_repo.list_orders(tenant_id)
                  if o.get("source") == "odoo"}
    nuevas, actualizadas, omitidas, numeros_actualizados = [], 0, 0, []
    for o in pull["ordenes"]:
        if str(o["id"]) in vinculadas:
            fila = staging.coerce_orden_compra_odoo(o)
            if not fila.get(staging._REQUERIDO_ODOO["orden_compra"]):
                omitidas += 1
                continue
            purchase_orders_repo.upsert_from_odoo(tenant_id, fila)
            actualizadas += 1
            numeros_actualizados.append(fila["numero"])
        else:
            nuevas.append(o)

    if actualizadas:
        # Odoo-synced writes bypass core/ordenes.py's own audited
        # crear_orden_compra/cambiar_estado_orden_compra paths entirely (it
        # calls purchase_orders_repo.upsert_from_odoo directly), so — unlike
        # those manual paths — they would otherwise leave no audit trail at
        # all. One summary record per ingest call, same shape as
        # proveedores.upsert_desde_conector's connector-upsert audit call.
        _audit.record(actor, "upsert_ordenes_compra_conector", None,
                       {"actualizadas": actualizadas, "numeros": numeros_actualizados})

    batch_id = None
    if nuevas:
        r = staging.crear_batch_odoo("orden_compra", nuevas, nombre="Odoo · órdenes de compra")
        batch_id = r["id"]

    return {"actualizados": actualizadas, "nuevos_para_revisar": len(nuevas),
            "omitidos_malformados": omitidas, "batch_id": batch_id}
