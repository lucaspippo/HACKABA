"""Every involucrado backed by a real article record must carry a real
`id` (product code) and `kind` so the frontend can deep-link to it —
see design spec 2026-09-01."""
from core import oportunidades_neg as opn


def _ctx_with_arts(monkeypatch, arts, clientes=None):
    base_ctx = opn._ctx("es")
    base_ctx["arts"] = arts
    base_ctx["clientes"] = clientes or []
    return base_ctx


def test_dormido_involucrados_carry_product_id(monkeypatch):
    from core import analisis
    monkeypatch.setattr(analisis, "rotacion", lambda lang: {
        "disponible": True, "pct_dormido": 10,
        "por_estado": {"dormido": 500_000},
        "dormidos_top": [{"codigo": "P1", "producto": "Prod Uno",
                          "inmovilizado": 500_000, "dias_rotacion": None}],
    })
    ctx = _ctx_with_arts(monkeypatch, [])
    card = opn._card_dormido("es", ctx)
    assert card is not None
    iv = card["drill"]["involucrados"][0]
    assert iv["id"] == "P1" and iv["kind"] == "product"


def test_margen_bajo_involucrados_carry_product_id(monkeypatch):
    from core import analisis
    arts = [{"codigo": f"P{i}", "descripcion": f"Prod {i}", "tipo": "cat",
             "pvp": 100, "costo_iva": 60 + (i % 2) * 20} for i in range(6)]
    monkeypatch.setattr(analisis, "rotacion", lambda lang: {
        "disponible": True,
        "detalle": [{"producto": a["descripcion"], "unidades_12m": 120} for a in arts],
    })
    ctx = _ctx_with_arts(monkeypatch, arts)
    card = opn._card_margen_bajo("es", ctx)
    assert card is not None
    for iv in card["drill"]["involucrados"]:
        assert iv.get("kind") == "product"
        assert iv.get("id")
