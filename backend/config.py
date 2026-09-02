"""
config.py · El switch central de PolPilot.

Acá vive la decisión de UNA LÍNEA que enchufa el modelo real cuando llega la
API key, y el routing de modelos Haiku/Sonnet/Opus (apagado por defecto, como
se decidió: durante la validación con Horizonte usamos un solo modelo —
calidad > costo).
"""
from __future__ import annotations

import os

# La key vive en backend/.env (gitignored), nunca en el código. config es el
# switch central y todos lo importan primero, así que la carga vive acá.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass  # sin python-dotenv, la key puede venir del entorno igual

# En esta máquina la consulta WMI de Windows se cuelga indefinidamente, y
# platform.win32_ver() (Python 3.12+) la usa. El SDK de Anthropic llama a
# platform.system() al armar sus headers → la PRIMERA llamada real de Ángela
# quedaba colgada para siempre. Deshabilitamos solo la fuente WMI: al tirar
# OSError, _win32_ver cae en su propio fallback oficial (registro +
# sys.getwindowsversion), que da los mismos datos sin colgarse.
if os.name == "nt":
    import platform
    if hasattr(platform, "_wmi_query"):
        def _wmi_deshabilitado(*_a, **_k):
            raise OSError("WMI deshabilitado por PolPilot (se cuelga en esta máquina)")
        platform._wmi_query = _wmi_deshabilitado

# --- PROVIDER ABSTRACTION -----------------------------------------------------
# Which LLM provider answers Ángela's calls, chosen by configuration, never by
# code edits. AI Gateway exposes an ANTHROPIC-COMPATIBLE endpoint, so the same
# `anthropic` SDK talks to either provider — only the transport (base_url +
# auth header) and the model slug change. Adding a third provider (Bedrock,
# Vertex, a self-hosted gateway) means adding one entry to _PROVIDERS below,
# never editing a call site: callers only ever ask this module for a client
# (get_client()) and a model (modelo_para() / modelo_validacion()).
PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_GATEWAY = "gateway"

# AI Gateway's Anthropic-compatible base URL when ANTHROPIC_BASE_URL is unset.
DEFAULT_GATEWAY_BASE_URL = "https://ai-gateway.vercel.sh"


def _anthropic_configured() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _anthropic_client_kwargs() -> dict:
    # Direct Anthropic: `x-api-key` auth via api_key=.
    return {"api_key": os.environ.get("ANTHROPIC_API_KEY")}


def _gateway_configured() -> bool:
    return bool(os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _gateway_client_kwargs() -> dict:
    # AI Gateway authenticates with `Authorization: Bearer`, which is
    # auth_token=, NOT api_key= (api_key= sends `x-api-key` and gets a 401
    # that looks like a bad key, when the real problem is the wrong header).
    return {
        "base_url": os.environ.get("ANTHROPIC_BASE_URL") or DEFAULT_GATEWAY_BASE_URL,
        "auth_token": os.environ.get("ANTHROPIC_AUTH_TOKEN"),
    }


# One entry per provider: whether it's configured, the kwargs to build its
# client, and the model slug to use when ANGELA_MODEL doesn't override it.
# Gateway model slugs need a provider prefix and a DOTTED version — a
# hyphenated slug (the direct-Anthropic style) returns HTTP 400 through the
# gateway — so the two defaults below are deliberately NOT the same string.
_PROVIDERS = {
    PROVIDER_ANTHROPIC: {
        "configured": _anthropic_configured,
        "client_kwargs": _anthropic_client_kwargs,
        "default_model": "claude-sonnet-4-6",
    },
    PROVIDER_GATEWAY: {
        "configured": _gateway_configured,
        "client_kwargs": _gateway_client_kwargs,
        "default_model": "anthropic/claude-sonnet-4.6",
    },
}


def _resolve_provider() -> str | None:
    """Which provider is actually usable right now, or None if neither is
    (→ the deterministic 'simulado' fallback).

    Selection:
    1. LLM_PROVIDER=anthropic|gateway, if set, is authoritative — but only
       when THAT provider's own credential is present; an explicit choice
       with no credential falls through to "not configured" (None), it does
       not silently borrow the other provider's credential.
    2. Otherwise auto-detect: a direct ANTHROPIC_API_KEY means anthropic; no
       direct key but an ANTHROPIC_AUTH_TOKEN means gateway.
       TIE-BREAK (both configured, no explicit LLM_PROVIDER): anthropic wins
       — it is the direct, one-hop path, so it's the safer deterministic
       default when nothing told us otherwise.
    3. Neither configured → None.
    """
    explicit = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if explicit in _PROVIDERS:
        return explicit if _PROVIDERS[explicit]["configured"]() else None

    for name in (PROVIDER_ANTHROPIC, PROVIDER_GATEWAY):
        if _PROVIDERS[name]["configured"]():
            return name
    return None


def provider() -> str | None:
    """The provider that would answer right now, or None (simulado fallback)."""
    return _resolve_provider()


def model_disponible() -> bool:
    """True when some provider is fully configured — the one gate every
    caller (Ángela's chat, health, WhatsApp, ...) should use instead of
    reading ANTHROPIC_API_KEY directly, so they can never disagree."""
    return _resolve_provider() is not None


def get_client():
    """A ready `anthropic.Anthropic` client for the configured provider, or
    None when no provider is configured. Callers never see base_url/auth
    differences — that's the whole point of the seam."""
    selected = _resolve_provider()
    if selected is None:
        return None
    import anthropic
    return anthropic.Anthropic(**_PROVIDERS[selected]["client_kwargs"]())


def _default_model() -> str:
    """The provider-appropriate default model when ANGELA_MODEL is unset.
    Falls back to the anthropic-shaped default if nothing is configured
    (matches historical behaviour: MODELO_VALIDACION always had a value)."""
    return _PROVIDERS[_resolve_provider() or PROVIDER_ANTHROPIC]["default_model"]


def modelo_validacion() -> str:
    """Runtime-evaluated model for validation mode (ROUTING_ACTIVO=False):
    ANGELA_MODEL always wins verbatim when set — we never rewrite an
    explicit user-provided slug, only the default we'd pick ourselves."""
    return os.environ.get("ANGELA_MODEL") or _default_model()


# --- EL SWITCH ---------------------------------------------------------------
# Modo de Ángela: "claude" si CUALQUIER proveedor está totalmente configurado
# (ver _resolve_provider), si no "simulado" (router de intenciones). Enchufar
# el modelo real = setear ANTHROPIC_API_KEY (directo) o LLM_PROVIDER=gateway +
# ANTHROPIC_AUTH_TOKEN (AI Gateway). Nada más.
# OJO: se computa en runtime (ver modo()). MODO queda como snapshot de import-time
# sólo por compatibilidad; el código nuevo debe llamar modo().
MODO = "claude" if model_disponible() else "simulado"


def modo() -> str:
    """El modo REAL, evaluado ahora (no en import-time). Fuente única de verdad:
    si algún proveedor está configurado → 'claude'; si no → 'simulado'. Así health
    y Ángela nunca discrepan aunque la key se cargue después de importar."""
    return "claude" if model_disponible() else "simulado"


# --- ROUTING DE MODELOS ------------------------------------------------------
# DECISIÓN: apagado durante la validación. Un solo modelo para todo (Sonnet).
# El costo de unos meses de Sonnet es insignificante vs. perder el cliente por
# una respuesta mala. Cuando el producto esté validado y sepamos qué requests
# son simples (con datos reales), se prende ROUTING_ACTIVO = True.
ROUTING_ACTIVO = False

# Modelo para TODO mientras ROUTING_ACTIVO sea False. Default = Sonnet (calidad/costo
# conocido), resuelto por proveedor (ver _default_model): direct usa el slug con
# guiones, gateway el slug con prefijo y versión con punto. Se puede overridear con
# ANGELA_MODEL sin tocar código — eso hace TRIVIAL la prueba A/B Sonnet vs Fable 5:
# ANGELA_MODEL=claude-fable-5 (direct) / ANGELA_MODEL=anthropic/claude-fable-5 (gateway).
# OJO: snapshot de import-time por compatibilidad; el código nuevo debe llamar
# modelo_validacion() (evaluado en runtime, igual que modo()).
MODELO_VALIDACION = modelo_validacion()

MODELOS = {
    "simple": "claude-haiku-4-5",    # navegación, UI, lookups, clasificación (~70% requests)
    "analisis": "claude-sonnet-4-6",  # análisis, anomalías, documentos, pedidos custom (~30%)
    "dificil": "claude-opus-4-8",     # casos raros con evidencia de que vale el premium
}

# Modelos DISPONIBLES para Ángela (para la prueba A/B y para el futuro selector).
# 'claude-fable-5' queda disponible pero NO es default: el default sigue siendo Sonnet
# hasta que la prueba A/B con datos reales diga lo contrario.
MODELOS_DISPONIBLES = {
    "claude-sonnet-4-6": "Sonnet 4.6 (default de validación)",
    "claude-haiku-4-5": "Haiku 4.5 (barato, tareas simples)",
    "claude-opus-4-8": "Opus 4.8 (razonamiento pesado)",
    "claude-fable-5": "Fable 5 (candidato — pendiente prueba A/B vs Sonnet)",
}

# Tools de bajo razonamiento → ruteables a Haiku cuando el routing esté activo.
TOOLS_SIMPLES = {
    "navegar_a", "modificar_vista", "crear_pestana", "crear_widget", "plata_en",
    "buscar_productos", "top_inmovilizado", "listar_grupo", "recordar", "recuperar",
    "cancelar_mensaje", "recuperar_contexto_negocio",
}


def modelo_para(tools_pedidas: set[str] | None = None) -> str:
    """Elige el modelo según el tipo de pedido. Con routing apagado, siempre el
    modelo de validación (runtime, provider-aware — ver modelo_validacion())."""
    if not ROUTING_ACTIVO:
        return modelo_validacion()
    tools_pedidas = tools_pedidas or set()
    # Si TODAS las tools involucradas son simples → Haiku. Si hay análisis → Sonnet.
    if tools_pedidas and tools_pedidas.issubset(TOOLS_SIMPLES):
        return MODELOS["simple"]
    return MODELOS["analisis"]


# --- PROMPT CACHING ----------------------------------------------------------
# El system prompt + el contexto estable del negocio (esquema, reglas) se repiten
# en cada request. Marcarlos cacheables = pagar 10% del input en las lecturas.
# Mantener el bloque estable liviano (5-10k tokens). Ver angela.SYSTEM_PROMPT.
PROMPT_CACHE = True
