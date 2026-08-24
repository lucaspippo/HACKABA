from core.models import Articulo, Categoria, EstadoCalidad
from core import quality


def test_articulo_from_dict_mapea_campos(articulos_raw):
    a = Articulo.from_dict(articulos_raw[2])  # MANTECA SIN PRECIO
    assert a.codigo == 3
    assert a.descripcion == "MANTECA SIN PRECIO"
    assert a.estado == "activo"
    assert a.stock == 4
    assert a.pvp is None
    assert a.inmovilizado == 400


def test_articulo_from_dict_tolera_campos_faltantes():
    a = Articulo.from_dict({"codigo": 99, "descripcion": "X", "estado": "activo"})
    assert a.stock == 0.0
    assert a.costo_iva is None
    assert a.venta_x_peso is False
    assert a.inmovilizado == 0.0


def _art(raw_list, codigo):
    return Articulo.from_dict(next(r for r in raw_list if r["codigo"] == codigo))


def test_clasifica_fantasma(articulos_raw):
    issues = quality.clasificar(_art(articulos_raw, 1))
    cats = {i.categoria for i in issues}
    assert Categoria.FANTASMA in cats


def test_clasifica_negativo(articulos_raw):
    issues = quality.clasificar(_art(articulos_raw, 2))
    assert any(i.categoria == Categoria.NEGATIVO for i in issues)


def test_clasifica_sin_precio_con_impacto(articulos_raw):
    issues = quality.clasificar(_art(articulos_raw, 3))
    sin_precio = next(i for i in issues if i.categoria == Categoria.SIN_PRECIO)
    assert sin_precio.impacto_pesos == 400


def test_clasifica_balanza(articulos_raw):
    issues = quality.clasificar(_art(articulos_raw, 4))
    assert any(i.categoria == Categoria.BALANZA for i in issues)


def test_clasifica_costo_viejo(articulos_raw):
    issues = quality.clasificar(_art(articulos_raw, 5))
    assert any(i.categoria == Categoria.COSTO_VIEJO for i in issues)


def test_articulo_sano_sin_issues(articulos_raw):
    issues = quality.clasificar(_art(articulos_raw, 6))
    assert issues == []


def test_estado_general_toma_la_peor(articulos_raw):
    # el negativo (inconsistente) gana a cualquier otra
    issues = quality.clasificar(_art(articulos_raw, 2))
    assert quality.estado_general(issues) == EstadoCalidad.INCONSISTENTE


def test_estado_general_completo_sin_issues():
    assert quality.estado_general([]) == EstadoCalidad.COMPLETO


def test_libro_triado_agrupa_por_categoria(articulos_raw):
    arts = [Articulo.from_dict(r) for r in articulos_raw]
    libro = quality.libro_triado(arts)
    categorias = {g["categoria"] for g in libro["grupos"]}
    assert {"fantasma", "negativo", "sin_precio", "balanza", "costo_viejo"} <= categorias


def test_libro_triado_ordena_por_impacto_desc(articulos_raw):
    arts = [Articulo.from_dict(r) for r in articulos_raw]
    libro = quality.libro_triado(arts)
    impactos = [g["impacto_pesos"] for g in libro["grupos"]]
    assert impactos == sorted(impactos, reverse=True)


def test_libro_triado_totales(articulos_raw):
    arts = [Articulo.from_dict(r) for r in articulos_raw]
    libro = quality.libro_triado(arts)
    # 5 issues (uno por categoría); el sano no aporta
    assert libro["total_issues"] == 5
    # impacto total = sin_precio(400) + balanza(1000) + costo_viejo(600) = 2000
    assert libro["impacto_total"] == 2000


def test_store_libro_triado_sobre_inventario_real():
    from core import store
    libro = store.libro_triado()
    # El inventario real de Horizonte tiene issues en varias categorías.
    assert libro["total_issues"] > 0
    assert libro["impacto_total"] > 0
    assert any(g["categoria"] == "sin_precio" for g in libro["grupos"])
