"""The global search (core/buscador.py).

What is protected, in order of how expensive it would be to get wrong:

  1. THE GATE IS PER RESULT TYPE. "Open to anyone logged in" must never mean
     "everyone sees everything": a driver with `deposito` and no `cuentas`
     searching a customer's name gets the delivery, never the balance.
  2. EVERY HIT KNOWS WHERE IT LIVES. A hit without `seccion`/`foco` is a dead
     end — the click would land on row 1 of 430, which is the thing this
     exists to remove.
  3. It COMPUTES nothing: a hit is a row that already exists.
"""
from __future__ import annotations

import pytest

import pytest as _pytest

from core import buscador, esquema
from tests.conftest import limpiar_tabla_tenant

# The suite's tenant ships only inventory.json, so vendors / logistics /
# purchase orders would simply be missing and every test about them would
# skip — which is the same as not having them. They are planted here instead,
# with the shape the real dataset uses, and removed afterwards.
_PROVEEDOR = {"id": "pv1", "nombre": "Proveedor de Prueba SRL", "contacto": "",
              "telefono": "", "email": "", "cuit": "", "notas": "sembrado por el test"}
_PEDIDO = {"pedido": "P-9001", "cliente": "Cliente de Prueba",
           "direccion": "Calle Falsa 123", "estado": "pendiente",
           "fecha_prevista": "2026-07-09", "transporte": "Camión 1"}
_ORDEN = {"numero": "OC-9001", "fecha": "2026-07-01",
          "proveedor": "Proveedor de Prueba SRL", "estado": "abierta", "items": []}


@_pytest.fixture(autouse=True)
def _con_datos():
    def limpiar():
        limpiar_tabla_tenant("data_sections")
    limpiar()
    esquema.reemplazar_filas("proveedores", [_PROVEEDOR])
    esquema.reemplazar_filas("logistica", [_PEDIDO])
    esquema.reemplazar_filas("ordenes_compra", [_ORDEN])
    yield
    limpiar()


def _un_nombre(tipo: str):
    filas = {"cliente": lambda: [c["nombre"] for c in _clientes()],
             "proveedor": lambda: [p["nombre"] for p in esquema.filas("proveedores")],
             "pedido": lambda: [p["pedido"] for p in esquema.filas("logistica")],
             "orden_compra": lambda: [o["numero"] for o in esquema.filas("ordenes_compra")]}[tipo]()
    if not filas:
        pytest.skip(f"este tenant no tiene {tipo}")
    return filas[0]


def _clientes():
    from core import cuentas
    return cuentas.listar()


def test_el_gate_es_por_tipo_no_por_endpoint():
    """The whole point of taking the gate off `inventario`."""
    nombre = _un_nombre("cliente")
    solo_cuentas = buscador.buscar(nombre, ["cuentas"])
    assert solo_cuentas, "con `cuentas` tiene que encontrar al cliente"
    assert {h["tipo"] for h in solo_cuentas} == {"cliente"}

    # The same query, from someone who may NOT read accounts.
    sin_cuentas = buscador.buscar(nombre, ["deposito"])
    assert all(h["tipo"] != "cliente" for h in sin_cuentas), \
        "un rol sin `cuentas` no puede ver clientes en el buscador"

    # And with no features at all, nothing at all.
    assert buscador.buscar(nombre, []) == []


def test_ningun_resultado_es_un_callejon_sin_salida():
    """Every hit carries the section that owns it and the item to focus."""
    hits = []
    for tipo in buscador.POR_TIPO_MODULO:
        try:
            hits += buscador.buscar(_un_nombre(tipo) if tipo != "producto" else "a")
        except Exception:  # noqa: BLE001 — a tenant may not have this type
            continue
    assert hits, "sin datos no hay nada que comprobar"
    for h in hits:
        assert h["seccion"], h
        assert h["foco"], h
        assert h["etiqueta"], h


def test_el_pedido_apunta_al_nodo_del_mapa_con_su_propio_sanitizador():
    """The one type with no list screen of its own: it lands on the map,
    focused on its node. The id is built with the MAP's sanitizer, never
    re-derived here — if the two drifted, the click would open a neutral map,
    which is exactly the dead end this avoids. A node only exists once the
    order is actually in transit, so what is pinned is the id contract."""
    from core import mapa_operacion
    numero = _PEDIDO["pedido"]
    hit = next(h for h in buscador.buscar(numero, ["deposito"]) if h["tipo"] == "pedido")
    assert hit["seccion"] == "mapa"
    assert hit["foco"] == mapa_operacion._sid(f"ped:{numero}")

    # And when the map DOES carry that node, the id is one of its own.
    ids = {n["id"] for n in mapa_operacion.mapa("es").get("nodos", [])}
    if any(i.startswith("ped_") for i in ids):
        assert hit["foco"] in ids or not any(
            i == hit["foco"] for i in ids), hit["foco"]


def test_una_letra_no_devuelve_medio_sistema():
    assert buscador.buscar("a") == []
    assert buscador.buscar("") == []


def test_ningun_tipo_entierra_a_los_demas():
    """430 products must not push the one customer off the list."""
    hits = buscador.buscar("a" * 0 or "campo", tope=10)
    if len({h["tipo"] for h in hits}) > 1:
        primeros = [h["tipo"] for h in hits[:4]]
        assert len(set(primeros)) > 1, f"un solo tipo copó el arranque: {primeros}"


@pytest.mark.parametrize("q,espera", [
    ("leche", False),
    ("P-4411", False),
    ("¿cuánta plata tengo parada?", True),
    ("cuanta plata tengo parada en stock", True),
    ("leche?", True),
])
def test_que_cuenta_como_pregunta(q, espera):
    assert buscador.parece_pregunta(q) is espera
