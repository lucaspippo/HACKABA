from core import rotacion


def test_metricas_excedente():
    # Vendo 300 u en 30 días = 10/día. Cobertura 30 días → necesito 300.
    # Tengo 500 en stock → excedente 200 × costo 100 = $20.000.
    m = rotacion.metricas_articulo(
        stock_actual=500, costo_unitario=100, unidades_vendidas=300, dias_periodo=30,
        dias_reposicion=7, dias_cobertura=30,
    )
    assert m["demanda_diaria"] == 10
    assert m["stock_seguridad"] == 70
    assert m["stock_necesario"] == 300
    assert m["stock_excedente"] == 200
    assert m["plata_excedente"] == 20000


def test_sin_excedente_si_stock_bajo():
    m = rotacion.metricas_articulo(100, 50, 300, 30)  # necesito 300, tengo 100
    assert m["stock_excedente"] == 0
    assert m["plata_excedente"] == 0


def test_analizar_dry_run_sin_ventas():
    arts = [{"codigo": 1, "stock": 10, "costo_iva": 100, "inmovilizado": 1000}]
    r = rotacion.analizar(arts)
    assert r["disponible"] is False
    assert r["inmovilizado_total"] == 1000


def test_analizar_con_ventas():
    arts = [{"codigo": 1, "stock": 500, "costo_iva": 100, "inmovilizado": 50000}]
    r = rotacion.analizar(arts, ventas_por_codigo={1: 300}, dias_periodo=30)
    assert r["disponible"] is True
    assert r["plata_excedente"] == 20000
