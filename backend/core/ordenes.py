"""
ordenes.py — las órdenes de compra que Ángela PREPARA y el dueño aprueba.

Regla inviolable de la casa: Ángela detecta y propone, nunca ejecuta sola. El
hallazgo de quiebre (P38·B) llega con la orden ya armada — producto, cantidad,
proveedor y el porqué — pero queda en borrador hasta que alguien la aprueba.
Aprobarla no la manda al proveedor: la deja lista para salir, con su registro
en la auditoría. El paso al ERP viaja por el delta sync de siempre.
"""
from __future__ import annotations

import datetime

from . import fechas, paths
from .audit import AuditLog

_audit = AuditLog(paths.DATA_DIR)


def listar() -> list[dict]:
    from core.db import purchase_orders_repo, tenant as _tenant
    return purchase_orders_repo.list_orders(_tenant.current_tenant_id())


def preparar(*, producto: str, codigo: int | None, cantidad: float,
             proveedor: str, actor: str, motivo: str = "",
             origen: str = "quiebre_inminente") -> dict:
    """Deja la orden en BORRADOR. Idempotente por (código, origen): aprobar dos
    veces el mismo hallazgo no duplica el pedido — devuelve la que ya existe."""
    from core.db import purchase_orders_repo, tenant as _tenant
    tid = _tenant.current_tenant_id()
    ya = purchase_orders_repo.find_draft(tid, codigo=codigo, origen=origen)
    if ya:
        return ya
    hoy = fechas.hoy()
    n = purchase_orders_repo.count(tid)
    orden = {
        "numero": f"OC-{hoy.year}-{900 + n + 1:04d}",
        "fecha": hoy.isoformat(),
        "proveedor": proveedor,
        "estado": "borrador",
        "origen": origen,
        "motivo": motivo,
        "preparada_por": "Ángela",
        "aprobada_por": actor,
        "preparada": datetime.datetime.now().isoformat(timespec="seconds"),
        "items": [{"codigo": codigo, "producto": producto, "cantidad": cantidad}],
    }
    purchase_orders_repo.create(tid, orden)
    _audit.record(actor, "preparar_orden_compra", None,
                  {"numero": orden["numero"], "proveedor": proveedor,
                   "producto": producto, "cantidad": cantidad, "origen": origen})
    return orden
