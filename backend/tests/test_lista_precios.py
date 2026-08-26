"""
P22·A — La lista de precios del proveedor: diff con criterio, aplicación con
backup, revert byte-igual. Los casos usan una extracción sintética con la MISMA
forma que devuelve la visión (el contrato es idéntico foto o CSV).
"""
from __future__ import annotations

import hashlib
import json
import os

import pytest

import angela
from core import comprobantes, lista_precios, memoria, store
from tests.conftest import limpiar_tabla_tenant


def _hash() -> str:
    return hashlib.sha256(json.dumps(store.raw_actual(), sort_keys=True).encode()).hexdigest()


@pytest.fixture(autouse=True)
def estado_limpio():
    store.resetear_actual()
    limpiar_tabla_tenant("user_memory")
    usuario, rol = angela._usuario_actual(), angela._rol_actual()
    yield
    angela._set_sesion(usuario=usuario, rol=rol)
    store.resetear_actual()
    limpiar_tabla_tenant("user_memory")


def _articulo(idx: int = 0) -> dict:
    activos = [a for a in store.raw_actual()
               if a.get("estado") == "activo" and a.get("costo_iva") and a.get("descripcion")]
    return activos[idx]


def _extraccion(items) -> dict:
    return {"tipo_comprobante": "lista_precios",
            "proveedor": {"razon_social": "Lácteos Campo Alegre"},
            "items": items}


def test_diff_subas_normales_ok():
    a, b = _articulo(0), _articulo(1)
    d = lista_precios.diff(_extraccion([
        {"codigo": a["codigo"], "descripcion": a["descripcion"],
         "precio_unitario": round(a["costo_iva"] * 1.05, 2)},
        {"codigo": b["codigo"], "descripcion": b["descripcion"],
         "precio_unitario": round(b["costo_iva"] * 1.06, 2)},
    ]), "es")
    assert d["n"] == 2 and d["limpios"] == 2 and not d["dudosos"]
    assert 4.0 < d["promedio_pct"] < 7.0


def test_diff_detecta_salto_sospechoso():
    arts = [_articulo(i) for i in range(6)]
    items = [{"codigo": a["codigo"], "descripcion": a["descripcion"],
              "precio_unitario": round(a["costo_iva"] * 1.05, 2)} for a in arts[:5]]
    items.append({"codigo": arts[5]["codigo"], "descripcion": arts[5]["descripcion"],
                  "precio_unitario": round(arts[5]["costo_iva"] * 1.40, 2)})
    d = lista_precios.diff(_extraccion(items), "es")
    assert d["limpios"] == 5
    saltos = [x for x in d["dudosos"] if x["estado"] == "salto_sospechoso"]
    assert len(saltos) == 1 and saltos[0]["pct"] == 40.0


def test_diff_detecta_codigo_pisado_y_sugiere():
    a, b = _articulo(0), _articulo(1)  # el código de A con la descripción de B
    d = lista_precios.diff(_extraccion([
        {"codigo": a["codigo"], "descripcion": b["descripcion"],
         "precio_unitario": round(b["costo_iva"] * 1.05, 2)},
    ]), "es")
    pisados = [x for x in d["dudosos"] if x["estado"] == "codigo_no_coincide"]
    assert len(pisados) == 1
    assert pisados[0]["sugerido"]["codigo"] == b["codigo"]  # el que el nombre matchea


def test_diff_codigo_inexistente_honesto():
    d = lista_precios.diff(_extraccion([
        {"codigo": 999999, "descripcion": "PRODUCTO MISTERIOSO", "precio_unitario": 100},
    ]), "es")
    assert d["items"][0]["estado"] == "sin_catalogo" and d["limpios"] == 0


def test_aplicar_con_backup_y_revert_byte_igual():
    hash_canonico = _hash()
    a = _articulo(0)
    r = lista_precios.aplicar([{"codigo": a["codigo"],
                                "precio_nuevo": round(a["costo_iva"] * 1.05, 2)}],
                              actor="test")
    assert r["ok"] and r["items"] == 1 and r["version_backup"]
    assert _hash() != hash_canonico  # el costo cambió de verdad
    nuevo = next(x for x in store.raw_actual() if x["codigo"] == a["codigo"])
    assert nuevo["costo_iva"] == round(a["costo_iva"] * 1.05, 2)
    assert nuevo["antiguedad_costo_dias"] == 0  # el costo quedó fresco
    # el revert de siempre restaura byte-igual (protege la grabación)
    from core import saneamiento
    saneamiento.revertir(r["version_backup"], actor="test")
    assert _hash() == hash_canonico


def test_confirmar_enruta_y_narra():
    arts = [_articulo(i) for i in range(6)]
    items = [{"codigo": a["codigo"], "descripcion": a["descripcion"],
              "precio_unitario": round(a["costo_iva"] * 1.05, 2)} for a in arts[:5]]
    salto = arts[5]
    items.append({"codigo": salto["codigo"], "descripcion": salto["descripcion"],
                  "precio_unitario": round(salto["costo_iva"] * 1.45, 2)})
    r = comprobantes.confirmar(_extraccion(items), actor="test", lang="en")
    assert r["ok"] and r["tipo"] == "lista_precios"
    assert r["items"] == 5 and r["retenidos"] == 1  # el sospechoso NO se aplicó
    assert r["sync"]["estado"] == "simulado"  # declarado, como siempre
    assert "backup" in r["mensaje_angela"].lower()
    # el retenido no cambió
    intacto = next(x for x in store.raw_actual() if x["codigo"] == salto["codigo"])
    assert intacto["costo_iva"] == salto["costo_iva"]


def test_fallback_revert_por_chat():
    a = _articulo(0)
    lista_precios.aplicar([{"codigo": a["codigo"],
                            "precio_nuevo": round(a["costo_iva"] * 1.05, 2)}], actor="test")
    hash_mutado = _hash()
    angela._set_sesion(usuario="emilio", rol="dueño", idioma="en")
    r = angela._fallback("revert the price update")
    assert "revertir_version" in r["tools_usadas"]
    assert _hash() != hash_mutado  # volvió
    assert "back" in r["respuesta"].lower()


def test_fallback_revert_sin_backup_honesto(monkeypatch):
    # sin backups DE LISTA a la vista (el índice real acumula los de otros tests)
    monkeypatch.setattr(store.versiones, "list", lambda: [])
    angela._set_sesion(usuario="emilio", rol="dueño", idioma="es")
    r = angela._fallback("revertí la lista de precios")
    assert "ninguna lista" in r["respuesta"].lower()


def test_muestra_lista_existe_en_demo():
    """El archivo de muestra (PNG + CSV) vive en data-demo, con las 2 anomalías."""
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    demo = os.path.join(os.path.dirname(backend), "data-demo", "comprobantes")
    assert os.path.exists(os.path.join(demo, "lista.png"))
    csv_path = os.path.join(demo, "lista_precios_campo_alegre.csv")
    assert os.path.exists(csv_path)
    filas = open(csv_path, encoding="utf-8").read().strip().splitlines()
    assert len(filas) == 24  # header + 23 productos
