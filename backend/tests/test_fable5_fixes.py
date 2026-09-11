"""
Tests de la auditoría (AUDITORIA_FABLE5.md) — cubren los fixes de A y B:
  A1/paridad → Ángela sabe hacer cuentas/caja también en el path real (TOOLS + _run_tool).
  A2/B4     → el modo y el modelo salen de config (fuente única, runtime).
  A4        → el grafo propaga: un cobro entra a la caja del día.
"""
from __future__ import annotations

import os

import pytest

import angela
import config
from core import cuentas, caja


@pytest.fixture(autouse=True)
def _reset_datos():
    for f in (cuentas.CUENTAS_JSON, caja.CAJA_JSON):
        if os.path.exists(f):
            os.remove(f)
    yield
    for f in (cuentas.CUENTAS_JSON, caja.CAJA_JSON):
        if os.path.exists(f):
            os.remove(f)


# --- A4: el grafo propaga (cobro de cuenta corriente → ingreso en caja) ---

def test_cobro_impacta_la_caja():
    caja.abrir(0)  # caja limpia y abierta
    ingresos_antes = caja.estado()["totales"]["ingresos"]

    cuentas.registrar_cobro("perez", 5_000_000, medio="transferencia")

    est = caja.estado()
    assert est["totales"]["ingresos"] == ingresos_antes + 5_000_000
    assert any("Cobro cta. cte." in mv.get("detalle", "") for mv in est["movimientos"])


def test_cobro_no_rompe_con_caja_cerrada():
    caja.abrir(0)
    caja.cerrar()  # caja cerrada
    # El cobro debe guardarse igual (best-effort con la caja); no debe tirar excepción.
    c = cuentas.registrar_cobro("perez", 1_000_000)
    assert c["saldo"] < 30_000_000


# --- A1 + paridad simulado↔real: Ángela sabe cuentas/caja también con tools ---

TOOLS_NUEVAS = ["cuentas_corrientes", "scoring_credito", "mensaje_cobro",
                "estado_caja", "cerrar_caja"]


def test_tools_de_cuentas_y_caja_existen_en_el_array():
    nombres = {t["name"] for t in angela.TOOLS}
    for t in TOOLS_NUEVAS:
        assert t in nombres, f"falta la tool {t} en el array TOOLS (path real)"


def test_run_tool_resuelve_cuentas_y_caja():
    caja.abrir(0)
    res, _ = angela._run_tool("cuentas_corrientes", {})
    assert "clientes" in res and "morosos" in res

    res, _ = angela._run_tool("cuentas_corrientes", {"cliente": "Pérez"})
    assert res.get("nombre") == "Almacén Don Pérez"

    res, _ = angela._run_tool("scoring_credito", {"cliente": "La Esquina"})
    assert res["conocido"] is True

    res, _ = angela._run_tool("estado_caja", {})
    assert "totales" in res

    res, accion = angela._run_tool("cerrar_caja", {"declarado": 0})
    assert "total" in res and accion["section"] == "caja"


# --- A2 / B4: el modo y el modelo salen de config, en runtime ---

def test_modo_se_evalua_en_runtime(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert config.modo() == "simulado"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert config.modo() == "claude"


def test_modelo_default_es_sonnet_no_fable():
    # Fable 5 está DISPONIBLE pero no es el default de validación (decisión tomada).
    assert "claude-fable-5" in config.MODELOS_DISPONIBLES
    assert config.modelo_para() != "claude-fable-5"
    assert config.modelo_para().startswith("claude-sonnet")


# --- C3: el fallback TLS de macro tiene que atrapar el SSLError aunque urllib
# --- lo envuelva en URLError (que es lo que pasa en un handshake fallido real) ---

def test_tls_fallback_atrapa_ssl_envuelto_en_urlerror(monkeypatch):
    import ssl
    import urllib.error
    from core import macro

    modos = []

    def fake_fetch(url, ctx):
        modos.append(ctx.verify_mode)
        if ctx.verify_mode != ssl.CERT_NONE:
            raise urllib.error.URLError(ssl.SSLCertVerificationError("cadena incompleta"))
        return {"ok": True}

    monkeypatch.setattr(macro, "_fetch", fake_fetch)
    assert macro._get_json("https://ejemplo")["ok"] is True
    assert modos == [ssl.CERT_REQUIRED, ssl.CERT_NONE]


def test_wmi_deshabilitado_para_que_el_sdk_no_se_cuelgue():
    # En esta máquina el WMI de Windows se cuelga y el SDK de Anthropic pasa por
    # platform.system() al armar headers. config debe dejar _wmi_query tirando
    # OSError (así platform cae en su fallback oficial y nada se cuelga).
    import platform
    if os.name != "nt" or not hasattr(platform, "_wmi_query"):
        pytest.skip("solo aplica en Windows con el path WMI")
    with pytest.raises(OSError):
        platform._wmi_query("OS", "Version")
    # y el fallback tiene que responder al instante con datos razonables
    release, version, csd, ptype = platform.win32_ver()
    assert version  # ej. "10.0.26200"


def test_tls_fallback_no_reintenta_errores_no_ssl(monkeypatch):
    import urllib.error
    from core import macro

    def fake_fetch(url, ctx):
        raise urllib.error.URLError(TimeoutError("la fuente no responde"))

    monkeypatch.setattr(macro, "_fetch", fake_fetch)
    with pytest.raises(urllib.error.URLError):
        macro._get_json("https://ejemplo")
