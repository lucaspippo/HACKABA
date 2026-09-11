"""
Contexto macroeconómico bajo demanda — fuentes oficiales, no documento estático.

Ángela consulta esto SOLO cuando el pedido lo requiere ("¿me conviene comprar
ahora?", una orden de productos dolarizados), nunca en cada mensaje. Trae el dato
con fecha y fuente; si la fuente no responde, lo dice. Cachea por día para no
pegarle a la API en cada consulta.

Fuentes (gratuitas, JSON):
  - BCRA: tipo de cambio oficial USD.
  - INDEC vía datos.gob.ar: inflación mensual.
La estructura permite sumar fuentes (tasas, regulaciones) sin reescribir.
"""
from __future__ import annotations

import datetime
import json
import os
import ssl
import unicodedata
import urllib.error
import urllib.request

from . import paths

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = paths.DATA_DIR  # por-tenant: env POLPILOT_DATA_DIR o data/ (ver core/paths.py)
CACHE_JSON = os.path.join(DATA_DIR, "macro_cache.json")

BCRA_USD = "https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones/USD"
# Fallback de cotización oficial (SOLO si el BCRA falla): API pública estable,
# sin key. La respuesta siempre lleva la fuente real para que Ángela la cite.
DOLARAPI_OFICIAL = "https://dolarapi.com/v1/dolares/oficial"
# OJO: sort=desc es OBLIGATORIO. Sin él la serie viene ascendente y limit=1
# devuelve enero de 2017 como si fuera la inflación actual (bug real, 03/07/2026).
INDEC_IPC = ("https://apis.datos.gob.ar/series/api/series/"
             "?ids=148.3_INIVELNAL_DICI_M_26:percent_change&limit=1&sort=desc&format=json")
# La MISMA serie sin ':percent_change' es el NIVEL del índice (base dic-2016=100):
# lo que hace falta para deflactar montos históricos ("pesos de hoy"). ~4KB total.
INDEC_IPC_SERIE = ("https://apis.datos.gob.ar/series/api/series/"
                   "?ids=148.3_INIVELNAL_DICI_M_26&limit=1000&sort=asc&format=json")

_TIMEOUT = 4


def _hoy() -> str:
    # P11·B13b: el "hoy" congelable de la casa (P9·B), no la fecha del reloj.
    # En el demo (POLPILOT_DEMO_TODAY) el cache macro queda estable para
    # siempre: cero fetches vivos en cámara. En el piloto, fechas.hoy() ES
    # la fecha real: nada cambia.
    from .fechas import hoy
    return hoy().isoformat()


def _cache_load() -> dict:
    try:
        return json.load(open(CACHE_JSON, encoding="utf-8"))
    except Exception:
        return {}


def _cache_save(c: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(c, open(CACHE_JSON, "w", encoding="utf-8"), ensure_ascii=False)


def _fetch(url: str, ctx):
    req = urllib.request.Request(url, headers={"User-Agent": "PolPilot/1.0"})
    with urllib.request.urlopen(req, timeout=_TIMEOUT, context=ctx) as r:
        return json.load(r)


def _get_json(url: str):
    """Primero intenta CON verificación TLS (lo correcto). Sólo si la cadena del
    BCRA/INDEC falla —a veces viene incompleta— cae a un contexto sin verificar,
    dato público de sólo lectura. Así no bajamos la seguridad por default."""
    try:
        return _fetch(url, ssl.create_default_context())
    except (ssl.SSLError, urllib.error.URLError) as e:
        # urllib envuelve el SSLError del handshake en URLError(reason=SSLError),
        # así que hay que mirar la causa; si no es un problema de certificado,
        # no es de cadena incompleta y no corresponde reintentar sin verificar.
        causa = getattr(e, "reason", e)
        if not isinstance(causa, ssl.SSLError):
            raise
        inseguro = ssl.create_default_context()
        inseguro.check_hostname = False
        inseguro.verify_mode = ssl.CERT_NONE
        return _fetch(url, inseguro)


def _con_cache(clave: str, fetch, lang: str | None = None) -> dict:
    """Devuelve el valor cacheado del día; si no, lo busca y lo guarda."""
    cache = _cache_load()
    if cache.get(clave, {}).get("fecha_consulta") == _hoy():
        return cache[clave]
    try:
        val = fetch()
        val["fecha_consulta"] = _hoy()
        cache[clave] = val
        _cache_save(cache)
        return val
    except Exception as e:
        import i18n
        return {"disponible": False,
                "motivo": i18n.t("core.macro.no_respondio", lang,
                                 error=type(e).__name__)}


def dolar_oficial(lang: str | None = None) -> dict:
    def fetch():
        # 1) BCRA, la fuente primaria. OJO: en 07/2026 cambió el formato de
        #    {results: {fecha, detalle}} a {results: [{fecha, detalle}]} sin aviso
        #    (nos rompió el parser dos días). Bancamos los dos formatos.
        try:
            res = _get_json(BCRA_USD)["results"]
            dia = res[0] if isinstance(res, list) else res
            det = dia["detalle"][0]
            return {"disponible": True, "indicador": "Dólar oficial (BCRA)",
                    "valor": det.get("tipoCotizacion"), "unidad": "ARS/USD",
                    "fecha": dia.get("fecha"), "fuente": "BCRA"}
        except Exception:
            pass  # cae al fallback; si también falla, _con_cache reporta no disponible
        # 2) Fallback: dolarapi (cotización oficial). La fuente citada es la real.
        d = _get_json(DOLARAPI_OFICIAL)
        return {"disponible": True, "indicador": "Dólar oficial",
                "valor": d.get("venta"), "unidad": "ARS/USD",
                "fecha": str(d.get("fechaActualizacion") or "")[:10],
                "fuente": "dolarapi.com (cotización oficial)"}
    return _con_cache("dolar", fetch, lang)


def inflacion_mensual(lang: str | None = None) -> dict:
    def fetch():
        d = _get_json(INDEC_IPC)
        # La serie viene DESC (sort=desc): el dato más reciente es el primero.
        # Por las dudas no confiamos en la posición: tomamos el de fecha máxima.
        fecha, valor = max(d["data"], key=lambda fila: str(fila[0]))
        # percent_change devuelve FRACCIÓN (0.03 = 3%): convertimos para que
        # valor+unidad sean inequívocos y Ángela no pueda leer "0,03%".
        return {"disponible": True, "indicador": "Inflación mensual (INDEC)",
                "valor": round(valor * 100, 2), "unidad": "%", "fecha": fecha, "fuente": "INDEC"}
    return _con_cache("inflacion", fetch, lang)


def ipc_serie(lang: str | None = None) -> dict:
    """La serie mensual completa del índice IPC (nivel general) para deflactar.
    Cache diario: la historia no cambia, sólo se agrega un mes. Si la fuente
    falla, {'disponible': False} — el que deflacta decide qué decir, no inventa."""
    def fetch():
        d = _get_json(INDEC_IPC_SERIE)
        indices = {str(fecha)[:7]: float(valor) for fecha, valor in d["data"]
                   if valor is not None}
        if not indices:
            raise ValueError("la serie vino vacía")
        ultimo = max(indices)
        return {"disponible": True, "indicador": "IPC nivel general (INDEC, dic-2016=100)",
                "indices": indices, "ultimo_mes": ultimo, "fuente": "INDEC"}
    return _con_cache("ipc_serie", fetch, lang)


_INDICADORES = {"dolar": dolar_oficial, "inflacion": inflacion_mensual}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def consultar(indicadores: list[str] | None = None, lang: str | None = None) -> dict:
    """Trae los indicadores pedidos (default: dólar + inflación).

    El modelo pide con nombres libres ("dólar oficial", "tipo de cambio", "IPC"):
    matcheamos tolerante. Nunca devolvemos {} silencioso — si no reconocemos
    nada de lo pedido, van los defaults (antes un nombre no exacto devolvía
    vacío y Ángela lo leía como fuente caída)."""
    pedidos = []
    for k in (indicadores or []):
        kn = _norm(k)
        if any(t in kn for t in ("dolar", "cambio", "usd", "cotizacion")):
            pedidos.append("dolar")
        elif any(t in kn for t in ("infla", "ipc", "precios")):
            pedidos.append("inflacion")
    if not pedidos:
        pedidos = ["dolar", "inflacion"]
    out = {}
    for k in dict.fromkeys(pedidos):
        fn = _INDICADORES[k]
        try:
            out[k] = fn(lang)
        except TypeError:
            # Compat: dobles de test/plugins registrados sin el param lang.
            # Si el TypeError fuera interno, la segunda llamada lo re-lanza igual.
            out[k] = fn()
    return out
