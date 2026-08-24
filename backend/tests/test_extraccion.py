"""El seam de extracción: una muestra conocida se resuelve SIN LLM, siempre igual.

Lo que se protege: que el momento más impactante del demo ("foto → datos") no
dependa de que haya red y API key en la sala, y que ese atajo no se pueda
disparar desde el cliente (se reconoce por hash del contenido, no por un flag).
"""
import base64
import json
import os

import pytest

from core import comprobantes, extraccion, paths

REMITO = os.path.join(paths.DATA_DIR, "comprobantes", "remito.png")
hay_muestras = os.path.exists(REMITO)
solo_demo = pytest.mark.skipif(not hay_muestras, reason="las muestras viven en el tenant demo")


def _b64(ruta):
    with open(ruta, "rb") as f:
        return base64.b64encode(f.read()).decode()


@solo_demo
def test_la_muestra_no_pasa_por_la_vision(monkeypatch):
    # si la visión se llegara a llamar, este test explota: es el punto entero
    def _prohibido(*a, **k):
        raise AssertionError("una muestra NO puede llamar a la visión")
    from core import vision_facturas
    monkeypatch.setattr(vision_facturas, "leer_comprobante", _prohibido)

    r = extraccion.extraer(_b64(REMITO), "image/png", "es")
    assert r["ok"] is True and r["origen"] == "muestra"
    assert r["extraccion"]["tipo_comprobante"] == "remito"


@solo_demo
def test_es_determinista():
    a = extraccion.extraer(_b64(REMITO), "image/png", "es")["extraccion"]
    b = extraccion.extraer(_b64(REMITO), "image/png", "es")["extraccion"]
    assert a == b


@solo_demo
def test_editar_lo_extraido_no_ensucia_el_canonico():
    # la card es EDITABLE: si el que llama muta la extracción, la próxima
    # lectura tiene que volver a salir limpia
    primera = extraccion.extraer(_b64(REMITO), "image/png", "es")["extraccion"]
    primera["items"][0]["cantidad"] = 99999
    primera["numero"] = "PISADO"
    segunda = extraccion.extraer(_b64(REMITO), "image/png", "es")["extraccion"]
    assert segunda["numero"] != "PISADO"
    assert segunda["items"][0]["cantidad"] != 99999


@solo_demo
def test_una_imagen_cualquiera_va_a_la_vision(monkeypatch):
    llamadas = []
    from core import vision_facturas
    monkeypatch.setattr(vision_facturas, "leer_comprobante",
                        lambda *a, **k: llamadas.append(1) or {"error": "sin_vision"})
    # un PNG de 1×1 que no es ninguna muestra
    otro = base64.b64encode(bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
        "1f15c4890000000a49444154789c6300010000050001"
        "0d0a2db40000000049454e44ae426082")).decode()
    r = extraccion.extraer(otro, "image/png", "es")
    assert llamadas, "una imagen desconocida TIENE que ir a la visión real"
    assert r["origen"] == "vision"


@solo_demo
def test_la_muestra_dice_lo_que_dibuja_la_imagen():
    """El JSON canónico y el PNG salen del mismo script: no pueden divergir."""
    ruta = os.path.join(paths.DATA_DIR, "comprobantes", "extracciones.json")
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    import hashlib
    for mid, m in datos["muestras"].items():
        png = os.path.join(paths.DATA_DIR, "comprobantes", f"{mid}.png")
        with open(png, "rb") as f:
            real = hashlib.sha256(f.read()).hexdigest()
        assert m["sha256"] == real, (
            f"{mid}.png cambió sin regenerar extracciones.json — "
            "corré data-demo/comprobantes/generar_comprobantes.py")


# --- el remito de muestra cuenta la historia que el demo necesita -----------

@solo_demo
def test_el_remito_trae_lote_y_vencimiento():
    ext = extraccion.extraer(_b64(REMITO), "image/png", "es")["extraccion"]
    assert ext["items"], "el remito tiene que traer ítems"
    for it in ext["items"]:
        assert it.get("lote") and it.get("vencimiento")
        assert len(it["vencimiento"]) == 10 and it["vencimiento"][4] == "-"  # ISO


@solo_demo
def test_el_cruce_contra_la_orden_encuentra_las_dos_diferencias():
    ext = extraccion.extraer(_b64(REMITO), "image/png", "es")["extraccion"]
    c = comprobantes.cruzar_remito(ext)
    assert c["oc_encontrada"]["numero"] == "OC-2026-0847"
    tipos = sorted(d["tipo"] for d in c["diferencias"])
    # una llegó incompleta y otra no se había pedido: es la historia del demo
    assert tipos == ["cantidad", "no_pedido"]
    assert c["coincidencias"] == 4


@solo_demo
def test_el_reclamo_sale_de_una_cuenta_no_de_una_estimacion():
    from core import store
    ext = extraccion.extraer(_b64(REMITO), "image/png", "es")["extraccion"]
    c = comprobantes.cruzar_remito(ext)
    rec = comprobantes.reclamo_sugerido(c, "Lácteos Campo Alegre", "es")
    assert rec and rec["items"]
    catalogo = {a["descripcion"]: a for a in store.raw_actual()}
    for it in rec["items"]:
        costo = catalogo[it["producto"]]["costo_iva"]
        assert it["monto"] == pytest.approx(it["falta"] * costo, rel=1e-6)
    assert rec["monto"] == pytest.approx(sum(i["monto"] for i in rec["items"]), rel=1e-6)


def test_lo_que_llego_de_mas_no_es_un_reclamo():
    cruce = {"diferencias": [{"tipo": "cantidad", "producto": "X",
                              "pedido": 5, "recibido": 9}]}
    assert comprobantes.reclamo_sugerido(cruce, "Prov", "es") is None


def test_sin_diferencias_no_hay_reclamo():
    assert comprobantes.reclamo_sugerido({"diferencias": []}, "Prov", "es") is None
