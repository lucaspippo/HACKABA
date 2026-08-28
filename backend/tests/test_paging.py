"""Shared filter / sort / slice helper for operational CRUD lists."""

from core.paging import page_rows, rows_to_csv


def test_page_rows_slices_and_reports_total():
    rows = [{"n": i, "name": f"item-{i}"} for i in range(10)]
    page = page_rows(rows, offset=4, limit=3)
    assert page["total"] == 10
    assert page["offset"] == 4
    assert page["limit"] == 3
    assert [r["n"] for r in page["items"]] == [4, 5, 6]
    assert page["has_more"] is True


def test_page_rows_search_is_case_insensitive_across_fields():
    rows = [
        {"producto": "Harina 000", "codigo": 1},
        {"producto": "Aceite", "codigo": 2},
        {"producto": "Azúcar", "codigo": 10},
    ]
    page = page_rows(rows, q="ACE", search_in=("producto", "codigo"))
    assert page["total"] == 1
    assert page["items"][0]["producto"] == "Aceite"

    by_code = page_rows(rows, q="10", search_in=("producto", "codigo"))
    assert by_code["total"] == 1
    assert by_code["items"][0]["producto"] == "Azúcar"


def test_page_rows_sorts_strings_and_numbers():
    rows = [
        {"producto": "C", "cantidad": 2},
        {"producto": "a", "cantidad": 10},
        {"producto": "B", "cantidad": 1},
    ]
    alpha = page_rows(rows, sort="producto", direction="asc")
    assert [r["producto"] for r in alpha["items"]] == ["a", "B", "C"]

    qty = page_rows(rows, sort="cantidad", direction="desc")
    assert [r["cantidad"] for r in qty["items"]] == [10, 2, 1]


def test_page_rows_filters_equals_and_date_range():
    rows = [
        {"source": "odoo", "fecha": "2026-07-01", "producto": "A"},
        {"source": "odoo", "fecha": "2026-07-10", "producto": "B"},
        {"fecha": "2026-06-01", "producto": "C"},
    ]
    odoo = page_rows(rows, equals={"source": "odoo"})
    assert odoo["total"] == 2

    july = page_rows(rows, date_field="fecha", date_from="2026-07-01", date_to="2026-07-31")
    assert [r["producto"] for r in july["items"]] == ["A", "B"]


def test_page_rows_missing_source_does_not_match_odoo():
    rows = [{"producto": "CSV"}, {"source": "odoo", "producto": "Odoo"}]
    page = page_rows(rows, equals={"source": "odoo"})
    assert page["total"] == 1
    assert page["items"][0]["producto"] == "Odoo"


def test_page_rows_filters_empty_fields():
    rows = [
        {"po_number": "PO1", "producto": "A"},
        {"po_number": "", "producto": "B"},
        {"producto": "C"},
    ]
    page = page_rows(rows, empty=("po_number",))
    assert {r["producto"] for r in page["items"]} == {"B", "C"}


def test_collect_facets_unique_sorted():
    from core.paging import collect_facets
    rows = [
        {"proveedor": "Molinos", "deposito": "WH"},
        {"proveedor": "acme", "deposito": "WH"},
        {"proveedor": "Molinos", "deposito": ""},
        {"proveedor": None},
    ]
    facets = collect_facets(rows, ("proveedor", "deposito"))
    assert facets["proveedor"] == ["acme", "Molinos"]
    assert facets["deposito"] == ["WH"]


def test_rows_to_csv_emits_headers_and_values():
    csv = rows_to_csv(
        [{"fecha": "2026-07-01", "producto": "Harina", "cantidad": 2}],
        columns=("fecha", "producto", "cantidad"),
    )
    lines = csv.strip().splitlines()
    assert lines[0] == "fecha,producto,cantidad"
    assert lines[1] == "2026-07-01,Harina,2"


def test_rows_to_csv_escapes_commas_and_quotes():
    csv = rows_to_csv(
        [{"producto": 'Harina, "000"', "cantidad": 1}],
        columns=("producto", "cantidad"),
    )
    assert '"Harina, ""000"""' in csv
