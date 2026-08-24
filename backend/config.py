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

# --- EL SWITCH ---------------------------------------------------------------
# Modo de Ángela: "claude" si hay API key, si no "simulado" (router de intenciones).
# Enchufar el modelo real = setear ANTHROPIC_API_KEY. Nada más.
# OJO: se computa en runtime (ver modo()). MODO queda como snapshot de import-time
# sólo por compatibilidad; el código nuevo debe llamar modo().
MODO = "claude" if os.environ.get("ANTHROPIC_API_KEY") else "simulado"


def modo() -> str:
    """El modo REAL, evaluado ahora (no en import-time). Fuente única de verdad:
    si la API key está seteada → 'claude'; si no → 'simulado'. Así health y Ángela
    nunca discrepan aunque la key se cargue después de importar."""
    return "claude" if os.environ.get("ANTHROPIC_API_KEY") else "simulado"


# --- ROUTING DE MODELOS ------------------------------------------------------
# DECISIÓN: apagado durante la validación. Un solo modelo para todo (Sonnet).
# El costo de unos meses de Sonnet es insignificante vs. perder el cliente por
# una respuesta mala. Cuando el producto esté validado y sepamos qué requests
# son simples (con datos reales), se prende ROUTING_ACTIVO = True.
ROUTING_ACTIVO = False

# Modelo para TODO mientras ROUTING_ACTIVO sea False. Default = Sonnet (calidad/costo
# conocido). Se puede overridear con ANGELA_MODEL sin tocar código — eso hace TRIVIAL
# la prueba A/B Sonnet vs Fable 5 cuando conectemos la API key: ANGELA_MODEL=claude-fable-5.
MODELO_VALIDACION = os.environ.get("ANGELA_MODEL", "claude-sonnet-4-6")

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
    """Elige el modelo según el tipo de pedido. Con routing apagado, siempre Sonnet."""
    if not ROUTING_ACTIVO:
        return MODELO_VALIDACION
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
