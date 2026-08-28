"""
Seasonal monthly demand forecast per product.

Numbers come from esquema.filas("venta") only. Ángela narrates this output;
she never computes it. No extra libraries.
"""
from __future__ import annotations

import statistics

from . import esquema, fechas, stock, store
from .evolucion import _monto_fila
from .fechas import parse_fecha


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    total = year * 12 + (month - 1) + delta
    return total // 12, total % 12 + 1


def _period(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _monthly_totals(filas: list[dict]) -> dict[int, dict[str, dict[str, float]]]:
    """product_code -> YYYY-MM -> {qty, amount}."""
    out: dict[int, dict[str, dict[str, float]]] = {}
    for f in filas:
        cod = f.get("codigo")
        if cod is None:
            continue
        d = parse_fecha(f.get("fecha"))
        if not d:
            continue
        period = _period(d.year, d.month)
        bucket = out.setdefault(int(cod), {}).setdefault(period, {"qty": 0.0, "amount": 0.0})
        bucket["qty"] += float(f.get("cantidad") or 0)
        bucket["amount"] += _monto_fila(f)
    return out


def _confidence(cv: float | None, interval_ok: bool) -> str:
    if not interval_ok:
        return "low"
    if cv is None:
        return "low"
    if cv < 0.15:
        return "high"
    if cv < 0.35:
        return "medium"
    return "low"


def _point_forecast(by_month: dict[str, dict[str, float]], year: int, month: int
                    ) -> tuple[float, float, float]:
    """Returns (qty, amount, trend)."""
    last_year = _period(year - 1, month)
    ly = by_month.get(last_year)
    last3, prior3 = [], []
    for delta in range(-3, 0):
        y, m = _shift_month(year, month, delta)
        last3.append(by_month.get(_period(y, m), {}).get("qty", 0.0))
        prior3.append(by_month.get(_period(y - 1, m), {}).get("qty", 0.0))
    prior_sum = sum(prior3)
    trend = (sum(last3) / prior_sum) if prior_sum else 1.0
    if ly and ly.get("qty"):
        qty = ly["qty"] * trend
        amount = ly.get("amount", 0.0) * trend
    else:
        qty = (sum(last3) / 3.0) if any(last3) else 0.0
        last3_amt = []
        for delta in range(-3, 0):
            y, m = _shift_month(year, month, delta)
            last3_amt.append(by_month.get(_period(y, m), {}).get("amount", 0.0))
        amount = (sum(last3_amt) / 3.0) if any(last3_amt) else 0.0
    return qty, amount, trend


def _residuals(by_month: dict[str, dict[str, float]], today) -> tuple[list[float], list[float]]:
    """Actual − formula over the last 12 months that have a prior year."""
    residuals, actuals = [], []
    for delta in range(-12, 0):
        y, m = _shift_month(today.year, today.month, delta)
        prior = by_month.get(_period(y - 1, m))
        if not prior:
            continue
        actual = by_month.get(_period(y, m), {}).get("qty", 0.0)
        pred, _, _ = _point_forecast(by_month, y, m)
        residuals.append(actual - pred)
        actuals.append(actual)
    return residuals, actuals


def forecast_demand(lang: str | None = None) -> dict:
    import i18n
    filas = esquema.filas("venta")
    if not any(f.get("codigo") is not None for f in filas):
        return {
            "available": False,
            "reason": i18n.t("core.forecast.sin_ventas", lang),
            "as_of": fechas.hoy().isoformat(),
            "items": [],
        }

    today = fechas.hoy()
    cutoff = _period(*_shift_month(today.year, today.month, -11))
    by_product = _monthly_totals(filas)
    catalogo = {d.get("codigo"): d for d in store.raw_actual()}
    horizon = [_shift_month(today.year, today.month, i) for i in range(1, 4)]
    items = []

    for codigo, by_month in sorted(by_product.items()):
        recent = [p for p in by_month if p >= cutoff]
        if not recent:
            items.append({
                "product_code": codigo,
                "description": (catalogo.get(codigo) or {}).get("descripcion") or "",
                "available": False,
                "reason": i18n.t("core.forecast.sin_demanda_reciente", lang),
                "months": [],
                "confidence": "low",
                "trend": None,
                "stockout_risk": False,
            })
            continue

        residuals, actuals = _residuals(by_month, today)
        interval_ok = len(residuals) >= 6
        stdev = statistics.stdev(residuals) if interval_ok else 0.0
        mean_actual = (sum(actuals) / len(actuals)) if actuals else 0.0
        cv = (stdev / mean_actual) if interval_ok and mean_actual else None
        months = []
        trend_used = 1.0
        for i, (y, m) in enumerate(horizon):
            qty, amount, trend = _point_forecast(by_month, y, m)
            if i == 0:
                trend_used = trend
            qty = max(0.0, qty)
            amount = max(0.0, amount)
            band = 1.96 * stdev if interval_ok else None
            months.append({
                "period": _period(y, m),
                "qty": round(qty, 2),
                "amount": round(amount, 2),
                "qty_low": round(max(0.0, qty - band), 2) if band is not None else None,
                "qty_high": round(qty + band, 2) if band is not None else None,
                "interval_ok": interval_ok,
            })
        art = catalogo.get(codigo) or {}
        cover = stock.projected_stock(art)
        stockout_risk = bool(months) and months[0]["qty"] > cover
        items.append({
            "product_code": codigo,
            "description": art.get("descripcion") or "",
            "available": True,
            "months": months,
            "confidence": _confidence(cv, interval_ok),
            "trend": round(trend_used, 4),
            "stockout_risk": stockout_risk,
        })

    return {
        "available": True,
        "as_of": today.isoformat(),
        "items": items,
    }
