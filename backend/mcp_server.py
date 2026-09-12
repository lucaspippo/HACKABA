"""
mcp_server.py · PolPilot's MCP server
======================================
A READ-ONLY bridge between one tenant's business data and whichever LLM its
users prefer (Claude Desktop, claude.ai, any MCP client): the same queries
Angela already answers over chat, exposed as MCP tools.

Why this doesn't reimplement anything: every tool delegates to
`angela._run_tool`, the single existing entry point into `core/` (the
deterministic edge) — it already carries Angela's three anti-leak layers
(tool list filtered by feature, a hard gate on execution, and scoped
context). This module adds one more layer of its own: the tools it exposes
are a read-only subset of `angela.TOOLS` — nothing that corrects data, closes
the register, sends a message or pins a widget lives here. Those stay
human-in-the-loop inside the app, same as always.

Identity: comes from the `Authorization: Bearer <token>` header on EACH MCP
call — the same token `POST /api/login` returns, never a role declared in
the request. Without a valid token there are no tools and no results: the
tool list a client sees, and what each tool returns, respects exactly the
same modules (`features`) enabled for that user — a salesperson doesn't see
`estado_caja` over MCP any more than they see it in the app.

Transport: Streamable HTTP (the current spec's remote transport), stateless
— every request opens and closes its own internal session, since there's
nothing to negotiate: identity travels on every header already. See MCP.md
for how to point a client at `/mcp`.
"""
from __future__ import annotations

import asyncio

from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

import angela
import auth

# ---------------------------------------------------------------------------
# Catalog: the subset of angela.TOOLS that is pure reads (never writes, never
# corrects data, never sends a message or closes the register). Names are
# validated against angela.TOOLS at import time, so a rename over there
# breaks loudly here instead of silently dropping a tool.
# ---------------------------------------------------------------------------
READ_ONLY_TOOLS = [
    "resumen_negocio", "plata_en", "buscar_productos", "top_inmovilizado",
    "listar_grupo", "cuentas_corrientes", "scoring_credito", "consultar_deposito",
    "consultar_cruces", "consultar_manual", "consultar_envios", "consultar_evolucion",
    "consultar_pronostico", "consultar_contexto_macro", "estado_caja",
    "capital_recuperable", "listar_prioridades", "analisis_rotacion",
    "analisis_estacionalidad", "analisis_push_pull", "consultar_compras",
    "objetivos_negocio", "mis_recordatorios", "leer_preferencias", "recuperar",
    "recuperar_contexto_negocio", "normalizaciones_staging", "consultar_serie",
]

_TOOLS_BY_NAME = {t["name"]: t for t in angela.TOOLS}
_missing = [n for n in READ_ONLY_TOOLS if n not in _TOOLS_BY_NAME]
if _missing:
    raise RuntimeError(f"mcp_server: tools missing from angela.TOOLS: {_missing}")

# Arguments with a side effect that never reach _run_tool from here — this
# turns off the one non-read edge of a tool without forking a whole separate
# read-only copy of it. consultar_serie's 'fijar_en' persists a widget on the
# user's own view: that's app UI, not a query.
_STRIP_ARGS = {"consultar_serie": {"fijar_en", "tipo", "posicion", "titulo"}}


def _sanitize_args(name: str, args: dict) -> dict:
    args = dict(args or {})
    for key in _STRIP_ARGS.get(name, ()):
        args.pop(key, None)
    if name == "normalizaciones_staging":
        # 'revertir' undoes an entire batch: that's an action, not a query.
        args["accion"] = "consultar"
    return args


_READ_ONLY_ANNOTATIONS = types.ToolAnnotations(readOnlyHint=True)


def _to_mcp_tool(name: str) -> types.Tool:
    spec = _TOOLS_BY_NAME[name]
    return types.Tool(name=spec["name"], description=spec["description"],
                       inputSchema=spec["input_schema"], annotations=_READ_ONLY_ANNOTATIONS)


def _bearer_token(request) -> str | None:
    if request is None:
        return None
    header = request.headers.get("authorization") or ""
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return None


def _user_from_request() -> dict:
    """The logged-in user for THIS MCP call, or a clear error. Never trusts
    anything but the current request's own header (same rule as
    authz.usuario_actual in the REST API)."""
    try:
        request = server.request_context.request
    except LookupError:
        request = None
    token = _bearer_token(request)
    user = auth.usuario_por_token(token) if token else None
    if not user:
        raise PermissionError(
            "No valid session. Send the 'Authorization: Bearer <token>' header "
            "with a live token from POST /api/login — see MCP.md."
        )
    return user


server: Server = Server(
    "polpilot",
    version="1.0",
    instructions=(
        "This business's PolPilot data, READ-ONLY. Every call needs "
        "'Authorization: Bearer <token>' carrying a real user's session "
        "(POST /api/login) — the tools you see and what they return match "
        "exactly the modules enabled for that user in the app; a role without "
        "a module doesn't get its tools here either. Money amounts arrive with "
        "an already-formatted '<key>_fmt' twin ($1,234,567 or its Spanish form, "
        "depending on the user's language): quote it verbatim — don't round or "
        "recompute it. The raw number is only there to compare/sort."
    ),
)


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    user = _user_from_request()
    features = user.get("features")
    allowed = set(features) if features is not None else None

    def visible(name: str) -> bool:
        feature = angela.TOOL_FEATURE.get(name)
        return feature is None or allowed is None or feature in allowed

    return [_to_mcp_tool(n) for n in READ_ONLY_TOOLS if visible(n)]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    user = _user_from_request()
    if name not in READ_ONLY_TOOLS:
        raise ValueError(f"unknown tool, or not exposed over MCP: {name!r}")

    # Angela's request-scoped session (contextvars): this is what activates
    # her three anti-leak layers inside _run_tool — TOOL_FEATURE included,
    # the real gate that doesn't depend on what list_tools already filtered.
    angela._set_sesion(usuario=user["username"], rol=user.get("rol"),
                        features=user.get("features"), idioma=user.get("idioma"))

    args = _sanitize_args(name, arguments)
    # Off the event loop: _run_tool is synchronous, CPU-bound `core/` work and
    # uvicorn runs a single worker here, so calling it inline stalls every
    # concurrent request — main.py's own handlers avoid this by being plain
    # `def`, which FastAPI hands to the anyio threadpool. asyncio.to_thread
    # copies the current context, so the contextvars session _set_sesion just
    # installed still applies inside the thread.
    result, _accion = await asyncio.to_thread(angela._run_tool, name, args)
    result = angela._con_pesos(result)
    if isinstance(result, list):
        result = {"items": result}
    return result


# ---------------------------------------------------------------------------
# HTTP transport — stateless (no negotiated MCP session: identity travels on
# every request's Authorization header) and plain JSON responses (no need to
# require Server-Sent Events support from the client for the typical case:
# ask for one piece of data and get it back). Mounted at /mcp in main.py.
# ---------------------------------------------------------------------------
session_manager = StreamableHTTPSessionManager(app=server, json_response=True, stateless=True)


async def mcp_asgi_app(scope, receive, send) -> None:
    await session_manager.handle_request(scope, receive, send)
