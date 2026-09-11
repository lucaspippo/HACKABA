"""
P43 · Cada rol ve los hallazgos de SU incumbencia.

El bug que esto cierra: `/api/oportunidades` no tenía ningún gate, así que el
encargado de depósito —y el chofer del camión— recibían las mismas nueve
tarjetas que el dueño, incluidas "cobrá los $85,7M de morosos" y "3 clientes
concentran $470,8M de exposición". No es su trabajo ni su información.

Lo que se protege:
  · el recorte sale de los MÓDULOS del rol (la matriz «Quién ve qué»), nunca de
    una lista de usernames — si el dueño habilita un módulo, los hallazgos de
    ese dominio aparecen solos;
  · el dueño sigue viendo el set completo y los montos canónicos no se mueven:
    el cálculo es uno solo y cacheado, el filtro va después;
  · un hallazgo nuevo sin dominio declarado NO se filtra a quien no corresponde.
"""
import pytest

from core import oportunidades_neg as opn


def _ids(cards):
    return {c["id"] for c in cards}


def _falsas(ids):
    """Tarjetas mínimas, para probar el filtro sin depender del dataset."""
    return [{"id": i} for i in ids]


# --- el filtro, en aislamiento -------------------------------------------------

def test_todo_hallazgo_del_set_declara_de_quien_es():
    """El set de hallazgos y la tabla de dominios tienen que cubrirse. Si mañana
    se agrega una card y nadie dice a qué dominio pertenece, deja de mostrarse a
    todo el mundo (el default seguro) — pero eso se nota acá antes de deployar."""
    emitidos = {c["id"] for c in opn.cards("es")}
    if not emitidos:
        pytest.skip("sin datos en este tenant")
    faltan = sorted(emitidos - set(opn.DOMINIO))
    assert not faltan, f"hallazgos sin dominio declarado: {faltan}"


def test_los_modulos_pedidos_existen_en_la_matriz():
    """El vocabulario del filtro es el MISMO de «Quién ve qué». Si acá apareciera
    un módulo inventado, el hallazgo no se le mostraría nunca a nadie."""
    import auth
    for cid, mods in opn.DOMINIO.items():
        for m in mods:
            assert m in auth.MODULOS, f"{cid} pide un módulo inexistente: {m}"


def test_sin_modulos_no_se_ve_nada():
    assert opn.visibles_para(_falsas(opn.DOMINIO), []) == []


def test_un_hallazgo_sin_dominio_no_se_filtra_a_cualquiera():
    """El default es NO mostrar: es preferible que falte a que se le escape al
    rol equivocado la plata del negocio."""
    todos = ["panel", "cuentas", "inventario", "oportunidades", "deposito"]
    assert opn.visibles_para([{"id": "hallazgo_nuevo_sin_declarar"}], todos) == []


def test_el_dueno_ve_todo():
    import auth
    feats = auth.USUARIOS["emilio"]["features"]
    assert _ids(opn.visibles_para(_falsas(opn.DOMINIO), feats)) == set(opn.DOMINIO)


# --- lo que ve cada oficio -----------------------------------------------------

def test_deposito_ve_el_quiebre_y_nada_de_plata():
    """LA prueba del prompt: al de depósito le importa que se acabe la gaseosa,
    no quién debe ni cuánto factura el cliente más grande."""
    import usuarios_demo
    for quien in ("ramon", "tomas"):
        feats = usuarios_demo.USUARIOS[quien]["features"]
        vistos = _ids(opn.visibles_para(_falsas(opn.DOMINIO), feats))
        assert "quiebre_inminente" in vistos
        for prohibido in ("cobrar_morosos", "concentracion", "cliente_frio",
                          "margen_bajo", "ventana_compra"):
            assert prohibido not in vistos, f"{quien} no debería ver {prohibido}"


def test_el_reparto_no_recibe_hallazgos_de_negocio():
    import usuarios_demo
    feats = usuarios_demo.USUARIOS["walter"]["features"]
    assert opn.visibles_para(_falsas(opn.DOMINIO), feats) == []


def test_el_preventista_ve_su_cobranza_pero_no_la_exposicion_global():
    """El matiz del prompt: cobrar a SUS clientes es su trabajo; cuánto del
    negocio depende de tres nombres es una lectura de estrategia, no de calle."""
    import usuarios_demo
    feats = usuarios_demo.USUARIOS["diego"]["features"]
    vistos = _ids(opn.visibles_para(_falsas(opn.DOMINIO), feats))
    assert "cobrar_morosos" in vistos and "cliente_frio" in vistos
    assert "concentracion" not in vistos


def test_compras_ve_lo_de_comprar_y_nada_de_clientes():
    import usuarios_demo
    feats = usuarios_demo.USUARIOS["celeste"]["features"]
    vistos = _ids(opn.visibles_para(_falsas(opn.DOMINIO), feats))
    assert {"ventana_compra", "sobrecompra", "quiebre_inminente"} <= vistos
    assert "cobrar_morosos" not in vistos and "concentracion" not in vistos


def test_nadie_menos_el_dueno_ve_la_exposicion_de_470m():
    """La card de $470,8M pide cuentas + oportunidades a la vez: es la única
    combinación que sólo tiene quien administra el negocio entero."""
    import usuarios_demo
    for quien, v in usuarios_demo.USUARIOS.items():
        if v.get("interno"):
            continue
        vistos = _ids(opn.visibles_para(_falsas(opn.DOMINIO), v["features"]))
        if "concentracion" in vistos:
            assert v.get("es_admin"), f"{quien} no debería ver la exposición global"


# --- el filtro no toca el cálculo ----------------------------------------------

def test_el_filtro_no_mueve_los_canonicos():
    """El recorte es de presentación: se aplica DESPUÉS del cache, sobre la misma
    lista. Los montos que ve el dueño son exactamente los calculados."""
    todas = opn.cards("es")
    if not todas:
        pytest.skip("sin datos en este tenant")
    import auth
    del_dueno = opn.visibles_para(todas, auth.USUARIOS["emilio"]["features"])
    assert [c["id"] for c in del_dueno] == [c["id"] for c in todas]
    assert [c.get("monto") for c in del_dueno] == [c.get("monto") for c in todas]


def test_el_filtro_no_reordena():
    """El orden por monto lo decide `cards()`; el filtro sólo saca."""
    import usuarios_demo
    todas = _falsas(["concentracion", "cobrar_morosos", "quiebre_inminente",
                     "margen_bajo", "cliente_frio"])
    feats = usuarios_demo.USUARIOS["vanesa"]["features"]
    vistos = [c["id"] for c in opn.visibles_para(todas, feats)]
    assert vistos == ["cobrar_morosos", "quiebre_inminente", "cliente_frio"]


# --- la voz, extendida a los oficios físicos -----------------------------------

def test_el_motor_de_voz_ya_contemplaba_los_tres_oficios():
    """C2 no agrega capacidad al backend: la expone donde faltaba. `entrega` es
    del reparto y `reposicion` del mostrador — ya existían."""
    from core import voz
    assert {"entrega", "reposicion", "faltante", "conteo"} <= set(voz.INTENCIONES)
    assert "reparto" in voz._SISTEMA and "mostrador" in voz._SISTEMA
