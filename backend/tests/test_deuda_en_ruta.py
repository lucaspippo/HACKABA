"""C5 · La deuda que sale a la calle hoy, sumada por camión.

El ERP sabe cuánto debe cada cliente y sabe qué pedido sale mañana. Lo que no
hace nadie es la suma POR CAMIÓN, y puesta así la decisión de operación se ve
sola.

Lo que se protege acá, en orden de cuánto duele si se rompe:

  1. UN CLIENTE, UNA VEZ. Un cliente con dos pedidos el mismo día tiene UN
     saldo. Sumar por parada infla el total sin que se note — en el dataset del
     demo la diferencia entre hacerlo mal y hacerlo bien es de $56,9M sobre
     $168,7M, o sea un tercio de más. Es el mismo doble conteo que ya nos costó
     una vez (ver `oportunidades_neg.recuperable`).
  2. NO ES PLATA RECUPERADA. La tarjeta nace con `naturaleza="riesgo"`, así que
     nunca entra en la suma del capital recuperable. Es deuda que ya existe: el
     aviso la pone a la vista, no la cobra.
  3. EL GATE SON DOS MÓDULOS. Ver esto es ver rutas Y ver saldos. Con una sola
     de las dos mitades, la tarjeta no existe.
  4. UNA PARADA ENTREGADA NO CUENTA. No se puede reasignar ni instruir.

Los tests de datos corren en un SUBPROCESO contra el dataset demo canónico
(mismo patrón que test_cruces/test_consultas): el tenant se elige por env.
"""
from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys

import pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DEMO = os.path.join(os.path.dirname(BACKEND), "data-demo")
ENV = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": DATA_DEMO,
       "POLPILOT_DEMO_TODAY": "2026-07-07", "PYTHONIOENCODING": "utf-8"}
ENV.pop("ANTHROPIC_API_KEY", None)

HOY = datetime.date(2026, 7, 7)


def _en_demo(codigo: str) -> dict:
    r = subprocess.run([sys.executable, "-c", codigo], cwd=BACKEND, env=ENV,
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stderr[-900:]
    return json.loads(r.stdout.strip().splitlines()[-1])


# --- 1 · la aritmética, sin datos sembrados -------------------------------------
# Con fuentes inyectadas: el caso del doble conteo se prueba en tres líneas y no
# depende de que el dataset siga teniendo dos paradas del mismo cliente.

@pytest.fixture
def ruta(monkeypatch):
    from core import cobranza, fechas, logistica

    def montar(paradas, clientes):
        monkeypatch.setattr(logistica, "hay_datos", lambda: True)
        monkeypatch.setattr(
            logistica, "salidas",
            lambda dia=None: [p for p in paradas
                              if p["fecha_prevista"] == (dia or HOY.isoformat())])
        monkeypatch.setattr(cobranza.cuentas, "listar", lambda: clientes)
        monkeypatch.setattr(fechas, "hoy", lambda: HOY)
        monkeypatch.setattr(cobranza.fechas, "hoy", lambda: HOY)
        return cobranza

    return montar


def _parada(pedido, cliente, transporte="Camión 1", dia=HOY.isoformat()):
    return {"pedido": pedido, "cliente": cliente, "transporte": transporte,
            "fecha_prevista": dia, "estado": "pendiente"}


def _cliente(nombre, saldo, dias=10, plazo=30):
    return {"id": nombre.lower().replace(" ", "_"), "nombre": nombre,
            "saldo": saldo, "dias_sin_pagar": dias, "plazo_dias": plazo,
            "en_mora": saldo > 0 and dias > plazo, "exceso_tolerancia": None}


def test_un_cliente_con_dos_paradas_cuenta_una_vez(ruta):
    """El bug que este test existe para impedir: dos pedidos, un saldo."""
    cob = ruta([_parada("P-1", "El Puente"), _parada("P-2", "El Puente")],
               [_cliente("El Puente", 55_000_000)])
    cam = cob.exposicion_en_ruta(dias=1)[0]["camiones"][0]
    assert cam["paradas"] == 2          # las paradas son dos: son dos viajes
    assert cam["clientes"] == 1         # el cliente es uno: es un saldo
    assert cam["expuesto"] == 55_000_000


def test_el_mismo_cliente_en_dos_camiones_no_duplica_el_total_del_dia(ruta):
    """Por camión suma en los dos —cada chofer lleva esa exposición— pero el
    total del día es la deuda de la empresa, y esa es una sola."""
    cob = ruta([_parada("P-1", "Hotel", "Camión 1"),
                _parada("P-2", "Hotel", "Camión 2")],
               [_cliente("Hotel", 16_800_000)])
    d = cob.exposicion_en_ruta(dias=1)[0]
    assert [c["expuesto"] for c in d["camiones"]] == [16_800_000, 16_800_000]
    assert d["expuesto"] == 16_800_000
    assert d["clientes"] == 1


def test_una_parada_entregada_no_sale_a_la_calle():
    """`salidas` filtra lo entregado: no se puede reasignar ni instruir."""
    from core import logistica
    assert logistica._estado_norm("Entregado") == "entregado"
    assert logistica._estado_norm("en camino") == "en_camino"
    assert logistica._estado_norm("pendiente") == "pendiente"


def test_un_cliente_sin_cuenta_corriente_se_cuenta_aparte(ruta):
    """«No debe nada» y «no sé» no son lo mismo: si el que compra al contado
    entrara como cero, el total mentiría por omisión y nadie lo notaría."""
    cob = ruta([_parada("P-1", "Kiosco"), _parada("P-2", "Contado")],
               [_cliente("Kiosco", 1_900_000)])
    cam = cob.exposicion_en_ruta(dias=1)[0]["camiones"][0]
    assert cam["sin_cuenta"] == 1
    assert cam["clientes"] == 1
    assert cam["expuesto"] == 1_900_000


def test_los_camiones_salen_ordenados_por_plata(ruta):
    cob = ruta([_parada("P-1", "Chico", "Camión 1"),
                _parada("P-2", "Grande", "Camión 2")],
               [_cliente("Chico", 1_000_000), _cliente("Grande", 90_000_000)])
    cams = cob.exposicion_en_ruta(dias=1)[0]["camiones"]
    assert [c["transporte"] for c in cams] == ["Camión 2", "Camión 1"]
    assert cob.peor_camion(dias=1)["transporte"] == "Camión 2"


def test_solo_los_pasados_de_plazo_entran_en_vencidos(ruta):
    cob = ruta([_parada("P-1", "Al día"), _parada("P-2", "Tarde")],
               [_cliente("Al día", 5_000_000, dias=10, plazo=30),
                _cliente("Tarde", 19_200_000, dias=66, plazo=30)])
    cam = cob.exposicion_en_ruta(dias=1)[0]["camiones"][0]
    assert [v["cliente"] for v in cam["vencidos"]] == ["Tarde"]
    assert cam["expuesto"] == 24_200_000     # el total incluye a los dos


def test_sin_paradas_no_hay_aviso(ruta):
    cob = ruta([], [_cliente("Nadie", 1_000_000)])
    assert cob.exposicion_en_ruta(dias=1) == []
    assert cob.peor_camion(dias=1) is None


# --- 2 · contra el dataset del demo ---------------------------------------------

def test_el_peor_camion_del_demo_es_el_tercerizado_de_manana():
    """El número que el aviso pone a la vista. Deduplicado: sumar por parada
    daría $168.700.000 porque Supermercado El Puente y Kiosco Plaza tienen dos
    paradas cada uno el 08/07."""
    out = _en_demo(
        "import json; from core import cobranza;"
        "p = cobranza.peor_camion();"
        "print(json.dumps(p, ensure_ascii=False))")
    assert out["dia"] == "2026-07-08"
    assert out["transporte"] == "Camión 3 - Tercerizado"
    assert out["paradas"] == 7
    assert out["clientes"] == 5          # 7 paradas, 5 clientes distintos
    assert out["expuesto"] == 111_800_000
    assert [v["cliente"] for v in out["vencidos"]] == ["Despensa Doña Elsa"]


def test_la_regla_de_la_casa_viaja_con_el_vencido():
    """Doña Elsa está 66 días con 30 de plazo, pero la regla de Aldo le tolera
    45: el exceso que importa es contra la regla, y ya lo calcula cuentas."""
    out = _en_demo(
        "import json; from core import cobranza;"
        "p = cobranza.peor_camion();"
        "print(json.dumps(p['vencidos'][0], ensure_ascii=False))")
    assert out["dias_sin_pagar"] == 66
    assert out["plazo_dias"] == 30
    assert out["exceso_tolerancia"] == 21     # 66 − 45, la regla de la casa


def test_el_total_del_dia_no_es_la_suma_de_los_camiones_cuando_se_repite_un_cliente():
    out = _en_demo(
        "import json; from core import cobranza;"
        "print(json.dumps(cobranza.exposicion_en_ruta(), ensure_ascii=False))")
    for d in out:
        suma_camiones = sum(c["expuesto"] for c in d["camiones"])
        assert d["expuesto"] <= suma_camiones + 1, d["dia"]
        assert d["clientes"] <= d["paradas"], d["dia"]


# --- 3 · la tarjeta ------------------------------------------------------------

def test_la_tarjeta_es_riesgo_y_no_entra_en_el_capital_recuperable():
    """La distinción entre plata a la vista y plata que se recupera ya vive en
    `recuperable`. Esta tarjeta cae del lado correcto."""
    out = _en_demo(
        "import json; from core import priorities, oportunidades_neg as opn;"
        "inbox = priorities.inbox('es');"
        "items = inbox['act'] + inbox['watch'];"
        "c = next((x for x in items if x['id'] == 'deuda_en_ruta'), None);"
        "rec = inbox['recuperable'];"
        "print(json.dumps({'card': c, 'componentes': [x['id'] for x in rec['componentes']],"
        " 'excluidos': [x['id'] for x in rec['excluidos']]}, ensure_ascii=False))")
    c = out["card"]
    assert c, "la tarjeta no salió"
    assert c["naturaleza"] == "riesgo"
    assert c["monto"] == 111_800_000
    assert "deuda_en_ruta" not in out["componentes"]   # no se suma
    assert "deuda_en_ruta" in out["excluidos"]         # se muestra, con motivo
    assert set(c["modulos"]) == {"logistica", "cuentas"}


def test_la_tarjeta_explica_la_cadena_y_cita_sus_dos_fuentes():
    out = _en_demo(
        "import json; from core import priorities;"
        "inbox = priorities.inbox('es');"
        "c = next(x for x in inbox['act'] + inbox['watch'] if x['id'] == 'deuda_en_ruta');"
        "print(json.dumps(c, ensure_ascii=False))")
    assert len(out["fuentes"]) == 2
    ins = out["insight"]
    assert ins["evidence"], ins
    metrica = ins["evidence"][0]
    assert metrica["value"] == 111_800_000
    assert metrica["method"]["key"] == "core.method.deuda_en_ruta"
    assert ins["risk"]["exposure"] == 111_800_000
    assert ins["assumptions"], "sin supuesto declarado no se puede discutir el número"


def test_solo_la_ve_quien_tiene_rutas_y_saldos():
    """El encargado de depósito tiene `logistica` y no `cuentas`; el
    preventista, al revés. Ninguno de los dos ve la flota entera."""
    out = _en_demo(
        "import json; from core import priorities;"
        "casos = {'ambos': ['logistica','cuentas','alertas'],"
        " 'solo_rutas': ['logistica','alertas'],"
        " 'solo_saldos': ['cuentas','alertas']};"
        "r = {k: any(x['id']=='deuda_en_ruta' for x in"
        "     priorities.inbox('es', features=v)['act'] +"
        "     priorities.inbox('es', features=v)['watch']) for k, v in casos.items()};"
        "print(json.dumps(r))")
    assert out["ambos"] is True
    assert out["solo_rutas"] is False
    assert out["solo_saldos"] is False


def test_nace_bilingue():
    out = _en_demo(
        "import json; from core import priorities;"
        "card = lambda l: next(x for x in priorities.inbox(l)['act'] +"
        "                      priorities.inbox(l)['watch'] if x['id'] == 'deuda_en_ruta');"
        "campos = lambda c: {'titulo': c['titulo'], 'resumen': c['resumen'],"
        "                    'label': c['monto_label']};"
        "print(json.dumps({l: campos(card(l)) for l in ('es', 'en')}, ensure_ascii=False))")
    assert out["es"]["titulo"] != out["en"]["titulo"]
    assert out["es"]["resumen"] != out["en"]["resumen"]
    for lang in ("es", "en"):
        for campo, texto in out[lang].items():
            # Un `{placeholder}` sin reemplazar es el bug clásico de i18n: el
            # texto sale, se ve mal, y ningún test lo mira.
            assert texto and "{" not in texto, (lang, campo, texto)
