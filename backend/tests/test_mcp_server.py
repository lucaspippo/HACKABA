"""
MCP server (backend/mcp_server.py): identity comes from the same
'Authorization: Bearer <token>' as the REST API (POST /api/login), and both
the tool catalog a client sees and what each tool returns are gated by the
same per-user `features` Angela's own chat tools already respect.

Each test builds its own throwaway StreamableHTTPSessionManager wrapping the
shared `mcp_server.server` MCP server, instead of going through
`mcp_server.session_manager` (the one mounted at /mcp in main.py) or
`main.app`'s own lifespan — that manager's `.run()` may only be entered once
per process (see mcp_server.py), and main.py's lifespan already gets
exercised elsewhere in the suite (test_analisis_cache.py). Exercising the
shared MCP `Server` object directly (auth, tool filtering, dispatch) is what
actually matters here; the /mcp mount itself is checked separately below
without ever entering a lifespan.
"""
from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.routing import Mount

import auth
import main
import mcp_server

_rest_client = TestClient(main.app)


@pytest.fixture(scope="module")
def tokens():
    creds = auth.cargar_o_generar_credenciales()
    return {u: _rest_client.post("/api/login", json={"username": u, "password": creds[u]}).json()["token"]
            for u in ("emilio", "vendedor", "deposito")}


def _mcp_call(token: str | None, do):
    """Runs `do(session)` against a throwaway MCP session manager wrapping
    the real `mcp_server.server`, authenticated with `token` (or none)."""
    session_manager = StreamableHTTPSessionManager(app=mcp_server.server, json_response=True, stateless=True)

    async def asgi(scope, receive, send):
        await session_manager.handle_request(scope, receive, send)

    async def run():
        transport = httpx.ASGITransport(app=asgi)
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        def factory(**kw):
            kw.pop("transport", None)
            return httpx.AsyncClient(transport=transport, base_url="http://test",
                                      follow_redirects=True, **kw)

        async with session_manager.run():
            async with streamablehttp_client("http://test/mcp", headers=headers,
                                              httpx_client_factory=factory) as (r, w, _):
                async with ClientSession(r, w) as session:
                    await session.initialize()
                    return await do(session)

    return asyncio.run(run())


def test_mounted_at_mcp():
    """main.py actually mounts the real server/session_manager at /mcp — a
    static check, no lifespan involved."""
    mounts = [r for r in main.app.routes if isinstance(r, Mount) and r.path == "/mcp"]
    assert len(mounts) == 1
    assert mounts[0].app is mcp_server.mcp_asgi_app


def _messages(exc: BaseException) -> list[str]:
    """Flattens a possibly-nested BaseExceptionGroup (anyio task groups wrap
    the real error) into the str() of every leaf exception."""
    if isinstance(exc, BaseExceptionGroup):
        return [m for sub in exc.exceptions for m in _messages(sub)]
    return [str(exc)]


def test_no_token_is_rejected():
    with pytest.raises(BaseException) as excinfo:
        _mcp_call(None, lambda s: s.list_tools())
    assert any("No valid session" in m for m in _messages(excinfo.value))


def test_bad_token_is_rejected():
    with pytest.raises(BaseException) as excinfo:
        _mcp_call("not-a-real-token", lambda s: s.list_tools())
    assert any("No valid session" in m for m in _messages(excinfo.value))


def test_tool_list_matches_role_features(tokens):
    # emilio (Dueño): full roster, incl. inventario + caja.
    owner_tools = {t.name for t in _mcp_call(tokens["emilio"], lambda s: s.list_tools()).tools}
    assert {"resumen_negocio", "estado_caja", "cuentas_corrientes"} <= owner_tools

    # vendedor: cobranzas/cuentas, no inventario/caja.
    seller_tools = {t.name for t in _mcp_call(tokens["vendedor"], lambda s: s.list_tools()).tools}
    assert "cuentas_corrientes" in seller_tools
    assert "resumen_negocio" not in seller_tools
    assert "estado_caja" not in seller_tools

    # deposito: deposito/logistica, no inventario/caja/cuentas.
    warehouse_tools = {t.name for t in _mcp_call(tokens["deposito"], lambda s: s.list_tools()).tools}
    assert "consultar_deposito" in warehouse_tools
    assert "resumen_negocio" not in warehouse_tools
    assert "cuentas_corrientes" not in warehouse_tools

    # No tool outside the curated read-only allowlist is ever advertised.
    assert owner_tools <= set(mcp_server.READ_ONLY_TOOLS)


def test_call_tool_returns_real_data(tokens):
    result = _mcp_call(tokens["emilio"], lambda s: s.call_tool("resumen_negocio", {}))
    assert not result.isError
    assert "resumen" in (result.structuredContent or {})


def test_call_tool_is_blocked_server_side_even_if_not_listed(tokens):
    """CAPA 2: a client that calls a tool it was never shown (not just one
    that doesn't exist) still gets refused by angela._run_tool's own gate —
    the block doesn't depend on what list_tools filtered out."""
    result = _mcp_call(tokens["vendedor"], lambda s: s.call_tool("resumen_negocio", {}))
    assert result.content and "sin_acceso" in result.content[0].text


def test_unknown_tool_name_is_rejected(tokens):
    result = _mcp_call(tokens["emilio"], lambda s: s.call_tool("aplicar_correccion_en_lote", {"categoria": "fantasma"}))
    assert result.isError
    assert "not exposed over MCP" in result.content[0].text


def test_read_only_tools_are_all_pure_queries():
    """Guards the design invariant documented in MCP.md: nothing exposed over
    MCP is one of angela's own action tools — except consultar_serie, whose
    only side effect (pinning a widget via 'fijar_en') mcp_server.py strips
    before ever calling _run_tool (see test below)."""
    import angela
    accion_tools = set(mcp_server.READ_ONLY_TOOLS) & angela.TOOLS_ACCION
    assert accion_tools == {"consultar_serie"}


def test_consultar_serie_never_pins_a_widget(tokens):
    """consultar_serie's only non-read side effect is 'fijar_en' (persists a
    widget to the user's own view). mcp_server._sanitize_args must strip it
    before it ever reaches _run_tool, regardless of what a client asks for."""
    args = {"fuente": "ventas", "metrica": "pesos_reales", "fijar_en": "inicio"}
    assert mcp_server._sanitize_args("consultar_serie", args) == {
        "fuente": "ventas", "metrica": "pesos_reales",
    }
    result = _mcp_call(tokens["emilio"], lambda s: s.call_tool("consultar_serie", args))
    structured = result.structuredContent or {}
    assert structured.get("fijado") is not True
