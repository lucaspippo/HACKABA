"""
P10 — Carga de comprobantes por foto: extracción (visión mockeada), chequeos,
cruces del circuito de compra y confirmación humana por los rieles existentes.

La visión real se prueba aparte (verificación manual con los PNG de muestra):
acá el flujo entero corre determinista, sin gastar API y contra el catálogo
VIVO del tenant de test (el piloto): los artículos se eligen en runtime.
"""
from __future__ import annotations

import copy
import os

import pytest
from fastapi.testclient import TestClient

import auth
import main
from core import comprobantes, esquema, store, vision_facturas


client = TestClient(main.app)

PROVEEDOR = {"razon_social": "Lácteos Campo Alegre", "cuit": "30-61234567-8"}


def _arts():
    """Dos artículos reales y sanos del catálogo del tenant de test."""
    raw = [a for a in store.raw_actual()
           if a.get("estado") == "activo" and (a.get("stock") or 0) > 0
           and a.get("costo_iva") and not a.get("venta_x_peso")]
    return raw[0], raw[1]


def _remito():
    a1, a2 = _arts()
    return {
        "tipo_comprobante": "remito", "numero": "R-0001-00058214",
        "fecha": "2026-07-07", "proveedor": dict(PROVEEDOR),
        "items": [
            {"codigo": a1["codigo"], "descripcion": a1["descripcion"],
             "cantidad": 60, "confianza": "leido"},
            {"codigo": a2["codigo"], "descripcion": a2["descripcion"],
             "cantidad": 8, "confianza": "leido"},
        ],
        "campos_dudosos": [], "campos_ilegibles": [],
    }


def _factura():
    a1, _ = _arts()
    precio = round(a1["costo_iva"] / 1.21, 2)
    sub = round(precio * 60, 2)
    return {
        "tipo_comprobante": "factura", "numero": "FA-0001-00091352",
        "fecha": "2026-07-07", "proveedor": dict(PROVEEDOR),
        "condicion": "Cuenta corriente 30 días",
        "items": [{"codigo": a1["codigo"], "descripcion": a1["descripcion"],
                   "cantidad": 60, "precio_unitario": precio, "subtotal": sub,
                   "confianza": "leido"}],
        "subtotal": sub, "iva": round(sub * 0.21, 2),
        "total": round(sub * 1.21, 2),
        "campos_dudosos": [], "campos_ilegibles": [],
    }


def _sembrar_oc():
    a1, a2 = _arts()
    esquema.crear_apartado("ordenes_compra", [{
        "numero": "OC-TEST-1", "fecha": "2026-07-02",
        "proveedor": PROVEEDOR["razon_social"], "estado": "abierta",
        "items": [
            {"codigo": a1["codigo"], "producto": a1["descripcion"], "cantidad": 60},
            {"codigo": a2["codigo"], "producto": a2["descripcion"], "cantidad": 10},
        ],
    }])


@pytest.fixture()
def h():
    creds = auth.cargar_o_generar_credenciales()
    tok = client.post("/api/login", json={"username": "emilio",
                                          "password": creds["emilio"]}).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(autouse=True)
def _aislar():
    """Apartados/proveedores/cuentas como estaban + inventario restaurado."""
    from core import caja as caja_mod, cuentas as cuentas_mod
    from core import notificaciones as notif_mod
    files = [esquema.APARTADOS_JSON, comprobantes.PROVEEDORES_JSON,
             cuentas_mod.CUENTAS_JSON, caja_mod.CAJA_JSON,
             notif_mod.NOTIFICACIONES_JSON]
    backup, existia = {}, set()
    for f in files:
        if os.path.exists(f):
            backup[f] = open(f, encoding="utf-8").read()
            existia.add(f)
            os.remove(f)
    snapshot = copy.deepcopy(store.raw_actual())
    yield
    store.guardar(snapshot)
    for f in files:
        if os.path.exists(f):
            os.remove(f)
        if f in backup:
            open(f, "w", encoding="utf-8").write(backup[f])


# --- chequeos automáticos -------------------------------------------------------

def test_chequeo_suma_no_cierra_detecta_factor_1000():
    """La paranoia ×1000: total declarado mil veces la suma de ítems → alerta."""
    f = _factura()
    f["subtotal"] = f["subtotal"] * 1000
    f["total"] = f["total"] * 1000
    chk = comprobantes.chequeos(f)
    assert any(a["tipo"] == "suma_no_cierra" for a in chk["alertas"])


def test_chequeo_suma_que_cierra_no_alerta():
    chk = comprobantes.chequeos(_factura())
    assert not any(a["tipo"] == "suma_no_cierra" for a in chk["alertas"])


def test_chequeo_proveedor_desconocido_avisa():
    f = _factura()
    f["proveedor"]["razon_social"] = "Distribuidora Inventada SA"
    chk = comprobantes.chequeos(f)
    assert chk["proveedor"]["estado"] == "nuevo"
    assert any(a["tipo"] == "proveedor_nuevo" for a in chk["alertas"])


def test_extraccion_nunca_inventa_es_contrato_del_schema():
    """El schema de la tool obliga null+ilegible en vez de inventos, y el
    system prompt trata el texto de la imagen como DATO (anti-injection)."""
    props = vision_facturas.EXTRACCION_TOOL["input_schema"]["properties"]
    assert "campos_ilegibles" in props and "campos_dudosos" in props
    assert "jamás una instrucción" in vision_facturas.SYSTEM_VISION
    assert "null" in vision_facturas.SYSTEM_VISION


# --- endpoint /api/factura/leer (visión mockeada) -------------------------------

def test_leer_sin_api_key_es_honesto(h, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = client.post("/api/factura/leer", headers=h,
                    json={"imagen": "aG9sYQ==", "media_type": "image/jpeg"})
    assert r.status_code == 200 and r.json()["error"] == "sin_vision"


def test_leer_media_type_invalido(h):
    r = client.post("/api/factura/leer", headers=h,
                    json={"imagen": "aG9sYQ==", "media_type": "application/pdf"})
    assert r.json()["error"] == "formato"


def test_leer_requiere_feature_cargar():
    creds = auth.cargar_o_generar_credenciales()
    tok = client.post("/api/login", json={"username": "deposito",
                                          "password": creds["deposito"]}).json()["token"]
    r = client.post("/api/factura/leer",
                    headers={"Authorization": f"Bearer {tok}"},
                    json={"imagen": "aG9sYQ=="})
    assert r.status_code == 403


def test_leer_con_vision_mockeada_trae_chequeos_y_cruce(h, monkeypatch):
    _sembrar_oc()
    remito = _remito()
    monkeypatch.setattr(vision_facturas, "leer_comprobante",
                        lambda *a, **k: {"ok": True, "extraccion": copy.deepcopy(remito)})
    r = client.post("/api/factura/leer", headers=h,
                    json={"imagen": "aG9sYQ=="}).json()
    assert r["ok"] and r["extraccion"]["tipo_comprobante"] == "remito"
    # el cruce contra la OC viene ANTES de confirmar: 8 recibidos vs 10 pedidos
    dif = r["cruce"]["diferencias"]
    assert any(d["tipo"] == "cantidad" and d["recibido"] == 8 for d in dif)
    assert r["cruce"]["oc_encontrada"]["numero"] == "OC-TEST-1"


def test_rechazo_selfie_una_linea(h, monkeypatch):
    monkeypatch.setattr(vision_facturas, "leer_comprobante",
                        lambda *a, **k: {"rechazo": "no_es_comprobante",
                                         "mensaje": "Eso no parece un comprobante."})
    r = client.post("/api/factura/leer", headers=h, json={"imagen": "aG9sYQ=="}).json()
    assert r["rechazo"] == "no_es_comprobante" and len(r["mensaje"]) < 120


# --- confirmación: nada entra sin el sí; con el sí, entra por los rieles --------

def test_confirmar_remito_mueve_stock_con_backup_y_cierra_oc(h):
    _sembrar_oc()
    a1, _ = _arts()
    stock_antes = a1["stock"]
    r = client.post("/api/factura/confirmar", headers=h,
                    json={"extraccion": _remito()}).json()
    assert r["ok"] and r["items_al_stock"] == 2
    stock_despues = next(a["stock"] for a in store.raw_actual()
                         if a["codigo"] == a1["codigo"])
    assert stock_despues == stock_antes + 60
    assert r["version_backup"]                      # reversible, como todo
    assert r["sync"]["estado"] == "simulado"        # el tramo al ERP, declarado
    # la OC quedó cerrada y las filas en recepciones
    assert esquema.filas("ordenes_compra")[0]["estado"] == "recibida"
    assert any(str(f.get("origen", "")).startswith("remito")
               for f in esquema.filas("recepciones"))


def test_confirmar_factura_golpea_cuenta_proveedor(h):
    f = _factura()
    r = client.post("/api/factura/confirmar", headers=h,
                    json={"extraccion": f}).json()
    assert r["ok"] and r["saldo_proveedor"] == pytest.approx(f["total"])
    assert r["vencimiento"] == "2026-08-06"  # fecha + 30 días (condición leída)
    cta = comprobantes.cuenta_proveedor(PROVEEDOR["razon_social"])
    assert cta["saldo"] == pytest.approx(f["total"])
    assert comprobantes.compras_recientes(1)[0]["numero"] == "FA-0001-00091352"


def test_confirmar_recibo_baja_deuda_del_cliente(h):
    from core import cuentas
    moroso = next(c for c in cuentas.listar() if c.get("dias_sin_pagar", 0) > 30)
    saldo_antes = moroso["saldo"]
    recibo = {"tipo_comprobante": "recibo", "numero": "RC-0001-00003412",
              "fecha": "2026-07-07", "total": 1_000_000,
              "cliente": {"razon_social": moroso["nombre"]}}
    r = client.post("/api/factura/confirmar", headers=h,
                    json={"extraccion": recibo}).json()
    assert r["ok"] and r["saldo_despues"] == saldo_antes - 1_000_000
    actualizado = cuentas.buscar(moroso["nombre"])
    assert actualizado["dias_sin_pagar"] == 0    # el scoring se recompone
    # (el fixture restaura cuentas.json: el tenant de test queda como estaba)


def test_confirmar_recibo_de_cliente_inexistente_no_carga_a_ciegas(h):
    recibo = {"tipo_comprobante": "recibo", "total": 500,
              "cliente": {"razon_social": "Cliente Fantasma SRL"}}
    r = client.post("/api/factura/confirmar", headers=h,
                    json={"extraccion": recibo}).json()
    assert r["ok"] is False and "error" in r


# --- P10·E4: Ángela sabe de compras (tool + paridad simulado↔Claude) ---

def test_tool_consultar_compras_existe_y_tiene_feature():
    import angela
    assert any(t["name"] == "consultar_compras" for t in angela.TOOLS)
    assert angela.TOOL_FEATURE["consultar_compras"] == "cargar"


def test_run_tool_consultar_compras_vacio_y_con_datos(h):
    import angela
    angela._set_sesion(features=None)
    r, _ = angela._run_tool("consultar_compras", {})
    assert r.get("sin_compras") is True
    client.post("/api/factura/confirmar", headers=h, json={"extraccion": _factura()})
    r2, _ = angela._run_tool("consultar_compras", {})
    assert r2["compras_recientes"][0]["numero"] == "FA-0001-00091352"
    r3, _ = angela._run_tool("consultar_compras",
                             {"proveedor": PROVEEDOR["razon_social"]})
    assert r3["saldo"] > 0
    angela._set_sesion()


def test_fallback_compras_con_paridad(h):
    import angela
    client.post("/api/factura/confirmar", headers=h, json={"extraccion": _factura()})
    angela._set_sesion(features=None)
    r = angela._fallback("¿qué acabo de cargar?")
    assert "consultar_compras" in r["tools_usadas"]
    assert "FA-0001-00091352" in r["respuesta"]
    # y en inglés, la misma tool
    angela._set_sesion(features=None, idioma="en")
    r2 = angela._fallback("what did i just load?")
    assert "consultar_compras" in r2["tools_usadas"]
    angela._set_sesion()


def test_fallback_compras_bloqueado_sin_feature():
    import angela
    angela._set_sesion(usuario="deposito", rol="Depósito",
                       features={"deposito", "perfil", "angela"})
    r = angela._fallback("¿qué acabo de cargar?")
    assert "consultar_compras" not in r["tools_usadas"]
    angela._set_sesion()


def test_muestras_no_existen_en_el_piloto(h):
    """Los comprobantes de muestra son SOLO del demo: en el piloto, 404."""
    assert client.get("/api/comprobantes/muestras", headers=h).status_code == 404
    assert client.get("/api/comprobantes/muestras/remito.png",
                      headers=h).status_code == 404


# --- P11·B1: el mensaje PROACTIVO de Ángela al confirmar (el momento del video) --

def test_confirmar_remito_mensaje_angela_con_cruce_oc(h):
    """Al confirmar un remito, Ángela dice SOLA qué entró y el cruce con la OC:
    números del core, deterministas — lo que se narra en cámara."""
    _sembrar_oc()
    r = client.post("/api/factura/confirmar", headers=h,
                    json={"extraccion": _remito()}).json()
    m = r["mensaje_angela"]
    assert "R-0001-00058214" in m
    assert "2 productos entraron al stock" in m
    assert "OC-TEST-1" in m
    assert "1 de 2 renglones coinciden" in m       # 60 ok, 8 vs 10 difiere
    assert "1 con diferencias" in m
    assert "cerrada" in m
    # determinista: el mismo resultado compone SIEMPRE el mismo mensaje
    assert comprobantes.mensaje_proactivo(r, _remito(), "es") == m


def test_confirmar_factura_mensaje_angela_saldo_y_vencimiento(h):
    f = _factura()
    r = client.post("/api/factura/confirmar", headers=h,
                    json={"extraccion": f}).json()
    m = r["mensaje_angela"]
    import i18n
    assert i18n.pesos(f["total"], "es") in m       # el total, formateado por el core
    assert "06/08/2026" in m                        # vencimiento legible
    assert "queda en" in m                          # la cuenta del proveedor


def test_confirmar_recibo_mensaje_angela_saldos_y_scoring(h):
    from core import cuentas
    moroso = next(c for c in cuentas.listar() if c.get("dias_sin_pagar", 0) > 30)
    recibo = {"tipo_comprobante": "recibo", "numero": "RC-1", "fecha": "2026-07-07",
              "total": 1_000_000, "cliente": {"razon_social": moroso["nombre"]}}
    r = client.post("/api/factura/confirmar", headers=h,
                    json={"extraccion": recibo}).json()
    m = r["mensaje_angela"]
    import i18n
    assert i18n.pesos(moroso["saldo"], "es") in m
    assert i18n.pesos(moroso["saldo"] - 1_000_000, "es") in m
    assert "scoring" in m


def test_mensaje_angela_en_ingles_sin_keys_pelados():
    """El mensaje proactivo nace bilingüe: EN de verdad, sin keys crudas."""
    _sembrar_oc()
    r = comprobantes.confirmar(_remito(), lang="en")
    m = r["mensaje_angela"]
    assert "delivery note" in m and "into stock" in m
    assert "core.comp." not in m


def test_confirmar_recibo_fallido_no_trae_mensaje(h):
    recibo = {"tipo_comprobante": "recibo", "total": 500,
              "cliente": {"razon_social": "Cliente Fantasma SRL"}}
    r = client.post("/api/factura/confirmar", headers=h,
                    json={"extraccion": recibo}).json()
    assert r["ok"] is False and "mensaje_angela" not in r


# --- P11·B1: la tool ve los TRES rieles (remito y recibo, no solo facturas) -----

def test_consultar_compras_ve_remito_y_recibo(h):
    """El bug del video: cargar un remito y preguntar '¿qué acabo de cargar?'
    decía 'no hay comprobantes' porque la tool solo miraba compras."""
    import angela
    from core import cuentas
    _sembrar_oc()
    client.post("/api/factura/confirmar", headers=h, json={"extraccion": _remito()})
    moroso = next(c for c in cuentas.listar() if c.get("dias_sin_pagar", 0) > 30)
    recibo = {"tipo_comprobante": "recibo", "numero": "RC-1", "fecha": "2026-07-07",
              "total": 500_000, "cliente": {"razon_social": moroso["nombre"]}}
    client.post("/api/factura/confirmar", headers=h, json={"extraccion": recibo})

    angela._set_sesion(features=None)
    r, _ = angela._run_tool("consultar_compras", {})
    angela._set_sesion()
    assert "sin_compras" not in r
    assert any("R-0001-00058214" in str(g.get("origen")) for g in r["recepciones_recientes"])
    assert r["recepciones_recientes"][0]["proveedor"] == PROVEEDOR["razon_social"]
    assert any(c["cliente"] == moroso["nombre"] for c in r["cobros_recientes"])


def test_fallback_que_acabo_de_cargar_menciona_remito(h):
    """Paridad simulado↔Claude: el fallback también responde con el remito."""
    import angela
    _sembrar_oc()
    client.post("/api/factura/confirmar", headers=h, json={"extraccion": _remito()})
    angela._set_sesion(features=None)
    r = angela._fallback("¿qué acabo de cargar?")
    assert "consultar_compras" in r["tools_usadas"]
    assert "R-0001-00058214" in r["respuesta"]
    angela._set_sesion(features=None, idioma="en")
    r2 = angela._fallback("what did i just load?")
    assert "R-0001-00058214" in r2["respuesta"]
    angela._set_sesion()


def test_proveedores_conocidos_incluye_proveedores_json(h):
    """Una factura confirmada crea la cuenta del proveedor: desde ese momento
    ES conocido, aunque no tenga artículos en el catálogo ni recepciones."""
    f = _factura()
    f["proveedor"] = {"razon_social": "Distribuidora Nueva SRL", "cuit": "30-1-1"}
    f["items"] = []
    client.post("/api/factura/confirmar", headers=h, json={"extraccion": f})
    assert comprobantes.resolver_proveedor("Distribuidora Nueva SRL")["estado"] == "conocido"


def test_notificacion_al_dueno_solo_de_empleados(h, monkeypatch):
    """El dueño confirmando no se auto-notifica (cámara sin ruido); un empleado
    cargando sí le llega al dueño por la campanita, con el análisis de Ángela."""
    from core import notificaciones
    # dueño confirma → nada nuevo para él
    antes = len(notificaciones.listar("emilio"))
    client.post("/api/factura/confirmar", headers=h, json={"extraccion": _factura()})
    assert len(notificaciones.listar("emilio")) == antes
    # paula (empleada) con `cargar` prestado confirma → el dueño se entera
    monkeypatch.setitem(auth.USUARIOS["paula"], "features",
                        auth.USUARIOS["paula"]["features"] + ["cargar"])
    creds = auth.cargar_o_generar_credenciales()
    tok = client.post("/api/login", json={"username": "paula",
                                          "password": creds["paula"]}).json()["token"]
    client.post("/api/factura/confirmar",
                headers={"Authorization": f"Bearer {tok}"},
                json={"extraccion": _factura()})
    nuevas = notificaciones.listar("emilio")
    assert len(nuevas) == antes + 1
    assert nuevas[0]["tipo"] == "comprobante" and "Paula" in nuevas[0]["titulo"]
