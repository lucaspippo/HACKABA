import datetime

import pytest

from core import esquema, fechas, forecast, store
from tests.conftest import limpiar_tabla_tenant


@pytest.fixture(autouse=True)
def limpio(monkeypatch):
    limpiar_tabla_tenant("data_sections")
    store.resetear_actual()
    monkeypatch.setattr(fechas, "hoy", lambda: datetime.date(2026, 4, 7))
    yield
    limpiar_tabla_tenant("data_sections")
    store.resetear_actual()


def _seed_months(codigo, descripcion, months_qty, precio=10.0):
    filas = []
    for period, qty in months_qty:
        filas.append({
            "fecha": f"{period}-15",
            "producto": descripcion,
            "codigo": codigo,
            "cantidad": qty,
            "precio": precio,
        })
    esquema.reemplazar_filas("venta", filas)


def _twenty_four_months(may_qty=100, other_qty=10):
    """2024-04 … 2026-03: May is the spike, every other month is flat."""
    out = []
    y, m = 2024, 4
    for _ in range(24):
        qty = may_qty if m == 5 else other_qty
        out.append((f"{y:04d}-{m:02d}", qty))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def test_forecast_empty_ventas_unavailable():
    r = forecast.forecast_demand()
    assert r["available"] is False
    assert r["items"] == []
    assert "ventas" in r["reason"].lower() or "sales" in r["reason"].lower()
    assert r["as_of"] == "2026-04-07"


def test_forecast_may_spike_beats_trend_only_baseline():
    art = store.raw_actual()[0]
    codigo = art["codigo"]
    raw = store.raw_actual()
    raw[0]["stock"] = 10
    raw[0]["incoming_qty"] = 0
    raw[0]["outgoing_qty"] = 0
    store.guardar(raw)

    _seed_months(codigo, art["descripcion"], _twenty_four_months())
    r = forecast.forecast_demand()
    assert r["available"] is True
    item = next(i for i in r["items"] if i["product_code"] == codigo)
    assert item["available"] is True
    periods = [m["period"] for m in item["months"]]
    assert periods == ["2026-05", "2026-06", "2026-07"]
    may = item["months"][0]
    assert may["qty"] > 50  # well above the flat-10 trend-only baseline
    jun = item["months"][1]
    assert jun["qty"] < 30
    assert item["stockout_risk"] is True
    assert may["interval_ok"] is True
    assert may["qty_low"] is not None and may["qty_high"] is not None


def test_forecast_young_sku_has_no_interval():
    art = store.raw_actual()[0]
    codigo = art["codigo"]
    _seed_months(codigo, art["descripcion"], [
        ("2026-01", 4), ("2026-02", 5), ("2026-03", 6),
    ])
    r = forecast.forecast_demand()
    item = next(i for i in r["items"] if i["product_code"] == codigo)
    assert item["available"] is True
    assert item["confidence"] == "low"
    assert item["months"][0]["interval_ok"] is False
    assert item["months"][0]["qty_low"] is None


def test_forecast_stale_sku_unavailable():
    art = store.raw_actual()[0]
    codigo = art["codigo"]
    _seed_months(codigo, art["descripcion"], [("2024-01", 9)])
    r = forecast.forecast_demand()
    item = next(i for i in r["items"] if i["product_code"] == codigo)
    assert item["available"] is False
    assert item["months"] == []


def test_angela_tool_consultar_pronostico():
    import angela
    assert "consultar_pronostico" in {t["name"] for t in angela.TOOLS}
    r, _ = angela._run_tool("consultar_pronostico", {})
    assert r["available"] is False
