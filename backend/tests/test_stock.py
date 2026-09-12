"""projected_stock is the single operational cover quantity."""
from core import stock


def test_csv_article_without_pipeline_equals_on_hand():
    art = {"stock": 40}
    assert stock.projected_stock(art) == 40
    assert stock.days_of_cover(art, 4) == 10


def test_incoming_extends_cover_outgoing_reduces_it():
    art = {"stock": 10, "incoming_qty": 30, "outgoing_qty": 5}
    assert stock.projected_stock(art) == 35
    assert stock.days_of_cover(art, 7) == 5


def test_fully_reserved_is_zero_cover_not_negative_days():
    art = {"stock": 20, "incoming_qty": 0, "outgoing_qty": 20}
    assert stock.projected_stock(art) == 0
    assert stock.days_of_cover(art, 2) == 0


def test_over_reserved_does_not_invent_negative_cover():
    art = {"stock": 5, "outgoing_qty": 12}
    assert stock.projected_stock(art) == -7
    assert stock.days_of_cover(art, 1) == 0


def test_zero_rate_is_zero_cover():
    assert stock.days_of_cover({"stock": 100}, 0) == 0
