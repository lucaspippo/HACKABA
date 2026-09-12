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


def test_costo_viejo_drill_has_product_involucrados(monkeypatch):
    from core import store
    monkeypatch.setattr(store, "panorama", lambda: {"alertas": {"costo_viejo": {"cantidad": 1}},
                                                     "grupos": {"costo_viejo": [
                                                         {"codigo": "P3", "descripcion": "Prod Tres",
                                                          "inmovilizado": 20_000,
                                                          "antiguedad_costo_dias": 400}]}})
    out = priorities._alerts_inventario("es")
    cv = next(i for i in out if i["id"] == "costo_viejo")
    assert cv["drill"]["grafico"] is not None
    iv = cv["drill"]["involucrados"][0]
    assert iv["id"] == "P3" and iv["kind"] == "product"


def test_caida_interanual_drill_has_chart(monkeypatch):
    from core import evolucion
    pan = {"hay_datos": True,
          "serie": [{"mes": "2026-01", "nominal": 100, "real": 95},
                    {"mes": "2026-02", "nominal": 110, "real": 90}]}
    monkeypatch.setattr(evolucion, "panorama", lambda lang: pan)
    monkeypatch.setattr(evolucion, "alertas_de", lambda p, lang: [
        {"titulo": "Caída real", "detalle": "cayó"}])
    out = priorities._alerts_evolucion("es")
    a = out[0]
    assert a["drill"]["grafico"] is not None
    assert len(a["drill"]["grafico"]["series"][0]["puntos"]) == 2


def test_caja_inusual_drill_has_chart(monkeypatch):
    from core import caja
    monkeypatch.setattr(caja, "estado", lambda: {
        "abierta": True,
        "totales": {"total": 500_000},
        "historial": [{"fecha": f"2026-06-2{i}", "total": 260_000, "diferencia": 0}
                     for i in range(5)],
    })
    out = priorities._alerts_caja("es")
    a = out[0]
    assert a["drill"]["grafico"] is not None
    assert len(a["drill"]["grafico"]["series"][0]["puntos"]) == 6
