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
    conector = conectores.conector_odoo(tenant_id)
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
    conector = conectores.conector_odoo(tenant_id)
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
    conector = conectores.conector_odoo(tenant_id)
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
    conector = conectores.conector_odoo(tenant_id)
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


def _flatten_confirmed_sale_lines(ordenes: list[dict]) -> list[dict]:
    """One ingest row per confirmed sale.order.line (estado == confirmada).

    `precio` is the pricelist-resolved unit price already charged
    (`price_unit`), converted to company currency when the order is USD.
    Never recomputed from product.list_price.
    """
    from core import store
    out = []
    for o in ordenes:
        if o.get("estado") != "confirmada":
            continue
        fecha = (o.get("fecha") or "")[:10]
        currency = o.get("currency") or ""
        for it in o.get("items") or []:
            tmpl = it.get("product_tmpl_id")
            art = store.buscar_por_source("odoo", str(tmpl)) if tmpl is not None else None
            precio = it.get("precio_company")
            if precio is None:
                precio = it.get("precio_unitario")
            out.append({
                "id": it["id"],
                "nombre": it.get("producto") or "",
                "fecha": fecha,
                "cantidad": it.get("cantidad") or 0,
                "qty_delivered": it.get("qty_delivered") or 0,
                "precio": precio,
                "precio_original": it.get("precio_unitario"),
                "currency": currency,
                "product_tmpl_id": tmpl,
                "codigo": art["codigo"] if art else None,
                "estado": o.get("estado") or "",
            })
    return out


def ingest_ventas(actor: str = "dueño") -> dict:
    from core import esquema

    tenant_id = _tenant.current_tenant_id()
    conector = conectores.conector_odoo(tenant_id)
    pull = conector.pull_ordenes_venta()
    filas = _flatten_confirmed_sale_lines(pull["ordenes"])

    vinculadas = {str(f.get("source_id")) for f in esquema.filas("venta")
                  if f.get("source") == "odoo"}
    nuevas, actualizadas_filas, omitidas = [], [], 0
    pulled_ids = [str(p["id"]) for p in filas]
    for p in filas:
        fila = staging.coerce_venta_odoo(p)
        if not fila.get(staging._REQUERIDO_ODOO["venta"]):
            omitidas += 1
            continue
        if str(p["id"]) in vinculadas:
            actualizadas_filas.append(fila)
        else:
            nuevas.append(p)

    if actualizadas_filas:
        esquema.upsert_filas("venta", actualizadas_filas)
        _audit.record(actor, "upsert_ventas_conector", None,
                       {"actualizadas": len(actualizadas_filas),
                        "source_ids": [f["source_id"] for f in actualizadas_filas]})

    esquema.delete_odoo_missing("venta", pulled_ids)

    batch_id = None
    if nuevas:
        r = staging.crear_batch_odoo("venta", nuevas, nombre="Odoo · ventas")
        batch_id = r["id"]

    return {"actualizados": len(actualizadas_filas), "nuevos_para_revisar": len(nuevas),
            "omitidos_malformados": omitidas, "batch_id": batch_id}


def _resolve_odoo_codigo(product_tmpl_id) -> int | None:
    if product_tmpl_id is None:
        return None
    art = store.buscar_por_source("odoo", str(product_tmpl_id))
    return art["codigo"] if art else None


def _ingest_blob(tipo: str, pulled: list[dict], actor: str, nombre: str) -> dict:
    from core import esquema
    vinculadas = {str(f.get("source_id")) for f in esquema.filas(tipo)
                  if f.get("source") == "odoo"}
    nuevas, actualizadas_filas, omitidas = [], [], 0
    pulled_ids = [str(p["id"]) for p in pulled]
    coercer = staging._COERCERS_ODOO[tipo]
    required = staging._REQUERIDO_ODOO[tipo]
    for p in pulled:
        fila = coercer(p)
        if not fila.get(required):
            omitidas += 1
            continue
        if str(p["id"]) in vinculadas:
            actualizadas_filas.append(fila)
        else:
            nuevas.append(p)
    if actualizadas_filas:
        esquema.upsert_filas(tipo, actualizadas_filas)
        _audit.record(actor, f"upsert_{tipo}_conector", None,
                       {"actualizadas": len(actualizadas_filas),
                        "source_ids": [f["source_id"] for f in actualizadas_filas]})
    esquema.delete_odoo_missing(tipo, pulled_ids)
    batch_id = None
    if nuevas:
        r = staging.crear_batch_odoo(tipo, nuevas, nombre=nombre)
        batch_id = r["id"]
    return {"actualizados": len(actualizadas_filas), "nuevos_para_revisar": len(nuevas),
            "omitidos_malformados": omitidas, "batch_id": batch_id}


def ingest_deposito(actor: str = "dueño") -> dict:
    tenant_id = _tenant.current_tenant_id()
    conector = conectores.conector_odoo(tenant_id)
    pull = conector.pull_deposito()
    filas = []
    for q in pull["quants"]:
        row = dict(q)
        row["nombre"] = q.get("producto") or ""
        row["codigo"] = _resolve_odoo_codigo(q.get("product_tmpl_id"))
        filas.append(row)
    return _ingest_blob("deposito", filas, actor, "Odoo · depósito")


def ingest_recepciones(actor: str = "dueño") -> dict:
    """Done incoming pickings → recepciones. Does not change product.stock."""
    from core.db import purchase_orders_repo

    tenant_id = _tenant.current_tenant_id()
    conector = conectores.conector_odoo(tenant_id)
    pull = conector.pull_recepciones()
    filas = []
    for p in pull["recepciones"]:
        row = dict(p)
        row["nombre"] = p.get("producto") or ""
        row["codigo"] = _resolve_odoo_codigo(p.get("product_tmpl_id"))
        filas.append(row)
    result = _ingest_blob("recepciones", filas, actor, "Odoo · recepciones")
    po_numbers = {p.get("po_number") for p in filas if p.get("po_number")}
    for number in po_numbers:
        po = purchase_orders_repo.find_by_number(tenant_id, number)
        if not po or po.get("source") != "odoo":
            continue
        if po.get("estado") in ("cancelada", "recibida"):
            continue
        pending_rows = [
            p for p in filas
            if p.get("po_number") == number and p.get("pendiente")
        ]
        done_rows = [
            p for p in filas
            if p.get("po_number") == number and not p.get("pendiente")
        ]
        if pending_rows:
            continue
        if done_rows:
            purchase_orders_repo.update_status(tenant_id, number, "recibida")
    return result


def ingest_entregas(actor: str = "dueño") -> dict:
    tenant_id = _tenant.current_tenant_id()
    conector = conectores.conector_odoo(tenant_id)
    pull = conector.pull_entregas()
    filas = []
    for p in pull["entregas"]:
        row = dict(p)
        row["nombre"] = p.get("producto") or ""
        row["codigo"] = _resolve_odoo_codigo(p.get("product_tmpl_id"))
        filas.append(row)
    return _ingest_blob("entregas", filas, actor, "Odoo · entregas")


def _apply_customer_ar(tenant_id: str, facturas: list[dict]) -> None:
    """Odoo invoices own AR for linked customers: saldo = sum(residual)."""
    from core import cuentas
    from core.db import customer_accounts_repo
    from . import odoo_fx

    as_of = odoo_fx.hoy_facturas()
    by_partner: dict[str, list[dict]] = {}
    for f in facturas:
        if f.get("move_type") != "out_invoice":
            continue
        pid = f.get("partner_id")
        if pid is None:
            continue
        by_partner.setdefault(str(pid), []).append(f)

    for c in cuentas.listar():
        if c.get("source") != "odoo" or not c.get("source_id"):
            continue
        invs = by_partner.get(str(c["source_id"])) or []
        saldo = round(sum(float(i.get("residual_company") or i.get("residual") or 0) for i in invs), 2)
        overdue_dates = []
        for i in invs:
            if not i.get("overdue"):
                continue
            d = i.get("vencimiento") or i.get("invoice_date_due")
            if d:
                overdue_dates.append(d)
        dias = 0
        if overdue_dates:
            oldest = min(overdue_dates)
            from core.fechas import parse_fecha
            od = parse_fecha(oldest)
            if od:
                dias = (as_of - od).days
        customer_accounts_repo.update_ar_from_odoo(
            tenant_id, c["id"], saldo=saldo, days_overdue=max(0, dias))


def ingest_facturas(actor: str = "dueño") -> dict:
    from core import pagos as pagos_mod

    tenant_id = _tenant.current_tenant_id()
    conector = conectores.conector_odoo(tenant_id)
    pull = conector.pull_facturas()
    out_inv = [f for f in pull["facturas"] if f.get("move_type") == "out_invoice"]
    in_inv = [f for f in pull["facturas"] if f.get("move_type") == "in_invoice"]
    ar = _ingest_blob("cuenta_corriente", out_inv, actor, "Odoo · facturas")
    ap = _ingest_blob("compras", in_inv, actor, "Odoo · facturas de compra")
    _apply_customer_ar(tenant_id, pull["facturas"])
    pagos_mod.upsert_from_odoo_bills([
        {
            "proveedor": f.get("partner") or "",
            "numero": f.get("numero") or "",
            "emision": f.get("fecha") or "",
            "vencimiento": f.get("vencimiento") or "",
            "monto": f.get("residual_company") if f.get("aging") != "paid" else f.get("total_company") or f.get("total") or 0,
            "estado": "pagado" if f.get("aging") == "paid" else "pendiente",
            "payment_state": f.get("payment_state") or "",
            "aging": f.get("aging") or "",
            "currency": f.get("currency") or "",
            "source": "odoo",
            "source_id": str(f["id"]),
        }
        for f in in_inv
    ])
    return {
        "actualizados": (ar.get("actualizados") or 0) + (ap.get("actualizados") or 0),
        "nuevos_para_revisar": (ar.get("nuevos_para_revisar") or 0) + (ap.get("nuevos_para_revisar") or 0),
        "omitidos_malformados": (ar.get("omitidos_malformados") or 0) + (ap.get("omitidos_malformados") or 0),
        "batch_id": ar.get("batch_id") or ap.get("batch_id"),
        "batch_id_facturas": ar.get("batch_id"),
        "batch_id_compras": ap.get("batch_id"),
    }


def ingest_pagos(actor: str = "dueño") -> dict:
    tenant_id = _tenant.current_tenant_id()
    conector = conectores.conector_odoo(tenant_id)
    pull = conector.pull_pagos()
    return _ingest_blob("pagos", pull["pagos"], actor, "Odoo · pagos")
