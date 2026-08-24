"""LA VOZ DEL PISO — que hablar no sea un atajo para saltear los controles.

El empleado dicta porque tiene las manos ocupadas, no porque quiera menos
seguridad. Lo que se protege acá:
  · un número dicho por voz pasa por el MISMO peaje que uno leído de un remito;
  · un producto NUNCA lo elige el modelo solo cuando hay empate real;
  · nada se persiste sin que un humano apruebe.
"""
import pytest

from core import transcripcion, voz

ARTICULO = {"codigo": 1, "descripcion": "LECHE ENTERA CAMPO ALEGRE 1L (X12U)",
            "um": "UN", "venta_x_peso": False, "costo_iva": 1000.0}


# --- transcripción: los tres caminos, y el que falta ------------------------

def test_si_el_navegador_ya_transcribio_no_se_toca():
    r = transcripcion.transcribir(texto="llegaron ocho cajas falladas")
    assert r["ok"] and r["origen"] == "navegador"
    assert r["texto"] == "llegaron ocho cajas falladas"


def test_audio_sin_transcriptor_lo_dice_no_lo_inventa():
    # audio real que no es muestra: hoy no hay a quién mandárselo
    r = transcripcion.transcribir(audio_b64="AAAAAAAAAAAAAAAA", lang="es")
    assert r["ok"] is False and r["motivo"]


def test_sin_audio_ni_texto_no_explota():
    r = transcripcion.transcribir(lang="es")
    assert r["ok"] is False


# --- el matching de producto -------------------------------------------------

def test_los_candidatos_son_una_lista_no_una_decision():
    c = voz.candidatos("leche entera campo alegre")
    assert isinstance(c, list)
    if c:  # el piloto puede no tener ese producto
        assert {"codigo", "descripcion"} <= set(c[0])


def test_una_palabra_suelta_no_matchea_medio_catalogo():
    assert voz.candidatos("de") == []
    assert voz.candidatos("") == []


def test_un_producto_inexistente_bloquea_no_adivina():
    p = voz.proponer("faltan 3 de zzzz inexistente qqq", lang="es")
    campos = {b["campo"] for b in p["bloqueado"]}
    assert "producto" in campos or p["intencion"] == "consulta"


# --- el peaje del número: el mismo del remito -------------------------------

def test_una_cantidad_imposible_dicha_por_voz_frena_igual(monkeypatch):
    monkeypatch.setattr(voz, "interpretar", lambda t, lang=None: {
        "intencion": "conteo", "producto": "leche entera campo alegre",
        "cantidad": 1.234, "motivo": None, "cliente": None, "nota": None,
        "confianza": "clara", "_origen": "test"})
    p = voz.proponer("da igual", lang="es")
    if p["candidatos"]:   # requiere catálogo con ese producto
        assert any(b["campo"] == "cantidad" for b in p["bloqueado"])


def test_sin_cantidad_un_faltante_no_puede_confirmarse(monkeypatch):
    monkeypatch.setattr(voz, "interpretar", lambda t, lang=None: {
        "intencion": "faltante", "producto": "leche entera campo alegre",
        "cantidad": None, "motivo": "roto", "cliente": None, "nota": None,
        "confianza": "clara", "_origen": "test"})
    p = voz.proponer("se rompieron unas cajas", lang="es")
    assert any(b["campo"] == "cantidad" for b in p["bloqueado"])


def test_el_historial_de_recepciones_no_se_usa_contra_un_faltante(monkeypatch):
    """8 cajas falladas sobre una entrega de 259 es lo NORMAL. Comparar esas dos
    distribuciones daba un falso positivo, y un validador que grita de más se
    apaga a la semana."""
    monkeypatch.setattr(voz, "interpretar", lambda t, lang=None: {
        "intencion": "faltante", "producto": "leche entera campo alegre",
        "cantidad": 8, "motivo": "roto", "cliente": None, "nota": None,
        "confianza": "clara", "_origen": "test"})
    p = voz.proponer("llegaron ocho falladas", lang="es")
    assert not [b for b in p["bloqueado"] if b["campo"] == "cantidad"]


# --- human-in-the-loop -------------------------------------------------------

def test_proponer_nunca_persiste(monkeypatch):
    from core import piso
    antes = len(piso.listar())
    voz.proponer("Ángela, llegaron ocho cajas falladas de gaseosa", lang="es")
    assert len(piso.listar()) == antes, "proponer() NO puede escribir un reporte"


def test_una_consulta_no_propone_escribir_nada():
    p = voz.proponer("¿cuánto sale el kilo de jamón cocido?", lang="es")
    if p["intencion"] == "consulta":
        assert p["accion"]["tipo"] == "preguntar"
        assert p["bloqueado"] == []


def test_toda_intencion_tiene_un_riel_real():
    """Una intención sin riel es una promesa que no se cumple."""
    for nombre, cfg in voz.INTENCIONES.items():
        assert cfg["riel"], nombre


# --- las frases preparadas del demo -----------------------------------------

def _muestras():
    return (transcripcion.muestras_crudas().get("muestras") or {}).values()


solo_demo = pytest.mark.skipif(not list(_muestras()),
                               reason="las muestras viven en el tenant demo")


@solo_demo
def test_las_frases_preparadas_no_pasan_por_el_modelo(monkeypatch):
    import os
    monkeypatch.setenv("ANTHROPIC_API_KEY", "no-deberia-usarse")
    monkeypatch.setattr("anthropic.Anthropic", lambda **k: (_ for _ in ()).throw(
        AssertionError("una frase preparada NO puede llamar al modelo")))
    for m in _muestras():
        r = voz.interpretar(m["texto"], lang="es")
        assert r["_origen"] == "muestra"
        assert r["intencion"] == m["interpretacion"]["intencion"]


@solo_demo
def test_editar_una_propuesta_no_ensucia_la_frase_canonica():
    m = next(iter(_muestras()))
    a = voz.interpretar(m["texto"], lang="es")
    a["cantidad"] = 99999
    b = voz.interpretar(m["texto"], lang="es")
    assert b["cantidad"] != 99999


@solo_demo
def test_el_demo_de_voz_cuenta_la_historia_completa():
    """Tres casos reales pasan limpio; el número imposible lo frena el código."""
    estados = {}
    for k, m in (transcripcion.muestras_crudas()["muestras"]).items():
        p = voz.proponer(m["texto"], lang="es")
        estados[k] = bool(p["bloqueado"])
    assert estados.get("deposito_fallado") is False
    assert estados.get("reparto_entrega_parcial") is False
    assert estados.get("mostrador_precio") is False
    assert estados.get("deposito_escala") is True, "el ×48 TIENE que frenar"
