import datetime
import os

from core import odoo_fx


def test_to_company_amount_uses_dated_rate_not_flat():
    rates = odoo_fx.normalize_rates([
        {"name": "2024-08-01", "currency_id": [2, "USD"], "rate": 1 / 950,
         "inverse_company_rate": 950.0},
        {"name": "2026-07-07", "currency_id": [2, "USD"], "rate": 1 / 1450,
         "inverse_company_rate": 1450.0},
    ])
    early = odoo_fx.to_company_amount(10, "USD", "2024-08-15", rates, "ARS")
    late = odoo_fx.to_company_amount(10, "USD", "2026-07-07", rates, "ARS")
    assert early == 9500.0
    assert late == 14500.0
    assert early != late


def test_to_company_amount_same_currency_unchanged():
    rates = odoo_fx.normalize_rates([
        {"name": "2026-07-07", "currency_id": [2, "USD"], "inverse_company_rate": 1450.0},
    ])
    assert odoo_fx.to_company_amount(100, "ARS", "2026-07-07", rates, "ARS") == 100
    assert odoo_fx.to_company_amount(100, None, "2026-07-07", rates, "ARS") == 100


def test_normalize_rates_derives_inverse_from_rate():
    rates = odoo_fx.normalize_rates([
        {"name": "2026-01-01", "currency_id": [2, "USD"], "rate": 1 / 1200},
    ])
    assert abs(rates[0]["inverse_company_rate"] - 1200) < 0.01


def test_classify_invoice_aging_open_vs_overdue():
    as_of = datetime.date(2026, 7, 20)
    open_inv = odoo_fx.classify_invoice_aging("not_paid", "2026-08-01", as_of, 500)
    overdue = odoo_fx.classify_invoice_aging("not_paid", "2026-06-01", as_of, 500)
    paid = odoo_fx.classify_invoice_aging("paid", "2026-06-01", as_of, 0)
    partial = odoo_fx.classify_invoice_aging("partial", "2026-08-01", as_of, 120)
    partial_overdue = odoo_fx.classify_invoice_aging("partial", "2026-05-01", as_of, 120)
    assert open_inv["aging"] == "open" and open_inv["overdue"] is False
    assert overdue["aging"] == "overdue" and overdue["overdue"] is True
    assert paid["aging"] == "paid"
    assert partial["aging"] == "partial"
    assert partial_overdue["aging"] == "overdue"
    assert partial["amount_residual"] == 120


def test_hoy_facturas_uses_seed_date_when_demo_today_set(monkeypatch):
    monkeypatch.setenv("POLPILOT_DEMO_TODAY", "2026-07-07")
    monkeypatch.delenv("POLPILOT_INVOICE_TODAY", raising=False)
    assert odoo_fx.hoy_facturas() == datetime.date(2026, 7, 20)


def test_resolve_wholesale_only_vs_needs_pricing():
    pricelists = [
        {"id": 10, "name": "Mayorista ARS", "currency_id": [1, "ARS"]},
        {"id": 11, "name": "Minorista ARS", "currency_id": [1, "ARS"]},
        {"id": 12, "name": "Mayorista USD", "currency_id": [2, "USD"]},
    ]
    wholesale = odoo_fx.resolve_product_pricing(
        {"id": 1, "list_price": 0, "categ_id": [4, "Electronics"]},
        pricelists,
        [{"pricelist_id": [10, "Mayorista ARS"], "applied_on": "1_product",
          "compute_price": "fixed", "fixed_price": 8500.0, "product_tmpl_id": [1, "X"]}],
    )
    assert wholesale["pricing_status"] == odoo_fx.PRICING_WHOLESALE_ONLY
    assert wholesale["precio"] == 8500.0
    assert wholesale["precio_lista"] == 0.0

    unpriced = odoo_fx.resolve_product_pricing(
        {"id": 2, "list_price": 0, "categ_id": [4, "Electronics"]},
        pricelists, [],
    )
    assert unpriced["pricing_status"] == odoo_fx.PRICING_NEEDS_PRICING
    assert unpriced["precio"] is None


def test_resolve_usd_fixed_not_converted_from_list_price():
    pricelists = [
        {"id": 12, "name": "Minorista USD", "currency_id": [2, "USD"]},
    ]
    resolved = odoo_fx.resolve_product_pricing(
        {"id": 5, "list_price": 1_200_000, "categ_id": [4, "Electronics"]},
        pricelists,
        [{"pricelist_id": [12, "Minorista USD"], "applied_on": "1_product",
          "compute_price": "fixed", "fixed_price": 890.0, "product_tmpl_id": [5, "Laptop"]}],
    )
    usd = next(e for e in resolved["precios_pricelist"] if e["currency"] == "USD")
    assert usd["price"] == 890.0
    assert usd["origin"] == "fixed"
    # Must NOT be ARS list_price / some rate.
    assert usd["price"] != 1_200_000


def test_category_formula_discount():
    pricelists = [{"id": 10, "name": "Mayorista ARS", "currency_id": [1, "ARS"]}]
    resolved = odoo_fx.resolve_product_pricing(
        {"id": 7, "list_price": 1000, "categ_id": [8, "Office"]},
        pricelists,
        [{"pricelist_id": [10, "Mayorista ARS"], "applied_on": "2_product_category",
          "compute_price": "formula", "price_discount": 20.0, "categ_id": [8, "Office"]}],
    )
    mayorista = resolved["precios_pricelist"][0]
    assert mayorista["price"] == 800.0
    assert mayorista["origin"] == "formula"
    assert resolved["pricing_status"] == odoo_fx.PRICING_RETAIL
    assert resolved["precio"] == 1000  # list_price remains the retail reference


def test_fulfillment_partial_with_open_backorder():
    assert odoo_fx.fulfillment(10, 0) == "none"
    assert odoo_fx.fulfillment(10, 10) == "complete"
    assert odoo_fx.fulfillment(10, 4) == "partial"
    assert odoo_fx.fulfillment(10, 10, open_backorder=True) == "partial"


def test_is_open_backorder_pending_only():
    assert odoo_fx.is_open_backorder({"backorder_id": [9, "WH/IN/00001"], "state": "assigned"})
    assert not odoo_fx.is_open_backorder({"backorder_id": [9, "WH/IN/00001"], "state": "cancel"})
    assert not odoo_fx.is_open_backorder({"backorder_id": False, "state": "assigned"})
