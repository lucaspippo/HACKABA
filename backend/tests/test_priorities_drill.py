"""Alert-only card types must carry real drill data (chart, involucrados
with a real product id) instead of an empty/blank drill — see design spec
2026-09-01."""
from core import priorities


def test_dep_vencidos_drill_has_product_involucrados(monkeypatch):
    from core import deposito, store
    monkeypatch.setattr(deposito, "resumen", lambda: {"vencidos": 1, "por_vencer": 0,
                                                       "discrepancias": 0})
    monkeypatch.setattr(deposito, "vencidos", lambda: [
        {"codigo": "P1", "producto": "Prod Uno", "cantidad": 5, "dias_vencido": 3}])
    monkeypatch.setattr(store, "raw_actual", lambda: [
        {"codigo": "P1", "descripcion": "Prod Uno", "costo_iva": 1000}])
    out = priorities._alerts_deposito("es")
    dep_venc = next(i for i in out if i["id"] == "dep_vencidos")
    assert dep_venc["drill"]["porque"]
    assert dep_venc["drill"]["grafico"] is not None
    iv = dep_venc["drill"]["involucrados"][0]
    assert iv["id"] == "P1" and iv["kind"] == "product"


def test_venc_riesgo_drill_has_product_involucrados(monkeypatch):
    from core import vencimientos
    monkeypatch.setattr(vencimientos, "en_riesgo", lambda dias, lang: {
        "disponible": True, "lotes_en_riesgo": 1, "total_en_riesgo": 5000,
        "items": [{"codigo": "P2", "producto": "Prod Dos", "dias_restantes": 4,
                  "plata_en_riesgo": 5000}]})
    out = priorities._alerts_deposito("es")
    venc = next(i for i in out if i["id"] == "venc_riesgo")
    assert venc["drill"]["grafico"] is not None
    iv = venc["drill"]["involucrados"][0]
    assert iv["id"] == "P2" and iv["kind"] == "product"
