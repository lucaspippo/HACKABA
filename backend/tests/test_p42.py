"""
P42 · Cobranzas para el dueño + BLOQUE F: human-in-the-loop VISIBLE.

Lo que se protege acá no es una feature: es el argumento de confianza. Si algo
de esto se rompe en silencio, el producto sigue funcionando y deja de ser
defendible — que es la peor forma de romperse.

  1. El dueño ve Cobranzas, y la ve DESDE ARRIBA (el panorama), sin que eso
     cambie un solo número de la lista que ve el preventista.
  2. Toda acción auditada está DECLARADA: qué toca y cómo se ejecutó. Una acción
     nueva sin declarar cae en `otros` — visible, nunca escondida.
  3. Nada que toque plata, stock o permisos se ejecuta sin un sí humano. Ni el
     código lo permite, ni hay setting que lo habilite.
"""
import pytest

from core import auditoria, autonomia, cobranza


# --- PARTE 1 · Cobranzas también es del dueño ---------------------------------

def test_el_dueno_tiene_cobranzas_y_el_preventista_tambien():
    """La sección deja de ser exclusiva del preventista sin sacársela a él."""
    import auth
    assert "cobranzas" in auth.USUARIOS["emilio"]["features"]
    assert "cobranzas" in auth.USUARIOS["vendedor"]["features"]


def test_el_dueno_del_demo_tambien():
    import usuarios_demo
    assert "cobranzas" in usuarios_demo.USUARIOS["aldo"]["features"]


def test_la_matriz_quien_ve_que_tilda_cobranzas_para_el_dueno():
    """«Quién ve qué» sale de features_efectivas: si el seed cambió, la celda
    se tilda sola. Sin esta prueba el panel y la realidad se pueden ir separando."""
    from core import perfiles
    fila = next(f for f in perfiles.matriz() if f["username"] == "emilio")
    assert fila["modulos"]["cobranzas"] is True
    assert fila["modulos"]["auditoria"] is True


def test_el_panorama_del_dueno_no_toca_la_lista_del_preventista():
    """La vista del dueño es la MISMA tabla mirada desde otra altura: se agrega
    un bloque derivado, no se reordena ni se recalcula nada."""
    p = cobranza.prioridad()
    if not p["disponible"]:
        pytest.skip("sin morosos en este tenant")
    exp = [x["exposicion"] for x in p["items"]]
    assert exp == sorted(exp, reverse=True)          # el orden, intacto
    assert p["entra_si_cobras"] == round(sum(x["saldo"] for x in p["items"]), 2)
    assert p["panorama"]["disponible"] is True


def test_el_panorama_se_deriva_de_los_mismos_items():
    """Cada número del panorama tiene que poder rastrearse hasta la lista. Si
    alguno saliera de otra fuente, el dueño y el preventista verían negocios
    distintos — y uno de los dos estaría equivocado."""
    p = cobranza.prioridad()
    if not p["disponible"]:
        pytest.skip("sin morosos en este tenant")
    items, pan = p["items"], p["panorama"]
    cabeza = items[:3] if len(items) > 3 else items[:1]
    assert pan["concentracion_n"] == len(cabeza)
    assert pan["concentracion_saldo"] == round(sum(x["saldo"] for x in cabeza), 2)
    assert pan["concentracion_nombres"] == [x["cliente"] for x in cabeza]
    sin_tocar = [x for x in items if x["gestion"]["estado"] == "pendiente"]
    assert pan["sin_tocar"] == len(sin_tocar)
    assert pan["sin_tocar_saldo"] == round(sum(x["saldo"] for x in sin_tocar), 2)
    assert 0 <= pan["concentracion_share"] <= 100


def test_con_pocas_cuentas_la_concentracion_no_dice_una_obviedad():
    """Con tres morosos, «los tres primeros son el 100%» no informa nada. El
    corte lo decide el tamaño de la lista, no el copy."""
    p = cobranza.prioridad()
    if not p["disponible"]:
        pytest.skip("sin morosos en este tenant")
    pan = p["panorama"]
    if len(p["items"]) <= 3:
        assert pan["concentracion_n"] == 1
        assert pan["concentracion_share"] < 100
    else:
        assert pan["concentracion_n"] == 3


def test_sin_morosos_el_panorama_no_inventa_un_panel_vacio():
    assert cobranza._panorama([], [], []) == {"disponible": False}


# --- BLOQUE F·1 · el registro, legible ----------------------------------------

def test_toda_accion_auditada_esta_declarada():
    """El registro tiene que poder explicar CADA slug que el producto escribe.

    Se lee del CÓDIGO, no del audit.json en disco: el log de una corrida
    depende de qué se ejecutó (y los tests le escriben ruido), pero los slugs
    que el producto emite son los que están escritos en las llamadas. Si mañana
    alguien audita algo nuevo y no lo declara acá, esto lo señala: no rompe la
    pantalla, pero la acción deja de estar clasificada y eso se paga en confianza."""
    import glob
    import io
    import os
    import re
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fuentes = glob.glob(os.path.join(raiz, "core", "*.py")) + [os.path.join(raiz, "main.py")]
    emitidos = set()
    for f in fuentes:
        src = io.open(f, encoding="utf-8").read()
        emitidos |= set(re.findall(r'accion=["\']([a-z_0-9]+)["\']', src))
        # las que se pasan posicionales: record(actor, "slug", ...)
        emitidos |= set(re.findall(r'\.record\(\s*[\w\["\']+\s*,\s*["\']([a-z_0-9]+)["\']', src))
    # `core/auditoria.py` se cita a sí mismo en su tabla: no es una emisión.
    emitidos -= set(auditoria.ACCIONES)
    sin_declarar = sorted(a for a in emitidos
                          if auditoria.ficha(a)["clase"] == "otros")
    assert not sin_declarar, f"acciones sin declarar en core/auditoria.py: {sin_declarar}"


def test_las_familias_dinamicas_tambien_estan_cubiertas():
    """Dos slugs no son literales en el código: `cobranza_{estado}` y los
    `sanear_<categoria>` del libro de calidad. Se cubren igual."""
    from core import cobranza, piso
    for estado in cobranza.ESTADOS:
        assert auditoria.ficha(f"cobranza_{estado}")["clase"] == "plata"
    assert auditoria.ficha("sanear_lo_que_sea")["clase"] == "datos"
    for slug in piso.ACCION.values():
        assert auditoria.ficha(slug)["clase"] == "stock"


def test_lo_no_declarado_se_ve_no_se_esconde():
    f = auditoria.ficha("accion_que_nadie_declaro")
    assert f["clase"] == "otros" and f["gate"] == "desconocido"


def test_el_registro_traduce_el_slug_a_una_frase():
    """Un registro con `sanear_fantasma_custom` en pantalla no es un registro:
    es un log. La frase tiene que estar en el idioma del que mira."""
    import i18n
    e = {"accion": "cobranza_recordado"}
    assert auditoria._frase(e, "es") == i18n.CATALOGO["audit.acc.cobranza_recordado"]["es"]
    assert auditoria._frase(e, "en") == i18n.CATALOGO["audit.acc.cobranza_recordado"]["en"]
    # las familias por prefijo también, sin declarar una por una
    assert "balanza" in auditoria._frase({"accion": "sanear_balanza"}, "es")


def test_el_registro_dice_quien_aprobo():
    r = auditoria.registro("es")
    for e in r["eventos"]:
        if e["gate"] == "aprobacion":
            assert e["aprobado_por"] == e["actor"] and e["aprobado_por"]
        else:
            assert e["aprobado_por"] is None


def test_las_consultas_no_tapan_las_decisiones_pero_se_pueden_ver():
    """F·3 aplicado al registro: noventa preguntas a Ángela tapando tres
    decisiones de plata es el mismo problema que la fatiga de aprobación. No se
    listan por defecto — y el registro DICE cuántas dejó afuera, con el chip
    para verlas. Esconder sin avisar sería peor que el ruido."""
    todo = auditoria.registro("es")
    assert all(e["clase"] not in auditoria.SIN_EFECTO for e in todo["eventos"])
    ocultos = todo["resumen"]["sin_efecto_ocultos"]
    assert ocultos == todo["resumen"]["por_clase"]["consulta"] + \
                      todo["resumen"]["por_clase"]["tecnico"]
    # el chip las trae de vuelta
    consultas = auditoria.registro("es", clase="consulta")
    assert len(consultas["eventos"]) == todo["resumen"]["por_clase"]["consulta"] \
        or consultas["total_filtrado"] == todo["resumen"]["por_clase"]["consulta"]


def test_una_pregunta_a_angela_no_es_una_accion_de_angela():
    """`consulta_angela` no tocó nada: no puede llevar el mismo sello que la
    normalización, que sí escribe."""
    assert auditoria.ficha("consulta_angela")["gate"] == "sin_efecto"
    assert auditoria.ficha("normalizacion_nivel1")["gate"] == "sistema"


def test_el_resumen_no_baila_al_filtrar():
    """Los totales de la cabecera se cuentan sobre TODO el registro. Si se
    recalcularan con el filtro puesto, «0 acciones sensibles sin aprobación»
    diría cualquier cosa según qué chip esté tocado."""
    todo = auditoria.registro("es")
    filtrado = auditoria.registro("es", clase="perfil")
    assert filtrado["resumen"] == todo["resumen"]
    assert filtrado["total_filtrado"] <= todo["total_filtrado"]
    assert all(e["clase"] == "perfil" for e in filtrado["eventos"])


def test_el_registro_viene_de_lo_mas_nuevo_a_lo_mas_viejo():
    ev = auditoria.registro("es")["eventos"]
    cuandos = [e["cuando"] for e in ev]
    assert cuandos == sorted(cuandos, reverse=True)


def test_los_montos_son_los_guardados_no_recalculados():
    """El impacto sale del evento tal como se escribió. Nunca de una consulta
    de hoy: un registro que se actualiza solo no sirve para auditar nada."""
    e = {"accion": "cobranza_recordado", "despues": {"saldo": 19_200_000}}
    assert auditoria._impacto(e) == 19_200_000
    assert auditoria._impacto({"accion": "x", "despues": {"nada": 1}}) is None


def test_el_hilo_cuenta_la_historia_en_orden():
    """El «y después qué pasó»: las acciones sobre el mismo sujeto, de la más
    vieja a la más nueva.

    El registro es append-only por diseño (esa es la garantía), así que el test
    escribe de verdad y después deja el archivo como estaba: el dataset del demo
    no se ensucia con clientes inventados."""
    import json
    from core import store
    cliente = "Hilo Test SA"
    crudo_antes = json.load(open(store.audit.path, encoding="utf-8")) \
        if __import__("os").path.exists(store.audit.path) else []
    try:
        store.audit.record("Tester", "cobranza_recordado", None, {"cliente": cliente})
        store.audit.record("Tester", "cobranza_pagado", None, {"cliente": cliente})
        h = auditoria.hilo(cliente, "es")
        assert [x["accion"] for x in h] == ["cobranza_recordado", "cobranza_pagado"]
        assert all(x["en_hilo"] == 2 for x in h)
        assert len(store.audit.list()) == len(crudo_antes) + 2
    finally:
        json.dump(crudo_antes, open(store.audit.path, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    assert auditoria.hilo(cliente, "es") == []


def test_el_limite_no_miente_sobre_lo_que_hay():
    r = auditoria.registro("es", limite=3)
    assert r["mostrados"] <= 3
    assert r["total_filtrado"] >= r["mostrados"]


# --- BLOQUE F·2/3 · los gates y la autonomía graduada -------------------------

def test_nada_sensible_se_ejecuta_sin_un_si_humano():
    """LA prueba del bloque F. De todo lo que tocó plata, stock o permisos, cero
    salió sin que alguien lo aprobara o sin que fuera la propia persona sobre lo
    suyo. Si esto se pone en rojo, el producto perdió su argumento."""
    r = auditoria.registro("es")
    assert r["resumen"]["sensibles_sin_aprobacion"] == 0
    for e in r["eventos"]:
        if e["clase"] in ("plata", "stock", "permisos"):
            assert e["gate"] in ("aprobacion", "propia"), e["accion"]


def test_la_plata_el_stock_y_los_permisos_no_se_graduan():
    """No es un default conservador: es un candado. No hay endpoint ni setting
    que lo mueva."""
    for clase in ("plata", "stock", "permisos"):
        assert autonomia.nivel_de(clase) == "pide_ok"
        with pytest.raises(ValueError):
            autonomia.set_nivel(clase, "agrupa", actor="Tester")
        assert autonomia.nivel_de(clase) == "pide_ok"


def test_el_candado_manda_sobre_el_archivo():
    """Aunque alguien edite autonomia.json a mano, la clase con candado sigue
    en pide_ok: el permiso vive en el código, no en un JSON editable."""
    autonomia._save({"plata": "agrupa", "stock": "agrupa"})
    try:
        assert autonomia.nivel_de("plata") == "pide_ok"
        assert autonomia.nivel_de("stock") == "pide_ok"
    finally:
        autonomia._save({})


def test_la_limpieza_reversible_si_se_gradua_y_queda_auditada():
    """Lo único graduable es lo reversible — y moverlo es, él mismo, una
    decisión que queda registrada."""
    from core import store
    antes = len(store.audit.list())
    try:
        autonomia.set_nivel("datos", "agrupa", actor="Tester")
        assert autonomia.nivel_de("datos") == "agrupa"
        ev = store.audit.list()[-1]
        assert ev["accion"] == "cambiar_autonomia_angela"
        assert ev["despues"]["nivel"] == "agrupa" and ev["antes"]["nivel"] == "pide_ok"
        assert len(store.audit.list()) == antes + 1
    finally:
        autonomia._save({})
    assert autonomia.nivel_de("datos") == "pide_ok"   # el default vuelve


def test_un_nivel_inventado_no_entra():
    with pytest.raises(ValueError):
        autonomia.set_nivel("datos", "hace_lo_que_quiere", actor="Tester")
    with pytest.raises(ValueError):
        autonomia.set_nivel("clase_inventada", "agrupa", actor="Tester")


def test_solo_hay_una_accion_que_angela_hace_sola():
    """Y está declarada. La autonomía de hoy es exactamente una cosa —
    normalización de formato al entrar un archivo, reversible — y el panel la
    dice de frente en vez de esconderla."""
    automaticas = {a for a, f in auditoria.ACCIONES.items() if f["gate"] == "sistema"}
    # `crear_apartado` lo emite el seed en cada boot (no es trabajo de Ángela).
    # La única automática que ESCRIBE sobre los datos del negocio es la
    # normalización de formato al entrar un archivo — y es reversible.
    assert automaticas == {"normalizacion_nivel1", "crear_apartado"}, automaticas
    assert auditoria.ACCIONES["normalizacion_nivel1"]["reversible"] is True
    assert autonomia.estado("es")["ya_hace_sola"]["accion"] == "normalizacion_nivel1"


def test_toda_accion_sobre_plata_es_reversible_o_pide_aprobacion():
    """No se puede tocar plata sin una de las dos redes: o lo aprobó alguien, o
    se deshace. En la práctica hoy tienen las dos."""
    for accion, f in auditoria.ACCIONES.items():
        if f["clase"] in ("plata", "stock", "permisos"):
            assert f["gate"] in ("aprobacion", "propia"), accion


# --- El texto: todo lo que un humano lee, bilingüe el mismo día ---------------

def test_cada_accion_declarada_tiene_su_frase_en_los_dos_idiomas():
    import i18n
    faltan = []
    for accion in auditoria.ACCIONES:
        entrada = i18n.CATALOGO.get(f"audit.acc.{accion}")
        if not entrada or not entrada.get("es") or not entrada.get("en"):
            faltan.append(accion)
    assert not faltan, f"acciones sin frase bilingüe: {faltan}"


def test_el_panel_de_autonomia_esta_entero_en_los_dos_idiomas():
    for lang in ("es", "en"):
        e = autonomia.estado(lang)
        for c in e["clases"]:
            assert c["label"] and not c["label"].startswith("autonomia.")
            assert c["nivel_label"] and not c["nivel_label"].startswith("autonomia.")
            if not c["graduable"]:
                assert c["motivo"] and not c["motivo"].startswith("autonomia.")
        for n in e["niveles"]:
            assert n["label"] and n["detalle"] and not n["detalle"].startswith("autonomia.")
        assert not e["proximo_paso"].startswith("autonomia.")
