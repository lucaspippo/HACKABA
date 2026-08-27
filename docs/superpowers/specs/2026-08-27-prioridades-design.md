# Prioridades — unified “what should I do now” inbox

Date: 2026-08-27
Status: draft for review

## Goal

Replace the desktop **Alertas** and **Oportunidades** pages (and the “Alertas y oportunidades” submenu) with a single **Prioridades** inbox: a ranked list of decisions, not a filterable catalog of findings.

Success: the owner opens one leaf, sees what to do now in order, and acts. The same fact never appears twice. Ángela cites this list; she does not invent a second ranking.

## Locked decisions

- Job: curated “what should I do now”, not “browse everything sliced how I want”.
- Name: **Prioridades** (Spanish UI). Code/module: `priorities` (English).
- Full ranked list. Watch is a heading at the bottom. No “ver todas”. No kind chips (All / Problems / Money).
- Duplicate facts merge into **one card**. The title is the action; the leak lives in tone and drill.
- Desktop: **work row** (chip + title + one-line why + pesos) in a **master-detail** (list | drill). Overlay fallback when the main column is too narrow.
- Mobile already fused these as Insights; it consumes the same API. Compact rows + overlay stay on the phone.

## What stays out

- **Evolución**: report, not an inbox. Leaves the submenu; becomes a sidebar leaf next to Mapa. Its company-level YoY drop may appear as one Watch item that navigates to Evolución.
- **Datos a corregir (Saneamiento)**: dirty-record work queue. Inventory `alertas` (fantasmas, negativos, sin_pvp, balanza, costo_viejo-as-data-error) stay there. `lib/alertas.js` is unchanged.
- **Campanita**: system notifications. `solicitud_pendiente` is dropped from this inbox (it already lives there).
- No new row in “Quién ve qué”. The nav item shows if the person has `alertas` **or** `oportunidades`. Card visibility still follows existing domain gates (`visibles_para` / module-gated alert fetches).

## Information architecture

### Sidebar

The `senales` accordion (`alertas`, `oportunidades`, `evolucion`) goes away.

Leaves, same level as Panel and Mapa:

1. Panel
2. Mapa
3. **Evolución** (existing feature `evolucion`)
4. **Prioridades** (Radar icon)

Campanita stays in the header.

### Routes

- Canonical: `/prioridades`
- Redirects: `/alertas`, `/oportunidades`, `/insights` → `/prioridades`
- Ángela `navegar_a`, command palette, Home CTAs, purchasing “preparar OC” all go to `prioridades`

### Badge

One number: count of **act** items after merge. Watch does not count (not dispatchable work). Same source as the page (`GET /api/prioridades`).

### Home

The two exits (“ver alertas” / “ver oportunidades”) become one: Prioridades. Home’s “today” opportunity cards, if kept, read the top of the same `act` list so Home and Prioridades cannot disagree.

## Ranking and merge

Computed in `core/`, once. Frontends do not re-sort.

### Bands on the page

1. **Main list (`act`)** — every decision. No Hoy / Semana / Cuenta headers. Chip and tone carry urgency.
2. **Watch** — only heading, at the bottom. Does not compete with `act` for rank.

Floor reports (`piso`) sit in `act` with chip **Tu equipo**. They are not pinned above the ranking.

### `act` sort

1. Leak-today first: stockout, mora, lots that will be thrown, vendor payment already due, warehouse expired.
2. Then pesos descending.
3. A card with no `$` (only a count / “4 días”) sits at the bottom of its band, not above a real amount.

Watch is sorted by pesos inside its own block.

### Merge map (true duplicates only)

| Sources today | One item `id` | Title is the action |
|---|---|---|
| `morosos` + `moroso_atraso` + `cobrar_morosos` | `cobrar_morosos` | Cobrá estos $X. Worst client and payment curve in the drill. |
| `quiebre` + `quiebre_inminente` | `quiebre_inminente` | This SKU / these SKUs will break. Current holes and “in 14 days” in the same drill. |
| `pico` + `pre_pico` | `pre_pico` | Planificá la compra del pico. The informational peak is porqué, not a second row. |

Canonical `id` is the opportunity id when one exists, so adopt / orden de compra / Ángela prompts keep working.

**Do not merge** (related, different action): `costo_viejo` vs `margen_bajo`; `venc_riesgo` / `dep_vencidos` vs `sobrecompra`; company YoY vs `estrella_caida`.

**Drop from this page:** `solicitud_pendiente`.

### Tone

Red if any source was a leak. Salvia only for pure upside (ventana de compra, cliente frío, dormido). Oro for Watch / riesgo. Chip names the move (Cobrar, Reponer, Comprar, Liquidar, Tu equipo, Riesgo).

Drill keeps both: why it hurts, then the move, then existing actions (adopt, approve PO, Ángela, navigate to the module).

## Data

### Composer

New `backend/core/priorities.py`:

1. Opportunity cards from the existing closed set (`oportunidades_neg.cards`).
2. Alert signals — ported out of `frontend/src/lib/centroAlertas.js` into core (today that logic lives in the browser and fans out to 11 APIs).
3. Floor reports from `piso`.

Then merge, split `act` / `watch`, rank, and filter with `visibles_para` **after** cache (canonical set computed once; role cut applied per request).

`oportunidades_neg.py` still owns the ten calculations and `recuperable()`. Priorities is a composer on top. Map/grafo can keep calling `oportunidades_neg` until they switch; the **inbox** does not call `/api/oportunidades`.

### Endpoint

`GET /api/prioridades`

- Gate: user has `alertas` or `oportunidades`.
- Bilingual copy on the server (same i18n pattern as opportunity cards).
- Same analysis cache invalidation as `/api/oportunidades`.
- Response shape (stable):

```
{
  "act": [ item, ... ],      # already ranked
  "watch": [ item, ... ],
  "badge": n                 # len(act)
}
```

Item (minimum):

```
{
  "id": "cobrar_morosos",
  "band": "act" | "watch",
  "tone": "rojo" | "oro" | "azul" | "salvia",
  "chip": "Cobrar",
  "titulo": "...",
  "resumen": "...",          # one-line why
  "monto": 85700000,         # or null
  "monto_label": null,
  "cifra_texto": null,       # e.g. "4 días" when there is no homogeneous $
  "fuentes": ["…"],
  "origen": ["alerta:morosos", "oportunidad:cobrar_morosos"],
  "navegar": "cuentas",
  "accion_chat": "...",
  "propuesta": { ... } | null,
  "piso": false,
  "drill": { "porque": [], "grafico": null, "involucrados": [], "supuestos": [] }
}
```

### Consumers

Desktop Prioridades, mobile Insights, sidebar badge, Home’s today cards, Ángela’s tool: **this endpoint / this function only**. Delete client-side `cargarSenales` + `construirAlertas` + InsightsMobile merge/sort as they become unused.

`/api/oportunidades` may remain for map/grafo compatibility; it is not the inbox.

## Desktop UI

Work row, not a 3-column card grid (a grid equalizes rank).

**Master-detail.** Left: ranked list (~38% of the main column, min ~280px). Right: the open item’s current `DrillNegocio` body (porqué, chart, involucrados, propuesta, actions). No modal on a comfortable width.

- First `act` item (or first Watch if `act` is empty) is selected on load so the right pane is never a blank “elegí una”.
- Selecting a row updates the right pane; it does not navigate away.
- When the main column is too narrow (Ángela’s ~23.75rem panel open, or content width under ~1200px): keep the list full width and open **DrillNegocio overlay** (today’s modal). Do not squeeze three columns (list | drill | Ángela).

The list itself is a **capped work-row**: chip, title, one-line why, pesos on the right of **that column** — so the number stays next to the words even in the master-detail.

Header: **Prioridades** + short subtitle (“Lo que hay que hacer, en orden”). Badge is in the sidebar, not repeated as a filter bar.

## Mobile

Insights remains one tab. Same API. Compact rows (already built) + overlay drill. Routes `alertas` / `oportunidades` / `insights` already resolve to this view; keep that, point data at `/api/prioridades`. Optional later copy change from “Insights” to “Prioridades” so desktop and mobile share the name — do it in the same change if cheap, do not block on it.

## Ángela

A tool that calls `priorities.inbox` (same ranking). `navegar_a` target: `prioridades`. She must not re-order items in the prompt. `capital_recuperable` stays on `oportunidades_neg`.

## Empty and error

- Loading: skeleton of work rows + empty drill pane, never the empty state.
- `act` and `watch` both empty because sales/data are missing: one CTA to load sales (current Dormida intent). **No** dashed “when you load data you’ll see…” placeholder gallery.
- Both empty and data are present: honest “nada que hacer ahora”.
- Fetch failure: honest error, retry. Never a silent empty list.

## Testing

- Merge: with demo (or piloto) data, `morosos` / `quiebre` / `pico` do not appear as sibling ids next to their opportunity twins. One id each.
- Rank: a leak-today with no `$` still sorts above a large dormant-stock card; Watch ids never appear in `act`.
- Role: warehouse features do not see `cobrar_morosos`; owner sees the full `act` set the tests already pin for opportunities, minus dropped/merged alerts.
- Badge === `len(act)` for the same payload.
- Redirects: `/alertas` and `/oportunidades` land on Prioridades.
- Cache: mutating stock/sales invalidates the inbox the same way it invalidates opportunity cards.

Tests write into the data dir — restore seeds after (`git checkout -- data-demo/`).

## Out of scope

- Filter-by-module / priority / impact as primary UI.
- Merging Saneamiento or Campanita into this page.
- Rewriting `oportunidades_neg` calculations.
- Pixel-perfect restyle of DrillNegocio internals; reuse it in the right pane.
- New “Quién ve qué” module named Prioridades.

## Files likely touched (implementation, not this spec)

- `backend/core/priorities.py` (new), `backend/main.py` (`GET /api/prioridades`), Ángela tools
- `frontend/src/sections/Prioridades.jsx` (new; replaces desktop use of AlertasNegocio + OportunidadesNegocio)
- `frontend/src/desktop/DesktopApp.jsx` (nav, routes, badge)
- `frontend/src/mobile/InsightsMobile.jsx` + `MobileApp.jsx`
- `frontend/src/desktop/sections/Inicio.jsx`
- `frontend/src/lib/locales/{es,en}.js`
- Remove or stop using `centroAlertas.js` / `alertasNegocio.jsx` once no consumer remains
- Tests under `backend/tests/`
