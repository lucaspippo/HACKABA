"""Odoo multi-currency, pricelist resolution, backorder fulfillment, and
invoice aging — pure functions, no XML-RPC.

The odoo-demo seed (ARS company currency, USD secondary) is the fixture
this module is written against:

- `res.currency.rate` holds dated ARS→USD points (peso devaluing ~950→1450
  ARS/USD). Never assume a flat rate.
- `product.list_price` is the retail/reference price, not what a sale
  charged (`sale.order.line.price_unit` is). A zero list_price is not
  automatically broken data — mayorista pricelist items can still price it.
- Open backorders (`stock.picking.backorder_id` + pending state) are real;
  a partial receipt is not a complete receipt.
- Invoice aging is keyed off 2026-07-20 in the demo seed, distinct from
  the stock-aging "today" of 2026-07-07.
"""
from __future__ import annotations

import datetime
import os
from typing import Iterable

from .fechas import parse_fecha, hoy

# Demo seed: invoice/bill payment aging is frozen on this date, even when
# POLPILOT_DEMO_TODAY (stock/sales "today") is 2026-07-07.
INVOICE_AGING_TODAY = datetime.date(2026, 7, 20)

PENDING_PICKING_STATES = frozenset({
    "assigned", "confirmed", "waiting", "partially_available",
})
DONE_PICKING_STATES = frozenset({"done"})
OPEN_PICKING_STATES = PENDING_PICKING_STATES | DONE_PICKING_STATES

PRICING_RETAIL = "retail"
PRICING_WHOLESALE_ONLY = "wholesale_only"
PRICING_NEEDS_PRICING = "needs_pricing"

_PRODUCT_APPLIED = frozenset({"1_product", "0_product_variant"})
_CATEGORY_APPLIED = frozenset({"2_product_category"})


def _iso_code(val) -> str:
    """res.currency name, or an m2o [id, name] display, → uppercase ISO code."""
    if not val:
        return ""
    if isinstance(val, (list, tuple)) and len(val) > 1:
        val = val[1]
    text = str(val).strip()
    if not text:
        return ""
    return text.split()[0].upper()


def _m2o_id(val):
    if not val:
        return None
    return val[0] if isinstance(val, (list, tuple)) else val


def normalize_rates(rows: Iterable[dict], currency_names: dict | None = None) -> list[dict]:
    """Turn raw `res.currency.rate` reads into dated conversion points.

    Odoo 17 (company currency ARS): `rate` is units of this currency per 1
    company currency; `inverse_company_rate` is company currency per 1 of
    this currency (ARS per USD). We prefer inverse_company_rate so a USD
    amount converts with a multiply.
    """
    currency_names = currency_names or {}
    out = []
    for row in rows or []:
        cur = currency_names.get(row.get("currency_id") and _m2o_id(row.get("currency_id")))
        if not cur:
            cur = _iso_code(row.get("currency_id"))
        day = parse_fecha(row.get("name") or row.get("date"))
        if not cur or not day:
            continue
        rate = row.get("rate")
        inverse = row.get("inverse_company_rate")
        if inverse in (None, False) and rate not in (None, False, 0, 0.0):
            try:
                inverse = 1.0 / float(rate)
            except (TypeError, ZeroDivisionError, ValueError):
                inverse = None
        out.append({
            "currency": cur,
            "date": day,
            "rate": float(rate) if rate not in (None, False) else None,
            "inverse_company_rate": float(inverse) if inverse not in (None, False) else None,
        })
    return out


def to_company_amount(amount, currency: str | None, when,
                      rates: list[dict], company_currency: str = "ARS") -> float:
    """Convert `amount` in `currency` to company currency using the latest
    rate on or before `when`. Same-currency and missing-rate fall through
    unchanged — never invent a flat FX rate."""
    try:
        value = float(amount or 0)
    except (TypeError, ValueError):
        return 0.0
    cur = _iso_code(currency) or (company_currency or "ARS").upper()
    company = (company_currency or "ARS").upper()
    if cur == company:
        return value
    day = parse_fecha(when)
    if day is None and when not in (None, False, ""):
        day = parse_fecha(str(when)[:10])
    day = day or datetime.date.max
    applicable = [r for r in rates if r.get("currency") == cur and r["date"] <= day]
    if not applicable:
        applicable = [r for r in rates if r.get("currency") == cur]
    if not applicable:
        return value
    best = max(applicable, key=lambda r: r["date"])
    inverse = best.get("inverse_company_rate")
    if inverse:
        return round(value * inverse, 2)
    rate = best.get("rate")
    if rate:
        return round(value / rate, 2)
    return value


def hoy_facturas() -> datetime.date:
    """Invoice/bill aging 'today'. Honours POLPILOT_INVOICE_TODAY; when the
    demo clock is frozen, defaults to the seed's 2026-07-20 (not 2026-07-07)."""
    pinned = os.environ.get("POLPILOT_INVOICE_TODAY", "").strip()
    if pinned:
        d = parse_fecha(pinned)
        if d:
            return d
    if os.environ.get("POLPILOT_DEMO_TODAY", "").strip():
        return INVOICE_AGING_TODAY
    return hoy()


def classify_invoice_aging(payment_state: str | None, due,
                           as_of: datetime.date | None = None,
                           amount_residual=None) -> dict:
    """paid / partial / open (not yet due) / overdue.

    `payment_state` is Odoo's mix (paid, partial, not_paid, in_payment).
    Residual is never assumed 0 or the full total — the caller passes it.
    """
    as_of = as_of or hoy_facturas()
    state = (payment_state or "").lower() or "not_paid"
    due_date = parse_fecha(due)
    residual = float(amount_residual) if amount_residual not in (None, False) else None
    overdue = bool(due_date and due_date < as_of and state != "paid"
                   and (residual is None or residual > 0))
    if state == "paid" or (residual is not None and residual <= 0 and state != "partial"):
        aging = "paid"
        overdue = False
    elif overdue:
        aging = "overdue"
    elif state == "partial":
        aging = "partial"
    else:
        aging = "open"
    return {
        "payment_state": state,
        "aging": aging,
        "overdue": overdue,
        "invoice_date_due": due_date.isoformat() if due_date else "",
        "as_of": as_of.isoformat(),
        "amount_residual": residual,
    }


def _item_matches(item: dict, tmpl_id, variant_id, categ_id) -> bool:
    applied = item.get("applied_on") or ""
    if applied in _PRODUCT_APPLIED:
        return (_m2o_id(item.get("product_tmpl_id")) == tmpl_id
                or (variant_id is not None and _m2o_id(item.get("product_id")) == variant_id))
    if applied in _CATEGORY_APPLIED:
        return categ_id is not None and _m2o_id(item.get("categ_id")) == categ_id
    if applied == "3_global":
        return True
    return False


def _item_price(item: dict, list_price) -> tuple[float | None, str]:
    compute = item.get("compute_price") or ""
    if compute == "fixed":
        price = item.get("fixed_price")
        if price in (None, False):
            return None, "fixed"
        return float(price), "fixed"
    try:
        base = float(list_price or 0)
    except (TypeError, ValueError):
        base = 0.0
    if compute == "percentage":
        pct = float(item.get("percent_price") or 0)
        return round(base * (1 - pct / 100.0), 2), "percentage"
    if compute == "formula":
        disc = float(item.get("price_discount") or 0)
        return round(base * (1 - disc / 100.0), 2), "formula"
    return None, compute or ""


def _is_mayorista(name: str) -> bool:
    return "mayorista" in (name or "").lower()


def resolve_product_pricing(product: dict, pricelists: list[dict],
                            items: list[dict]) -> dict:
    """Resolve sellable prices from pricelist items.

    - `list_price` is kept as the retail/reference price (`precio_lista`).
    - Product-level `fixed` items on a USD pricelist are native USD quotes;
      they are NOT derived by converting the ARS list_price.
    - `list_price = 0` with a mayorista item → wholesale_only (has a price).
    - `list_price = 0` and no item anywhere → needs_pricing.
    """
    tmpl_id = product.get("id")
    categ_id = _m2o_id(product.get("categ_id"))
    list_price = product.get("list_price")
    try:
        list_price_n = float(list_price) if list_price not in (None, False) else 0.0
    except (TypeError, ValueError):
        list_price_n = 0.0

    by_pricelist: dict[int, list[dict]] = {}
    for it in items or []:
        pid = _m2o_id(it.get("pricelist_id"))
        if pid is None:
            continue
        by_pricelist.setdefault(pid, []).append(it)

    precios = []
    has_any_item = False
    mayorista_ars = None
    for pl in pricelists or []:
        pl_items = by_pricelist.get(pl["id"]) or []
        matching = [it for it in pl_items if _item_matches(it, tmpl_id, None, categ_id)]
        if not matching:
            continue
        # Product-level beats category/global.
        matching.sort(key=lambda it: (
            0 if (it.get("applied_on") or "") in _PRODUCT_APPLIED else 1,
            0 if it.get("compute_price") == "fixed" else 1,
        ))
        chosen = matching[0]
        price, origin = _item_price(chosen, list_price_n)
        if price is None:
            continue
        has_any_item = True
        currency = _iso_code(pl.get("currency_id")) or "ARS"
        entry = {
            "pricelist_id": pl["id"],
            "pricelist": pl.get("name") or "",
            "currency": currency,
            "price": price,
            "origin": origin,
            "applied_on": chosen.get("applied_on") or "",
        }
        precios.append(entry)
        if _is_mayorista(entry["pricelist"]) and currency == "ARS" and origin == "fixed":
            mayorista_ars = price
        elif _is_mayorista(entry["pricelist"]) and currency == "ARS" and mayorista_ars is None:
            mayorista_ars = price

    if list_price_n > 0:
        status = PRICING_RETAIL
        pvp = list_price_n
    elif mayorista_ars and mayorista_ars > 0:
        status = PRICING_WHOLESALE_ONLY
        pvp = mayorista_ars
    elif has_any_item:
        # Priced only in a non-ARS list (e.g. native USD quote) — still a
        # real price; caller converts to company currency when needed.
        usd_fixed = next((e["price"] for e in precios
                          if e["origin"] == "fixed" and e["currency"] != "ARS"), None)
        if usd_fixed:
            status = PRICING_WHOLESALE_ONLY if any(_is_mayorista(e["pricelist"]) for e in precios) else PRICING_RETAIL
            pvp = None  # filled by caller via FX on the USD quote
            # Stash so the caller can convert.
        else:
            status = PRICING_WHOLESALE_ONLY
            pvp = next((e["price"] for e in precios if e["price"]), None)
    else:
        status = PRICING_NEEDS_PRICING
        pvp = None
        usd_fixed = None

    native_usd = next((e for e in precios if e["origin"] == "fixed" and e["currency"] != "ARS"), None)
    return {
        "precio_lista": list_price_n,
        "precio": pvp,
        "pricing_status": status,
        "precios_pricelist": precios,
        "usd_fixed": native_usd["price"] if native_usd else None,
        "usd_currency": native_usd["currency"] if native_usd else None,
    }


def fulfillment(ordered: float, done: float, open_backorder: bool = False) -> str:
    """none / partial / complete for a PO or SO against received/delivered qty."""
    try:
        o = float(ordered or 0)
        d = float(done or 0)
    except (TypeError, ValueError):
        return "none"
    if d <= 0 and not open_backorder:
        return "none"
    if open_backorder or (o > 0 and d < o - 1e-6):
        return "partial"
    return "complete"


def lines_fulfillment(items: list[dict], *,
                      qty_key: str = "cantidad",
                      done_key: str = "qty_received",
                      open_backorder: bool = False) -> str:
    ordered = sum(float(it.get(qty_key) or 0) for it in items or [])
    done = sum(float(it.get(done_key) or 0) for it in items or [])
    return fulfillment(ordered, done, open_backorder)


def is_pending_picking(state: str | None) -> bool:
    return (state or "") in PENDING_PICKING_STATES


def is_open_backorder(picking: dict) -> bool:
    """This picking is a still-open remainder of another (backorder_id set
    and state pending). Cancelled backorders do not count."""
    backorder = picking.get("backorder_id")
    if not backorder:
        return False
    return is_pending_picking(picking.get("estado") or picking.get("state"))
