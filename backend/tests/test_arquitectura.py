import os

import pytest

import auth
import config
from core import organizacion, macro


@pytest.fixture(autouse=True)
def limpio():
    for f in (organizacion.ORG_JSON, macro.CACHE_JSON):
        if os.path.exists(f):
            os.remove(f)
    yield
    for f in (organizacion.ORG_JSON, macro.CACHE_JSON):
        if os.path.exists(f):
            os.remove(f)


def test_routing_apagado_usa_sonnet():
    assert config.ROUTING_ACTIVO is False
    assert config.modelo_para({"navegar_a"}) == config.MODELO_VALIDACION
    assert "sonnet" in config.MODELO_VALIDACION


def test_modelo_para_rutea_cuando_se_active():
    # Simula routing activo sin tocar el default global.
    assert config.MODELOS["simple"].startswith("claude-haiku")
    assert config.MODELOS["analisis"].startswith("claude-sonnet")


def test_organizacion_config_y_scope():
    org = organizacion.set_config("margen_minimo", 35)
    assert org["config"]["margen_minimo"] == 35
    assert organizacion.get()["config"]["margen_minimo"] == 35
    assert organizacion.puede_config_org("dueño") is True
    assert organizacion.puede_config_org("Ventas y cobranzas") is False


def test_whatsapp_numero_a_empleado():
    u = auth.usuario_por_numero("+5491100000001")
    assert u and u["nombre"] == "Emilio"
    assert auth.usuario_por_numero("+540000") is None


def test_macro_estructura_y_fallback():
    # Sin red, cada indicador debe devolver una estructura con 'disponible'.
    d = macro.consultar(["dolar", "inflacion"])
    assert set(d.keys()) == {"dolar", "inflacion"}
    assert "disponible" in d["dolar"]
    assert "disponible" in d["inflacion"]


# --- Resiliencia del conector de cotización (BCRA cambió el formato en 07/2026) ---

def test_dolar_parsea_formato_nuevo_del_bcra(monkeypatch):
    # results ahora es una LISTA de días; el parser tiene que bancarlo.
    def fake(url):
        assert "bcra" in url
        return {"results": [{"fecha": "2026-07-03", "detalle": [{"tipoCotizacion": 1234.5}]}]}
    monkeypatch.setattr(macro, "_get_json", fake)
    d = macro.dolar_oficial()
    assert d["disponible"] is True and d["valor"] == 1234.5
    assert d["fuente"] == "BCRA" and d["fecha"] == "2026-07-03"


def test_dolar_parsea_formato_viejo_del_bcra(monkeypatch):
    # Si el BCRA vuelve al dict original, también funciona.
    def fake(url):
        return {"results": {"fecha": "2026-07-03", "detalle": [{"tipoCotizacion": 1200.0}]}}
    monkeypatch.setattr(macro, "_get_json", fake)
    d = macro.dolar_oficial()
    assert d["disponible"] is True and d["valor"] == 1200.0 and d["fuente"] == "BCRA"


def test_dolar_fallback_cuando_el_bcra_falla(monkeypatch):
    def fake(url):
        if "bcra" in url:
            raise OSError("BCRA caído")
        return {"venta": 1300.0, "fechaActualizacion": "2026-07-03T10:00:00.000Z"}
    monkeypatch.setattr(macro, "_get_json", fake)
    d = macro.dolar_oficial()
    assert d["disponible"] is True and d["valor"] == 1300.0
    assert "dolarapi" in d["fuente"]  # cita la fuente REAL, no dice BCRA
    assert d["fecha"] == "2026-07-03"


def test_dolar_ambas_fuentes_caidas_no_inventa(monkeypatch):
    def fake(url):
        raise OSError("todo caído")
    monkeypatch.setattr(macro, "_get_json", fake)
    d = macro.dolar_oficial()
    assert d["disponible"] is False and "motivo" in d


def test_indec_pide_la_serie_descendente():
    # Sin sort=desc, limit=1 devuelve ENERO 2017 como inflación "actual" (bug 03/07/2026).
    assert "sort=desc" in macro.INDEC_IPC and "limit=1" in macro.INDEC_IPC


def test_inflacion_toma_el_dato_mas_reciente_no_el_primero(monkeypatch):
    # Aunque la API devuelva varias filas o cambie el orden, se toma la fecha
    # máxima. Falla si alguna vez volvemos a citar un dato viejo como actual.
    def fake(url):
        return {"data": [["2017-01-01", 0.0159], ["2026-05-01", 0.021], ["2026-06-01", 0.019]]}
    monkeypatch.setattr(macro, "_get_json", fake)
    d = macro.inflacion_mensual()
    assert d["disponible"] is True
    # fecha máxima + fracción convertida a porcentaje real (0.019 → 1.9%)
    assert d["fecha"] == "2026-06-01" and d["valor"] == 1.9 and d["unidad"] == "%"


def test_consultar_matchea_nombres_libres(monkeypatch):
    # El modelo pide "dólar oficial"/"IPC", no nuestras keys exactas. Antes eso
    # devolvía {} silencioso y Ángela lo leía como fuente caída.
    monkeypatch.setattr(macro, "dolar_oficial", lambda: {"disponible": True, "valor": 1})
    monkeypatch.setattr(macro, "inflacion_mensual", lambda: {"disponible": True, "valor": 2})
    monkeypatch.setitem(macro._INDICADORES, "dolar", lambda: {"disponible": True, "valor": 1})
    monkeypatch.setitem(macro._INDICADORES, "inflacion", lambda: {"disponible": True, "valor": 2})
    assert set(macro.consultar(["dólar oficial", "tipo de cambio"])) == {"dolar"}
    assert set(macro.consultar(["IPC"])) == {"inflacion"}
    # nombres irreconocibles → defaults, nunca {}
    assert set(macro.consultar(["cualquier cosa"])) == {"dolar", "inflacion"}


# --- P9·C7 (M11): paridad simulado↔Claude en los nombres de tools ---

def test_tools_usadas_del_simulado_existen_en_tools():
    """El router simulado solo reporta nombres que EXISTEN en TOOLS: reportar
    tools inventadas rompió la paridad declarada y ya causó un test flaky."""
    import inspect
    import re

    import angela

    src = inspect.getsource(angela)
    reales = {t["name"] for t in angela.TOOLS}
    reportadas = set()
    for m in re.finditer(r"tools=\[([^\]]*)\]", src):
        reportadas.update(re.findall(r'"([a-z_]+)"', m.group(1)))
    fantasmas = reportadas - reales
    assert not fantasmas, f"tools reportadas que no existen: {sorted(fantasmas)}"


def test_navegar_a_declara_todas_las_secciones_actuales():
    """M12: el modelo tiene que poder llevarte a TODAS las secciones de hoy."""
    import angela

    decl = next(t for t in angela.TOOLS if t["name"] == "navegar_a")["description"]
    for seccion in ("oportunidades", "documentos", "pendientes", "administracion",
                    "cobranzas", "panel", "perfil"):
        assert f"'{seccion}'" in decl, f"navegar_a no declara «{seccion}»"
