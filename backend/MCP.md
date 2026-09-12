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
