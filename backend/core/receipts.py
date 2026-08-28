"""Goods receipts: match against a PO, and CRUD over the `recepciones` section."""
from __future__ import annotations

from . import esquema, paging, section_records
from .db import purchase_orders_repo
from .db import tenant as _tenant

TYPE = "recepciones"
FIELDS = ("fecha", "producto", "codigo", "proveedor", "cantidad", "deposito",
          "origen", "po_number", "source", "source_id", "source_status")
REQUIRED = ("producto",)
SEARCH = ("fecha", "producto", "codigo", "proveedor", "po_number", "deposito", "source")
CSV_COLUMNS = ("fecha", "producto", "codigo", "proveedor", "cantidad",
               "deposito", "po_number", "source")
_LIST_KW = dict(search_in=SEARCH, date_field="fecha")


def _coerce(data: dict) -> dict:
    out = dict(data)
    if "cantidad" in out and out["cantidad"] is not None:
        out["cantidad"] = float(out["cantidad"])
    if "codigo" in out and out["codigo"] not in (None, ""):
        out["codigo"] = int(out["codigo"])
    return out


def _equals(*, proveedor: str | None = None, deposito: str | None = None,
            po_number: str | None = None) -> dict:
    out = {}
    if proveedor:
        out["proveedor"] = proveedor
    if deposito:
        out["deposito"] = deposito
    if po_number:
        out["po_number"] = po_number
    return out


def list_page(*, q: str = "", sort: str | None = "fecha", direction: str = "desc",
              offset: int = 0, limit: int = paging.DEFAULT_LIMIT,
              source: str | None = None, date_from: str | None = None,
              date_to: str | None = None, proveedor: str | None = None,
              deposito: str | None = None, po_number: str | None = None,
              sin_po: bool = False) -> dict:
    return section_records.list_page(
        TYPE, **_LIST_KW, q=q, sort=sort, direction=direction,
        offset=offset, limit=limit, source=source,
        date_from=date_from, date_to=date_to,
        equals=_equals(proveedor=proveedor, deposito=deposito, po_number=po_number),
        empty=("po_number",) if sin_po else None,
        facet_fields=("proveedor", "deposito"),
    )


def create(data: dict, actor: str) -> dict:
    return section_records.create(
        TYPE, FIELDS, REQUIRED, _coerce(data), actor, "crear_recepcion")


def update(id_: str, changes: dict, actor: str) -> dict:
    return section_records.update(
        TYPE, FIELDS, id_, _coerce(changes), actor, "editar_recepcion")


def delete(id_: str, actor: str) -> None:
    section_records.delete(TYPE, id_, actor, "eliminar_recepcion")


def export_csv(*, q: str = "", sort: str | None = "fecha", direction: str = "desc",
               source: str | None = None, date_from: str | None = None,
               date_to: str | None = None, proveedor: str | None = None,
               deposito: str | None = None, po_number: str | None = None,
               sin_po: bool = False) -> str:
    return section_records.export_csv(
        TYPE, CSV_COLUMNS, **_LIST_KW, q=q, sort=sort, direction=direction,
        source=source, date_from=date_from, date_to=date_to,
        equals=_equals(proveedor=proveedor, deposito=deposito, po_number=po_number),
        empty=("po_number",) if sin_po else None,
    )


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
