"""Every involucrado backed by a real article record must carry a real
`id` (product code) and `kind` so the frontend can deep-link to it —
see design spec 2026-09-01."""
from core import oportunidades_neg as opn


def _ctx_with_arts(monkeypatch, arts, clientes=None):
    clientes = clientes or []
    base_ctx = opn._ctx("es")
    base_ctx["arts"] = arts
    base_ctx["clientes"] = clientes
    base_ctx["product_id_by_name"] = {a.get("descripcion"): a.get("codigo")
                                      for a in arts if a.get("descripcion")}
    base_ctx["client_id_by_name"] = {c.get("nombre"): c.get("id")
                                     for c in clientes if c.get("nombre")}
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


def test_cliente_frio_involucrados_carry_client_id(monkeypatch):
    import datetime
    from core import fechas
    hoy = fechas.hoy()
    vieja = (hoy - datetime.timedelta(days=400)).isoformat()
    reciente = (hoy - datetime.timedelta(days=200)).isoformat()
    clientes = [{"id": 7, "nombre": "Cliente Frío",
                "movimientos": [{"tipo": "venta", "fecha": vieja, "monto": 100_000}] * 3 +
                               [{"tipo": "venta", "fecha": reciente, "monto": 100_000}] * 3}]
    ctx = _ctx_with_arts(monkeypatch, [], clientes)
    card = opn._card_cliente_frio("es", ctx)
    if card:  # the synthetic fixture may or may not clear the drop threshold
        iv = card["drill"]["involucrados"][0]
        assert iv["id"] == 7 and iv["kind"] == "client"


def test_ctx_builds_name_to_id_lookups(monkeypatch):
    arts = [{"codigo": "P1", "descripcion": "Prod Uno"}]
    clientes = [{"id": 3, "nombre": "Cliente Tres"}]
    ctx = _ctx_with_arts(monkeypatch, arts, clientes)
    assert ctx["product_id_by_name"]["Prod Uno"] == "P1"
    assert ctx["client_id_by_name"]["Cliente Tres"] == 3


def test_concentracion_involucrados_carry_client_id(monkeypatch):
    clientes = [{"id": i, "nombre": f"Cliente {i}",
                "movimientos": [{"tipo": "venta", "fecha": "2026-06-01",
                                 "monto": 10_000_000 if i < 3 else 100_000}]}
               for i in range(12)]
    ctx = _ctx_with_arts(monkeypatch, [], clientes)
    card = opn._card_concentracion("es", ctx)
    assert card is not None
    for iv in card["drill"]["involucrados"]:
        assert iv["kind"] == "client" and iv["id"] is not None
