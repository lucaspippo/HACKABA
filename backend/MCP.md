# PolPilot's MCP server

`backend/mcp_server.py` exposes one tenant's PolPilot data to whatever LLM a
user prefers — Claude Desktop, claude.ai, ChatGPT's connectors, or any other
[MCP](https://modelcontextprotocol.io) client — over the network, the same
way the REST API (`main.py`) already serves the PolPilot frontend and
`angela.py` already serves Angela's own chat tool-use loop.

It answers exactly the same questions Angela answers by chat ("how much
money is tied up in stock?", "who owes me money?", "what's expiring in the
warehouse this week?") through the same deterministic calculations in
`core/` — nothing here recomputes a number a different way.

## Why it's safe to point an external LLM at this

- **It's read-only.** Every tool it exposes is a query. Nothing that
  corrects data, closes the cash register, sends a collection message, or
  changes a user's saved view is reachable over MCP — those stay
  human-in-the-loop inside the app, same as always. See "Tool catalog"
  below for the exact list.
- **Identity comes from a real PolPilot login, not from the request body.**
  Every MCP call carries `Authorization: Bearer <token>` — the same token
  `POST /api/login` already returns for the web app. There is no separate
  MCP credential to provision or leak.
- **The same role permissions apply.** The tool list an MCP client sees, and
  what each tool is allowed to return, is filtered by that user's `features`
  — precisely the modules (`auth.MODULOS`) their PolPilot role has enabled.
  A warehouse role doesn't get `estado_caja` (cash register) over MCP any
  more than they get a "Caja" tab in the app.
- **Enforcement doesn't depend on what the client asked for.** Every call
  re-checks the caller's session and re-runs the exact same
  `angela.TOOL_FEATURE` gate Angela's own chat loop uses inside
  `angela._run_tool` — a client that somehow calls a tool it was never shown
  still gets refused server-side, not just hidden from a menu.
- **Nothing is reimplemented.** Every MCP tool is a thin wrapper around
  `angela._run_tool`, the one existing entry point into `core/` (the
  deterministic edge). A number reached through MCP is the exact same number
  Angela would say and the app would show — same cache, same rounding, same
  `_fmt` money formatting.

## Where it lives

PolPilot's multi-tenancy is per-deployment (`POLPILOT_TENANT` +
`POLPILOT_DATA_DIR` — see the repo's root `CLAUDE.md`): each tenant already
runs its own backend process. The MCP server is mounted straight into that
same FastAPI app, at `/mcp` — there's no separate service to deploy or
tenant-routing layer to add. Whichever tenant's backend a user's PolPilot
lives on is also where their MCP endpoint lives.

## Getting a token

There's no separate MCP credential. Log in the same way the app does:

```bash
curl -s -X POST https://<your-polpilot-host>/api/login \
  -H 'Content-Type: application/json' \
  -d '{"username": "<username>", "password": "<password>"}'
# -> {"token": "...", "usuario": {...}}
```

Use that `token` as the bearer credential for every MCP call. It expires
after `POLPILOT_TOKEN_TTL_HORAS` hours (12h by default, same as the app) —
see "Known limitations" below.

## Configuring a client

### Claude Desktop / claude.ai (remote MCP connector)

Point it at `https://<your-polpilot-host>/mcp` with an `Authorization`
header carrying the bearer token above. In Claude Desktop's config
(`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "polpilot": {
      "url": "https://<your-polpilot-host>/mcp",
      "headers": {
        "Authorization": "Bearer <token>"
      }
    }
  }
}
```

claude.ai's custom connector UI (Settings → Connectors → Add custom
connector) takes the same URL and header.

### Any other MCP client

The endpoint speaks standard MCP Streamable HTTP
(`POST`/`GET`/`DELETE /mcp`, JSON-RPC 2.0 bodies) — any client built on an
MCP SDK works out of the box. A raw smoke test with `curl`:

```bash
curl -s -X POST https://<your-polpilot-host>/mcp \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{
        "protocolVersion":"2025-06-18",
        "capabilities":{},
        "clientInfo":{"name":"curl","version":"0"}}}'
```

## Tool catalog

`mcp_server.READ_ONLY_TOOLS` is the full, explicit allowlist — a curated
subset of `angela.TOOLS`. Each tool is gated by the same `feature` Angela's
chat loop uses (`angela.TOOL_FEATURE`); `—` means every logged-in user can
use it regardless of role.

| Tool | Feature required | What it answers |
|---|---|---|
| `resumen_negocio` | `inventario` | Overall snapshot: money tied up in stock, catalog health, alert counts. |
| `plata_en` | `inventario` | Money tied up in a product/category by name. |
| `buscar_productos` | `inventario` | Product lookup (stock, cost, price, status). |
| `top_inmovilizado` | `inventario` | Biggest money-tied-up items, ranked. |
| `listar_grupo` | `inventario` | Items in a data-quality group (ghosts, negative stock, no price, scale/weight, stale cost). |
| `cuentas_corrientes` | `cuentas` | Who owes money, how much, who's overdue. |
| `scoring_credito` | `cuentas` | Credit limit check for a customer. |
| `consultar_deposito` | `deposito` | Warehouse (WMS export): location, expirations, discrepancies. |
| `consultar_cruces` | `mapa` | Cross-domain findings joining 3+ data sources. |
| `consultar_manual` | — | The "how work gets done here" playbook (locations, restocking cadence, processes, house rules, contacts). |
| `consultar_envios` | `logistica` | Deliveries (TMS export): today's route, a customer's order status, delays. |
| `consultar_evolucion` | `evolucion` | Historical revenue, inflation-adjusted, year over year. |
| `consultar_pronostico` | `evolucion` | Deterministic demand forecast, next 3 months. |
| `consultar_contexto_macro` | — | Official macro indicators (FX rate, inflation) with source and date. |
| `estado_caja` | `caja` | Today's cash register state. |
| `capital_recuperable` | — | Recoverable capital and its breakdown. |
| `listar_prioridades` | `alertas` or `oportunidades` | The canonical "what to do now" list. |
| `analisis_rotacion` | `inventario` | Stock turnover: healthy / slow / dormant money. |
| `analisis_estacionalidad` | `evolucion` | Seasonality by category, whole sales history. |
| `analisis_push_pull` | `oportunidades` | What's worth promoting vs. what sells on its own. |
| `consultar_compras` | `cargar` | What came in by photo capture: invoices, receipts, collections, plus a supplier's running balance. |
| `objetivos_negocio` | `oportunidades` | Goals the system proposes from the data. |
| `mis_recordatorios` | — | The caller's own reminders/tasks. |
| `leer_preferencias` | — | The caller's own saved view preferences. |
| `recuperar` | — | The caller's own remembered notes/preferences. |
| `recuperar_contexto_negocio` | — | Snapshot + loaded-data status + preferences, for orienting a conversation. |
| `normalizaciones_staging` | `cargar` | What automatic import cleanup did (read-only here — the server always forces `accion: "consultar"`; reverting a batch stays app-only). |
| `consultar_serie` | varies by `fuente` | Ad-hoc chart/table queries (sales, inventory, accounts, cash) — the server strips `fijar_en`/`tipo`/`posicion`/`titulo`, since pinning a widget is app UI, not a query. |

Everything else in `angela.TOOLS` — navigation, corrections, widgets,
reminders, documents, closing the register, sending a collection message,
team/module management — is intentionally **not** exposed here. That stays
behind the app's own confirm-before-you-act flow.

Every tool is also advertised with `annotations.readOnlyHint = True` (MCP's
own [tool annotations](https://modelcontextprotocol.io/specification/2025-06-18/server/tools#tool-annotations)),
so a compliant client can tell — without reading this doc — that nothing
here needs a confirmation dialog. `tests/test_mcp_server.py::test_every_tool_is_marked_read_only`
enforces this on every tool in the catalog, so a future write tool added to
the wrong list fails loudly instead of silently losing its warning.

## How this was tested

There's no separate MCP staging environment — it was validated against the
real code path, end-to-end, minus the network socket:

1. A real local Postgres, migrated with `alembic upgrade head` (the same
   migrations production runs).
2. A **throwaway tenant** (`test-mcp-<uuid>`, never `demo`/`piloto`), seeded
   with real users at different `features` via `auth.crear_usuario` and
   logged in for real (`auth.login`) to get real bearer tokens — the same
   path a browser takes.
3. The actual `main.app` (FastAPI instance, lifespan and all) driven by the
   real `mcp` Python SDK client (`mcp.client.streamable_http` +
   `ClientSession`) — full `initialize` handshake, real `list_tools`/
   `call_tool` JSON-RPC — over `httpx.ASGITransport(app=main.app)` instead of
   a TCP socket. Everything above the socket (routing, auth, `angela._run_tool`,
   the Postgres reads underneath it) is the real thing; only the transport
   is swapped for something that doesn't need a bound port.
4. That scenario is now `tests/test_mcp_server.py`, run the same way as the
   rest of the suite (`cd backend && python -m pytest tests/test_mcp_server.py`).
   Each test builds its own throwaway `StreamableHTTPSessionManager` wrapping
   the shared `mcp_server.server` object rather than the one mounted at `/mcp`
   — that manager's `.run()` is one-shot per process (see the SDK's own
   `StreamableHTTPSessionManager` docstring), and `main.app`'s lifespan is
   already exercised once elsewhere in the suite (`test_analisis_cache.py`).

**What this does *not* cover:** an actual Claude Desktop or claude.ai client
talking to a real deployed instance over the network. Real clients can be
pickier than the SDK's own test client about trailing-slash redirects,
header casing, or `Accept` negotiation — worth a manual check against a real
deployment before depending on a specific client integration.

## Known limitations

- **Token TTL.** MCP tokens are regular PolPilot session tokens
  (`POLPILOT_TOKEN_TTL_HORAS`, 12h default). A client left connected across
  that window needs a fresh `POST /api/login` and an updated header — there
  is no separate long-lived personal access token yet. If daily
  re-authentication turns out to be too rough for how people actually use
  this, a longer-lived, revocable API-token type (scoped the same way as a
  user's `features`, distinct from the browser session) is the natural next
  step — it wasn't built here to avoid growing the auth surface for a v1
  that's read-only anyway.
- **No cross-tenant routing.** One MCP endpoint serves exactly the tenant its
  backend process is running as — matching the rest of the app. There's no
  "pick your company" step in the protocol; the host you point a client at
  already decides that.
- **`stateless_http=True`, `json_response=True`.** Each call opens and
  closes its own internal MCP session rather than negotiating one long-lived
  `Mcp-Session-Id`, and responses come back as plain JSON instead of
  Server-Sent Events. This keeps the implementation simple and matches the
  actual usage pattern (independent, self-contained queries) — there's
  nothing here that needs a server-push stream. If a future tool benefits
  from progress notifications or resumable streams, that's a deliberate
  trade-off to revisit, not an oversight.

## Roadmap: adding write / destructive operations

Nothing here is built yet — this is the design to pick up when a real need
shows up for the LLM side of MCP to *do* something (apply a correction, send
a collection message, close the register), not just answer questions. Opening
this up isn't a config flip: the read-only boundary is the entire safety
argument in "Why it's safe" above, so widening it means replacing each of
those bullets with a real mechanism, not deleting them.

1. **Reuse the app's existing propose-then-apply pattern — don't invent a
   new one.** Every mutation already splits into two calls: a preview with
   no side effect (`proponer_correccion`, `proponer_plan`) and an apply step
   that only runs after an explicit human "yes" (`aplicar_correccion_en_lote`,
   `ejecutar_plan`). That maps directly onto MCP: expose the propose tools
   freely (they're reads), and put a real confirmation gate only in front of
   the apply tools. Never expose a single-shot tool that mutates data with no
   preview step — an LLM client will call it eagerly, without the friction a
   person clicking a confirm button in the app provides today.

2. **Use MCP's own signaling for the confirmation, not just the propose/apply
   split.** Mark every mutating tool with `annotations.destructiveHint = True`
   (and `readOnlyHint = False`) so a compliant client visibly warns before
   calling it — the same annotations object this server already sets to
   `readOnlyHint = True` today (see `_to_mcp_tool` in `mcp_server.py`). For a
   real "are you sure, and here's exactly what will change" round-trip, look
   at the SDK's **elicitation** support (`ctx.elicit(...)`) instead of
   trusting the client's own UI to ask.

3. **Tighten auth before widening scope.** MCP currently reuses the same
   12h browser session token — acceptable for read-only, where the worst
   case is an information leak already bounded by that user's `features`.
   Destructive actions need a separate, narrower, revocable credential: a
   proper API-token type (its own table, not `sessions`), ideally scoped
   *below* a user's full feature set independently (e.g. "this MCP token can
   read everything and apply saneamiento corrections, but never touch
   `caja` or send a collection message") rather than inheriting the app
   role wholesale. This is real schema/auth work, not a flag — see "Known
   limitations" above, which already flags the token-TTL gap this would
   also need to resolve.

4. **Attribute and audit every mutation distinctly from the app.**
   `core/store.audit.record(actor=...)` already logs every correction with
   who did it. Route MCP-triggered writes through the exact same call with a
   distinguishable actor (e.g. `f"{username} (mcp)"`), so the owner's audit
   trail and activity feed can tell "done in the app" apart from "an LLM did
   this via MCP" — this matters more here than anywhere else in the product,
   since the human that approved it isn't looking at a PolPilot screen at
   the moment it happens.

5. **Structurally, this is additive, not a rewrite.** Add a second explicit
   list next to `READ_ONLY_TOOLS` — e.g. `WRITE_TOOLS` — kept genuinely
   separate (not a flag on entries in the existing list) so the read-only
   guarantee for the current catalog stays true by construction and
   trivially auditable by reading one constant. Each entry still just wraps
   `angela._run_tool`; reuse `_sanitize_args`'s pattern for stripping any
   argument you don't want an external caller to control (e.g. forcing a
   `motivo`/reason field, or capping a monetary threshold a tool accepts).
   Gate `WRITE_TOOLS` behind the point-3 token scope from day one — don't
   ship it gated only by the existing session token and "for now, don't
   configure a client with it."

6. **Rate/anomaly limits are worth adding specifically for this.** An LLM
   client can loop in a way a person clicking through the UI won't — put a
   cap on destructive calls per token per time window before shipping
   `WRITE_TOOLS`, independent of whatever rate limiting (if any) the REST
   API has.

## Adding a new read-only tool

1. The tool must already exist in `angela.TOOLS` / `angela._run_tool` — this
   module never defines its own business logic, only decides what's exposed.
2. Confirm it's a pure query (check `angela.TOOLS_ACCION` and read the
   `_run_tool` branch — no writes to `core/`, `memoria`, or anything else).
3. Add its name to `mcp_server.READ_ONLY_TOOLS`.
4. If any of its arguments have a side effect you want off for MCP (like
   `consultar_serie`'s `fijar_en`), add them to `_STRIP_ARGS` — don't fork a
   second copy of the tool.
5. Add a row to the table above.
