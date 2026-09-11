"""EL CEREBRO — que el grafo de entidades no invente ni se rompa.

Lo que se protege acá es lo que hace confiable la vista: que la co-venta salga
de un cálculo y no de la nada, que la única relación inferida viaje marcada como
tal, que el grafo no se parta en islas y que el camino de un hallazgo apunte a
entidades que existen.
"""
from core import grafo


# --- co-venta: es un cálculo, y tiene que poder fallar ----------------------

def test_coventa_ignora_pares_que_no_se_repiten():
    # dos productos juntos UNA sola vez no son una relación: son una casualidad
    canastas = {(f"d{i}", "C"): {1, 2} for i in range(20)}
    canastas[("solo", "C")] = {3, 4}
    pares = grafo._coventa(canastas)
    juntos = {(a, b) for a, b, _n, _l in pares}
    assert (3, 4) not in juntos


def test_coventa_exige_lift_no_solo_frecuencia():
    # 1 y 2 aparecen en TODAS las canastas: juntos mucho, pero no más de lo que
    # el azar explica (lift ≈ 1). No es una relación.
    canastas = {(f"d{i}", "C"): {1, 2} for i in range(40)}
    for a, b, _n, lift in grafo._coventa(canastas):
        if {a, b} == {1, 2}:
            assert lift >= grafo.COVENTA_LIFT_MIN


def test_coventa_sin_historial_no_inventa():
    assert grafo._coventa({("d1", "C"): {1, 2}}) == []


def test_coventa_descarta_canastas_gigantes():
    # un día con 200 productos no dice nada de ningún par en particular
    grande = {(f"d{i}", "C"): set(range(200)) for i in range(30)}
    assert grafo._coventa(grande) == []


# --- la afinidad: la única inferencia, y no puede disfrazarse de dato -------

def test_afinidad_distingue_el_rubro_del_cliente():
    rubros = {"golosinas_y_galletitas": "rubro:gol", "congelados": "rubro:cong",
              "bebidas": "rubro:beb", "lacteos": "rubro:lac"}
    kiosco = grafo._rubros_afines("Kiosco La Terminal", rubros)
    rotiseria = grafo._rubros_afines("Rotisería Avenida", rubros)
    assert "rubro:gol" in kiosco
    assert "rubro:cong" not in kiosco        # un kiosco no compra congelados
    assert "rubro:cong" in rotiseria


def test_afinidad_no_adivina_cuando_no_reconoce_el_rubro():
    assert grafo._rubros_afines("Zzz S.A.", {"bebidas": "rubro:beb"}) == []


def test_aristas_de_afinidad_van_marcadas_como_inferidas():
    g = grafo.construir()
    afin = [a for a in g["aristas"] if a["rel"] == "afinidad"]
    if afin:  # el piloto puede no tener rubros cargados
        assert all(a.get("inferida") is True for a in afin)
    # y ninguna OTRA relación puede venir marcada: el resto es dato
    assert not [a for a in g["aristas"] if a["rel"] != "afinidad" and a.get("inferida")]


# --- estructura -------------------------------------------------------------

def test_toda_arista_apunta_a_nodos_que_existen():
    g = grafo.construir()
    ids = {n["id"] for n in g["nodos"]}
    for a in g["aristas"]:
        assert a["source"] in ids and a["target"] in ids
        assert a["source"] != a["target"]


def test_el_grado_es_el_que_se_cuenta_en_las_aristas():
    g = grafo.construir()
    real = {}
    for a in g["aristas"]:
        real[a["source"]] = real.get(a["source"], 0) + 1
        real[a["target"]] = real.get(a["target"], 0) + 1
    for n in g["nodos"]:
        assert n["grado"] == real.get(n["id"], 0)


def test_el_nucleo_esta_ordenado_por_cruces():
    nucleo = grafo.completo("es")["meta"]["nucleo"]
    assert nucleo == sorted(nucleo, key=lambda n: -n["grado"])


def test_los_recortes_se_declaran_no_se_esconden():
    meta = grafo.completo("es")["meta"]
    assert meta["derivados"]["coventa"]["como"]
    assert meta["recortes"]["local_top"] == grafo.LOCAL_TOP


# --- el camino de un hallazgo ----------------------------------------------

def test_camino_solo_usa_entidades_del_grafo():
    g = grafo.construir()
    ids = {n["id"] for n in g["nodos"]}
    cards = [{"id": "quiebre", "titulo": "x",
              "datos": {"producto": g["nodos"][0]["nombre"]}}]
    for c in grafo.caminos(g, cards):
        assert set(c["nodos"]) <= ids
        assert all(0 <= i < len(g["aristas"]) for i in c["aristas"])


def test_camino_no_explota_con_datos_raros():
    g = grafo.construir()
    # `productos` a veces es un CONTEO, no una lista (ventana_compra: 27)
    raras = [{"id": "a", "datos": {"productos": 27}},
             {"id": "b", "datos": None},
             {"id": "c", "datos": {"cliente": "no existe ningún cliente así"}},
             {"id": "d"}]
    # ninguna de estas resuelve una entidad: la lista tiene que salir vacía,
    # no lanzar (un TypeError acá apaga los caminos de TODOS los hallazgos)
    assert grafo.caminos(g, raras) == []


def test_un_hallazgo_sin_entidades_no_deja_camino_vacio():
    g = grafo.construir()
    cams = grafo.caminos(g, [{"id": "x", "datos": {"cliente": "zzz inexistente"}}])
    assert all(c["nodos"] for c in cams)


# --- el contrato del endpoint ----------------------------------------------

def test_completo_no_filtra_los_indices_internos():
    r = grafo.completo("es")
    assert "_indice" not in r and "_por_codigo" not in r
    assert set(r) == {"disponible", "nodos", "aristas", "caminos", "meta"}
