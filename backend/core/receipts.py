"""Match ingested goods receipts against an ingested purchase order."""
from __future__ import annotations

from . import esquema
from .db import purchase_orders_repo
from .db import tenant as _tenant


def match_receipt_to_purchase_order(po_number: str) -> dict:
    """Compare received qty per codigo to that PO's lines.

    Computed on read — nothing is persisted. Rows without codigo are ignored
    on both sides.
    """
    po = purchase_orders_repo.find_by_number(_tenant.current_tenant_id(), po_number)
    if not po:
        return {
            "po_number": po_number, "found": False,
            "matches": [], "short": [], "extra": [],
        }
    received: dict = {}
    for f in esquema.filas("recepciones"):
        if (f.get("po_number") or "") != po_number:
            continue
        c = f.get("codigo")
        if c is None:
            continue
        received[c] = received.get(c, 0.0) + float(f.get("cantidad") or 0)
    ordered: dict = {}
    names: dict = {}
    for it in po.get("items") or []:
        c = it.get("codigo")
        if c is None:
            continue
        ordered[c] = ordered.get(c, 0.0) + float(it.get("cantidad") or 0)
        names[c] = it.get("producto") or names.get(c) or ""
    matches, short, extra = [], [], []
    for c, qty in ordered.items():
        got = received.get(c, 0.0)
        row = {"codigo": c, "producto": names.get(c, ""),
               "ordered": qty, "received": got, "diff": round(got - qty, 2)}
        if abs(got - qty) <= 0.01:
            matches.append(row)
        elif got < qty:
            short.append(row)
        else:
            extra.append(row)
    for c, got in received.items():
        if c in ordered:
            continue
        extra.append({"codigo": c, "producto": "", "ordered": 0.0,
                      "received": got, "diff": round(got, 2)})
    return {
        "po_number": po_number, "found": True,
        "matches": matches, "short": short, "extra": extra,
    }
