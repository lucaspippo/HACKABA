# Ángela Chat Phase 2 — Context and Prompts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The app tells Ángela what the user is looking at (D6) and offers relevant next questions (D7), replacing today's ad-hoc, hand-threaded equivalents (`onPreguntar` prop-drilled through ~20 sections, a hardcoded `CHIPS` array) with reusable, typed primitives.

**Architecture:** A `runContext` store (mirroring the existing `focoStore` exactly) tracks `{ view, focus, entityId, entityName }` outside React, fed by one `<ChatRunContextSync/>` mounted per app shell (desktop and mobile both use `useParams().section` already). Sections opt in to richer context via `useAssistantContext({ getContext })`, which `@assistant-ui/react` merges into `ChatModelRunOptions.context.system` — the adapter forwards that as `app_context` in the request body, and the backend appends it to the system prompt under an explicit heading, bounded to ~2KB. `useAskAngela()` formalizes the `preguntar()`/`onPreguntar` pattern that already exists (project already has `accion_chat` strings on priority/opportunity cards) into a context-based hook so new call sites don't need prop drilling. Suggestions come from a `SuggestionAdapter` merging a new deterministic backend endpoint, a per-section registry, and today's global chips as the last resort.

**Tech Stack:** React 18 + TypeScript (chat layer), `@assistant-ui/react` 0.15.16 (`useAssistantContext`, `ThreadPrimitive.Suggestions`, `SuggestionPrimitive`, `ChatModelRunOptions.context: ModelContext` — all confirmed present in `frontend/node_modules/@assistant-ui/core/dist/`), FastAPI + Python 3.12.

**Spec:** `docs/superpowers/specs/2026-09-02-chat-experience-design.md` — D6, D7, and the Phase 2 phase description. Read it before starting. This plan assumes Phase 1 (landed, PR #29) and Phase 1.5 (`docs/superpowers/plans/2026-09-02-chat-phase-1.5-remove-fallback.md`) are both done: the adapter throws typed `ChatStreamError`s, `stream_response` speaks protocol v2, and `_fallback` can no longer activate silently in production.

## Global Constraints

- **All code, identifiers, comments, commit messages, docstrings in English.** User-facing copy may stay Spanish.
- **Every new UI string is an i18n key**, added to `frontend/src/lib/locales/es.js` **and** `en.js` in the same commit.
- **`core/` computes every number; the LLM never calculates, remembers, or reformats one.** `app_context` and suggestions are DATA, never instructions or numbers Ángela is told to trust — she still calls `core/` tools for every figure (D6, constraint 3).
- **`app_context` is bounded (~2KB, truncated server-side)** and is data, never directives/secrets/tokens (D6, constraints 1-2).
- **Pre-production:** breaking changes to code and wire contracts are permitted and preferred over compatibility shims.
- **TypeScript is chat-layer only** (`frontend/src/components/assistant/**`, `frontend/src/lib/chat/**`). Run `npm run typecheck` before merging.
- **`ChatThread` never grows a per-tool branch**; a presenter is always an override over `Fallback` (Phase 1 invariants, unaffected by this plan but not to be violated by new tool-adjacent UI).
- **Dataset "today" is 2026-07-07.** Run the backend with `POLPILOT_DEMO_TODAY=2026-07-07`.
- **Local Postgres is on port 5434.** Do not move it to 5432.
- **After running backend tests, restore seeds:** `git checkout -- data-demo/`.
- **Both app shells matter.** `DesktopApp.jsx` and `MobileApp.jsx` (mobile, via `AngelaView.jsx`) each mount their own `ChatRuntimeProvider` instance and both already read `useParams().section` — any new store or sync component must be mounted in BOTH, and `useChatDock()`'s existing "degrade gracefully outside a provider" pattern (`frontend/src/lib/chatRuntimeProvider.jsx:31-37`) is the model to copy for `runContext`.

## Current state (verified against `main`, post Phase 1 / pre Phase 1.5)

- `frontend/src/lib/focoStore.js` — the exact pattern to mirror: a module-level singleton (`{ titulo, codigos }` for foco's case) + `Set` of listeners + `subscribe/getSnapshot/set/clear` + a `useFoco()` wrapper over `useSyncExternalStore`. No provider needed — works everywhere, same file imported from both desktop and mobile sections (`frontend/src/desktop/sections/Inventario.jsx`, `Saneamiento.jsx`).
- `frontend/src/lib/chatRuntimeProvider.jsx` — `ChatRuntimeProvider` builds `createChatModelAdapter()` with NO options (confirmed: no `getCurrentView` dead wiring remains post-Phase-1). `useChatDock()` returns a safe no-op object when called outside the provider (lines 31-37) — `runContext`'s `useSyncExternalStore` hook needs no such guard since it's not context-based, but any NEW provider-dependent hook this plan adds must follow this same "degrade, don't throw" rule.
- `frontend/src/lib/chat/adapter.ts` — `run({ messages, abortSignal })` does NOT currently destructure `context` from `ChatModelRunOptions`, even though `context: ModelContext` is present on the type (confirmed in `node_modules/@assistant-ui/core/dist/runtime/utils/chat-model-adapter.d.ts`: `ModelContext = { system?: string; ... }`). `doFetch(message, history, extra, init)` already accepts an arbitrary `extra` object forwarded verbatim into the POST body via `api.chatStream`'s `{ message, history, ...extra }` (`frontend/src/lib/api.js`).
- `frontend/src/desktop/DesktopApp.jsx:201` — `const { section: sectionParam } = useParams();` already exists. `frontend/src/mobile/MobileApp.jsx:85` — `const { section: viewParam } = useParams();` already exists. Both are the exact signal `runContext`'s `view` field needs.
- `frontend/src/lib/vistaStore.js` — a DIFFERENT concern (view-modification preferences: widgets, tabs, hidden columns), not to be confused with the new `runContext`. No overlap, no rename needed.
- `preguntar(texto)` (`frontend/src/desktop/DesktopApp.jsx:308-311`) — `setConsultaAngela(texto); setAngelaOpen(true);` — opens the chat panel and pre-fills/sends a prompt. Threaded as `onPreguntar` prop through ~20 sections (confirmed via `grep -n "onPreguntar=" DesktopApp.jsx` — every mounted section receives it). This is the exact behavior `useAskAngela()` must preserve, just without prop drilling.
- `accion_chat` — a field already returned by `core/priorities.py`'s `_item()` builder (`backend/core/priorities.py:147-166`) and consumed today via prop-drilled callbacks in `frontend/src/sections/Prioridades.jsx:303-304`, `frontend/src/sections/OportunidadesNegocio.jsx:272`, `frontend/src/desktop/sections/MapaNegocio.jsx:282`, `frontend/src/mobile/Hoy.jsx:154`, `frontend/src/mobile/InsightsMobile.jsx:42`, `frontend/src/mobile/MobileApp.jsx:92` (`op.accion_chat || \`Ayudame a gestionar esto: ${op.titulo}\``). This is a ready-made prompt string per priority/opportunity card — Task 6's `core/prompt_suggestions.py` reuses it directly instead of inventing new prompt text.
- `frontend/src/views/ChatPanel.jsx:27-29` — `placeholderChips = []` prop; rendered at line 239 as a flat map of chip buttons. `frontend/src/views/AngelaView.jsx:8-13` defines the hardcoded `CHIPS` (4 entries, `{ lk, enviar }` shape — `lk` an i18n key, `enviar` the raw Spanish prompt sent to the backend). `frontend/src/desktop/DesktopApp.jsx:462,587` calls `chipsPorRol(user)` (defined at `DesktopApp.jsx:665`) to build a role-varying chip list. All three call sites are what Task 7 deletes/replaces.
- `backend/main.py:146-154` — current `ChatRequest`: `message: str`, `history`, `token`, `rol`, `nombre` (post Phase-1 English rename). No `view` or `app_context` field yet.
- `backend/angela.py:3372` — `_prepare_turn(message, history, role, name, features, language)` builds the system prompt (`system_text = SYSTEM_PROMPT.format(...) + _contexto_externo() + who + language_directive`, `angela.py:3439-3440`) and is the ONE shared place `responder()`'s duplicate inline version and `stream_response()` both should eventually use — for this plan, only `_prepare_turn` (the path `stream_response`/the actual web chat uses) gets the new `app_context` parameter; `responder()` (WhatsApp/guest) has no concept of "what screen is the user looking at" and is out of scope.
- `backend/core/priorities.py:298` — `inbox(lang=None, features=None) -> dict` returns `{"act": [...], "watch": [...], "badge", "hay_ventas", "recuperable"}`, each item shaped by `_item()` (has `id`, `titulo`, `resumen`, `accion_chat`, `origen`, `navegar`, ...). `backend/main.py:2191-2197` — `/api/prioridades` is gated with `Depends(authz.require_any_feature("alertas", "oportunidades"))` and calls `priorities.inbox(_lang(u), perfiles.features_efectivas(u["username"]))`. This is the exact gating and data source Task 6's `/api/angela/suggestions` reuses.
- `backend/authz.py:56-82` — `require_feature(feature)` / `require_any_feature(*features)`, both `Depends`-based FastAPI dependencies backed by `core/perfiles.features_efectivas(username)`. The established gating pattern for any new endpoint.
- Confirmed present in the installed `@assistant-ui/react`/`@assistant-ui/core` (0.15.16): `useAssistantContext`, `ThreadPrimitive.Suggestions`, `SuggestionPrimitive` (`.Title`, `.Description`, `.Trigger`), `ChatModelRunOptions.context: ModelContext` where `ModelContext.system?: string`. None of these are used anywhere in the frontend yet (`grep -rn "useAssistantContext\|ThreadPrimitive.Suggestions\|SuggestionPrimitive" frontend/src` → no hits before this plan).

## File structure

**Created**

| File | Responsibility |
|---|---|
| `frontend/src/lib/chat/runContext.ts` | `{ view, focus, entityId, entityName }` store, mirrors `focoStore` |
| `frontend/src/lib/chat/runContext.test.ts` | Store behavior + reset-on-navigate |
| `frontend/src/components/assistant/ChatRunContextSync.tsx` | Mounts once per app shell; writes `runContext` from `useParams().section` + `useFoco()` |
| `frontend/src/lib/chat/ask.ts` | `useAskAngela()` — replaces prop-drilled `onPreguntar` |
| `frontend/src/lib/chat/ask.test.ts` | Hook behavior over a mocked dock context |
| `frontend/src/components/assistant/AskAngela.tsx` | The reusable trigger button/affordance |
| `frontend/src/lib/chat/sectionPrompts.ts` | Declarative `Record<view, Prompt[]>` with role/feature gates |
| `frontend/src/lib/chat/sectionPrompts.test.ts` | Gate-filtering tests |
| `frontend/src/lib/chat/suggestions.ts` | `SuggestionAdapter`: merges backend + section registry + generic fallback |
| `frontend/src/lib/chat/suggestions.test.ts` | Merge-order and de-duplication tests |
| `backend/core/prompt_suggestions.py` | Deterministic mapping from `priorities.inbox()` items to `{title, label, prompt}` |
| `backend/tests/test_prompt_suggestions.py` | Unit tests for the mapping |
| `backend/tests/test_angela_suggestions_route.py` | Route-level tests (gating, shape) |

**Modified**

| File | Change |
|---|---|
| `frontend/src/lib/chat/adapter.ts` | `run()` reads `context.system`, forwards it as `app_context` in the request `extra` |
| `frontend/src/lib/chat/adapter.test.ts` | Cover `app_context` forwarding |
| `frontend/src/lib/api.js` | No change needed — `extra` already spreads into the body (verified above) |
| `frontend/src/desktop/DesktopApp.jsx` | Mount `<ChatRunContextSync/>` once; start migrating `onPreguntar` call sites to `useAskAngela()` (only where touched by this plan's worked sections) |
| `frontend/src/mobile/MobileApp.jsx` | Mount `<ChatRunContextSync/>` once |
| `frontend/src/desktop/sections/Inicio.jsx`, `Ventas.jsx`, `Caja.jsx`, `Inventario.jsx`, `frontend/src/sections/Cobranzas.jsx` | Add `useAssistantContext({ getContext })` |
| `frontend/src/views/ChatPanel.jsx` | Replace `placeholderChips` prop with `ThreadPrimitive.Suggestions` fed by the new `SuggestionAdapter` |
| `frontend/src/views/AngelaView.jsx`, `frontend/src/desktop/DesktopApp.jsx` (chip call sites) | Delete `CHIPS`/`chipsPorRol`, delete `placeholderChips` prop threading |
| `backend/main.py` | `ChatRequest` gains `view: str \| None`, `app_context: str \| None`; new `GET /api/angela/suggestions` route |
| `backend/angela.py` | `_prepare_turn` gains `app_context` parameter, appended to the system prompt under a heading, truncated to ~2KB |
| `backend/tests/test_chat_protocol.py` | New test: `app_context` reaches the system prompt, truncated |

---

### Task 1: `runContext` store + `ChatRunContextSync`

**Files:**
- Create: `frontend/src/lib/chat/runContext.ts`
- Create: `frontend/src/lib/chat/runContext.test.ts`
- Modify: `frontend/src/desktop/DesktopApp.jsx`
- Modify: `frontend/src/mobile/MobileApp.jsx`

**Interfaces:**
- Consumes: nothing.
- Produces: `runContext.getSnapshot(): RunContext`, `runContext.subscribe`, `runContext.set(patch: Partial<RunContext>)`, `useRunContext(): RunContext` from `runContext.ts`, where `RunContext = { view: string | null; focus: string | null; entityId: string | null; entityName: string | null }`. Later tasks (`ask.ts`, section `useAssistantContext` calls) read `useRunContext()`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/chat/runContext.test.ts`:

```ts
import { describe, expect, it, beforeEach } from "vitest";
import { runContext } from "./runContext";

describe("runContext", () => {
  beforeEach(() => runContext.set({ view: null, focus: null, entityId: null, entityName: null }));

  it("starts with every field null", () => {
    expect(runContext.getSnapshot()).toEqual({
      view: null, focus: null, entityId: null, entityName: null,
    });
  });

  it("merges a partial patch rather than replacing the whole object", () => {
    runContext.set({ view: "inventario" });
    runContext.set({ entityId: "SKU-1", entityName: "Manteca 500g" });
    expect(runContext.getSnapshot()).toEqual({
      view: "inventario", focus: null, entityId: "SKU-1", entityName: "Manteca 500g",
    });
  });

  it("notifies subscribers on every set", () => {
    let calls = 0;
    const unsubscribe = runContext.subscribe(() => { calls += 1; });
    runContext.set({ view: "ventas" });
    unsubscribe();
    runContext.set({ view: "caja" });
    expect(calls).toBe(1);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm test`
Expected: FAIL — `Failed to resolve import "./runContext"`.

- [ ] **Step 3: Write `frontend/src/lib/chat/runContext.ts`**

```ts
/**
 * What screen the user is on, for Ángela (D6). Mirrors lib/focoStore.js's
 * shape exactly: a module-level singleton + listener set, no React context —
 * so it works identically inside DesktopApp's and MobileApp's separate
 * ChatRuntimeProvider trees without either needing to know about the other.
 */
import { useSyncExternalStore } from "react";

export type RunContext = {
  view: string | null;
  focus: string | null;
  entityId: string | null;
  entityName: string | null;
};

const EMPTY: RunContext = { view: null, focus: null, entityId: null, entityName: null };

let state: RunContext = { ...EMPTY };
const listeners = new Set<() => void>();

export const runContext = {
  subscribe(l: () => void) {
    listeners.add(l);
    return () => listeners.delete(l);
  },
  getSnapshot(): RunContext {
    return state;
  },
  set(patch: Partial<RunContext>) {
    state = { ...state, ...patch };
    listeners.forEach((l) => l());
  },
};

export function useRunContext(): RunContext {
  return useSyncExternalStore(runContext.subscribe, runContext.getSnapshot);
}
```

- [ ] **Step 4: Run the tests and typecheck**

Run: `cd frontend && npm test && npm run typecheck`
Expected: 3 tests PASS, typecheck exits 0.

- [ ] **Step 5: Write `frontend/src/components/assistant/ChatRunContextSync.tsx`**

```tsx
/**
 * Mounted ONCE per app shell (desktop and mobile each mount their own — see
 * DesktopApp.jsx and MobileApp.jsx). Keeps runContext in sync with the
 * router's current section and the existing foco selection, so Ángela's
 * system prompt (via useAssistantContext, see later tasks) always reflects
 * what's on screen without every section having to report it manually.
 */
import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { useFoco } from "../../lib/focoStore";
import { runContext } from "../../lib/chat/runContext";

export default function ChatRunContextSync() {
  const { section } = useParams<{ section?: string }>();
  const foco = useFoco();

  useEffect(() => {
    runContext.set({ view: section ?? null });
  }, [section]);

  useEffect(() => {
    runContext.set({
      focus: foco?.titulo ?? null,
      // focoStore carries a list of codigos, not a single entity; entityId/
      // entityName are populated by sections themselves via useRunContext's
      // setter when they have ONE specific record in view (see Task 4).
    });
  }, [foco]);

  return null;
}
```

- [ ] **Step 6: Mount it in both app shells**

In `frontend/src/desktop/DesktopApp.jsx`, import and render `<ChatRunContextSync />` once inside `DesktopAppInner` (the component that already calls `useParams()` at line 201), alongside the existing `<Toasts />` at the top of the returned tree (line 327 area):

```jsx
import ChatRunContextSync from "../components/assistant/ChatRunContextSync";
```

```jsx
    <div className="flex h-[100dvh] overflow-hidden bg-papel text-tinta">
      <ChatRunContextSync />
      <Toasts />
```

In `frontend/src/mobile/MobileApp.jsx`, same pattern: import `ChatRunContextSync` and render it once near the top of the component that already destructures `useParams()` at line 85.

- [ ] **Step 7: Manual verification**

Run the app (`cd backend && POLPILOT_DEMO_TODAY=2026-07-07 python -m uvicorn main:app --port 8000` and `cd frontend && npm run dev`), navigate between sections, and confirm no console errors from `ChatRunContextSync` mounting twice or `useParams()` returning `undefined` outside a route.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/lib/chat/runContext.ts frontend/src/lib/chat/runContext.test.ts frontend/src/components/assistant/ChatRunContextSync.tsx frontend/src/desktop/DesktopApp.jsx frontend/src/mobile/MobileApp.jsx
git commit -m "Add runContext store tracking the current view for Angela"
```

---

### Task 2: Adapter forwards `context.system` as `app_context`

**Files:**
- Modify: `frontend/src/lib/chat/adapter.ts`
- Modify: `frontend/src/lib/chat/adapter.test.ts`

**Interfaces:**
- Consumes: `ChatModelRunOptions.context: ModelContext` (from `@assistant-ui/react`, confirmed present).
- Produces: the POST body to `/api/angela/stream` gains `app_context: string | undefined` alongside `token`.

- [ ] **Step 1: Write the failing test**

In `frontend/src/lib/chat/adapter.test.ts`, add a new `describe` block:

```ts
describe("app_context", () => {
  it("forwards context.system as app_context in the request", async () => {
    const fetchStream = vi.fn(async () =>
      responseOf(['{"type":"done","result":{"mode":"claude","tools_used":[],"actions":[]}}\n']),
    );
    const adapter = createChatModelAdapter({ fetchStream });
    for await (const _ of adapter.run({
      messages: [userMessage],
      context: { system: "view=inventario; focus=Manteca 500g" },
      abortSignal: new AbortController().signal,
    } as never)) { /* drain */ }

    const [, , extra] = fetchStream.mock.calls[0]!;
    expect(extra).toMatchObject({ app_context: "view=inventario; focus=Manteca 500g" });
  });

  it("omits app_context when there is no context.system", async () => {
    const fetchStream = vi.fn(async () =>
      responseOf(['{"type":"done","result":{"mode":"claude","tools_used":[],"actions":[]}}\n']),
    );
    const adapter = createChatModelAdapter({ fetchStream });
    for await (const _ of adapter.run({
      messages: [userMessage],
      context: {},
      abortSignal: new AbortController().signal,
    } as never)) { /* drain */ }

    const [, , extra] = fetchStream.mock.calls[0]!;
    expect(extra).not.toHaveProperty("app_context");
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm test`
Expected: FAIL — today's `run()` destructures only `{ messages, abortSignal }`, so `context` is silently ignored and `extra` never gains `app_context`.

- [ ] **Step 3: Update `createChatModelAdapter`'s `run()`**

In `frontend/src/lib/chat/adapter.ts`, change the signature and the `doFetch` call:

```ts
    async *run({ messages, context, abortSignal }: ChatModelRunOptions) {
      const { message, history } = splitMessages(messages);
      if (!message) return;

      const token = authStore.getSnapshot()?.token;
      const appContext = context?.system;

      let res: Response;
      try {
        res = await doFetch(
          message, history,
          { token, ...(appContext ? { app_context: appContext } : {}) },
          { signal: abortSignal },
        );
      } catch (e) {
```

(The rest of `run()` is unchanged — only the destructuring and the `doFetch` call site above it.)

- [ ] **Step 4: Run the tests and typecheck**

Run: `cd frontend && npm test && npm run typecheck`
Expected: all PASS, typecheck exits 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/chat/adapter.ts frontend/src/lib/chat/adapter.test.ts
git commit -m "Forward ModelContext.system as app_context in the chat request"
```

---

### Task 3: Backend accepts `view`/`app_context` and appends it to the system prompt

**Files:**
- Modify: `backend/main.py` (`ChatRequest`, `chat_stream`)
- Modify: `backend/angela.py` (`_prepare_turn`, `stream_response`)
- Modify: `backend/tests/test_chat_protocol.py`

**Interfaces:**
- Consumes: `app_context` field from Task 2's request body.
- Produces: `_prepare_turn(message, history, role, name, features, language, app_context=None)` — new keyword-only trailing parameter, defaulting to `None` so every other existing call site (there are none besides `stream_response`, confirmed at `angela.py:3525`) needs no change.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_chat_protocol.py`:

```python
def test_app_context_reaches_the_system_prompt(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "fake")  # deterministic path is enough to inspect _prepare_turn directly
    import angela
    system, _model, _tools, _messages = angela._prepare_turn(
        "hola", [], "dueño", "aldo", ["inventario"], "es",
        app_context="El usuario está mirando Inventario, categoría Lácteos.",
    )
    text = system[0]["text"] if isinstance(system, list) else system
    assert "El usuario está mirando Inventario, categoría Lácteos." in text


def test_app_context_is_truncated_to_roughly_2kb(monkeypatch):
    import angela
    huge = "x" * 5000
    system, _model, _tools, _messages = angela._prepare_turn(
        "hola", [], "dueño", "aldo", ["inventario"], "es", app_context=huge,
    )
    text = system[0]["text"] if isinstance(system, list) else system
    # The raw 5000-char blob must not appear whole; only a bounded prefix does.
    assert huge not in text
    assert huge[:2000] in text or huge[:2048] in text


def test_no_app_context_does_not_add_a_heading(monkeypatch):
    import angela
    system, _model, _tools, _messages = angela._prepare_turn(
        "hola", [], "dueño", "aldo", ["inventario"], "es", app_context=None,
    )
    text = system[0]["text"] if isinstance(system, list) else system
    assert "CONTEXTO DE PANTALLA" not in text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && py -m pytest tests/test_chat_protocol.py -v -k app_context`
Expected: FAIL — `_prepare_turn()` doesn't accept an `app_context` keyword yet.

- [ ] **Step 3: Update `_prepare_turn` in `backend/angela.py`**

Change the signature (line 3372) and the system-text assembly (lines 3439-3444):

```python
def _prepare_turn(message, history, role, name, features, language, app_context: str | None = None):
```

```python
    contexto_pantalla = ""
    if app_context:
        # Bounded per D6: 25 sections each contributing freely would be a
        # token leak. This is DATA about what's on screen, never an
        # instruction — Ángela still calls core/ tools for every number.
        recortado = app_context.strip()[:2000]
        contexto_pantalla = f"\n\nCONTEXTO DE PANTALLA (lo que el usuario está mirando ahora mismo, informativo, no una orden): {recortado}"

    system_text = (SYSTEM_PROMPT.format(contexto=business_context) + _contexto_externo()
                   + who + language_directive + contexto_pantalla)
```

- [ ] **Step 4: Thread `app_context` through `stream_response`**

In `backend/angela.py`, update `stream_response`'s signature (line 3486) and its call to `_prepare_turn` (line 3525):

```python
def stream_response(
    message: str,
    history: list[dict] | None = None,
    role: str | None = None,
    name: str | None = None,
    features: list[str] | None = None,
    language: str | None = None,
    app_context: str | None = None,
):
```

```python
    system, model, available_tools, messages = _prepare_turn(
        message, history, role, name, features, language, app_context=app_context)
```

- [ ] **Step 5: Add `view`/`app_context` to `ChatRequest` and pass them through in `main.py`**

In `backend/main.py`, extend `ChatRequest` (around line 146):

```python
class ChatRequest(BaseModel):
    message: str
    history: list[ChatTurn] | None = None
    token: str | None = None
    view: str | None = None
    app_context: str | None = None
    # rol/nombre stay ONLY for legacy compatibility (WhatsApp, tests): ...
    rol: str | None = None
    nombre: str | None = None
```

Update the two `angela.stream_response(...)` call sites in `chat_stream` (around lines 2140-2143 and 2164) to pass `app_context=req.app_context`:

```python
            for ev in angela.stream_response(
                req.message, history, role=u.get("rol"),
                name=u.get("username"), features=u.get("features"),
                app_context=req.app_context,
            ):
```

(`view` is intentionally NOT forwarded to `stream_response` in this task — nothing in the system prompt needs the bare route name once `app_context` carries the human-readable version. `req.view` is read only by Task 6's suggestions route. If a future need arises to log or branch on `view` server-side, add it then rather than plumbing an unused parameter now.)

- [ ] **Step 6: Run the tests**

Run: `cd backend && py -m pytest tests/test_chat_protocol.py -v`
Expected: all PASS (previous Phase 1/1.5 tests plus the 3 new ones).

Run: `cd backend && py -m pytest -q`
Expected: no new failures vs. baseline.

- [ ] **Step 7: Restore seeds and commit**

```bash
git checkout -- data-demo/
git add backend/angela.py backend/main.py backend/tests/test_chat_protocol.py
git commit -m "Accept app_context on the chat request and append it to the system prompt"
```

---

### Task 4: `useAssistantContext` in the 5 named sections

**Files:**
- Modify: `frontend/src/desktop/sections/Inicio.jsx`
- Modify: `frontend/src/desktop/sections/Ventas.jsx`
- Modify: `frontend/src/desktop/sections/Caja.jsx`
- Modify: `frontend/src/desktop/sections/Inventario.jsx`
- Modify: `frontend/src/sections/Cobranzas.jsx`

**Interfaces:**
- Consumes: `useAssistantContext` from `@assistant-ui/react` (confirmed present).
- Produces: each section's live data reaches `ModelContext.system` (and from there, via Task 2's adapter and Task 3's backend, the system prompt) whenever that section is mounted — lazily, read at send time per `AssistantContextConfig.getContext: () => string`.

Do Inicio first as the fully worked example; the other four repeat the exact same shape with section-appropriate fields, which is why they're grouped in one task rather than four.

- [ ] **Step 1: Add context to `Inicio.jsx`**

`frontend/src/desktop/sections/Inicio.jsx` already receives `data` and `oportunidades` as props (confirmed: `export default function Inicio({ data, oportunidades, onNavegar, onPreguntar })`, line 81). Add the import and the hook call right after the existing hooks at the top of the function body:

```jsx
import { useAssistantContext } from "@assistant-ui/react";
```

```jsx
export default function Inicio({ data, oportunidades, onNavegar, onPreguntar }) {
  useAssistantContext({
    getContext: () => {
      const alertas = (data?.alertas || []).length;
      const oportunidadesN = (oportunidades || []).length;
      return `El usuario está en Inicio (panel principal). ${alertas} alerta(s) activa(s), ${oportunidadesN} oportunidad(es) sin revisar.`;
    },
  });
  // ...rest of the component unchanged
```

Adjust the exact field names (`data?.alertas`, `oportunidades`) to whatever `Inicio.jsx` actually receives — read the component's existing body for the real shape of `data` before writing the string (the plan's job here is the PATTERN; the exact fields are visible once you open the file, which the executor must do since this plan can't enumerate every prop `data` carries).

- [ ] **Step 2: Manual verification for Inicio**

Run the app, open Ángela while on the Inicio section, ask "¿qué estoy mirando?" and confirm the reply's phrasing reflects the section (this is informational only — Ángela is not required to name the section verbatim, just to have plausibly used the context; do not assert exact wording in a test, since the model's phrasing is not deterministic).

- [ ] **Step 3: Repeat for Ventas, Caja, Inventario, Cobranzas**

For each of `frontend/src/desktop/sections/Ventas.jsx`, `frontend/src/desktop/sections/Caja.jsx`, `frontend/src/desktop/sections/Inventario.jsx`, `frontend/src/sections/Cobranzas.jsx`:
1. Open the file and identify its top-level props (data it already receives — sales totals, cash position, inventory filters, receivables aging, respectively).
2. Add the same `useAssistantContext({ getContext: () => \`...\` })` call, describing the section name and 1-3 concrete figures or filters currently in view (e.g. Inventario: which category/tab is selected; Caja: today's balance; Cobranzas: total overdue).
3. Keep each `getContext` string under ~300 characters — five sections' worth must fit inside Task 3's 2000-character server-side truncation with room for later sections (per D6 constraint 1: "25 sections each contributing freely is a token leak" — these five are the first cut, not the only ones ever).

- [ ] **Step 4: Typecheck**

Run: `cd frontend && npm run typecheck`
Expected: exits 0. (These files stay `.jsx` under `allowJs`; the import of a typed hook from `@assistant-ui/react` does not require converting the file to `.tsx`.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/desktop/sections/Inicio.jsx frontend/src/desktop/sections/Ventas.jsx frontend/src/desktop/sections/Caja.jsx frontend/src/desktop/sections/Inventario.jsx frontend/src/sections/Cobranzas.jsx
git commit -m "Feed Angela live section context via useAssistantContext (5 high-traffic sections)"
```

**Note for whoever extends this to the remaining ~20 sections (explicitly out of this task's scope, per the spec's own phasing):** same three-step pattern as Step 3 above, one section at a time, each its own small commit. No new infrastructure is needed — `useAssistantContext` is a hook, not a registration a central file has to know about.

---

### Task 5: `useAskAngela()` + `<AskAngela>`, replacing ad-hoc `onPreguntar` prop drilling

**Files:**
- Create: `frontend/src/lib/chat/ask.ts`
- Create: `frontend/src/lib/chat/ask.test.ts`
- Create: `frontend/src/components/assistant/AskAngela.tsx`
- Modify: `frontend/src/desktop/DesktopApp.jsx`

**Interfaces:**
- Consumes: `useChatDock()` from `frontend/src/lib/chatRuntimeProvider.jsx` (existing), `aui.thread.append` / composer send (via `useAui()`, existing pattern already used in `ChatPanel.jsx`).
- Produces: `useAskAngela(): (prompt: string) => void` from `ask.ts`; `<AskAngela prompt={string} label?={string} />` from `AskAngela.tsx` — a small button any component can drop in without receiving `onPreguntar` as a prop.

This does NOT rip out `onPreguntar` everywhere in one pass (20+ call sites, unrelated risk) — it adds the hook-based alternative and migrates `DesktopApp.jsx`'s own top-level `preguntar` definition to be backed by it, so `useAskAngela()` is the source of truth and `onPreguntar` becomes a thin, optional back-compat prop for sections not yet migrated.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/chat/ask.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";

const setOpen = vi.fn();
const append = vi.fn();

vi.mock("../chatRuntimeProvider", () => ({
  useChatDock: () => ({ open: false, setOpen, toggle: vi.fn(), fullscreen: false, setFullscreen: vi.fn() }),
}));
vi.mock("@assistant-ui/react", () => ({
  useAui: () => ({ thread: { append } }),
}));

import { useAskAngela } from "./ask";
import { renderHook } from "./testUtils"; // see Step 2 note

describe("useAskAngela", () => {
  it("opens the dock and appends the prompt as a user message", () => {
    const { result } = renderHook(() => useAskAngela());
    result.current("¿cuánta plata tengo en manteca?");
    expect(setOpen).toHaveBeenCalledWith(true);
    expect(append).toHaveBeenCalledWith({
      role: "user",
      content: [{ type: "text", text: "¿cuánta plata tengo en manteca?" }],
    });
  });
});
```

Note: this project has no `@testing-library/react` dependency yet (Phase 1 deliberately skipped it — see that plan's Task 1 note "Component-render tests arrive with Phase 4's accessibility work"). Rather than add that dependency here for one hook test, write `useAskAngela` as a **plain function factory** instead of a React hook with internal `useAui`/`useChatDock` calls, so it's testable with plain function calls:

Replace the test above with this simpler, dependency-free version:

```ts
import { describe, expect, it, vi } from "vitest";
import { createAskAngela } from "./ask";

describe("createAskAngela", () => {
  it("opens the dock and appends the prompt as a user message", () => {
    const setOpen = vi.fn();
    const append = vi.fn();
    const ask = createAskAngela({ setOpen, append });

    ask("¿cuánta plata tengo en manteca?");

    expect(setOpen).toHaveBeenCalledWith(true);
    expect(append).toHaveBeenCalledWith({
      role: "user",
      content: [{ type: "text", text: "¿cuánta plata tengo en manteca?" }],
    });
  });

  it("ignores an empty prompt", () => {
    const setOpen = vi.fn();
    const append = vi.fn();
    const ask = createAskAngela({ setOpen, append });

    ask("   ");

    expect(setOpen).not.toHaveBeenCalled();
    expect(append).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm test`
Expected: FAIL — `Failed to resolve import "./ask"`.

- [ ] **Step 3: Write `frontend/src/lib/chat/ask.ts`**

```ts
/**
 * Formalizes the "open Angela's panel and ask this" pattern that already
 * exists ad-hoc as DesktopApp.jsx's preguntar() + onPreguntar prop, threaded
 * through ~20 sections. createAskAngela is the pure, testable core; useAskAngela
 * wires it to the real runtime hooks so call sites don't need onPreguntar
 * threaded to them at all — they just call the hook.
 */
import { useAui } from "@assistant-ui/react";
import { useChatDock } from "../chatRuntimeProvider";

type AskDeps = {
  setOpen: (open: boolean) => void;
  append: (message: { role: "user"; content: { type: "text"; text: string }[] }) => void;
};

export function createAskAngela({ setOpen, append }: AskDeps) {
  return (prompt: string) => {
    const text = prompt.trim();
    if (!text) return;
    setOpen(true);
    append({ role: "user", content: [{ type: "text", text }] });
  };
}

export function useAskAngela() {
  const { setOpen } = useChatDock();
  const aui = useAui();
  return createAskAngela({
    setOpen,
    append: (message) => aui.thread.append(message),
  });
}
```

- [ ] **Step 4: Run the tests and typecheck**

Run: `cd frontend && npm test && npm run typecheck`
Expected: 2 tests PASS, typecheck exits 0. If `aui.thread.append`'s real signature differs from the `AskDeps.append` shape above, adjust `createAskAngela`'s call in `useAskAngela` to match — check `frontend/src/views/ChatPanel.jsx`'s existing use of `useAui()` for the confirmed shape of `aui.thread` before finalizing.

- [ ] **Step 5: Write `frontend/src/components/assistant/AskAngela.tsx`**

```tsx
/**
 * A reusable "ask Angela about this" trigger. Any component can drop this in
 * with just a prompt string — no onPreguntar prop threading required.
 */
import { MessageCircle } from "lucide-react";
import { useAskAngela } from "../../lib/chat/ask";
import { useT } from "../../lib/i18n";

type AskAngelaProps = {
  prompt: string;
  label?: string;
  className?: string;
};

export default function AskAngela({ prompt, label, className }: AskAngelaProps) {
  const ask = useAskAngela();
  const t = useT();
  return (
    <button
      type="button"
      onClick={() => ask(prompt)}
      className={
        className ??
        "inline-flex items-center gap-1.5 rounded-full border border-violeta/30 px-2.5 py-1 text-[0.78rem] font-medium text-violeta transition-colors hover:bg-violeta/10"
      }
    >
      <MessageCircle size={13} />
      {label ?? t("chat.ask_angela.default_label")}
    </button>
  );
}
```

- [ ] **Step 6: Add the i18n key**

`frontend/src/lib/locales/es.js`:
```js
  "chat.ask_angela.default_label": "Preguntarle a Ángela",
```
`frontend/src/lib/locales/en.js`:
```js
  "chat.ask_angela.default_label": "Ask Ángela",
```

- [ ] **Step 7: Back `DesktopApp.jsx`'s existing `preguntar` with `createAskAngela`**

This keeps the 20+ existing `onPreguntar` call sites working unchanged while making `useAskAngela()` the actual source of truth, so new components (Task 5's whole point) don't need `onPreguntar` threaded to them. In `frontend/src/desktop/DesktopApp.jsx`, replace the `preguntar` definition (lines 308-311):

```jsx
import { createAskAngela } from "../lib/chat/ask";
```

```jsx
  const preguntar = createAskAngela({
    setOpen: setAngelaOpen,
    append: (texto) => setConsultaAngela(texto.content[0].text),
  });
```

Wait — `DesktopApp.jsx`'s existing mechanism is `setConsultaAngela(texto)` (a plain string set as `inputInicial`, sent by `ChatPanel` on mount) rather than `aui.thread.append` directly (there is no `AssistantRuntimeProvider` in scope at `DesktopApp`'s level the way there is inside `ChatPanel`). Because of this difference, do NOT force `DesktopApp.jsx`'s `preguntar` through `createAskAngela` — leave `DesktopApp.jsx`'s existing `preguntar`/`onPreguntar` mechanism exactly as it is; `useAskAngela()` is an ADDITIONAL, independent mechanism for use INSIDE components that render below the `AssistantRuntimeProvider` (i.e. below `ChatPanel`/`ChatRuntimeProvider`), not a replacement for the panel-opening mechanism above it. Skip this step; it was based on a wrong assumption. Verify by reading `frontend/src/views/ChatPanel.jsx`'s handling of `inputInicial` (grep for it) before deciding whether any reconciliation between the two mechanisms is actually needed — if `ChatPanel` already auto-sends `inputInicial` through the same runtime `useAskAngela()` would use, document that the two mechanisms coexist by design (one opens the dock from OUTSIDE the runtime tree, the other posts a message from INSIDE it); no code change follows from this step.

- [ ] **Step 8: Typecheck and commit**

Run: `cd frontend && npm run typecheck`
Expected: exits 0.

```bash
git add frontend/src/lib/chat/ask.ts frontend/src/lib/chat/ask.test.ts frontend/src/components/assistant/AskAngela.tsx frontend/src/lib/locales
git commit -m "Add useAskAngela()/AskAngela as a prop-drilling-free ask-the-chat trigger"
```

**Note for extending `<AskAngela>` to KPI cards, alert rows, opportunity cards, widgets, and table rows** (the spec's full list, explicitly broader than this task's scope): each of those already either has an `accion_chat` string (priority/opportunity cards, per the "Current state" section above) or can derive an equivalent one-line prompt from its own data. Drop `<AskAngela prompt={item.accion_chat ?? \`...\`} />` into the card/row's render — no new infrastructure needed, since `AskAngela` only needs to be rendered somewhere below `ChatRuntimeProvider` in the tree, which every one of those surfaces already is.

---

### Task 6: `core/prompt_suggestions.py` + `/api/angela/suggestions`

**Files:**
- Create: `backend/core/prompt_suggestions.py`
- Create: `backend/tests/test_prompt_suggestions.py`
- Create: `backend/tests/test_angela_suggestions_route.py`
- Modify: `backend/main.py`

**Interfaces:**
- Consumes: `core.priorities.inbox(lang, features)` (existing, unchanged).
- Produces: `prompt_suggestions.from_inbox(inbox: dict, limit: int = 4) -> list[dict]`, each item `{"title": str, "label": str, "prompt": str}`; `GET /api/angela/suggestions?view=` returning `{"suggestions": [...]}`, gated identically to `/api/prioridades`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_prompt_suggestions.py`:

```python
"""Deterministic suggestions from the same ranked inbox /api/prioridades
already serves — no new analysis engine, no LLM call (D7)."""
from core import prompt_suggestions


def _card(id="c1", titulo="Quiebre inminente: Manteca 500g", accion_chat=None, tono="rojo"):
    return {"id": id, "titulo": titulo, "accion_chat": accion_chat, "tono": tono,
            "resumen": "Se agota en 3 días", "chip": "Stock"}


def test_uses_accion_chat_when_present():
    inbox = {"act": [_card(accion_chat="¿Por qué se está por agotar la manteca?")], "watch": []}
    out = prompt_suggestions.from_inbox(inbox)
    assert out[0]["prompt"] == "¿Por qué se está por agotar la manteca?"


def test_derives_a_prompt_when_accion_chat_is_absent():
    inbox = {"act": [_card(accion_chat=None)], "watch": []}
    out = prompt_suggestions.from_inbox(inbox)
    assert out[0]["prompt"], "must synthesize a prompt from titulo when accion_chat is missing"
    assert "Manteca 500g" in out[0]["prompt"]


def test_prefers_act_over_watch_and_respects_limit():
    inbox = {
        "act": [_card(id=f"a{i}", titulo=f"Act {i}") for i in range(3)],
        "watch": [_card(id=f"w{i}", titulo=f"Watch {i}") for i in range(3)],
    }
    out = prompt_suggestions.from_inbox(inbox, limit=4)
    assert len(out) == 4
    assert sum(1 for s in out if s["title"].startswith("Act")) == 3
    assert sum(1 for s in out if s["title"].startswith("Watch")) == 1


def test_empty_inbox_yields_no_suggestions():
    assert prompt_suggestions.from_inbox({"act": [], "watch": []}) == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && py -m pytest tests/test_prompt_suggestions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.prompt_suggestions'`.

- [ ] **Step 3: Write `backend/core/prompt_suggestions.py`**

```python
"""Deterministic chat suggestions from the ranked priorities inbox (D7).

Reuses core.priorities.inbox() — the same ranked "what should I do now" list
/api/prioridades already serves — instead of a second analysis engine. Every
card already carries (or can derive) a natural-language prompt: accion_chat
when the card builder set one (backend/core/priorities.py's _item()), else a
synthesized "tell me about <titulo>" fallback. No LLM call: this is a pure
transform of already-computed core/ output.
"""
from __future__ import annotations


def _prompt_for(card: dict) -> str:
    if card.get("accion_chat"):
        return card["accion_chat"]
    return f"Contame más sobre esto: {card.get('titulo', '')}".strip()


def _suggestion(card: dict) -> dict:
    return {
        "title": card.get("titulo", ""),
        "label": card.get("chip") or card.get("titulo", ""),
        "prompt": _prompt_for(card),
    }


def from_inbox(inbox: dict, limit: int = 4) -> list[dict]:
    """act cards first (higher urgency), then watch cards, capped at `limit`."""
    ordered = list(inbox.get("act") or []) + list(inbox.get("watch") or [])
    return [_suggestion(c) for c in ordered[:limit]]
```

- [ ] **Step 4: Run the tests**

Run: `cd backend && py -m pytest tests/test_prompt_suggestions.py -v`
Expected: 4 tests PASS.

- [ ] **Step 5: Write the failing route test**

Create `backend/tests/test_angela_suggestions_route.py` — read `backend/tests/test_deploy_hardening.py` or another route-level test file first for this repo's client-fixture convention (likely a `client` fixture from `conftest.py` plus a logged-in user helper), then write:

```python
"""GET /api/angela/suggestions: same gating and data source as /api/prioridades."""
def test_requires_a_feature(client):
    r = client.get("/api/angela/suggestions")
    assert r.status_code == 401  # no token at all


def test_returns_suggestions_for_a_gated_user(client, token_dueno):
    r = client.get("/api/angela/suggestions", headers={"Authorization": f"Bearer {token_dueno}"})
    assert r.status_code == 200
    body = r.json()
    assert "suggestions" in body
    assert isinstance(body["suggestions"], list)
    for s in body["suggestions"]:
        assert set(s) >= {"title", "label", "prompt"}
```

(Adjust the fixture names `client`/`token_dueno` to whatever `backend/tests/conftest.py` actually exposes — check it before writing this file; the pattern of "a fixture client + a role-specific token fixture" is standard across this test suite's route tests, but exact names must be verified, not guessed.)

- [ ] **Step 6: Run the test to verify it fails**

Run: `cd backend && py -m pytest tests/test_angela_suggestions_route.py -v`
Expected: FAIL — `404 Not Found`, the route doesn't exist yet.

- [ ] **Step 7: Add the route to `backend/main.py`**

Next to `/api/prioridades` (around line 2191), following its exact gating pattern:

```python
@app.get("/api/angela/suggestions")
def angela_suggestions(view: str | None = None,
                        u: dict = Depends(authz.require_any_feature("alertas", "oportunidades"))):
    """Deterministic chat suggestions (D7) — same ranked inbox, same gating,
    as /api/prioridades. `view` is accepted for future per-section tuning
    (see core/prompt_suggestions.py) but not yet used to filter."""
    from core import priorities, prompt_suggestions
    inbox = priorities.inbox(_lang(u), perfiles.features_efectivas(u["username"]))
    return {"suggestions": prompt_suggestions.from_inbox(inbox)}
```

Confirm `authz` is imported in `main.py` (it is, used by other routes per the file structure above) and that `Depends`/`perfiles` are already imported (both used by `/api/prioridades` immediately above).

- [ ] **Step 8: Run the tests**

Run: `cd backend && py -m pytest tests/test_angela_suggestions_route.py tests/test_prompt_suggestions.py -v`
Expected: all PASS.

Run: `cd backend && py -m pytest -q`
Expected: no new failures vs. baseline.

- [ ] **Step 9: Restore seeds and commit**

```bash
git checkout -- data-demo/
git add backend/core/prompt_suggestions.py backend/main.py backend/tests/test_prompt_suggestions.py backend/tests/test_angela_suggestions_route.py
git commit -m "Add deterministic chat suggestions from the priorities inbox"
```

---

### Task 7: Frontend `SuggestionAdapter`, `sectionPrompts.ts`, and deleting `placeholderChips`

**Files:**
- Create: `frontend/src/lib/chat/sectionPrompts.ts`
- Create: `frontend/src/lib/chat/sectionPrompts.test.ts`
- Create: `frontend/src/lib/chat/suggestions.ts`
- Create: `frontend/src/lib/chat/suggestions.test.ts`
- Modify: `frontend/src/views/ChatPanel.jsx`
- Modify: `frontend/src/views/AngelaView.jsx`
- Modify: `frontend/src/desktop/DesktopApp.jsx`
- Modify: `frontend/src/views/ChatFullscreen.jsx`

**Interfaces:**
- Consumes: `GET /api/angela/suggestions` (Task 6), `useRunContext()` (Task 1), `api` client (`frontend/src/lib/api.js`).
- Produces: `createSuggestionAdapter(): SuggestionAdapter` matching `@assistant-ui/react`'s `SuggestionAdapter` shape (`generate({ messages, signal }) -> Promise<{ title, label, prompt }[]>` — confirmed exported type name `SuggestionAdapter` in `@assistant-ui/core`), consumed via `ThreadPrimitive.Suggestions` + `SuggestionPrimitive` in `ChatPanel.jsx`.

- [ ] **Step 1: Write the failing test for `sectionPrompts.ts`**

Create `frontend/src/lib/chat/sectionPrompts.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { promptsFor } from "./sectionPrompts";

describe("promptsFor", () => {
  it("returns the inventory-section prompts for view=inventario", () => {
    const prompts = promptsFor("inventario", { features: ["inventario"] });
    expect(prompts.length).toBeGreaterThan(0);
    expect(prompts.every((p) => p.prompt)).toBe(true);
  });

  it("filters out prompts gated by a missing feature", () => {
    const prompts = promptsFor("cobranzas", { features: [] });
    expect(prompts).toEqual([]);
  });

  it("returns an empty list for an unknown view", () => {
    expect(promptsFor("unknown-view", { features: [] })).toEqual([]);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm test`
Expected: FAIL — `Failed to resolve import "./sectionPrompts"`.

- [ ] **Step 3: Write `frontend/src/lib/chat/sectionPrompts.ts`**

```ts
/**
 * Declarative per-section suggested prompts (D7, source 2 of 3 — after the
 * backend's data-driven suggestions, before the generic fallback). One entry
 * per view; each prompt can require a feature the user must have.
 */
export type SectionPrompt = { title: string; label: string; prompt: string; requiresFeature?: string };

const REGISTRY: Record<string, SectionPrompt[]> = {
  inventario: [
    { title: "Productos fantasma", label: "Fantasmas", prompt: "¿Cuáles son mis productos fantasma?" },
    { title: "Mayor riesgo", label: "Riesgo", prompt: "¿Dónde está el mayor riesgo de mi inventario?" },
  ],
  cobranzas: [
    { title: "Morosos", label: "Morosos", prompt: "¿Quién me debe plata hace más tiempo?", requiresFeature: "cobranzas" },
  ],
  caja: [
    { title: "Plata parada", label: "Plata parada", prompt: "¿Cuánta plata tengo parada hoy?" },
  ],
};

export function promptsFor(view: string, user: { features: string[] }): SectionPrompt[] {
  const entries = REGISTRY[view] ?? [];
  return entries.filter((p) => !p.requiresFeature || user.features.includes(p.requiresFeature));
}
```

- [ ] **Step 4: Run the tests**

Run: `cd frontend && npm test`
Expected: PASS. (`REGISTRY` above is a starting set covering the 5 sections named for `useAssistantContext` in Task 4, keyed by their actual route/view names — verify those against `DesktopApp.jsx`'s section-key constants, e.g. `secciones`/`CATALOGO`, before finalizing the keys, since "inventario"/"cobranzas"/"caja" must match what `useParams().section` actually yields.)

- [ ] **Step 5: Write the failing test for `suggestions.ts`**

Create `frontend/src/lib/chat/suggestions.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";
import { createSuggestionAdapter } from "./suggestions";

describe("createSuggestionAdapter", () => {
  it("prefers backend suggestions, then section prompts, then the generic fallback", async () => {
    const fetchSuggestions = vi.fn(async () => ([
      { title: "Quiebre", label: "Stock", prompt: "¿Por qué se agota X?" },
    ]));
    const adapter = createSuggestionAdapter({
      fetchSuggestions,
      getView: () => "inventario",
      getUser: () => ({ features: ["inventario"] }),
    });
    const result = await adapter.generate({ messages: [], signal: new AbortController().signal } as never);
    expect(result[0]).toMatchObject({ prompt: "¿Por qué se agota X?" });
  });

  it("falls back to section prompts when the backend call fails", async () => {
    const fetchSuggestions = vi.fn(async () => { throw new Error("network"); });
    const adapter = createSuggestionAdapter({
      fetchSuggestions,
      getView: () => "inventario",
      getUser: () => ({ features: ["inventario"] }),
    });
    const result = await adapter.generate({ messages: [], signal: new AbortController().signal } as never);
    expect(result.length).toBeGreaterThan(0);
  });

  it("falls back to the generic chips when there is no view and the backend returns nothing", async () => {
    const fetchSuggestions = vi.fn(async () => []);
    const adapter = createSuggestionAdapter({
      fetchSuggestions,
      getView: () => null,
      getUser: () => ({ features: [] }),
    });
    const result = await adapter.generate({ messages: [], signal: new AbortController().signal } as never);
    expect(result.length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 6: Run the test to verify it fails**

Run: `cd frontend && npm test`
Expected: FAIL — `Failed to resolve import "./suggestions"`.

- [ ] **Step 7: Write `frontend/src/lib/chat/suggestions.ts`**

```ts
/**
 * Three merged sources, in priority order (D7):
 *   1. backend, data-driven (GET /api/angela/suggestions)
 *   2. per-section registry (sectionPrompts.ts)
 *   3. generic fallback — today's global chips, now living here instead of
 *      AngelaView.jsx's hardcoded CHIPS array.
 */
import { promptsFor } from "./sectionPrompts";

export type Suggestion = { title: string; label: string; prompt: string };

const GENERIC_FALLBACK: Suggestion[] = [
  { title: "Manteca", label: "Manteca", prompt: "¿Cuánta plata tengo en manteca?" },
  { title: "Fantasmas", label: "Fantasmas", prompt: "¿Cuáles son mis productos fantasma?" },
  { title: "Riesgo", label: "Riesgo", prompt: "¿Dónde está el mayor riesgo de mi inventario?" },
];

export type SuggestionAdapterDeps = {
  fetchSuggestions: (view: string | null) => Promise<Suggestion[]>;
  getView: () => string | null;
  getUser: () => { features: string[] };
};

export function createSuggestionAdapter({ fetchSuggestions, getView, getUser }: SuggestionAdapterDeps) {
  return {
    async generate(_options: unknown): Promise<Suggestion[]> {
      const view = getView();
      try {
        const fromBackend = await fetchSuggestions(view);
        if (fromBackend.length) return fromBackend;
      } catch {
        // Network hiccup: fall through to the deterministic client-side sources.
      }
      if (view) {
        const sectionOnes = promptsFor(view, getUser());
        if (sectionOnes.length) return sectionOnes;
      }
      return GENERIC_FALLBACK;
    },
  };
}
```

- [ ] **Step 8: Run the tests and typecheck**

Run: `cd frontend && npm test && npm run typecheck`
Expected: all PASS, exits 0.

- [ ] **Step 9: Register the adapter on the runtime in `chatRuntimeProvider.jsx`, then consume it in `ChatPanel.jsx`**

Confirmed against the installed types (`frontend/node_modules/@assistant-ui/core/dist/react/runtimes/useLocalRuntime.d.ts`): `useLocalRuntime(chatModel: ChatModelAdapter, options?: { adapters？: { suggestion?: SuggestionAdapter, ... }, ... })` — the suggestion adapter is a **runtime construction option**, not a `ThreadPrimitive.Suggestions` prop. That means it must be registered where `useLocalRuntime` is actually called — `frontend/src/lib/chatRuntimeProvider.jsx:51` (`runtimeHook: () => useLocalRuntime(modelAdapter)`) — not inside `ChatPanel.jsx`, which only consumes the already-built runtime via `useAui`/`useAuiState`.

`chatRuntimeProvider.jsx` has no `user` prop today, so build the adapter from `authStore` directly — exactly how `lib/chat/adapter.ts` already reads `authStore.getSnapshot()?.token` for auth (confirmed: `backend/../frontend/src/lib/auth.js` exposes `authStore.getSnapshot()?.usuario?.features`). `runContext` is a plain external store (Task 1), so it's readable from any file, provider included, with no prop threading needed either.

In `frontend/src/lib/api.js`, add a thin wrapper next to `chatStream` (follow the file's existing style for an authenticated GET — check how `/api/prioridades` is called from the frontend and match that pattern exactly rather than reinventing a fetch wrapper):

```js
  angelaSuggestions: (view) =>
    api.get(`/api/angela/suggestions${view ? `?view=${encodeURIComponent(view)}` : ""}`),
```

In `frontend/src/lib/chatRuntimeProvider.jsx`:

```jsx
import { createSuggestionAdapter } from "./chat/suggestions";
import { runContext } from "./chat/runContext";
import { authStore } from "./auth";
import { api } from "./api";
```

```jsx
  const modelAdapter = useMemo(() => createChatModelAdapter(), []);
  const suggestionAdapter = useMemo(() => createSuggestionAdapter({
    fetchSuggestions: async (view) => (await api.angelaSuggestions(view))?.suggestions ?? [],
    getView: () => runContext.getSnapshot().view,
    getUser: () => ({ features: authStore.getSnapshot()?.usuario?.features || [] }),
  }), []);

  const runtime = useRemoteThreadListRuntime({
    runtimeHook: () => useLocalRuntime(modelAdapter, { adapters: { suggestion: suggestionAdapter } }),
    adapter: threadListAdapter,
  });
```

In `frontend/src/views/ChatPanel.jsx`, remove the `placeholderChips` prop and its render block (line 29 and the `.map` at line 239), and replace with `ThreadPrimitive.Suggestions` (which reads the runtime's registered suggestion adapter automatically — no prop needed) + `SuggestionPrimitive`. Read `ChatPanel.jsx`'s current imports and JSX structure around line 239 first (the existing chip buttons' exact markup/classes) so the new `SuggestionPrimitive.Root`/`.Title`/`.Trigger` markup preserves the same visual position and styling classes, swapped onto the primitive instead of a raw `.map`.

- [ ] **Step 10: Delete the now-unused chip sources**

Remove `CHIPS` and the `placeholderChips` prop from `frontend/src/views/AngelaView.jsx` (lines 8-13, 23, 33). Remove `chipsPorRol` and its two call sites from `frontend/src/desktop/DesktopApp.jsx` (function at line 665, call sites at 462 and 587). Remove the `placeholderChips` prop from `frontend/src/views/ChatFullscreen.jsx` (lines 7, 13) and from any remaining prop-type/destructuring in `ChatPanel.jsx`.

Per-message `metadata.custom.options` chips (a different, existing mechanism — the follow-up chips shown after ONE answer) are UNAFFECTED — do not touch `ChatThread.tsx`'s handling of `options`.

- [ ] **Step 11: Manual verification**

Run the app, open the chat with an empty thread on a couple of different sections (Inventario, Cobranzas, one with no registry entry) and confirm suggestions render and clicking one sends it. Check the Network tab for a call to `/api/angela/suggestions`; kill the backend and confirm the fallback chain still shows something (section prompts, or the generic list) instead of an empty suggestions area.

- [ ] **Step 12: Run the full frontend suite and typecheck**

Run: `cd frontend && npm test && npm run typecheck`
Expected: all PASS, exits 0.

- [ ] **Step 13: Commit**

```bash
git add frontend/src/lib/chat/sectionPrompts.ts frontend/src/lib/chat/sectionPrompts.test.ts frontend/src/lib/chat/suggestions.ts frontend/src/lib/chat/suggestions.test.ts frontend/src/views/ChatPanel.jsx frontend/src/views/AngelaView.jsx frontend/src/views/ChatFullscreen.jsx frontend/src/desktop/DesktopApp.jsx frontend/src/lib/api.js
git commit -m "Replace hardcoded chat chips with a merged SuggestionAdapter"
```

---

### Task 8: Documentation and exit criteria

**Files:**
- Modify: `docs/superpowers/specs/2026-09-02-chat-experience-design.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: nothing.
- Produces: docs matching shipped behavior.

- [ ] **Step 1: Update the spec**

Mark D6 and D7 as landed in the spec doc's status area, noting the two deliberate scope cuts made in this plan: only 5 sections got `useAssistantContext` (not the full ~25), and `useAskAngela()`/`<AskAngela>` was added as infrastructure but wired into DesktopApp's own dock-opening path only where noted in Task 5 — most of "KPI cards, alert rows, opportunity cards, widgets, table rows" from the spec's Phase 2 description remain unconverted, ready for incremental follow-up per Task 5's closing note.

- [ ] **Step 2: Update `CLAUDE.md`'s chat section status line**

Append that Phase 2 (D6, D7) landed, noting `runContext`, `useAssistantContext` (5 sections), and the `SuggestionAdapter` now exist, and that D8 (chart `display` payload split) and the accessibility pass remain for Phases 3/4.

- [ ] **Step 3: Full verification pass**

```bash
cd backend && py -m pytest -q
git checkout -- data-demo/
cd ../frontend && npm test && npm run typecheck
```

Expected: backend matches baseline; frontend all-green; typecheck exits 0.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md docs/superpowers/specs/2026-09-02-chat-experience-design.md
git commit -m "Document Phase 2: run context and suggestion adapter landed"
```

---

## Phase 2 exit criteria

- [ ] `cd backend && py -m pytest -q` — same pass/skip counts as the pre-Phase-2 baseline
- [ ] `git checkout -- data-demo/` run after every backend test run
- [ ] `cd frontend && npm test && npm run typecheck` — all green, exits 0
- [ ] Navigating sections updates `runContext.getSnapshot().view` (verify in the browser console: `import('/src/lib/chat/runContext.ts')`-style check, or simpler, confirm via the manual verification steps in Tasks 1 and 4)
- [ ] Asking Ángela a question while on Inicio/Ventas/Caja/Inventario/Cobranzas reaches the backend with a non-empty `app_context` (check the Network tab request body)
- [ ] `/api/angela/suggestions` returns 401 with no token and a well-shaped list with one
- [ ] The chat's empty-thread state shows suggestions sourced from the new adapter, not the deleted `CHIPS` constant
- [ ] `grep -rn "placeholderChips" frontend/src` → no output
- [ ] Docs updated per Task 8

## Notes for the Phase 3 planner

- `_prepare_turn` now takes `app_context` as its 7th (keyword) parameter — Phase 3's chart/renderer work does not touch this function, but any future change to its signature must keep `app_context` a keyword with a `None` default, since call sites outside `stream_response` may appear.
- `createSuggestionAdapter`'s registration point in `ChatPanel.jsx` (Task 7, Step 9) was left with an explicit "verify against installed types before finalizing" flag — if Task 7's executor left a TODO or a provisional wiring there, Phase 3's planner should confirm it actually shipped correctly rather than assume the plan's sketch was the final shape.
- `useAskAngela()`/`<AskAngela>` exists but is wired into few call sites. Phase 3 (charts/tables) is a natural place to add `<AskAngela>` to table rows and chart data points, per the spec's original list, since Phase 3 is already touching those renderers.
