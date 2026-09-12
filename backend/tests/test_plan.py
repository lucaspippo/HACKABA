"""
P19·D — Orquestación visible: el plan con confirmación y checkmarks.

Los pasos son las acciones reales que ya existen (saneamiento con backup,
recálculo, cola ERP). Cubre: el plan se arma con números reales, la ejecución
corre en secuencia y devuelve el resultado paso a paso con antes/después, un
paso que falla DETIENE y reporta (nada de fallar en silencio).
"""
from __future__ import annotations

import pytest

import angela
from core import store, saneamiento
from tests.conftest import limpiar_tabla_tenant


@pytest.fixture(autouse=True)
def estado_limpio():
    store.resetear_actual()
    limpiar_tabla_tenant("user_memory")
    usuario, rol = angela._usuario_actual(), angela._rol_actual()
    yield
    angela._set_sesion(usuario=usuario, rol=rol)
    store.resetear_actual()
    limpiar_tabla_tenant("user_memory")


def test_armar_plan_con_numeros_reales():
    plan = angela._armar_plan("es")
    assert plan["ok"]
    ids = [p["id"] for p in plan["pasos"]]
    # las dos correcciones automáticas + recálculo + cola, en ese orden
    assert ids[-2:] == ["recalcular", "cola_erp"]
    fantasma = next(p for p in plan["pasos"] if p["id"] == "fantasma")
    assert fantasma["cantidad"] == saneamiento.proponer("fantasma")["cantidad"]
    # lo no-automático queda declarado, no escondido
    assert any(f["categoria"] == "negativo" for f in plan["fuera_del_plan"])


def test_ejecutar_plan_en_secuencia_con_backup():
    angela._set_sesion(usuario="emilio", rol="dueño")
    r, accion = angela._run_tool("ejecutar_plan", {})
    assert r["ok"]
    assert all(p["ok"] for p in r["pasos"])
    assert accion["type"] == "plan_progreso"
    # cada corrección dice su backup (reversible, como todo)
    corr = [p for p in r["pasos"] if p["id"] in ("fantasma", "balanza")]
    assert corr and all("backup" in p["detalle"] for p in corr)
    # el resumen en $: capital antes y después, números reales
    assert r["resumen"]["inmovilizado_antes"] > 0
    assert r["resumen"]["inmovilizado_despues"] > 0
    # y de verdad corrigió: no quedan fantasmas
    assert saneamiento.proponer("fantasma")["cantidad"] == 0


def test_paso_que_falla_detiene_y_reporta(monkeypatch):
    angela._set_sesion(usuario="emilio", rol="dueño")
    original = saneamiento.aplicar

    def aplicar_con_falla(categoria, actor="dueño"):
        if categoria == "balanza":
            raise RuntimeError("simulada para el test")
        return original(categoria, actor=actor)

    monkeypatch.setattr(angela.saneamiento, "aplicar", aplicar_con_falla)
    r, _ = angela._run_tool("ejecutar_plan", {})
    assert r["ok"] is False
    # el fantasma se hizo (con backup), la balanza falló, lo demás quedó pendiente
    assert r["pasos"][0]["id"] == "fantasma" and r["pasos"][0]["ok"]
    assert r["pasos"][-1]["id"] == "balanza" and r["pasos"][-1]["ok"] is False
    assert "simulada" in r["pasos"][-1]["error"]
    assert len(r["pendientes"]) == 2  # recalcular + cola
    assert r["motivo"]  # Ángela tiene qué decir


def test_plan_sin_pendientes_honesto():
    angela._set_sesion(usuario="emilio", rol="dueño")
    angela._run_tool("ejecutar_plan", {})  # primera pasada corrige todo
    plan = angela._armar_plan("es")
    assert plan["ok"] is False  # no inventa pasos vacíos
    r, accion = angela._run_tool("ejecutar_plan", {})
    assert r["ok"] is False and r["pasos"] == []
