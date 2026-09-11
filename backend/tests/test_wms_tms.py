"""
Tests del Trabajo 3: dominios depósito (WMS) y logística (TMS) + recordatorios.

Cubren el flujo completo prometido en las métricas de éxito:
  - CSV de depósito → staging lo detecta como DEPOSITO → propone vincular al
    inventario → se integra → Ángela responde "¿qué vence esta semana?".
  - CSV de envíos → Ángela responde "¿qué entregas hay hoy?" → "avisame si la
    de García no sale" → recordatorio condicional creado y disparado.
  - Paridad simulado↔real (tools en TOOLS + _run_tool).
  - El rol Depósito ve depósito/logística y no ve caja/finanzas.
"""
from __future__ import annotations

import datetime
import os

import pytest

import angela
import auth
from core import staging, store, esquema, deposito, logistica, recordatorios

HOY = datetime.date.today()


def d(n: int) -> str:
    return (HOY + datetime.timedelta(days=n)).isoformat()


@pytest.fixture(autouse=True)
def limpio():
    """Aísla apartados/recordatorios/staging: guarda lo que hubiera y lo restaura."""
    files = [esquema.APARTADOS_JSON, recordatorios.RECORDATORIOS_JSON, staging.STAGING_JSON]
    backup = {}
    for f in files:
        if os.path.exists(f):
            backup[f] = open(f, encoding="utf-8").read()
            os.remove(f)
    store.resetear_actual()
    yield
    for f in files:
        if os.path.exists(f):
            os.remove(f)
        if f in backup:
            open(f, "w", encoding="utf-8").write(backup[f])
    store.resetear_actual()


def _articulos(n=3):
    arts = [a for a in store.raw_actual()
            if (a.get("stock") or 0) > 5 and a.get("codigo")
            and a.get("descripcion") and "," not in a["descripcion"]][:n]
    assert len(arts) == n, "el inventario demo debería tener artículos con stock"
    return arts


def _cargar_deposito():
    """Sube un CSV de depósito (productos reales) por staging y lo integra."""
    a0, a1, a2 = _articulos()
    csv_txt = (
        "Codigo,Producto,Ubicacion,Lote,Vencimiento,Cantidad\n"
        f"{a0['codigo']},{a0['descripcion']},Pasillo 1 - Estanteria A,L-1,{d(3)},{a0['stock']}\n"
        f"{a1['codigo']},{a1['descripcion']},Camara de frio 1,L-2,{d(-2)},{(a1['stock'] or 0) + 10}\n"
        f"{a2['codigo']},{a2['descripcion']},Pasillo 2 - Rack alto,L-3,{d(60)},{a2['stock']}\n"
    )
    b = staging.crear_batch("deposito_faro.csv", csv_txt)
    for o in b["observaciones"]:
        staging.resolver(b["id"], o["id"], "confirmar", {})
    return b, staging.integrar(b["id"]), (a0, a1, a2)


CSV_LOGISTICA = (
    "Pedido,Cliente,Direccion,Estado,Fecha prevista,Transporte\n"
    f"P-1,Autoservicio Garcia,Av. Pilar 450,pendiente,{d(0)},Camion 1 - Raul\n"
    f"P-2,Almacen Don Perez,Ruta 8 km 52,en camino,{d(0)},Camion 1 - Raul\n"
    f"P-3,Kiosco La Esquina,Belgrano 120,pendiente,{d(-1)},Camion 2 - Marcos\n"
    f"P-4,Despensa Gonzalez,San Martin 800,entregado,{d(0)},Camion 2 - Marcos\n"
)


def _cargar_logistica():
    b = staging.crear_batch("envios_reparto.csv", CSV_LOGISTICA)
    for o in b["observaciones"]:
        staging.resolver(b["id"], o["id"], "confirmar", {})
    return b, staging.integrar(b["id"])


# --- Detección de tipo (el grafo de esquema) ---

def test_detecta_deposito_por_columnas():
    det = esquema.detectar_tipo(["Codigo", "Producto", "Ubicacion", "Lote", "Vencimiento", "Cantidad"])
    assert det["tipo"] == "deposito"
    assert not det["ambiguo"]


def test_detecta_logistica_por_columnas():
    det = esquema.detectar_tipo(["Pedido", "Cliente", "Direccion", "Estado", "Fecha prevista", "Transporte"])
    assert det["tipo"] == "logistica"
    assert not det["ambiguo"]


# --- Flujo staging → apartado → consultas de depósito ---

def test_flujo_deposito_completo():
    b, res, (a0, a1, a2) = _cargar_deposito()
    assert b["tipo"] == "deposito"
    assert b["plan"]["relaciona_con"] == ["producto"]          # se vincula al inventario
    assert any(o["tipo"] == "lote_vencido" for o in b["observaciones"])  # detectó el vencido
    assert res["ok"] and res["tipo"] == "deposito"
    assert esquema.existe("deposito")

    # ¿Qué vence esta semana? → el lote a 3 días, no el de 60.
    v = deposito.vencimientos(7)
    assert len(v) == 1 and v[0]["dias_restantes"] == 3
    assert deposito.vencidos()[0]["lote"] == "L-2"

    # ¿Dónde está X? → ubicación real del export.
    ubi = deposito.ubicacion_de(str(a0["codigo"]))
    assert ubi and ubi[0]["ubicacion"] == "Pasillo 1 - Estanteria A"

    # Discrepancia física: a1 tiene +10 contra el stock contable.
    disc = deposito.discrepancias()
    assert any(x["codigo"] == a1["codigo"] and x["diferencia"] == 10 for x in disc)


def test_deposito_frena_productos_inexistentes():
    csv_txt = (
        "Codigo,Producto,Ubicacion,Lote,Vencimiento,Cantidad\n"
        f"99999999,PRODUCTO QUE NO EXISTE XYZ,Pasillo 9,L-9,{d(10)},5\n"
    )
    b = staging.crear_batch("deposito_raro.csv", csv_txt)
    assert any(o["tipo"] == "producto_inexistente" for o in b["observaciones"])


# --- Flujo staging → apartado → consultas de logística ---

def test_flujo_logistica_completo():
    b, res = _cargar_logistica()
    assert b["tipo"] == "logistica"
    assert any(o["tipo"] == "entrega_atrasada" for o in b["observaciones"])  # P-3
    assert res["ok"] and esquema.existe("logistica")

    hoy_env = logistica.de_hoy()
    assert len(hoy_env) == 3  # P-1, P-2, P-4 (P-3 era ayer)

    at = logistica.atrasados()
    assert len(at) == 1 and at[0]["pedido"] == "P-3"

    est = logistica.estado_pedido("garcia")
    assert est and est[0]["estado_norm"] == "pendiente" and est[0]["transporte"] == "Camion 1 - Raul"

    rr = logistica.resumen_reparto()
    assert rr["entregas_hoy"] == 3 and rr["atrasados"] == 1
    assert {c["transporte"] for c in rr["camiones"]} == {"Camion 1 - Raul", "Camion 2 - Marcos"}


# --- Ángela (router simulado) responde con los datos de los dominios nuevos ---

def test_angela_que_vence_esta_semana():
    _cargar_deposito()
    r = angela._fallback("¿qué vence esta semana?")
    assert "consultar_deposito" in r["tools_usadas"]
    assert "vencen" in r["respuesta"] or "vencidos" in r["respuesta"]


def test_angela_que_entregas_hay_hoy():
    _cargar_logistica()
    r = angela._fallback("¿qué entregas hay hoy?")
    assert "consultar_envios" in r["tools_usadas"]
    assert "3 entregas" in r["respuesta"]


def test_angela_salio_el_pedido_de_garcia():
    _cargar_logistica()
    r = angela._fallback("¿salió el pedido de García?")
    assert "Garcia" in r["respuesta"] and "no salió" in r["respuesta"]


def test_angela_sin_datos_es_honesta():
    r = angela._fallback("¿qué vence esta semana?")
    assert "Cargar datos" in r["respuesta"]  # no inventa: pide el export
    r = angela._fallback("¿qué entregas hay hoy?")
    assert "Cargar datos" in r["respuesta"]


# --- Recordatorios: simples, por condición y por evento ---

def test_recordatorio_condicional_vencimiento_dispara():
    _cargar_deposito()
    r = angela._fallback("avisame si algo del depósito vence en menos de 15 días")
    assert "crear_recordatorio" in r["tools_usadas"]
    rs = recordatorios.listar("dueño")  # listar evalúa las condiciones
    assert rs and rs[0]["estado"] == "disparado"
    assert "vencen" in rs[0]["detalle_disparo"]


def test_recordatorio_entrega_de_garcia_no_sale():
    _cargar_logistica()
    r = angela._fallback("avisame si la entrega de García no sale hoy")
    assert "crear_recordatorio" in r["tools_usadas"]
    rs = recordatorios.listar("dueño")
    assert rs and rs[0]["estado"] == "disparado"  # sigue pendiente y era para hoy
    assert "Garcia" in rs[0]["detalle_disparo"]


def test_recordatorio_evento_llega_remito():
    recordatorios.crear("avisame cuando llegue el remito de La Serenisima",
                        para="paula", creado_por="paula",
                        condicion={"tipo": "llegada_batch", "origen": "serenisima"})
    _, _, _ = _cargar_deposito()  # no matchea el origen
    assert recordatorios.listar("paula")[0]["estado"] == "latente"
    staging.crear_batch("remito la serenisima 0107.csv",
                        "Codigo,Producto,Ubicacion,Lote,Vencimiento,Cantidad\n")
    assert recordatorios.listar("paula")[0]["estado"] == "disparado"


def test_recordatorio_simple_y_completar():
    r = recordatorios.crear("llamar al contador", para="emilio", creado_por="emilio")
    assert r["estado"] == "activo"
    recordatorios.completar(r["id"])
    assert recordatorios.listar("emilio") == []  # hecho → ya no aparece


# --- Paridad simulado↔real: las tools existen en el path Claude ---

def test_tools_wms_tms_en_ambos_paths():
    nombres = {t["name"] for t in angela.TOOLS}
    for t in ("consultar_deposito", "consultar_envios", "mis_recordatorios"):
        assert t in nombres, f"falta {t} en TOOLS (path real)"

    _cargar_deposito()
    _cargar_logistica()
    res, _ = angela._run_tool("consultar_deposito", {"modo": "vencimientos", "dias": 7})
    assert len(res["vencimientos"]) == 1
    res, _ = angela._run_tool("consultar_envios", {"modo": "pedido", "cliente": "garcia"})
    assert res["resultados"][0]["pedido"] == "P-1"
    res, _ = angela._run_tool("crear_recordatorio", {
        "texto": "vigilar vencimientos", "condicion": {"tipo": "vencimiento_deposito", "dias": 15}})
    assert res["condicional"] is True
    res, _ = angela._run_tool("mis_recordatorios", {})
    assert res["recordatorios"][0]["estado"] == "disparado"


# --- Moldeo por rol: el de depósito ve lo suyo, no la plata ---

def test_rol_deposito_ve_lo_suyo_y_no_finanzas():
    u = auth.perfil_publico("deposito")
    assert "deposito" in u["features"] and "logistica" in u["features"]
    for f in ("caja", "finanzas", "cuentas", "cobranzas"):
        assert f not in u["features"]
    assert u["modulos_labels"]["logistica"] == "Logística y reparto"
