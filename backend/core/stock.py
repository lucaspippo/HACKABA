"""On-hand vs projected stock.

`inmovilizado` and rotation-in-days stay on on-hand (`stock`): that is capital
sitting in the warehouse. Operational cover (reponer, quiebre, forecast
stockout, Prioridades) uses projected stock so a PO already in transit is not
treated as a new buy, and reserved qty is not treated as sellable.

Missing incoming/outgoing keys (CSV-only articles) count as zero, so the
number equals on-hand — same behaviour as before Odoo ingest.
"""
from __future__ import annotations


def on_hand(art: dict) -> float:
    return float(art.get("stock") or 0)


def projected_stock(art: dict) -> float:
    """On-hand + incoming − outgoing (Odoo free/forecasted qty analogue)."""
    return (
        on_hand(art)
        + float(art.get("incoming_qty") or 0)
        - float(art.get("outgoing_qty") or 0)
    )


def days_of_cover(art: dict, daily_rate: float) -> float:
    """Days until projected stock hits zero at `daily_rate`. No rate → 0."""
    if daily_rate <= 0:
        return 0.0
    qty = projected_stock(art)
    return qty / daily_rate if qty > 0 else 0.0
