from core import importer


def test_inferir_mapeo_ventas_tipico():
    headers = ["Fecha", "Sucursal", "Producto", "Cantidad", "Precio Unitario", "Costo"]
    r = importer.inferir_mapeo(headers, "venta_historica")
    m = r["mapeo"]
    assert m["fecha"] == "Fecha"
    assert m["boca"] == "Sucursal"
    assert m["articulo"] == "Producto"
    assert m["cantidad"] == "Cantidad"
    assert m["precio"] == "Precio Unitario"
    assert m["costo"] == "Costo"


def test_inferir_mapeo_reporta_sin_mapear():
    headers = ["Fecha", "Producto", "ColumnaRara"]
    r = importer.inferir_mapeo(headers, "venta_historica")
    assert "ColumnaRara" in r["sin_mapear"]


def test_previsualizar_csv(tmp_path):
    p = tmp_path / "ventas.csv"
    p.write_text(
        "Fecha,Producto,Cantidad,Precio\n"
        "2026-01-02,MANTECA,10,1500\n"
        "2026-01-03,QUESO,5,3000\n",
        encoding="utf-8",
    )
    info = importer.previsualizar(str(p), "venta_historica")
    assert info["total_filas"] == 2
    assert info["mapeo"]["articulo"] == "Producto"
    assert len(info["filas_ejemplo"]) == 2
    assert info["mapeados"] >= 3
