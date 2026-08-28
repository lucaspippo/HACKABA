"""Browse surface for loaded operational rows: catalog, sales, receipts,
and warehouse positions (stock quants).

The analytical screens summarize this data. This module returns the raw
rows so the owner can see what landed after a CSV load or an Odoo ingest,
including provenance (`source`). Storage still uses the existing Spanish
column names; the payload this module exposes is English.
"""
from __future__ import annotations

from . import esquema, store

# (stored_key, api_key) — stored keys are the incumbent schema.
_PRODUCT_FIELDS = (
    ("codigo", "code"),
    ("sku", "sku"),
    ("descripcion", "description"),
    ("estado", "status"),
    ("stock", "stock"),
    ("costo_iva", "cost"),
    ("pvp", "list_price"),
    ("precio_lista", "reference_price"),
    ("pricing_status", "pricing_status"),
    ("moneda", "currency"),
    ("free_qty", "free_qty"),
    ("incoming_qty", "incoming_qty"),
    ("outgoing_qty", "outgoing_qty"),
    ("source", "source"),
    ("source_id", "source_id"),
)
_SALE_FIELDS = (
    ("fecha", "date"),
    ("producto", "product"),
    ("codigo", "code"),
    ("cantidad", "quantity"),
    ("precio", "price"),
    ("currency", "currency"),
    ("qty_delivered", "qty_delivered"),
    ("source", "source"),
    ("source_id", "source_id"),
    ("source_status", "source_status"),
)
_RECEIPT_FIELDS = (
    ("fecha", "date"),
    ("producto", "product"),
    ("codigo", "code"),
    ("proveedor", "vendor"),
    ("cantidad", "quantity"),
    ("deposito", "warehouse"),
    ("origen", "origin"),
    ("po_number", "po_number"),
    ("qty_ordered", "qty_ordered"),
    ("pendiente", "pending"),
    ("es_backorder", "is_backorder"),
    ("source", "source"),
    ("source_id", "source_id"),
    ("source_status", "source_status"),
)
_MOVEMENT_FIELDS = (
    ("producto", "product"),
    ("codigo", "code"),
    ("ubicacion", "location"),
    ("lote", "lot"),
    ("vencimiento", "expiry"),
    ("cantidad", "quantity"),
    ("in_date", "in_date"),
    ("counted_qty", "counted_qty"),
    ("source", "source"),
    ("source_id", "source_id"),
)
_INVOICE_FIELDS = (
    ("fecha", "date"),
    ("numero", "number"),
    ("partner", "partner"),
    ("tipo", "kind"),
    ("total", "total"),
    ("residual", "residual"),
    ("currency", "currency"),
    ("payment_state", "payment_state"),
    ("aging", "aging"),
    ("vencimiento", "due"),
    ("overdue", "overdue"),
    ("source", "source"),
    ("source_id", "source_id"),
)
_DELIVERY_FIELDS = (
    ("fecha", "date"),
    ("producto", "product"),
    ("codigo", "code"),
    ("cliente", "customer"),
    ("cantidad", "quantity"),
    ("qty_ordered", "qty_ordered"),
    ("origen", "origin"),
    ("so_number", "so_number"),
    ("pendiente", "pending"),
    ("es_backorder", "is_backorder"),
    ("source", "source"),
    ("source_id", "source_id"),
)


def _project(rows: list[dict], fields: tuple[tuple[str, str], ...], prefix: str) -> list[dict]:
    out = []
    for i, row in enumerate(rows):
        item = {api_key: row.get(stored) for stored, api_key in fields}
        item["_key"] = f"{prefix}-{i}"
        out.append(item)
    return out


def _count_source(rows: list[dict], source: str = "odoo") -> int:
    return sum(1 for row in rows if row.get("source") == source)


def overview() -> dict:
    """Four lists plus counts. Products come from the working catalog;
    the other three are schema sections filled by CSV or Odoo ingest."""
    products_raw = store.raw_actual()
    sales_raw = sorted(
        esquema.filas("venta"),
        key=lambda row: str(row.get("fecha") or ""),
        reverse=True,
    )
    receipts_raw = sorted(
        esquema.filas("recepciones"),
        key=lambda row: str(row.get("fecha") or ""),
        reverse=True,
    )
    movements_raw = sorted(
        esquema.filas("deposito"),
        key=lambda row: str(row.get("in_date") or row.get("vencimiento") or ""),
        reverse=True,
    )
    invoices_raw = sorted(
        esquema.filas("cuenta_corriente") + esquema.filas("compras"),
        key=lambda row: str(row.get("fecha") or ""),
        reverse=True,
    )
    deliveries_raw = sorted(
        esquema.filas("entregas"),
        key=lambda row: str(row.get("fecha") or ""),
        reverse=True,
    )
    products = _project(products_raw, _PRODUCT_FIELDS, "p")
    sales = _project(sales_raw, _SALE_FIELDS, "v")
    receipts = _project(receipts_raw, _RECEIPT_FIELDS, "r")
    movements = _project(movements_raw, _MOVEMENT_FIELDS, "m")
    invoices = _project(invoices_raw, _INVOICE_FIELDS, "i")
    deliveries = _project(deliveries_raw, _DELIVERY_FIELDS, "e")
    return {
        "products": products,
        "sales": sales,
        "receipts": receipts,
        "movements": movements,
        "invoices": invoices,
        "deliveries": deliveries,
        "summary": {
            "products": len(products),
            "sales": len(sales),
            "receipts": len(receipts),
            "movements": len(movements),
            "invoices": len(invoices),
            "deliveries": len(deliveries),
            "odoo": {
                "products": _count_source(products),
                "sales": _count_source(sales),
                "receipts": _count_source(receipts),
                "movements": _count_source(movements),
                "invoices": _count_source(invoices),
                "deliveries": _count_source(deliveries),
            },
        },
    }
