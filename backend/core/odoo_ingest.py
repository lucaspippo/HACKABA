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
