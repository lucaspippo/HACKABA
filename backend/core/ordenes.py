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
import json
import os

from . import fechas, paths
from .audit import AuditLog

ORDENES_JSON = os.path.join(paths.DATA_DIR, "ordenes_preparadas.json")
_audit = AuditLog(paths.DATA_DIR)


def _load() -> list[dict]:
    try:
        with open(ORDENES_JSON, encoding="utf-8") as f:
            return json.load(f) or []
    except Exception:  # noqa: BLE001
        return []


def _save(items: list[dict]) -> None:
    os.makedirs(paths.DATA_DIR, exist_ok=True)
    with open(ORDENES_JSON, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)


def listar() -> list[dict]:
    return sorted(_load(), key=lambda o: o.get("preparada", ""), reverse=True)


def preparar(*, producto: str, codigo: int | None, cantidad: float,
             proveedor: str, actor: str, motivo: str = "",
             origen: str = "quiebre_inminente") -> dict:
    """Deja la orden en BORRADOR. Idempotente por (código, origen): aprobar dos
    veces el mismo hallazgo no duplica el pedido — devuelve la que ya existe."""
    items = _load()
    ya = next((o for o in items if o.get("codigo") == codigo
               and o.get("origen") == origen and o.get("estado") == "borrador"), None)
    if ya:
        return ya
    hoy = fechas.hoy()
    orden = {
        "numero": f"OC-{hoy.year}-{900 + len(items) + 1:04d}",
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
    items.append(orden)
    _save(items)
    _audit.record(actor, "preparar_orden_compra", None,
                  {"numero": orden["numero"], "proveedor": proveedor,
                   "producto": producto, "cantidad": cantidad, "origen": origen})
    return orden
