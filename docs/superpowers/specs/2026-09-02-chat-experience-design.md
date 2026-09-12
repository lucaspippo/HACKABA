# Ángela chat experience — design

- **Date:** 2026-09-02
- **Status:** approved (design); implementation planned per phase
- **Scope:** the Ángela chat surface (frontend `components/assistant/`, `lib/chat*`,
  `views/Chat*`) and the `/api/angela/stream` contract that feeds it.

## Context

The chat already runs on `@assistant-ui/react` 0.15.16 with a sound foundation:
`useLocalRuntime` + `useRemoteThreadListRuntime`, `ThreadPrimitive`/
`MessagePrimitive`/`ComposerPrimitive`, an NDJSON adapter over
`/api/angela/stream`, and one shared thread across the desktop dock, the
fullscreen page and mobile. 53 backend tools are exposed to the model.

What is missing is everything *around* that foundation: tool presentation is a
hand-rolled `if` chain, errors are invisible or fake, the app tells Ángela
nothing about what the user is looking at, and the only chart is a bar chart
capped at 8 points. This document decides the architecture once, so the five
implementation phases below do not each re-litigate it.

The reference for "what good looks like" is the sibling repo `polfin`, which
runs the *same* assistant-ui version with a considerably richer chat layer.
Patterns are borrowed from it; its stack is not (see D2).

### Pre-production

This app has **not shipped to production**. Breaking changes to code and to
wire contracts are permitted and preferred over compatibility shims. Several
decisions below depend on that and should be revisited if it stops being true.

## Non-goals

- Rewriting the deterministic core. `core/` computes; this work presents.
- Changing where the agent loop runs. It stays in Python (`angela.py`); see D2.
- Migrating the whole frontend to TypeScript. Only the chat layer (D3).
- Normalizing `action.type` string values across `angela.py` (tracked as a
  follow-up, deliberately not bundled — see Follow-ups).

## Decisions and rationale

These are the durable decisions. Future changes should either follow them or
explicitly supersede them here.

### D1 — Tool presentation is a registry of presenters, layered over a shape-based fallback

A `ToolPresenter` is a plain object per tool: `{ labels, render?, chrome? }`,
collected in a flat `Record<string, ToolPresenter>` and fed to
`MessagePrimitive.Parts` as `components={{ tools: { by_name, Fallback } }}`.

**A presenter is always an override, never a requirement.** The existing
shape-based dispatcher (today's `ToolCallCard.Result`: `items`-like → table,
series → chart, otherwise a key/value grid) survives as `Fallback`. This is
the single most valuable property of the current code: a new Python tool gets
a reasonable UI with zero frontend work. The registry must not cost it.

*Why:* adding a custom look for one tool currently means editing three files
and extending an `if` chain. The registry makes it one file, and
`ChatThread` never grows another branch.

### D2 — Do not adopt assistant-ui "toolkits" (`defineToolkit`)

Toolkits co-locate a tool's schema + `execute` + `render` and require the
`"use generative"` compiler (`aui()` from `@assistant-ui/vite`). They assume
**the tool loop runs in JS**.

Here it does not: Anthropic's API dispatches, `angela.py` executes in Python,
and results stream out as one-directional NDJSON. There is no path for a
browser-side `execute` to return a value *into* that loop. Adopting toolkits
literally would mean duplicating 53 tool schemas in TS, or taking a compiler
dependency that buys nothing.

What is worth borrowing is the toolkit *shape* — one module per tool declaring
name, labels, types and renderer — which D1 provides.

**This is not a deprecated path.** `makeAssistantTool` /
`makeAssistantToolUI` / `useAssistantToolUI` are the deprecated APIs. The
inline `MessagePrimitive.Parts` tool override used here is what the docs name
as their replacement for per-message UI. Toolkits are the blessed path for
*defining and executing* tools; `Parts` overrides are the blessed path for
*rendering* them. Rendering is the only half this repo owns in JS.

**Keeping the door open.** Five decisions make a future migration mechanical,
should the agent loop ever move to JS:

1. Presenters are keyed by the **exact Python tool name** → toolkit object keys 1:1.
2. `render` takes **`ToolCallMessagePartProps`**, not a bespoke prop shape.
3. Presenters stay **pure**; side effects live in `ChatPanel`'s action applier.
4. Arg/result types live per tool in `tools/types.ts`, so codegen can replace
   them file-for-file.
5. The registry is a flat `Record<string, ToolPresenter>` — structurally a
   toolkit minus `execute`.

The genuinely compelling future reason to want toolkits is human-in-the-loop:
`proponer_plan`/`ejecutar_plan`, `proponer_correccion`/
`aplicar_correccion_en_lote` and `proponer_conocimiento` are all currently
**two model turns** (propose, user confirms, apply). Toolkit HITL would
collapse each into one paused tool call with inline approve/deny. That is
gated on making the stream bidirectional, not on the toolkit API.

### D3 — TypeScript for the chat layer only

`tsconfig.json` with `allowJs: true`, `checkJs: false`, `strict: true`,
`jsx: "react-jsx"`. Only `frontend/src/components/assistant/**` and
`frontend/src/lib/chat*` become `.ts`/`.tsx`. The other ~60 JSX files are
untouched and import normally.

Vite compiles TSX via esbuild with **no typechecking**, so `npm run typecheck`
(`tsc --noEmit`) is a real script and must run in CI / before merge, or the
types silently rot.

*Why:* the value is a typed tool contract — `args` and `result` per tool —
which is where bugs actually live in this layer.

### D4 — Generate TS tool-arg types from `angela.py:TOOLS`

Python stays the single source of truth for tool schemas (it must: the loop
and the feature gating via `tools_para(features)` are Python). A script emits
TS types from the 53 `input_schema` entries, so renderers get typed `args` and
a Python schema change surfaces at `typecheck` instead of at runtime.

*Why:* this is the actual daily value of the toolkit schema (D2), obtained
without the misfit dependency.

### D5 — Stream protocol v2: errors and notices are first-class

Events, English keys:

| Event | Notes |
|---|---|
| `{type:"text", delta}` | **deltas**, not accumulated text — adapter appends |
| `{type:"tool_call", id, name, input}` | unchanged |
| `{type:"tool_result", id, result, display?}` | `input` echo dropped; `display` per D8 |
| `{type:"error", code, message, retryable}` | **new** |
| `{type:"notice", kind, text}` | **new** — `cap`, `tool_loop_exhausted`, `fake_model` |
| `{type:"done", result:{mode, tools_used, actions}}` | `respuesta` dropped (redundant with text parts) |

Request envelope English too: `mensaje`→`message`, `historial`→`history`,
plus `view` and `app_context` (D6). `metadata.custom` keys likewise:
`acciones`→`actions`, `opciones`→`options`, `modo`→`mode`.

*Why — four defects this fixes, all verified:*

1. **Errors could not be expressed.** `stream_response` catches everything and
   degrades into `_fallback()`, yielding text + done as if nothing happened.
   The 200 is already committed, so a mid-stream failure had no channel.
2. **Hitting the message cap showed an empty bubble.** `cap_event` emitted
   only a `done` with `respuesta` and no `text` event; the adapter built parts
   from `text` events alone, so `parts` stayed empty while `status` went
   `complete`. The explanation never rendered. Both cap paths (per-IP,
   per-session) hit this.
3. **Abandoned partial text got glued to the fallback answer.** After a tool
   call the adapter resets its current text index, so a post-failure text
   event became a *second* text part — the user read a half-sentence and a
   fallback answer as one bubble.
4. **O(n²) bytes.** Every text delta re-sent the entire accumulated string.

`error_tecnico` (the raw exception string) stops going over the wire; it is
logged server-side and included only behind a dev flag.

### D6 — The app tells Ángela what the user is looking at, via `ModelContext`

Verified against the installed types: `ChatModelRunOptions.context: ModelContext`
*is* passed to a custom `ChatModelAdapter` under `useLocalRuntime`, and
`AssistantContextConfig.getContext` returns a **string** merged into
`ModelContext.system`. So the copilots API works against a Python backend.

- `lib/chat/runContext.ts` — a `useSyncExternalStore` store (same shape as the
  existing `focoStore`) holding `{ view, focus, entityId, entityName }`, fed by
  a `<ChatRunContextSync/>` mounted once in `DesktopApp` from
  `useParams().section` and `useFoco()`. This replaces
  `getCurrentView: () => null`, which was dead wiring.
- Sections contribute via `useAssistantContext({ getContext })` — lazy, called
  at send time.
- The adapter forwards `context.system` as `app_context`; the backend appends
  it to the system prompt under an explicit heading.

Three constraints:

1. **Bounded** — `app_context` truncated server-side (~2 KB). 25 sections each
   contributing freely is a token leak.
2. **Data, not instructions** — it is first-party but lands in the system
   prompt. Sections emit facts; never directives, secrets or tokens.
3. **Context is not truth** — Ángela still calls `core/` tools for every
   number. Context says *what to ask about*, never *what the answer is*.
   This is the repo's core invariant and the one way this feature could
   quietly violate it.

### D7 — Suggestions go through a `SuggestionAdapter`, not an ad-hoc prop

One `SuggestionAdapter.generate({ messages, signal })` returning
`{ title, label, prompt }[]`, rendered with `ThreadPrimitive.Suggestions` +
`SuggestionPrimitive`. Three merged sources in priority order:

1. **Backend, data-driven** — `GET /api/angela/suggestions?view=` → new
   `core/prompt_suggestions.py`, a deterministic mapping from
   `priorities.inbox()` items to prompts. Reuses the existing ranked inbox and
   the same feature gating as `/api/prioridades`; no new analysis engine.
2. **Per-section registry** — `lib/chat/sectionPrompts.ts`, declarative
   `Record<view, Prompt[]>` with role/feature gates.
3. **Generic fallback** — today's global chips.

This deletes the `placeholderChips` prop threaded through `ChatPanel`.
Per-message `metadata.custom.options` chips stay as they are — those are
follow-ups to one answer, a different concern.

`createSuggestionAdapter` from core is **not** used: it is LLM-based
(`complete(prompt)`), and these suggestions must be deterministic.

### D8 — The model gets a summary; the UI gets the full series

`consultar_serie`'s description says the data comes back summarized, to
control tokens — but the model and the UI currently receive the *same* object,
so chart resolution is capped by what the model needs to read.

Split the `tool_result` payload: `result` for the model, `display` for the UI.
Charts get real resolution, token cost does not move, and every number still
originates in `core/`.

### D9 — Remove the deterministic fallback as a production behavior

`_fallback` is ~920 lines (`angela.py:2283-3203`) of keyword-matched intent
routing, called from 6 sites (`responder()` ×3, `stream_response()` ×3).
23 test files reference `simulado`; several assert `_fallback` behavior
directly.

**It is removed as a production path**, because:

1. **It has no unique capability.** Every deterministic answer it gives
   already exists as real UI — `core/` computes it and ~25 sections render it.
   It is a text-only, keyword-matched duplicate of navigation the user can do
   directly.
2. **Wrong-looking-right is the expensive failure.** This is inventory and
   money. A keyword-matched approximation of "why did margin drop" is worse
   than "I can't answer right now", and the user cannot tell which they got.
3. **It hides outages.** If the model provider is down and the fallback
   answers, no alert fires. D5 already treats this as a defect; keeping the
   fallback means keeping a mode whose job is to be indistinguishable from the
   real thing.
4. **It only gets more wrong.** 53 tools and growing vs. a static keyword
   router; every new capability widens the gap.

**Replaced by** the sibling repo's shape (`hackaton-mdq`'s `LLM_MODE` via
`config.py::cliente_llm()`):

| Situation | Behavior |
|---|---|
| prod, key missing/bad | **config error at startup**; chat feature-flagged off with a clear message. The rest of the app works — that is the honest version of "everything still works without a key". |
| prod, model call fails | `error` event + retry (D5). Provider failover later if wanted. |
| dev / test / demo | `LLM_MODE=fake` — visibly labeled in the UI, **not selectable in prod** |

Tests asserting `_fallback` either move to the labeled fake or are deleted
where they only tested keyword matching.

The one *legitimate* production use of a deterministic path is cost control —
routing common queries away from the model. That is a confidence-gated
optimization that defers when unsure, not a catch-all failure handler, and it
is not what this was. It remains an open option, unrelated to this removal.

### D10 — Charts are driven by `meta`, and violeta is never a data color

`consultar_serie` already returns
`{ ok, series: [{ nombre, puntos }], meta: { temporal, unidad, composicion, deflactado, ventana, ... } }`.
`meta` already says how to draw it; today's `MiniChart` discards all of it and
always draws bars from `series[].top`.

| `meta` | Visual |
|---|---|
| `temporal: true` | line/area, full x-axis |
| `temporal: false` | grouped bars (2 series when `comparar_*` was used) |
| `composicion: true` | stacked share, % of group |
| `unidad: "%"` | single % line, 0–100 axis |
| `deflactado: true` | caption naming the IPC base (`meta.base_ipc`) |

Real vs. nominal must never be ambiguous.

**Color rule, from `lib/paleta.js` and `DESIGN.md`:** every color means exactly
one thing — `rojo` = real problem, `oro` = attention/decision, `salvia` = in
order, `hielo` = frozen capital. **`violeta` (`#2a5cdf`, same value as
`angela-blue`; the token name is historical) is exclusively Ángela/AI and must
never be a data-series color.** Series come from `paleta.SERIES`. Chart axes
and grids come from `components/charts/tema`.

## Target structure

```
frontend/src/
  components/assistant/
    tools/
      types.ts        ToolPresenter, ToolLabels, ToolRenderProps, per-tool arg/result types
      registry.ts     REGISTRY: Record<string, ToolPresenter>  ← the one place to add a tool
      labels.ts       default label derivation + i18n keys
      Fallback.tsx    the shape-based dispatcher (D1)
      series.tsx      consultar_serie / consultar_evolucion / consultar_pronostico
      accounts.tsx    cuentas_corrientes / scoring_credito / capital_recuperable
      ...             one module per family
    ChatThread.tsx    consumes the registry; must never grow a per-tool branch
    ErrorState.tsx    MessagePrimitive.Error content, retry, code-specific copy
    ThinkingIndicator.tsx
  lib/chat/
    adapter.ts        the NDJSON ChatModelAdapter (protocol v2)
    errors.ts         ChatStreamError { code, status, message }
    runContext.ts     { view, focus, entityId, entityName } (D6)
    sectionPrompts.ts declarative per-section prompts (D7)
    suggestions.ts    the SuggestionAdapter (D7)
    ask.ts            useAskAngela()
```

## Phases

Each phase gets its own implementation plan, reviewed and shipped before the
next. Order is dependency-driven.

### Phase 1 — Foundation

TS setup (D3) · tool-arg codegen (D4) · presenter registry + `Fallback` (D1) ·
tool labels via `lib/i18n` (English identifiers, Spanish copy) · protocol v2
on both sides (D5) · typed `ChatStreamError` codes
(`session_expired` / `rate_limit` / `server` / `network` / `aborted`) ·
adapter **throws** instead of yielding a fake assistant message ·
`MessagePrimitive.Error` + `ErrorState` with `aui.message.reload()` ·
`session_expired` breaks out to re-login rather than offering a pointless
retry · `ThinkingIndicator` using the registry's `labels.running` and the
built-in `useToolCallElapsed`, honoring `prefers-reduced-motion`.

Deliberately **not** here: the `view`/run-context plumbing, so it is done once
in Phase 2 together with the backend field and the copilots context.

### Phase 1.5 — Remove the deterministic fallback (D9)

Sequenced immediately after Foundation: protocol v2 and the real error states
are what make removal safe — you need an honest error path before deleting the
thing that hid errors. Everything after is then built against the final
contract.

### Phase 2 — Context and prompts

`runContext` + `ChatRunContextSync` · backend `view` + `app_context` fields ·
`useAssistantContext` in ~5 high-traffic sections (Inicio, Ventas, Cobranzas,
Inventario, Caja) with the remaining ~20 following the established pattern ·
`SuggestionAdapter` + `/api/angela/suggestions` + `core/prompt_suggestions.py` ·
`useAskAngela()` and the `<AskAngela>` trigger on KPI cards, alert rows,
opportunity cards, widgets and table rows.

`MobileApp` mounts its own provider, so `runContext` and the adapter must work
outside `ChatRuntimeProvider` — `useChatDock` already degrades gracefully and
`runContext` must too.

### Phase 3 — Renderers and charts

`SeriesTool` presenter per D10 · `display` payload split per D8 ·
`ResultTable` promoted to a real presenter for `cuentas_corrientes` /
`listar_grupo` / `top_inmovilizado` / `listar_prioridades` (sortable,
right-aligned numerics, unit-aware) · KPI tiles for `estado_caja` /
`resumen_negocio` · "Pin to Inicio" wiring the existing `fijar_en`/
`crear_widget` path to a button · click-a-category drill-down via `focoStore` ·
CSV export.

Load the `dataviz` skill before building the charts rather than improvising
color and axis choices.

### Phase 4 — Accessibility and UX polish

Target WCAG 2.1 AA on the chat surface: `aria-live="polite"` for streaming
text (there is none today, so a screen reader hears nothing) · focus
management on dock open/close and dock ↔ fullscreen, Escape closes ·
keyboard operability for composer, suggestions, `AskAngela` triggers and tool
cards, with visible focus rings · `prefers-reduced-motion` honored
(`animate-bounce`/`animate-spin` are currently unguarded) · real accessible
names instead of `title`-only buttons · contrast audit on `tinta-suave` and
the `oro`/`salvia` status dots · `ActionBarPrimitive` (copy, regenerate,
edit-and-resend) · `ThreadPrimitive.ScrollToBottom` · sticky `ViewportFooter`.

### Phase 5 — New capabilities

Generic `show_chart` / `show_table` tools — with the caveat that these pass
data *through* the model, the one place the "LLM never handles numbers"
invariant bends. Gate them to visualizing data a prior tool already returned
in the same turn, and say so in the tool description.

New `core/` analytics (variance decomposition, what-if). Deferred
deliberately: deterministic-core work with its own test surface, and the least
dependent on everything above.

## Testing

There are no frontend tests today (`playwright` is a devDep used by ad-hoc
`shot-*.mjs` / `probe-*.mjs` scripts, not a suite). Vitest is added for this
layer, which is unusually well-suited to it:

- The registry is pure data; presenters are pure functions of `(args, result)`.
- The adapter is a generator over a byte stream, so tests feed synthetic
  NDJSON — including **a chunk boundary splitting a line mid-JSON** (the
  buffer/`lines.pop()` logic is exactly the kind of thing that works until it
  doesn't), a `done`-without-text cap payload, an abort mid-stream, and each
  error code.

Backend: the chat contract tests move to protocol v2; `_fallback` tests are
migrated or deleted per D9.

`npm run typecheck` is part of the gate (D3).

## Invariants for future changes

1. `core/` computes every number. Presenters format; they never calculate.
   The LLM never calculates, never remembers a number, never reformats one.
2. A presenter is an override. `Fallback` must keep working for tools with no
   presenter (D1).
3. `ChatThread` never grows a per-tool branch. Add a module under `tools/`
   and register it (D1).
4. Presenters are pure. Side effects (navigate, create widget, apply
   preference) stay in the action applier (D2.3).
5. Tool labels and all user-facing copy are i18n keys, never inline strings.
6. `violeta` is Ángela, never data (D10).
7. App context is data, never instructions, and never the answer (D6).
8. Code, identifiers, comments and docstrings in English; user-facing copy may
   stay Spanish (repo `CLAUDE.md`).

## Follow-ups (tracked, not scheduled)

- **Normalize `action.type` string values** across `angela.py`'s `_run_tool`
  (`"crear_pestana"`, `"preferencia"`, `"orden_home"`, `"saneado"` alongside
  `"navigate"`, `"modify_view"`). Right to do, but a wide shallow backend edit
  with its own test exposure; kept out of Phase 1 to stop it inflating.
- **Bidirectional tool channel** (stream pauses → client posts a tool result →
  loop resumes), which would unlock real HITL and, with it, toolkits (D2).
- **Provider failover** at the transport layer, the real answer to resilience
  that D9 removes the fake answer to.
- **Confidence-gated deterministic routing** for cost control (D9), if and
  when there is measured reason.
