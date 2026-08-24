import os

import pytest

from core import store, saneamiento, memoria


@pytest.fixture(autouse=True)
def estado_limpio():
    """Cada test arranca y termina con la copia de trabajo en el original."""
    store.resetear_actual()
    if os.path.exists(memoria.MEMORIA_JSON):
        os.remove(memoria.MEMORIA_JSON)
    yield
    store.resetear_actual()
    if os.path.exists(memoria.MEMORIA_JSON):
        os.remove(memoria.MEMORIA_JSON)


# ---- Task 1: estado de trabajo ----
def test_raw_actual_arranca_del_original():
    raw = store.raw_actual()
    assert len(raw) > 0


def test_guardar_y_resetear():
    raw = store.raw_actual()
    raw[0]["descripcion"] = "MUTADO TEST"
    store.guardar(raw)
    assert store.raw_actual()[0]["descripcion"] == "MUTADO TEST"
    store.resetear_actual()
    assert store.raw_actual()[0]["descripcion"] != "MUTADO TEST"


# ---- Task 2: proponer ----
def test_proponer_fantasma():
    p = saneamiento.proponer("fantasma")
    assert p["auto"] is True
    assert p["cantidad"] > 0
    assert len(p["muestra"]) > 0
    assert p["muestra"][0]["despues"] == "activo"


def test_proponer_balanza_tiene_impacto_pesos():
    p = saneamiento.proponer("balanza")
    assert p["auto"] is True
    assert p["impacto_pesos"] > 0


def test_proponer_categoria_no_auto():
    p = saneamiento.proponer("sin_precio")
    assert p["auto"] is False


# ---- Task 3: aplicar ----
def test_aplicar_balanza_corrige_y_baja_el_libro():
    antes = next(g for g in store.libro_triado()["grupos"] if g["categoria"] == "balanza")
    res = saneamiento.aplicar("balanza", actor="emilio")
    assert res["corregidos"] == antes["cantidad"]
    assert res["impacto_pesos"] > 0
    assert "version_backup" in res
    # ya no quedan balanzas mal calibradas
    cats = {g["categoria"] for g in store.libro_triado()["grupos"]}
    assert "balanza" not in cats


def test_aplicar_fantasma_reactiva():
    saneamiento.aplicar("fantasma", actor="emilio")
    cats = {g["categoria"] for g in store.libro_triado()["grupos"]}
    assert "fantasma" not in cats


def test_aplicar_genera_backup_y_audit():
    n_versiones = len(store.versiones.list())
    saneamiento.aplicar("balanza", actor="emilio")
    assert len(store.versiones.list()) == n_versiones + 1
    assert any(e["accion"] == "sanear_balanza" for e in store.audit.list())


# ---- Task 4: revertir ----
def test_revertir_vuelve_al_estado_anterior():
    libro_antes = store.libro_triado()
    res = saneamiento.aplicar("balanza", actor="emilio")
    saneamiento.revertir(res["version_backup"], actor="emilio")
    libro_despues = store.libro_triado()
    assert libro_despues["total_issues"] == libro_antes["total_issues"]


# ---- Task 5: memoria ----
def test_aplicar_memoriza_preferencia():
    saneamiento.aplicar("balanza", actor="emilio")
    assert "balanza" in memoria.preferencias("emilio").get("categorias_auto", [])
