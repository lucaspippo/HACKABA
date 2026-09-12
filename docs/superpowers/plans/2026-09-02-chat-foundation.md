# Ángela Chat Foundation (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the chat's hand-rolled tool rendering and invisible error handling with a typed, extensible foundation: a tool-presenter registry over the existing shape-based fallback, TypeScript for the chat layer, and a stream protocol in which errors and notices are first-class.

**Architecture:** The Python agent loop keeps executing all 50 tools; the frontend only *renders* them. Tool presentation becomes a flat `Record<string, ToolPresenter>` fed to `MessagePrimitive.Parts` via `components={{ tools: { by_name, Fallback } }}`, where a presenter is always an override and the shape-based `Fallback` keeps giving new Python tools a usable UI for free. The NDJSON stream gains `error` and `notice` events so failures stop masquerading as answers, and the adapter throws instead of yielding fake assistant messages so `MessagePrimitive.Error` can own the error state.

**Tech Stack:** React 18 + Vite 6, `@assistant-ui/react` 0.15.16, Tailwind v4, recharts, TypeScript 5 (chat layer only), Vitest (new), FastAPI + Python 3.12.

**Spec:** `docs/superpowers/specs/2026-09-02-chat-experience-design.md` — decisions D1–D5 and the "Invariants for future changes" section. Read it before starting.

## Global Constraints

- **All code, identifiers, comments, docstrings in English.** User-facing copy may stay Spanish. (repo `CLAUDE.md`)
- **Every new UI string is an i18n key**, added to `frontend/src/lib/locales/es.js` **and** `en.js` in the same commit. Never inline a user-facing string. (`i18n.js` house convention)
- **`core/` computes every number.** Presenters format; they never calculate. The LLM never calculates, remembers, or reformats a number.
- **A presenter is an override, never a requirement.** `Fallback` must keep working for tools with no presenter. (D1)
- **Presenters are pure** functions of `(args, result)`. Side effects stay in `ChatPanel`'s action applier. (D2.3)
- **`ChatThread` must never grow a per-tool `if`.** Add a module under `tools/` and register it. (D1)
- **`violeta` (`#2a5cdf`) is Ángela, never a data-series color.** (D10, `lib/paleta.js`)
- **Pre-production:** breaking changes to code and wire contracts are permitted and preferred over compatibility shims.
- **TypeScript is chat-layer only** (D3): `frontend/src/components/assistant/**` and `frontend/src/lib/chat/**`. Everything else stays `.jsx` under `allowJs`. `npm run typecheck` must run before merge — Vite/esbuild does not typecheck.
- **Python is the single source of truth for tool schemas.** TS tool types are generated, never hand-edited. (D4)
- **Dataset "today" is 2026-07-07.** Run the backend with `POLPILOT_DEMO_TODAY=2026-07-07`.
- **Local Postgres is on port 5434** (`docker-compose.yml` / `backend/.env`). Do not move it to 5432.
- **After running backend tests, restore seeds:** `git checkout -- data-demo/`.

## Out of scope for this plan

- Run-context / `view` / `app_context` plumbing → Phase 2.
- Removing `_fallback` → Phase 1.5. It stays wired in Phase 1; only its envelope key names change (Task 3).
- Chart and table renderers → Phase 3. Task 7 ports the *existing* shape dispatcher unchanged; it does not improve it.
- Accessibility pass → Phase 4. Task 10 adds `prefers-reduced-motion` only because it is writing the animation.

## File structure

**Created**

| File | Responsibility |
|---|---|
| `frontend/tsconfig.json` | TS config for the chat layer; `allowJs`, `noEmit` |
| `frontend/src/lib/chat/protocol.ts` | Wire event types + `parseStreamLine` |
| `frontend/src/lib/chat/errors.ts` | `ChatStreamError`, `ChatErrorCode`, status→code mapping |
| `frontend/src/lib/chat/adapter.ts` | The `ChatModelAdapter` (protocol v2) |
| `frontend/src/lib/chat/adapter.test.ts` | Adapter unit tests over synthetic NDJSON |
| `frontend/src/lib/chat/errors.test.ts` | Status→code mapping tests |
| `frontend/src/lib/chat/toolArgs.generated.ts` | **Generated** per-tool arg types (D4) |
| `frontend/src/lib/chat/useElapsedSince.ts` | Ticking elapsed-ms hook |
| `frontend/src/components/assistant/tools/types.ts` | `ToolPresenter`, `ToolLabels`, `ToolChrome` |
| `frontend/src/components/assistant/tools/labels.ts` | i18n-backed label lookup |
| `frontend/src/components/assistant/tools/labels.test.ts` | Label fallback tests |
| `frontend/src/components/assistant/tools/Fallback.tsx` | Shape-based dispatcher (ported) |
| `frontend/src/components/assistant/tools/registry.ts` | `TOOL_PRESENTERS` + `toolComponentsByName()` |
| `frontend/src/components/assistant/tools/registry.test.ts` | Registry shape/consistency tests |
| `frontend/src/components/assistant/ErrorState.tsx` | Error UI + retry |
| `frontend/src/components/assistant/ThinkingIndicator.tsx` | Running label + elapsed |
| `backend/scripts/generate_tool_types.py` | AST → TS codegen (D4) |
| `backend/tests/test_tool_types_codegen.py` | Drift guard for the generated file |
| `backend/tests/test_chat_protocol.py` | Protocol v2 event tests |

**Modified**

| File | Change |
|---|---|
| `frontend/package.json` | Add `typescript`, `vitest`, `@types/*`; `typecheck` + `test` scripts |
| `frontend/vite.config.js` | Import `defineConfig` from `vitest/config`; add `test` block |
| `frontend/src/lib/api.js:354-363` | `chatStream` throws `ChatStreamError` with a code |
| `frontend/src/lib/chatRuntime.js` | **Deleted**, replaced by `lib/chat/adapter.ts` |
| `frontend/src/lib/chatRuntimeProvider.jsx` | Import the new adapter path |
| `frontend/src/components/assistant/ChatThread.jsx` → `.tsx` | Registry wiring; remove the `if` chain; notices; error slot |
| `frontend/src/components/assistant/ToolCallCard.jsx` → `.tsx` | Becomes the presenter card shell; label map moves to i18n |
| `frontend/src/views/ChatPanel.jsx` | English `metadata.custom` keys |
| `frontend/src/lib/locales/es.js`, `en.js` | New `tool.*`, `chat.error.*`, `chat.notice.*` keys |
| `backend/angela.py` | Envelope rename; protocol v2 events in `stream_response` |
| `backend/main.py` | Envelope rename; `ChatRequest` field rename; cap as a `notice` |
| `backend/tests/*` (6 assertions) | English envelope keys |

---

### Task 1: TypeScript + Vitest toolchain

**Files:**
- Create: `frontend/tsconfig.json`
- Create: `frontend/src/lib/chat/errors.ts`
- Create: `frontend/src/lib/chat/errors.test.ts`
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.js`

**Interfaces:**
- Consumes: nothing.
- Produces: `npm run typecheck` and `npm test` in `frontend/`. `ChatErrorCode`, `ChatStreamError`, `chatErrorCodeFromStatus(status: number): ChatErrorCode` from `src/lib/chat/errors.ts`.

This task is bundled because a toolchain with nothing type-checked or tested proves nothing. `errors.ts` is the smallest real module that exercises both.

- [ ] **Step 1: Install dev dependencies**

```bash
cd frontend
npm install --save-dev typescript@^5 vitest@^2 @types/react@^18 @types/react-dom@^18
```

No `jsdom` / `@testing-library` in this phase: everything tested here is pure logic. Component-render tests arrive with Phase 4's accessibility work.

- [ ] **Step 2: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "allowJs": true,
    "checkJs": false,
    "noEmit": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "forceConsistentCasingInFileNames": true,
    "types": ["vite/client"]
  },
  "include": ["src"]
}
```

`checkJs: false` is deliberate: `allowJs` lets TS *resolve* the ~60 existing `.jsx` files so chat-layer imports work, without reporting errors in them.

- [ ] **Step 3: Add scripts to `frontend/package.json`**

In `"scripts"`, alongside the existing `dev`/`build`/`preview`:

```json
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "test:watch": "vitest"
```

- [ ] **Step 4: Add the Vitest block to `frontend/vite.config.js`**

Change only the import line and add a `test` block. The import must come from `vitest/config` (it re-exports Vite's `defineConfig` with the `test` key typed):

```js
import { defineConfig } from "vitest/config";
```

Then, inside the `defineConfig({ ... })` object, after the existing `server: { ... }` block:

```js
  test: {
    environment: "node",
    include: ["src/**/*.test.{ts,tsx}"],
  },
```

Leave `plugins` and `server` exactly as they are — the dev proxy comment about `127.0.0.1` vs `localhost` documents a measured 2s-per-request Windows problem; do not touch it.

- [ ] **Step 5: Write the failing test**

Create `frontend/src/lib/chat/errors.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { ChatStreamError, chatErrorCodeFromStatus } from "./errors";

describe("chatErrorCodeFromStatus", () => {
  it("maps 401 to session_expired", () => {
    expect(chatErrorCodeFromStatus(401)).toBe("session_expired");
  });

  it("maps 429 to rate_limit", () => {
    expect(chatErrorCodeFromStatus(429)).toBe("rate_limit");
  });

  it("maps any 5xx to server", () => {
    expect(chatErrorCodeFromStatus(500)).toBe("server");
    expect(chatErrorCodeFromStatus(503)).toBe("server");
  });

  it("falls back to server for unexpected statuses", () => {
    expect(chatErrorCodeFromStatus(418)).toBe("server");
  });
});

describe("ChatStreamError", () => {
  it("keeps its code and is instanceof Error", () => {
    const err = new ChatStreamError("rate_limit", "too many");
    expect(err).toBeInstanceOf(Error);
    expect(err.code).toBe("rate_limit");
    expect(err.message).toBe("too many");
  });

  it("marks rate_limit and server and network as retryable", () => {
    expect(new ChatStreamError("rate_limit").retryable).toBe(true);
    expect(new ChatStreamError("server").retryable).toBe(true);
    expect(new ChatStreamError("network").retryable).toBe(true);
  });

  it("marks session_expired as not retryable", () => {
    expect(new ChatStreamError("session_expired").retryable).toBe(false);
  });
});
```

- [ ] **Step 6: Run the test to verify it fails**

Run: `cd frontend && npm test`
Expected: FAIL — `Failed to resolve import "./errors"`.

- [ ] **Step 7: Write `frontend/src/lib/chat/errors.ts`**

```ts
/**
 * Chat stream failure codes. These drive both the copy the user sees and
 * whether a retry button is offered, so they are a closed set rather than
 * free-form strings.
 */
export type ChatErrorCode =
  | "session_expired"
  | "rate_limit"
  | "server"
  | "network"
  | "stream"
  | "aborted";

/** Codes worth offering a retry for. `session_expired` needs a new session, not a retry. */
const RETRYABLE: ReadonlySet<ChatErrorCode> = new Set<ChatErrorCode>([
  "rate_limit",
  "server",
  "network",
  "stream",
]);

export class ChatStreamError extends Error {
  readonly code: ChatErrorCode;
  readonly status?: number;

  constructor(code: ChatErrorCode, message?: string, status?: number) {
    super(message ?? code);
    this.name = "ChatStreamError";
    this.code = code;
    this.status = status;
  }

  get retryable(): boolean {
    return RETRYABLE.has(this.code);
  }
}

/** HTTP status -> error code. Anything unrecognised is treated as a server fault. */
export function chatErrorCodeFromStatus(status: number): ChatErrorCode {
  if (status === 401 || status === 403) return "session_expired";
  if (status === 429) return "rate_limit";
  return "server";
}
```

- [ ] **Step 8: Run the tests and the typecheck**

Run: `cd frontend && npm test && npm run typecheck`
Expected: tests PASS (9 assertions across 6 tests); `typecheck` exits 0 with no output.

If `typecheck` reports errors in existing `.jsx` files, `checkJs` is not `false` — fix the config rather than the files.

- [ ] **Step 9: Commit**

```bash
git add frontend/tsconfig.json frontend/package.json frontend/package-lock.json frontend/vite.config.js frontend/src/lib/chat/errors.ts frontend/src/lib/chat/errors.test.ts
git commit -m "Add TypeScript and Vitest for the chat layer"
```

---

### Task 2: Generate TS tool-arg types from `angela.py`

**Files:**
- Create: `backend/scripts/generate_tool_types.py`
- Create: `backend/tests/test_tool_types_codegen.py`
- Create (generated, committed): `frontend/src/lib/chat/toolArgs.generated.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: `ToolArgs` (an interface keyed by tool name) and `ToolName = keyof ToolArgs` from `src/lib/chat/toolArgs.generated.ts`. Tasks 6 and 7 type tool arguments against these.

Verified approach: `TOOLS` is parsed out of `angela.py` with `ast.literal_eval` — no `import angela`, so no `core`/DB import side effects. Confirmed against the current file: 50 tools, all with `input_schema`, 26 with a `required` list, 3 nested `object`/`array` properties, and at least one property with no `type`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_tool_types_codegen.py`:

```python
"""The generated TS tool types must stay in sync with angela.py's TOOLS.

Python owns the tool schemas (the loop and the feature gating are Python);
the TS types are generated. This test fails loudly when someone edits a
tool schema and forgets to regenerate.
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "scripts"))

import generate_tool_types as gen  # noqa: E402

GENERATED = REPO / "frontend" / "src" / "lib" / "chat" / "toolArgs.generated.ts"


def test_tools_parse_without_importing_angela():
    tools = gen.load_tools(REPO / "backend" / "angela.py")
    assert len(tools) > 40
    assert all("name" in t and "input_schema" in t for t in tools)
    assert "consultar_serie" in {t["name"] for t in tools}


def test_json_schema_type_mapping():
    assert gen.ts_type({"type": "string"}) == "string"
    assert gen.ts_type({"type": "integer"}) == "number"
    assert gen.ts_type({"type": "number"}) == "number"
    assert gen.ts_type({"type": "boolean"}) == "boolean"
    assert gen.ts_type({"type": "array"}) == "unknown[]"
    assert gen.ts_type({"type": "object"}) == "Record<string, unknown>"
    assert gen.ts_type({}) == "unknown"


def test_required_properties_are_not_optional():
    rendered = gen.render_tool({
        "name": "demo_tool",
        "input_schema": {
            "type": "object",
            "properties": {"source": {"type": "string"}, "top_n": {"type": "integer"}},
            "required": ["source"],
        },
    })
    assert "source: string;" in rendered
    assert "top_n?: number;" in rendered


def test_generated_file_is_current():
    expected = gen.render(gen.load_tools(REPO / "backend" / "angela.py"))
    actual = GENERATED.read_text(encoding="utf-8")
    assert actual == expected, (
        "frontend/src/lib/chat/toolArgs.generated.ts is stale. "
        "Regenerate with: py backend/scripts/generate_tool_types.py"
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && py -m pytest tests/test_tool_types_codegen.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'generate_tool_types'`.

- [ ] **Step 3: Write `backend/scripts/generate_tool_types.py`**

```python
"""Generate TypeScript argument types from angela.py's TOOLS list.

Python is the single source of truth for tool schemas: the tool-use loop and
the per-user feature gating (`tools_para`) both live here. The frontend only
renders tool calls, so it needs the argument shapes as types — generated, not
hand-maintained, so a schema change surfaces at `npm run typecheck`.

TOOLS is read with `ast.literal_eval` instead of by importing angela, which
would pull in `core` and the database.

Run from the repo root or anywhere:  py backend/scripts/generate_tool_types.py
"""
from __future__ import annotations

import ast
import pathlib
import sys

HEADER = """// GENERATED FILE - DO NOT EDIT.
// Source: backend/angela.py (TOOLS)
// Regenerate: py backend/scripts/generate_tool_types.py
//
// Python owns the tool schemas; these types exist so tool-call renderers get
// typed `args` and a schema change fails `npm run typecheck` instead of at
// runtime.
"""

# JSON Schema -> TypeScript. Nested object/array item schemas are not modelled:
# only three tools use them, and a renderer that needs the detail should narrow
# it locally rather than inflate the generator.
TYPE_MAP = {
    "string": "string",
    "integer": "number",
    "number": "number",
    "boolean": "boolean",
    "array": "unknown[]",
    "object": "Record<string, unknown>",
}


def load_tools(angela_path: pathlib.Path) -> list[dict]:
    """Extract the TOOLS literal from angela.py without importing it."""
    tree = ast.parse(angela_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            getattr(target, "id", None) == "TOOLS" for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise RuntimeError(f"No TOOLS assignment found in {angela_path}")


def ts_type(prop: dict) -> str:
    """Map one JSON Schema property to a TypeScript type."""
    return TYPE_MAP.get(prop.get("type"), "unknown")


def render_tool(tool: dict) -> str:
    """Render one tool's argument object type as indented TS members."""
    schema = tool.get("input_schema") or {}
    properties: dict = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    if not properties:
        return f"  {tool['name']}: Record<string, never>;\n"

    lines = [f"  {tool['name']}: {{\n"]
    for name in sorted(properties):
        optional = "" if name in required else "?"
        lines.append(f"    {name}{optional}: {ts_type(properties[name])};\n")
    lines.append("  };\n")
    return "".join(lines)


def render(tools: list[dict]) -> str:
    """Render the whole generated module."""
    out = [HEADER, "\nexport interface ToolArgs {\n"]
    for tool in sorted(tools, key=lambda t: t["name"]):
        out.append(render_tool(tool))
    out.append("}\n\nexport type ToolName = keyof ToolArgs;\n")
    return "".join(out)


def main() -> int:
    repo = pathlib.Path(__file__).resolve().parents[2]
    tools = load_tools(repo / "backend" / "angela.py")
    target = repo / "frontend" / "src" / "lib" / "chat" / "toolArgs.generated.ts"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(tools), encoding="utf-8")
    print(f"Wrote {len(tools)} tool types to {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Generate the file**

Run: `cd backend && py scripts/generate_tool_types.py`
Expected: `Wrote 50 tool types to .../frontend/src/lib/chat/toolArgs.generated.ts`

- [ ] **Step 5: Run the tests and the typecheck**

Run: `cd backend && py -m pytest tests/test_tool_types_codegen.py -v`
Expected: 4 tests PASS.

Run: `cd frontend && npm run typecheck`
Expected: exits 0 — the generated file must be valid TS. If a tool name is not a valid TS identifier the generator needs to quote it; all 50 current names are `snake_case` and safe.

- [ ] **Step 6: Restore the seeds and commit**

```bash
git checkout -- data-demo/
git add backend/scripts/generate_tool_types.py backend/tests/test_tool_types_codegen.py frontend/src/lib/chat/toolArgs.generated.ts
git commit -m "Generate TypeScript tool argument types from angela.py TOOLS"
```

---

### Task 3: Rename the chat envelope to English

**Files:**
- Modify: `backend/angela.py` (11 `"respuesta"` sites; `resp()` at ~2295; `stream_response` done events)
- Modify: `backend/main.py:146-155` (`ChatRequest`), `1826-1832` (WhatsApp), `2042-2043`, `2064-2065`, `2074`, `2081`, `2107-2111`, `2142`, `2146`
- Modify: `frontend/src/lib/api.js` (`chat`, `chatStream` request bodies)
- Modify: `frontend/src/views/ChatPanel.jsx:114-122` and `frontend/src/components/assistant/ChatThread.jsx:38-39`
- Modify: `backend/tests/test_consultas.py:210-211`, `test_guardarrailes.py:31`, `test_plan.py:95`, `test_comprobantes.py:268,273,282,384`, `test_deploy_hardening.py:88,94`

**Interfaces:**
- Consumes: nothing.
- Produces: the wire envelope every later task builds on — request `{message, history, token, rol, nombre}`; response/`done.result` `{answer, mode, tools_used, actions, options}`; `metadata.custom` with the same English keys.

Rename map, applied everywhere:

| Old | New |
|---|---|
| `mensaje` (request field) | `message` |
| `historial` (request field) | `history` |
| `respuesta` | `answer` |
| `modo` | `mode` |
| `tools_usadas` | `tools_used` |
| `acciones` (chat envelope only) | `actions` |
| `opciones` | `options` |

**Do not touch** `hipotesis["acciones"]` in `core/conciliacion.py` and its tests, or `doc["acciones"]` in `test_pdf_documentos.py` — those are different domain concepts that happen to share a word. Verified: the only chat-envelope assertions are the 6 files listed above.

- [ ] **Step 1: Update the backend envelope builders**

In `backend/angela.py`, the single envelope builder inside `_fallback` (~line 2295):

```python
    def resp(texto, acciones=None, opciones=None, tools=None):
        return {"answer": texto, "mode": "simulado", "tools_used": tools or [],
                "actions": acciones or [], "options": opciones or []}
```

Keep the Python parameter names as they are for now — `_fallback` is deleted in Phase 1.5, and renaming its internals is throwaway work. Only the *dict keys* (the wire contract) change here.

Then update `responder()`'s return sites (~3358, ~3365) and `stream_response`'s `done` events (~3543, ~3551) to the English keys, and the `fb.get("respuesta")` / `fb["respuesta"]` reads (~3485-3486, ~3494-3495, ~3557-3558) to `fb.get("answer")` / `fb["answer"]`.

- [ ] **Step 2: Update `ChatRequest` and the routes**

`backend/main.py:146-155`:

```python
class ChatRequest(BaseModel):
    message: str
    history: list[ChatTurn] | None = None
    token: str | None = None
    # rol/nombre stay ONLY for legacy compatibility (WhatsApp, tests): when a
    # token is present, identity comes from the token and these are IGNORED
    # (the role cannot be spoofed from the request). See /api/angela.
    rol: str | None = None
    nombre: str | None = None
```

Then update every `req.mensaje` → `req.message` and `req.historial` → `req.history`, and the envelope keys in the cap payloads (`2042-2043`, `2064-2065`, `2107-2111`), the log lines (`2074`, `2142`) and the audit calls (`2081`, `2146`) to `tools_used`. The WhatsApp response at `1832` becomes `{"answer": r["answer"], "actions": r.get("actions", [])}`.

- [ ] **Step 3: Update the frontend request bodies and consumers**

`frontend/src/lib/api.js` — in `chatStream` (line ~358) and the non-streaming `chat` helper, the body becomes:

```js
      body: JSON.stringify({ message: mensaje, history: historial, ...extra }),
```

`frontend/src/views/ChatPanel.jsx` — in the side-effect effect (~114-122) and the mode read (~122):

```js
      const custom = m.metadata?.custom;
      if (!custom) continue;
      applyActions(custom.actions || []);
      if ((custom.actions || []).some((a) => a.type === "plan_progreso")) onDatosCambiaron?.();
```

```js
  const currentMode = [...messages].reverse().find((m) => m.metadata?.custom?.mode)?.metadata?.custom?.mode;
```

`frontend/src/components/assistant/ChatThread.jsx` (~38-39):

```js
  const actions = useAuiState((s) => s.message.metadata?.custom?.actions) || [];
  const options = useAuiState((s) => s.message.metadata?.custom?.options) || [];
```

Note `action.type` **values** (`"plan_progreso"`, `"crear_pestana"`, `"preferencia"`, …) are deliberately unchanged — that normalization is a tracked follow-up in the spec, kept out of this plan.

- [ ] **Step 4: Update the 6 test assertions**

- `backend/tests/test_consultas.py:210-211` → `r["tools_used"]`, `r["actions"]`
- `backend/tests/test_guardarrailes.py:31` → `r["actions"] == []`
- `backend/tests/test_plan.py:95` → `r2["actions"]`
- `backend/tests/test_comprobantes.py:268,273,282,384` → `r["tools_used"]` / `r2["tools_used"]`
- `backend/tests/test_deploy_hardening.py:88,94` → `j.get("mode")` / `j2.get("mode")`

- [ ] **Step 5: Verify nothing still reads the old keys**

Run:

```bash
cd backend && grep -rn '"respuesta"\|"tools_usadas"\|"modo"\|req\.mensaje\|req\.historial' angela.py main.py core/ tests/ | grep -v hipotesis
```

Expected: no output. (Occurrences inside `core/conciliacion.py`'s `hipotesis` and `documentos` action lists are filtered out and must remain.)

Run:

```bash
cd frontend && grep -rn "custom?.acciones\|custom?.opciones\|custom?.modo\|mensaje:" src/
```

Expected: no output.

- [ ] **Step 6: Run the backend suite**

Run: `cd backend && py -m pytest -q`
Expected: same pass/skip counts as before this task. Any failure mentioning `KeyError: 'answer'` or `'respuesta'` means a rename site was missed.

- [ ] **Step 7: Restore seeds and commit**

```bash
git checkout -- data-demo/
git add -A backend frontend/src
git commit -m "Rename the chat envelope and request fields to English"
```

---

### Task 4: Stream protocol v2 on the backend

**Files:**
- Modify: `backend/angela.py` — `stream_response` (~3462-3559)
- Modify: `backend/main.py` — `chat_stream` (~2095-2151), `cap_event`
- Create: `backend/tests/test_chat_protocol.py`

**Interfaces:**
- Consumes: the English envelope from Task 3.
- Produces: the v2 event stream the adapter in Task 6 parses.

| Event | Payload |
|---|---|
| `text` | `{"type": "text", "delta": str}` — a **delta**, not accumulated |
| `tool_call` | `{"type": "tool_call", "id": str, "name": str, "input": dict}` |
| `tool_result` | `{"type": "tool_result", "id": str, "result": Any}` |
| `notice` | `{"type": "notice", "kind": "cap" \| "tool_loop_exhausted" \| "fake_model", "text": str}` |
| `error` | `{"type": "error", "code": str, "message": str, "retryable": bool}` |
| `done` | `{"type": "done", "result": {"mode", "tools_used", "actions", "options"}}` |

`done.result` no longer carries `answer`: the text arrived as `text` deltas, and duplicating it is what let the cap bug hide. `tool_result` drops the `input` echo, already sent in `tool_call`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_chat_protocol.py`:

```python
"""Stream protocol v2: text arrives as deltas, and failures and degraded
modes are expressible as their own events instead of masquerading as answers.

Regression cover for three verified defects in v1:
  - hitting the message cap emitted a `done` with no `text`, so the frontend
    rendered an empty bubble and the explanation was never shown;
  - a failure after a tool call emitted a second `text` event, so the
    abandoned partial answer and the fallback answer were glued together;
  - every `text` event re-sent the whole accumulated string (O(n^2) bytes).
"""
import json

import angela
import pytest


def _events(monkeypatch, **kwargs):
    return list(angela.stream_response("¿cuánta plata tengo parada?", **kwargs))


def test_text_events_carry_deltas_not_accumulated_text(monkeypatch):
    """Concatenating every delta must reproduce the answer exactly once."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    events = _events(monkeypatch)
    deltas = [e["delta"] for e in events if e["type"] == "text"]
    assert deltas, "expected at least one text event"
    for e in events:
        if e["type"] == "text":
            assert "text" not in e, "v2 text events carry `delta`, not `text`"
    joined = "".join(deltas)
    # A delta stream must not repeat its own prefix (the v1 accumulation bug).
    assert joined.count(deltas[0]) == 1 or len(deltas) == 1


def test_no_api_key_emits_a_notice_not_a_silent_answer(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    events = _events(monkeypatch)
    kinds = [e["kind"] for e in events if e["type"] == "notice"]
    assert "fake_model" in kinds, (
        "a reply produced without the model must say so explicitly"
    )


def test_done_result_has_english_keys_and_no_answer(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    done = [e for e in _events(monkeypatch) if e["type"] == "done"]
    assert len(done) == 1
    result = done[0]["result"]
    assert set(result) >= {"mode", "tools_used", "actions"}
    assert "answer" not in result, "the text already arrived as deltas"
    assert "respuesta" not in result


def test_model_failure_emits_an_error_event(monkeypatch):
    """A raised model call must surface as `error`, not as a fake answer."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")

    class _Boom:
        def __init__(self, *a, **k):
            raise RuntimeError("model exploded")

    monkeypatch.setattr(angela, "_build_client", _Boom, raising=False)
    events = _events(monkeypatch)
    errors = [e for e in events if e["type"] == "error"]
    assert errors, "a model failure must emit an error event"
    assert errors[0]["code"]
    assert "model exploded" not in json.dumps(events), (
        "raw exception text must not reach the client"
    )


def test_every_event_is_json_serialisable(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    for e in _events(monkeypatch):
        json.dumps(e, ensure_ascii=False, default=str)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && py -m pytest tests/test_chat_protocol.py -v`
Expected: FAIL — text events still carry `text`, no `notice` or `error` events exist.

- [ ] **Step 3: Extract a client factory so failures are testable**

In `backend/angela.py`, add near the other module helpers:

```python
def _build_client(api_key: str):
    """The Anthropic client, behind a seam so tests can make construction fail."""
    import anthropic
    return anthropic.Anthropic(api_key=api_key)
```

- [ ] **Step 4: Rewrite `stream_response`**

Replace the body of `stream_response` (keeping its signature) with:

```python
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        yield from _degraded_stream(message, "fake_model")
        return

    try:
        client = _build_client(api_key)
    except Exception as e:  # noqa: BLE001
        print(f"[angela/stream] client init failed: {e}", flush=True)
        yield {"type": "error", "code": "model_unavailable",
               "message": "No pude conectarme al modelo.", "retryable": True}
        yield {"type": "done", "result": {"mode": "error", "tools_used": [],
                                          "actions": [], "options": []}}
        return

    system, model, available_tools, messages = _prepare_turn(
        message, history, role, name, features, language)

    tools_used: list[str] = []
    actions: list[dict] = []
    try:
        for _ in range(MAX_TOOL_TURNS):
            with client.messages.stream(
                model=model, max_tokens=MAX_TOKENS, system=system,
                tools=available_tools, messages=messages,
            ) as stream:
                for event in stream:
                    if (event.type == "content_block_delta"
                            and event.delta.type == "text_delta"):
                        # v2: the DELTA travels, never the accumulation.
                        yield {"type": "text", "delta": event.delta.text}
                resp = stream.get_final_message()

            if resp.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": resp.content})
                tool_results = []
                for block in resp.content:
                    if block.type == "tool_use":
                        tools_used.append(block.name)
                        yield {"type": "tool_call", "id": block.id,
                               "name": block.name, "input": block.input or {}}
                        result, action = _run_tool(block.name, block.input or {})
                        if action:
                            actions.append(action)
                        yield {"type": "tool_result", "id": block.id,
                               "result": result}
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(_con_pesos(result), ensure_ascii=False),
                        })
                messages.append({"role": "user", "content": tool_results})
                continue

            yield {"type": "done", "result": {
                "mode": "claude", "tools_used": tools_used,
                "actions": actions, "options": []}}
            return

        yield {"type": "notice", "kind": "tool_loop_exhausted",
               "text": i18n.t("angela.muchas_vueltas", _idioma_actual())}
        yield {"type": "done", "result": {
            "mode": "claude", "tools_used": tools_used,
            "actions": actions, "options": []}}
    except Exception as e:  # noqa: BLE001
        # The technical detail is logged, never shipped: it leaks internals.
        print(f"[angela/stream] failed after tools={tools_used}: {e}", flush=True)
        yield {"type": "error", "code": "model_failed",
               "message": i18n.t("angela.error_modelo", _idioma_actual()),
               "retryable": True}
        yield {"type": "done", "result": {
            "mode": "error", "tools_used": tools_used,
            "actions": actions, "options": []}}
```

Then add the degraded-mode helper next to it:

```python
def _degraded_stream(message: str, kind: str):
    """A reply produced WITHOUT the model, always labelled as such.

    Phase 1.5 removes `_fallback` entirely (see the design doc, D9); until
    then the deterministic router still answers, but it can no longer pass
    itself off as Ángela: the `notice` says where the answer came from.
    """
    fb = _fallback(message)
    yield {"type": "notice", "kind": kind,
           "text": i18n.t("angela.sin_modelo", _idioma_actual())}
    if fb.get("answer"):
        yield {"type": "text", "delta": fb["answer"]}
    yield {"type": "done", "result": {
        "mode": fb.get("mode", "simulado"),
        "tools_used": fb.get("tools_used", []),
        "actions": fb.get("actions", []),
        "options": fb.get("options", [])}}
```

Delete the now-unused `import anthropic` guard block at the top of the old `stream_response`; `_build_client` owns it, and an `ImportError` there becomes the same `model_unavailable` error.

- [ ] **Step 5: Add the three i18n keys**

In `backend/i18n.py`, next to the existing `"angela.cap_alcanzado"` entry (~line 366), following the file's `"key": {"es": ..., "en": ...}` shape:

```python
    "angela.sin_modelo": {
        "es": "Esto lo saqué de tus datos, sin el modelo conectado.",
        "en": "I got this from your data, without the model connected.",
    },
    "angela.error_modelo": {
        "es": "No pude responder. Probá de nuevo en un momento.",
        "en": "I couldn't answer. Try again in a moment.",
    },
    "angela.muchas_vueltas": {
        "es": "Estoy dando muchas vueltas con esa consulta. "
              "¿Me la reformulás más simple?",
        "en": "I'm going in circles with that one. Could you put it more simply?",
    },
```

The ES string for `angela.muchas_vueltas` is the existing hardcoded `stuck_text`, moved into the catalogue.

- [ ] **Step 6: Make the cap a notice in `main.py`**

Replace `cap_event` (~2107-2111):

```python
    def cap_events(u) -> str:
        """The cap is a NOTICE plus a done — never a done alone.

        v1 emitted only `done`, so the frontend built zero content parts and
        rendered an empty bubble: the user hit their limit and was told
        nothing. See the design doc, D5.
        """
        return (
            line({"type": "notice", "kind": "cap",
                  "text": i18n.t("angela.cap_alcanzado", _lang(u))})
            + line({"type": "done", "result": {
                "mode": "cap", "tools_used": [], "actions": [], "options": []}})
        )
```

Update both call sites (the per-IP guard at ~2114-2116 and the per-session guard at ~2124-2125) to use `cap_events(u)`.

- [ ] **Step 7: Run the tests**

Run: `cd backend && py -m pytest tests/test_chat_protocol.py -v`
Expected: 5 tests PASS.

Run: `cd backend && py -m pytest -q`
Expected: no new failures.

- [ ] **Step 8: Restore seeds and commit**

```bash
git checkout -- data-demo/
git add backend/angela.py backend/main.py backend/i18n.py backend/tests/test_chat_protocol.py
git commit -m "Add error and notice events to the chat stream protocol"
```

---

### Task 5: `api.chatStream` throws typed errors

**Files:**
- Modify: `frontend/src/lib/api.js:354-363`

**Interfaces:**
- Consumes: `ChatStreamError`, `chatErrorCodeFromStatus` from Task 1.
- Produces: `api.chatStream(...)` rejecting with a `ChatStreamError` whose `code` is set, instead of `new Error("angela/stream → 401")`.

- [ ] **Step 1: Rewrite `chatStream`**

```js
  chatStream: async (mensaje, historial = [], extra = {}, { signal } = {}) => {
    let res;
    try {
      res = await fetch("/api/angela/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: mensaje, history: historial, ...extra }),
        signal,
      });
    } catch (e) {
      // An aborted fetch is a cancellation, not a failure.
      if (signal?.aborted) throw new ChatStreamError("aborted");
      throw new ChatStreamError("network", String(e?.message || e));
    }
    if (!res.ok) {
      throw new ChatStreamError(
        chatErrorCodeFromStatus(res.status),
        `angela/stream → ${res.status}`,
        res.status,
      );
    }
    if (!res.body) throw new ChatStreamError("stream", "response has no body");
    return res;
  },
```

Add the import at the top of `api.js`:

```js
import { ChatStreamError, chatErrorCodeFromStatus } from "./chat/errors";
```

- [ ] **Step 2: Verify the typecheck still passes**

Run: `cd frontend && npm run typecheck`
Expected: exits 0. (`api.js` is JS and unchecked, but the import must resolve.)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api.js
git commit -m "Throw typed ChatStreamError from api.chatStream"
```

---

### Task 6: The protocol v2 adapter

**Files:**
- Create: `frontend/src/lib/chat/protocol.ts`
- Create: `frontend/src/lib/chat/adapter.ts`
- Create: `frontend/src/lib/chat/adapter.test.ts`
- Delete: `frontend/src/lib/chatRuntime.js`
- Modify: `frontend/src/lib/chatRuntimeProvider.jsx` (import path)

**Interfaces:**
- Consumes: `ChatStreamError` (Task 1), protocol v2 events (Task 4), `api.chatStream` (Task 5).
- Produces: `createChatModelAdapter(options?: ChatAdapterOptions): ChatModelAdapter` from `src/lib/chat/adapter.ts`, where
  `ChatAdapterOptions = { fetchStream?: (message: string, history: ChatTurn[], extra: Record<string, unknown>, init: { signal: AbortSignal }) => Promise<Response> }`.
  The injectable `fetchStream` (defaulting to `api.chatStream`) is what makes this testable without module mocking.

Behaviour contract:
- `text` deltas **append** to the current text part.
- A `tool_call` closes the current text part, so later text starts a new one.
- `notice` events accumulate into `metadata.custom.notices`.
- `error` **throws** a `ChatStreamError` — never yields a text part. This is what lets `MessagePrimitive.Error` own the error state.
- An aborted run returns quietly.
- Defensive: if a run ends with no parts and no notices but `done.result.answer` exists, synthesize a text part, so a future `done`-without-text can never again produce a silent empty bubble.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/chat/adapter.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";
import { ChatStreamError } from "./errors";
import { createChatModelAdapter } from "./adapter";

/** A Response whose body streams the given chunks verbatim. */
function responseOf(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
  return new Response(body, { status: 200 });
}

function adapterOver(chunks: string[]) {
  return createChatModelAdapter({ fetchStream: async () => responseOf(chunks) });
}

const userMessage = {
  role: "user" as const,
  content: [{ type: "text" as const, text: "¿cuánta plata tengo parada?" }],
};

async function runAll(chunks: string[]) {
  const adapter = adapterOver(chunks);
  const results = [];
  for await (const r of adapter.run({
    messages: [userMessage],
    abortSignal: new AbortController().signal,
  } as never)) {
    results.push(r);
  }
  return results;
}

describe("text deltas", () => {
  it("appends deltas into a single text part", async () => {
    const results = await runAll([
      '{"type":"text","delta":"Tenés "}\n',
      '{"type":"text","delta":"$4.2M "}\n',
      '{"type":"text","delta":"parados."}\n',
      '{"type":"done","result":{"mode":"claude","tools_used":[],"actions":[]}}\n',
    ]);
    const final = results.at(-1)!;
    expect(final.content).toEqual([
      { type: "text", text: "Tenés $4.2M parados." },
    ]);
  });

  it("survives a chunk boundary splitting a line mid-JSON", async () => {
    const results = await runAll([
      '{"type":"text","delta":"Ten',
      'és $4.2M"}\n{"type":"done","result":{"mode":"claude","tools_used":[],"actions":[]}}\n',
    ]);
    expect(results.at(-1)!.content).toEqual([
      { type: "text", text: "Tenés $4.2M" },
    ]);
  });

  it("starts a new text part after a tool call", async () => {
    const results = await runAll([
      '{"type":"text","delta":"Voy a mirar."}\n',
      '{"type":"tool_call","id":"t1","name":"plata_en","input":{}}\n',
      '{"type":"tool_result","id":"t1","result":{"total":42}}\n',
      '{"type":"text","delta":"Listo."}\n',
      '{"type":"done","result":{"mode":"claude","tools_used":["plata_en"],"actions":[]}}\n',
    ]);
    const content = results.at(-1)!.content!;
    expect(content.map((p) => p.type)).toEqual(["text", "tool-call", "text"]);
    expect((content[0] as { text: string }).text).toBe("Voy a mirar.");
    expect((content[2] as { text: string }).text).toBe("Listo.");
  });
});

describe("tool calls", () => {
  it("attaches the result to the matching tool-call part", async () => {
    const results = await runAll([
      '{"type":"tool_call","id":"t1","name":"plata_en","input":{"categoria":"lacteos"}}\n',
      '{"type":"tool_result","id":"t1","result":{"total":42}}\n',
      '{"type":"done","result":{"mode":"claude","tools_used":["plata_en"],"actions":[]}}\n',
    ]);
    const part = results.at(-1)!.content![0] as {
      type: string; toolName: string; args: unknown; result: unknown;
    };
    expect(part.type).toBe("tool-call");
    expect(part.toolName).toBe("plata_en");
    expect(part.args).toEqual({ categoria: "lacteos" });
    expect(part.result).toEqual({ total: 42 });
  });
});

describe("notices", () => {
  it("renders the cap notice with no text events at all", async () => {
    const results = await runAll([
      '{"type":"notice","kind":"cap","text":"Llegaste al límite."}\n',
      '{"type":"done","result":{"mode":"cap","tools_used":[],"actions":[]}}\n',
    ]);
    const final = results.at(-1)!;
    expect(final.metadata?.custom?.notices).toEqual([
      { kind: "cap", text: "Llegaste al límite." },
    ]);
  });
});

describe("errors", () => {
  it("throws a ChatStreamError on an error event instead of faking a message", async () => {
    await expect(
      runAll([
        '{"type":"error","code":"model_failed","message":"No pude responder.","retryable":true}\n',
      ]),
    ).rejects.toBeInstanceOf(ChatStreamError);
  });

  it("keeps the server-supplied code", async () => {
    await expect(
      runAll(['{"type":"error","code":"rate_limit","message":"esperá","retryable":true}\n']),
    ).rejects.toMatchObject({ code: "rate_limit" });
  });

  it("returns quietly when aborted rather than surfacing an error", async () => {
    const controller = new AbortController();
    const adapter = createChatModelAdapter({
      fetchStream: async () => {
        controller.abort();
        throw new ChatStreamError("aborted");
      },
    });
    const results = [];
    for await (const r of adapter.run({
      messages: [userMessage],
      abortSignal: controller.signal,
    } as never)) {
      results.push(r);
    }
    expect(results).toEqual([]);
  });

  it("ignores an unparseable line rather than dying", async () => {
    const results = await runAll([
      "not json at all\n",
      '{"type":"text","delta":"ok"}\n',
      '{"type":"done","result":{"mode":"claude","tools_used":[],"actions":[]}}\n',
    ]);
    expect(results.at(-1)!.content).toEqual([{ type: "text", text: "ok" }]);
  });
});

describe("defensive fallback", () => {
  it("synthesizes a text part when a run produces no parts but an answer", async () => {
    const results = await runAll([
      '{"type":"done","result":{"mode":"cap","tools_used":[],"actions":[],"answer":"Sin contenido."}}\n',
    ]);
    expect(results.at(-1)!.content).toEqual([
      { type: "text", text: "Sin contenido." },
    ]);
  });
});

describe("request shape", () => {
  it("sends the newest message separately from the history", async () => {
    const fetchStream = vi.fn(async () =>
      responseOf(['{"type":"done","result":{"mode":"claude","tools_used":[],"actions":[]}}\n']),
    );
    const adapter = createChatModelAdapter({ fetchStream });
    for await (const _ of adapter.run({
      messages: [
        { role: "user", content: [{ type: "text", text: "hola" }] },
        { role: "assistant", content: [{ type: "text", text: "buenas" }] },
        { role: "user", content: [{ type: "text", text: "¿y la caja?" }] },
      ],
      abortSignal: new AbortController().signal,
    } as never)) { /* drain */ }

    expect(fetchStream).toHaveBeenCalledOnce();
    const [message, history] = fetchStream.mock.calls[0]!;
    expect(message).toBe("¿y la caja?");
    expect(history).toEqual([
      { role: "user", content: "hola" },
      { role: "assistant", content: "buenas" },
    ]);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm test`
Expected: FAIL — `Failed to resolve import "./adapter"`.

- [ ] **Step 3: Write `frontend/src/lib/chat/protocol.ts`**

```ts
/**
 * The `/api/angela/stream` wire protocol (v2), one JSON object per NDJSON line.
 * Mirrors backend/angela.py::stream_response — change both together.
 */
export type NoticeKind = "cap" | "tool_loop_exhausted" | "fake_model";

export type StreamEvent =
  | { type: "text"; delta: string }
  | { type: "tool_call"; id: string; name: string; input?: Record<string, unknown> }
  | { type: "tool_result"; id: string; result?: unknown }
  | { type: "notice"; kind: NoticeKind; text: string }
  | { type: "error"; code: string; message: string; retryable?: boolean }
  | { type: "done"; result?: DoneResult };

export type Notice = { kind: NoticeKind; text: string };

/** The final envelope. `answer` is legacy-defensive only: v2 sends text as deltas. */
export type DoneResult = {
  mode?: string;
  tools_used?: string[];
  actions?: Array<{ type: string } & Record<string, unknown>>;
  options?: Array<{ label: string; enviar: string }>;
  answer?: string;
};

/** Parse one NDJSON line. Returns null for blank or malformed lines. */
export function parseStreamLine(line: string): StreamEvent | null {
  const trimmed = line.trim();
  if (!trimmed) return null;
  try {
    const parsed = JSON.parse(trimmed) as StreamEvent;
    return parsed && typeof parsed.type === "string" ? parsed : null;
  } catch {
    // A truncated or corrupt line must not kill the stream.
    return null;
  }
}
```

- [ ] **Step 4: Write `frontend/src/lib/chat/adapter.ts`**

```ts
/**
 * assistant-ui ChatModelAdapter over the NDJSON stream at
 * /api/angela/stream (see backend/angela.py::stream_response).
 *
 * The Vercel AI SDK protocol is not used: the backend is plain Python and
 * owns the tool loop. This translates wire events into the append-only
 * ChatModelRunResult assistant-ui expects, on top of useLocalRuntime.
 *
 * It never yields a fake assistant message for a failure — it THROWS, so
 * MessagePrimitive.Error owns the error state and a retry is possible.
 */
import type {
  ChatModelAdapter,
  ChatModelRunOptions,
  ChatModelRunResult,
  ThreadAssistantMessagePart,
  ThreadMessage,
} from "@assistant-ui/react";
import { api } from "../api";
import { authStore } from "../auth";
import { ChatStreamError, type ChatErrorCode } from "./errors";
import { parseStreamLine, type DoneResult, type Notice } from "./protocol";

export type ChatTurn = { role: "user" | "assistant"; content: string };

export type FetchStream = (
  message: string,
  history: ChatTurn[],
  extra: Record<string, unknown>,
  init: { signal: AbortSignal },
) => Promise<Response>;

export type ChatAdapterOptions = {
  /** Injectable for tests; defaults to api.chatStream. */
  fetchStream?: FetchStream;
};

function textOf(content: readonly { type: string; text?: string }[] = []): string {
  return content
    .filter((p) => p.type === "text")
    .map((p) => p.text ?? "")
    .join("");
}

/**
 * The backend takes history as {role, content:string}[] with the newest
 * message separate.
 */
function splitMessages(messages: readonly ThreadMessage[]) {
  const last = messages[messages.length - 1];
  const message = textOf(last?.content as never);
  const history = messages
    .slice(0, -1)
    .filter((m) => m.role === "user" || m.role === "assistant")
    .map((m) => ({ role: m.role as "user" | "assistant", content: textOf(m.content as never) }))
    .filter((m) => m.content);
  return { message, history };
}

const KNOWN_CODES: ReadonlySet<string> = new Set([
  "session_expired", "rate_limit", "server", "network", "stream", "aborted",
]);

/** Server codes are richer than the client's closed set; map the rest to `server`. */
function toClientCode(code: string): ChatErrorCode {
  return (KNOWN_CODES.has(code) ? code : "server") as ChatErrorCode;
}

export function createChatModelAdapter(
  { fetchStream }: ChatAdapterOptions = {},
): ChatModelAdapter {
  const doFetch: FetchStream = fetchStream ?? ((m, h, extra, init) =>
    api.chatStream(m, h, extra, init));

  return {
    async *run({ messages, abortSignal }: ChatModelRunOptions) {
      const { message, history } = splitMessages(messages);
      if (!message) return;

      const token = authStore.getSnapshot()?.token;

      let res: Response;
      try {
        res = await doFetch(message, history, { token }, { signal: abortSignal });
      } catch (e) {
        if (abortSignal.aborted) return;
        throw e instanceof ChatStreamError
          ? e
          : new ChatStreamError("network", String((e as Error)?.message ?? e));
      }

      const parts: ThreadAssistantMessagePart[] = [];
      const notices: Notice[] = [];
      const toolIndexById = new Map<string, number>();
      let textIndex: number | null = null;
      let done: DoneResult | null = null;

      const snapshot = (): ChatModelRunResult => ({
        content: parts.map((p) => ({ ...p })),
        metadata: {
          custom: {
            ...(done ?? {}),
            ...(notices.length ? { notices: [...notices] } : {}),
          },
        },
      });

      /** Returns a ChatStreamError to throw, or null to keep going. */
      const apply = (line: string): ChatStreamError | null => {
        const ev = parseStreamLine(line);
        if (!ev) return null;

        if (ev.type === "text") {
          if (textIndex == null) {
            parts.push({ type: "text", text: ev.delta });
            textIndex = parts.length - 1;
          } else {
            const current = parts[textIndex] as { type: "text"; text: string };
            parts[textIndex] = { type: "text", text: current.text + ev.delta };
          }
        } else if (ev.type === "tool_call") {
          textIndex = null; // later text belongs to a new turn
          parts.push({
            type: "tool-call",
            toolCallId: ev.id,
            toolName: ev.name,
            args: ev.input ?? {},
            argsText: JSON.stringify(ev.input ?? {}),
          } as ThreadAssistantMessagePart);
          toolIndexById.set(ev.id, parts.length - 1);
        } else if (ev.type === "tool_result") {
          const i = toolIndexById.get(ev.id);
          if (i != null) parts[i] = { ...parts[i], result: ev.result } as ThreadAssistantMessagePart;
        } else if (ev.type === "notice") {
          textIndex = null; // a notice closes the current text part
          notices.push({ kind: ev.kind, text: ev.text });
        } else if (ev.type === "error") {
          return new ChatStreamError(toClientCode(ev.code), ev.message);
        } else if (ev.type === "done") {
          done = ev.result ?? {};
        }
        return null;
      };

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        let chunk: ReadableStreamReadResult<Uint8Array>;
        try {
          chunk = await reader.read();
        } catch (e) {
          if (abortSignal.aborted) return;
          throw new ChatStreamError("stream", String((e as Error)?.message ?? e));
        }
        if (chunk.done) break;

        buffer += decoder.decode(chunk.value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? ""; // the tail may be half a line
        for (const line of lines) {
          const err = apply(line);
          if (err) throw err;
        }
        yield snapshot();
      }

      if (buffer.trim()) {
        const err = apply(buffer);
        if (err) throw err;
      }

      // Defensive: a `done` with neither text nor notices used to render an
      // empty bubble (the v1 cap bug). Never let that happen silently again.
      if (parts.length === 0 && notices.length === 0 && done?.answer) {
        parts.push({ type: "text", text: done.answer });
      }

      yield snapshot();
    },
  };
}
```

- [ ] **Step 5: Run the tests**

Run: `cd frontend && npm test`
Expected: all 12 adapter tests PASS, plus Task 1's error tests.

- [ ] **Step 6: Point the provider at the new adapter and delete the old one**

In `frontend/src/lib/chatRuntimeProvider.jsx`, change the import:

```js
import { createChatModelAdapter } from "./chat/adapter";
```

and simplify the memo (the `getCurrentView` option is gone — it was dead wiring returning `null`, and real run-context arrives in Phase 2):

```js
  const modelAdapter = useMemo(() => createChatModelAdapter(), []);
```

Then delete the old file:

```bash
git rm frontend/src/lib/chatRuntime.js
```

- [ ] **Step 7: Verify nothing still imports the old module**

Run: `cd frontend && grep -rn "chatRuntime\"" src/ ; grep -rn "from \"./chatRuntime\"\|lib/chatRuntime" src/`
Expected: no output.

Run: `cd frontend && npm run typecheck && npm test`
Expected: both pass.

- [ ] **Step 8: Commit**

```bash
git add -A frontend/src/lib
git commit -m "Replace the chat adapter with a typed protocol v2 implementation"
```

---

### Task 7: Tool presenter registry and shape-based fallback

**Files:**
- Create: `frontend/src/components/assistant/tools/types.ts`
- Create: `frontend/src/components/assistant/tools/labels.ts`
- Create: `frontend/src/components/assistant/tools/labels.test.ts`
- Create: `frontend/src/components/assistant/tools/Fallback.tsx`
- Create: `frontend/src/components/assistant/tools/registry.ts`
- Create: `frontend/src/components/assistant/tools/registry.test.ts`
- Modify: `frontend/src/lib/locales/es.js`, `frontend/src/lib/locales/en.js`

**Interfaces:**
- Consumes: `ToolName` (Task 2), `useT`/`t` from `lib/i18n`.
- Produces:
  - `ToolPresenter`, `ToolLabels`, `ToolChrome` from `tools/types.ts`
  - `toolLabels(name: string): ToolLabels` from `tools/labels.ts`
  - `TOOL_PRESENTERS: Record<string, ToolPresenter>`, `presenterFor(name: string): ToolPresenter | undefined`, and `toolComponentsByName(): Record<string, ToolCallMessagePartComponent>` from `tools/registry.ts`
  - `ToolFallback` (default export of `Fallback.tsx`)

**This task deliberately does not improve any rendering.** It ports the existing shape dispatcher verbatim and ships an *empty* `TOOL_PRESENTERS`. The point is that the seam exists and `Fallback` still covers all 50 tools. Real presenters (charts, tables, KPI tiles) are Phase 3.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/assistant/tools/labels.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { toolLabelKeys, humanizeToolName } from "./labels";

describe("humanizeToolName", () => {
  it("turns a snake_case tool name into readable words", () => {
    expect(humanizeToolName("top_inmovilizado")).toBe("top inmovilizado");
    expect(humanizeToolName("plata_en")).toBe("plata en");
  });

  it("leaves a single word alone", () => {
    expect(humanizeToolName("recordar")).toBe("recordar");
  });
});

describe("toolLabelKeys", () => {
  it("derives i18n keys from the tool name", () => {
    expect(toolLabelKeys("consultar_serie")).toEqual({
      running: "tool.consultar_serie.running",
      done: "tool.consultar_serie.done",
    });
  });
});
```

Create `frontend/src/components/assistant/tools/registry.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { TOOL_PRESENTERS, presenterFor, toolComponentsByName } from "./registry";

describe("the registry", () => {
  it("returns undefined for a tool with no presenter", () => {
    expect(presenterFor("a_tool_that_does_not_exist")).toBeUndefined();
  });

  it("exposes every presenter as a by_name component", () => {
    const byName = toolComponentsByName();
    expect(Object.keys(byName).sort()).toEqual(Object.keys(TOOL_PRESENTERS).sort());
  });

  it("only registers presenters that declare labels", () => {
    for (const [name, presenter] of Object.entries(TOOL_PRESENTERS)) {
      expect(presenter.labels, `${name} has no labels`).toBeTruthy();
    }
  });

  it("keys every presenter by a snake_case tool name", () => {
    // Exact matching against angela.py's tool names is enforced at COMPILE
    // time by typing the registry as Partial<Record<ToolName, ...>> — a typo
    // fails `npm run typecheck`, which beats any runtime assertion. This is
    // the cheap shape guard on top of it.
    for (const name of Object.keys(TOOL_PRESENTERS)) {
      expect(name).toMatch(/^[a-z][a-z0-9_]*$/);
    }
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npm test`
Expected: FAIL — `Failed to resolve import "./labels"` and `"./registry"`.

- [ ] **Step 3: Write `tools/types.ts`**

```tsx
import type { ToolCallMessagePartProps } from "@assistant-ui/react";
import type { ToolArgs } from "../../../lib/chat/toolArgs.generated";

/** i18n KEYS (never literal copy) for a tool's two states. */
export type ToolLabels = { running: string; done: string };

/**
 * "card" wraps the render in the standard tool card; "bare" lets a renderer
 * own its full width (charts and tables in Phase 3).
 */
export type ToolChrome = "card" | "bare";

export type ToolRenderProps<TName extends keyof ToolArgs = keyof ToolArgs> =
  Omit<ToolCallMessagePartProps, "args"> & { args: ToolArgs[TName] };

/**
 * How ONE tool call is presented. A presenter is always an OVERRIDE: a tool
 * without one falls through to the shape-based Fallback, so a new Python tool
 * gets a usable UI with zero frontend work (design doc D1).
 *
 * Presenters must be PURE functions of (args, result). Side effects —
 * navigation, widget creation, preferences — belong in ChatPanel's action
 * applier, never here (D2.3).
 */
export type ToolPresenter<TName extends keyof ToolArgs = keyof ToolArgs> = {
  labels: ToolLabels;
  render?: (props: ToolRenderProps<TName>) => React.ReactNode;
  chrome?: ToolChrome;
};
```

- [ ] **Step 4: Write `tools/labels.ts`**

```ts
import { t } from "../../../lib/i18n";
import type { ToolLabels } from "./types";

/** "top_inmovilizado" -> "top inmovilizado". The last-resort label. */
export function humanizeToolName(name: string): string {
  return name.replaceAll("_", " ");
}

/** The i18n keys for a tool, derived from its name. */
export function toolLabelKeys(name: string): ToolLabels {
  return { running: `tool.${name}.running`, done: `tool.${name}.done` };
}

/**
 * Resolved, display-ready labels. `t()` falls back to ES and then to the key
 * itself, so an unregistered tool would show "tool.foo.running" — we detect
 * that and humanize the name instead. No tool ever renders a raw key.
 */
export function toolLabels(name: string): ToolLabels {
  const keys = toolLabelKeys(name);
  const running = t(keys.running);
  const done = t(keys.done);
  const readable = humanizeToolName(name);
  return {
    running: running === keys.running ? `${readable}…` : running,
    done: done === keys.done ? readable : done,
  };
}
```

- [ ] **Step 5: Add the i18n keys**

The 23 tools that had entries in the old `ToolCallCard.LABELS` map get real copy; the other 27 rely on the humanized fallback until Phase 3 gives them presenters. Add to `frontend/src/lib/locales/es.js` (keeping the file's comment-grouped style, in a new `--- tools de Ángela ---` group), and the English equivalents to `en.js` in the same commit:

```js
  // --- tools de Ángela (label mientras corre / una vez terminada) ---
  "tool.resumen_negocio.running": "Mirando el resumen del negocio…",
  "tool.resumen_negocio.done": "Miró el resumen del negocio",
  "tool.plata_en.running": "Calculando la plata inmovilizada…",
  "tool.plata_en.done": "Calculó la plata inmovilizada",
  "tool.buscar_productos.running": "Buscando productos…",
  "tool.buscar_productos.done": "Buscó productos",
  "tool.top_inmovilizado.running": "Buscando dónde está la plata parada…",
  "tool.top_inmovilizado.done": "Buscó dónde está la plata parada",
  "tool.listar_grupo.running": "Listando el grupo…",
  "tool.listar_grupo.done": "Listó el grupo",
  "tool.navegar_a.running": "Llevándote a la sección…",
  "tool.navegar_a.done": "Te llevó a la sección",
  "tool.consultar_serie.running": "Consultando los datos…",
  "tool.consultar_serie.done": "Consultó los datos",
  "tool.cuentas_corrientes.running": "Revisando cuentas corrientes…",
  "tool.cuentas_corrientes.done": "Revisó cuentas corrientes",
  "tool.consultar_deposito.running": "Revisando el depósito…",
  "tool.consultar_deposito.done": "Revisó el depósito",
  "tool.consultar_envios.running": "Revisando envíos…",
  "tool.consultar_envios.done": "Revisó envíos",
  "tool.consultar_cruces.running": "Cruzando comprobantes…",
  "tool.consultar_cruces.done": "Cruzó comprobantes",
  "tool.consultar_evolucion.running": "Mirando la evolución…",
  "tool.consultar_evolucion.done": "Miró la evolución",
  "tool.estado_caja.running": "Mirando la caja…",
  "tool.estado_caja.done": "Miró la caja",
  "tool.crear_widget.running": "Armando un widget para tu panel…",
  "tool.crear_widget.done": "Armó un widget para tu panel",
  "tool.crear_recordatorio.running": "Anotando el recordatorio…",
  "tool.crear_recordatorio.done": "Anotó el recordatorio",
  "tool.mis_recordatorios.running": "Buscando tus recordatorios…",
  "tool.mis_recordatorios.done": "Buscó tus recordatorios",
  "tool.crear_objetivo.running": "Creando el objetivo…",
  "tool.crear_objetivo.done": "Creó el objetivo",
  "tool.proponer_correccion.running": "Calculando el impacto de la corrección…",
  "tool.proponer_correccion.done": "Calculó el impacto de la corrección",
  "tool.aplicar_correccion_en_lote.running": "Aplicando la corrección…",
  "tool.aplicar_correccion_en_lote.done": "Aplicó la corrección",
  "tool.generar_documento.running": "Generando el documento…",
  "tool.generar_documento.done": "Generó el documento",
  "tool.consultar_manual.running": "Revisando el manual…",
  "tool.consultar_manual.done": "Revisó el manual",
```

- [ ] **Step 6: Write `tools/Fallback.tsx`**

Port the shape dispatcher out of `ToolCallCard.jsx` **unchanged in behaviour**: `navegar_a` gets its one-line confirmation; a result with `items`/`recordatorios`/an array renders as `ResultTable`; a `series[].top` renders as `MiniChart`; everything else is the key/value grid. Keep `ResultTable` and `MiniChart` as the existing `.jsx` imports — they are Phase 3's problem.

```tsx
import type { ToolCallMessagePartProps } from "@assistant-ui/react";
import ResultTable from "../ResultTable";
import MiniChart from "../MiniChart";
import { peso, num } from "../../../lib/format";

const MONEY_KEY = /monto|inmovilizado|precio|costo|saldo|total|plata|deuda/i;

/** A "small" object (a few scalar keys) as a compact key/value grid. */
function GenericResult({ result }: { result: Record<string, unknown> }) {
  const entries = Object.entries(result).filter(
    ([, v]) =>
      v == null || typeof v === "string" || typeof v === "number" || typeof v === "boolean",
  );
  if (entries.length === 0) return null;
  return (
    <dl className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1 text-[0.8rem]">
      {entries.slice(0, 8).map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="capitalize text-tinta-suave">{k.replaceAll("_", " ")}</dt>
          <dd className="tabular-nums text-tinta">
            {typeof v === "number"
              ? MONEY_KEY.test(k)
                ? peso(v)
                : num(v)
              : String(v ?? "—")}
          </dd>
        </div>
      ))}
    </dl>
  );
}

/**
 * The DEFAULT tool renderer: dispatches on the SHAPE of the result, not on the
 * tool name, so any of angela.py's 50 tools gets a reasonable UI without a
 * presenter. A presenter in the registry is an override of this, never a
 * prerequisite for a tool to render (design doc D1) — do not "simplify" this
 * away by requiring one per tool.
 */
export default function ToolFallback({ toolName, result }: ToolCallMessagePartProps) {
  if (result == null) return null;

  if (typeof result !== "object" || Array.isArray(result)) {
    if (Array.isArray(result) && result.length && typeof result[0] === "object") {
      return <ResultTable rows={result} />;
    }
    return <p className="mt-1 text-[0.82rem] text-tinta">{String(result)}</p>;
  }

  const r = result as Record<string, unknown>;

  if (toolName === "navegar_a" && r.navegado_a) {
    return (
      <p className="mt-1 text-[0.82rem] text-tinta-suave">
        → te llevé a <b className="text-tinta">{String(r.navegado_a)}</b>
      </p>
    );
  }

  if (r.error || r.motivo) {
    return (
      <p className="mt-1 text-[0.82rem] text-rojo-hondo">
        {String(r.error || r.motivo)}
      </p>
    );
  }

  const items = Array.isArray(r.items)
    ? r.items
    : Array.isArray(r.recordatorios)
      ? r.recordatorios
      : null;
  if (items && items.length && typeof items[0] === "object") {
    return (
      <>
        {r.total_inmovilizado_listado != null && (
          <p className="mt-1 text-[0.82rem] text-tinta">
            Total: <b>{peso(r.total_inmovilizado_listado as number)}</b>
          </p>
        )}
        <ResultTable rows={items} />
      </>
    );
  }

  if (Array.isArray(r.series)) {
    const withTop = (r.series as Array<{ top?: unknown[] }>).find(
      (s) => Array.isArray(s.top) && s.top.length,
    );
    if (withTop) return <MiniChart points={withTop.top} />;
  }

  return <GenericResult result={r} />;
}
```

Because `ResultTable`, `MiniChart` and `format` are untyped `.jsx`/`.js`, add a declarations file so `strict` mode is satisfied without converting them — create `frontend/src/types/untyped-modules.d.ts`:

```ts
// Chat-layer TS imports of not-yet-typed JSX/JS modules. `strict` implies
// noImplicitAny, so every module a .tsx file imports needs a declaration.
// Delete each entry as its module is converted to TS (ResultTable and
// MiniChart in Phase 3).
import type { ReactNode } from "react";

declare module "*/ResultTable" {
  const C: (props: { rows: unknown[]; limit?: number }) => ReactNode;
  export default C;
}
declare module "*/MiniChart" {
  const C: (props: { points: unknown[]; format?: string }) => ReactNode;
  export default C;
}
declare module "*/AngelaMark" {
  const C: (props: {
    size?: number; pulse?: boolean; estado?: string;
  }) => ReactNode;
  export default C;
}
declare module "*/PlanChecklist" {
  const C: (props: {
    plan: { pasos?: unknown[]; resumen?: string };
    onExecutingChange?: (running: boolean) => void;
  }) => ReactNode;
  export default C;
}
declare module "*/DocCard" {
  const C: (props: { documento: unknown; t: (k: string) => string }) => ReactNode;
  export default C;
}
declare module "*/MemoryChips" {
  const C: (props: {
    chips: Array<{ id: string; pid: string; text: string; change: string }>;
    onForget: (chip: { id: string; pid: string }) => void;
  }) => ReactNode;
  export default C;
}
declare module "*/lib/format" {
  export function peso(n: number): string;
  export function num(n: number): string;
  export function fecha(d: unknown): string;
}
declare module "*/lib/i18n" {
  export function t(key: string, params?: Record<string, unknown>): string;
  export function useT(): (key: string, params?: Record<string, unknown>) => string;
}
declare module "*/lib/toastStore" {
  export function toast(message: string, kind?: string): void;
}
declare module "*/lib/api" {
  export const api: Record<string, (...args: never[]) => Promise<unknown>>;
}
declare module "*/lib/auth" {
  export const authStore: {
    getSnapshot(): { token?: string; usuario?: Record<string, unknown> } | null;
    logout(options?: { manual?: boolean }): void;
    tiene(feature: string): boolean;
    refresh(): Promise<void>;
  };
}
```

`api` is typed loosely on purpose: it has ~60 methods and pinning them here would duplicate `api.js`. `adapter.ts` (Task 6) calls `api.chatStream` through the injectable `fetchStream` seam, so it never depends on this loose type.

- [ ] **Step 7: Write `tools/registry.ts`**

```ts
/**
 * THE one place a tool's custom presentation is registered.
 *
 * To give a tool a custom look: add a module in this directory exporting a
 * ToolPresenter, then add one line here. Do NOT add a branch to ChatThread
 * (design doc D1) — it must stay free of per-tool logic.
 *
 * An empty entry set is CORRECT and complete: every tool renders through the
 * shape-based Fallback until a presenter overrides it. Phase 3 fills this in
 * with the series, table and KPI-tile presenters.
 */
import type { ToolCallMessagePartComponent } from "@assistant-ui/react";
import type { ToolName } from "../../../lib/chat/toolArgs.generated";
import type { ToolPresenter } from "./types";

/**
 * Typed as Partial<Record<ToolName, ...>> on purpose: a key that is not a real
 * tool name in angela.py fails `npm run typecheck`. Without that, a typo would
 * simply mean by_name never fires and the tool silently renders through the
 * Fallback — a bug nobody notices.
 */
export const TOOL_PRESENTERS: Partial<Record<ToolName, ToolPresenter>> = {
  // Phase 3: consultar_serie, cuentas_corrientes, estado_caja, ...
};

export function presenterFor(name: string): ToolPresenter | undefined {
  return TOOL_PRESENTERS[name as ToolName];
}

/**
 * The registry as MessagePrimitive.Parts's `tools.by_name` map. Derived, so
 * adding a presenter never means touching the Thread.
 */
export function toolComponentsByName(): Record<string, ToolCallMessagePartComponent> {
  const out: Record<string, ToolCallMessagePartComponent> = {};
  for (const [name, presenter] of Object.entries(TOOL_PRESENTERS)) {
    if (presenter.render) {
      out[name] = presenter.render as unknown as ToolCallMessagePartComponent;
    }
  }
  return out;
}
```

- [ ] **Step 8: Run the tests and the typecheck**

Run: `cd frontend && npm test && npm run typecheck`
Expected: labels (3) and registry (4) tests PASS; typecheck exits 0.

Sanity-check the compile-time guard that replaces a runtime name test: temporarily add `consultar_serieX: { labels: { running: "x", done: "x" } },` to `TOOL_PRESENTERS` and run `npm run typecheck`. Expected: it FAILS, naming the bad key. Remove it again.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/assistant/tools frontend/src/types frontend/src/lib/locales
git commit -m "Add the tool presenter registry over the shape-based fallback"
```

---

### Task 8: Wire `ChatThread` to the registry

**Files:**
- Modify → rename: `frontend/src/components/assistant/ChatThread.jsx` → `ChatThread.tsx`
- Modify → rename: `frontend/src/components/assistant/ToolCallCard.jsx` → `ToolCallCard.tsx`

**Interfaces:**
- Consumes: `toolComponentsByName`, `presenterFor` (Task 7), `toolLabels` (Task 7), notices in `metadata.custom.notices` (Task 6).
- Produces: `ChatThread` rendering tool parts through the registry, and notices as their own block. Same default export signature: `ChatThread({ onExecutingChange, composerLeading })`.

- [ ] **Step 1: Rewrite `ToolCallCard` as the card shell**

It keeps the running/done chrome and delegates the body to the presenter's `render` or to `ToolFallback`. The 23-entry inline Spanish `LABELS` map is deleted — labels now come from `toolLabels()` (Task 7).

```tsx
import { Loader2, Wrench } from "lucide-react";
import type { ToolCallMessagePartProps } from "@assistant-ui/react";
import ToolFallback from "./tools/Fallback";
import { presenterFor } from "./tools/registry";
import { toolLabels } from "./tools/labels";

/**
 * The card for ONE tool call: the label while it runs, the rendered result
 * once it arrives. The body comes from the tool's presenter if it has one,
 * otherwise from the shape-based Fallback (design doc D1).
 */
export default function ToolCallCard(props: ToolCallMessagePartProps) {
  const { toolName, status, result } = props;
  const isRunning = status?.type === "running" && result === undefined;
  const labels = toolLabels(toolName);
  const presenter = presenterFor(toolName);
  const Body = presenter?.render;

  if (presenter?.chrome === "bare" && Body) {
    return <>{Body(props as never)}</>;
  }

  return (
    <div className="my-1.5 rounded-xl border border-linea/70 bg-papel/50 px-3 py-2">
      <div className="flex items-center gap-2 text-[0.8rem] font-medium text-tinta-suave">
        {isRunning ? (
          <Loader2
            size={14}
            className="shrink-0 animate-spin text-violeta motion-reduce:animate-none"
          />
        ) : (
          <Wrench size={14} className="shrink-0 text-violeta" />
        )}
        <span>{isRunning ? labels.running : labels.done}</span>
      </div>
      {!isRunning && (Body ? Body(props as never) : <ToolFallback {...props} />)}
    </div>
  );
}
```

- [ ] **Step 2: Add prop types to the renamed `ChatThread.tsx`**

`strict` implies `noImplicitAny`, so the three destructured-prop components in this file must be typed or the rename fails to compile:

```tsx
type ExecutingHandler = (running: boolean) => void;

function MessageExtras({ onExecutingChange }: { onExecutingChange?: ExecutingHandler }) { /* … */ }

function Composer({ leading }: { leading?: React.ReactNode }) { /* … */ }

export default function ChatThread({
  onExecutingChange,
  composerLeading,
}: {
  onExecutingChange?: ExecutingHandler;
  composerLeading?: React.ReactNode;
}) { /* … */ }
```

Also type the two local callbacks that lose inference: in `MessageExtras`, the `useAuiState` selector's `p` is `unknown` under strict mode, so annotate the filter/map chain:

```tsx
  const propuestas = useAuiState((s) =>
    ((s.message.content ?? []) as Array<{
      type: string;
      toolName?: string;
      toolCallId?: string;
      result?: { ok?: boolean; pieza?: { id: string; texto: string } };
    }>)
      .filter((p) => p.type === "tool-call" && p.toolName === "proponer_conocimiento" && p.result?.ok)
      .map((p) => ({
        id: p.toolCallId!,
        pid: p.result!.pieza!.id,
        text: p.result!.pieza!.texto,
        change: "added",
      })),
  ) ?? [];
```

and the `onForget` handler's parameter as `{ id: string; pid: string }`.

- [ ] **Step 3: Replace the `if` chain in `ChatThread` with the registry**

In `ChatThread.tsx`, the `AssistantMessage` body becomes a `components` prop instead of a children render function. `proponer_conocimiento` keeps being suppressed here (it renders as a `MemoryChips` pill in `MessageExtras`, and showing it twice was the reason for the old special case) — but as a one-line presenter-style suppression, not a branch in the render function:

```tsx
import { MessagePrimitive } from "@assistant-ui/react";
import ToolCallCard from "./ToolCallCard";
import { toolComponentsByName } from "./tools/registry";

/**
 * proponer_conocimiento is shown as a MemoryChips pill by MessageExtras, so
 * the raw tool call renders as nothing here. This is a PRESENTATION choice
 * for one tool and therefore belongs in the by_name map, not in a branch.
 */
const SUPPRESSED = { proponer_conocimiento: () => null };

const TOOL_COMPONENTS = {
  Fallback: ToolCallCard,
  by_name: { ...SUPPRESSED, ...toolComponentsByName() },
};
```

and inside `AssistantMessage`:

```tsx
          <MessagePrimitive.Parts
            components={{
              Text: ({ text }: { text: string }) => <span>{text}</span>,
              tools: TOOL_COMPONENTS,
            }}
          />
```

- [ ] **Step 4: Render notices**

Notices are not content parts (assistant-ui's part types are a closed set), so they travel in `metadata.custom.notices` and render in the message shell. Add to `ChatThread.tsx`:

```tsx
import { AlertCircle } from "lucide-react";
import { useAuiState } from "@assistant-ui/react";
import type { Notice } from "../../lib/chat/protocol";

/**
 * A degraded-mode explanation (message cap, no model, tool loop exhausted).
 * Visually distinct on purpose: the v1 bug was a reply produced WITHOUT the
 * model being indistinguishable from a real one (design doc D5/D9).
 */
function MessageNotices() {
  const notices = (useAuiState((s) => s.message.metadata?.custom?.notices) ?? []) as Notice[];
  if (notices.length === 0) return null;
  return (
    <div className="mt-2 space-y-1.5">
      {notices.map((n, i) => (
        <p
          key={i}
          className="flex items-start gap-2 rounded-xl border border-oro/40 bg-oro/5 px-2.5 py-1.5 text-[0.78rem] leading-snug text-oro-tinta"
        >
          <AlertCircle size={14} className="mt-0.5 shrink-0" />
          <span>{n.text}</span>
        </p>
      ))}
    </div>
  );
}
```

Render `<MessageNotices />` inside the assistant bubble, immediately before `<MessageExtras … />`. Then widen the empty-bubble guard so a notice-only message still renders: change

```tsx
  const noContentYet = useAuiState(
    (s) => s.message.status?.type === "running" && (s.message.content?.length ?? 0) === 0
  );
```

to also require that no notices have arrived:

```tsx
  const noContentYet = useAuiState(
    (s) =>
      s.message.status?.type === "running" &&
      (s.message.content?.length ?? 0) === 0 &&
      ((s.message.metadata?.custom?.notices as Notice[] | undefined)?.length ?? 0) === 0,
  );
```

- [ ] **Step 5: Guard the animation for reduced motion**

In `ThinkingDots` (still in this file until Task 10 replaces it), add `motion-reduce:animate-none` to the bouncing dot's className.

- [ ] **Step 6: Verify the `if` chain is gone**

Run: `cd frontend && grep -n "part.type === \"tool-call\"\|part.toolName ===" src/components/assistant/ChatThread.tsx`
Expected: no output — per-tool branching must not exist in the Thread.

- [ ] **Step 7: Typecheck and run the app**

Run: `cd frontend && npm run typecheck && npm test`
Expected: both pass.

Then start both services and exercise the chat by hand — this is the first task whose result is visible, and the automated tests here are all pure-logic:

```bash
cd backend && POLPILOT_DEMO_TODAY=2026-07-07 py -m uvicorn main:app --port 8000
cd frontend && npm run dev
```

Log in as `aldo` / `demo-password`, open Ángela, and confirm:
- a question that calls a tool shows the tool card with the running label, then the done label plus the same result rendering as before;
- `proponer_conocimiento` still appears only as a memory chip, not twice.

- [ ] **Step 8: Commit**

```bash
git add -A frontend/src/components/assistant
git commit -m "Render tool calls through the registry instead of a branch chain"
```

---

### Task 9: Error state with retry

**Files:**
- Create: `frontend/src/components/assistant/ErrorState.tsx`
- Modify: `frontend/src/components/assistant/ChatThread.tsx`
- Modify: `frontend/src/lib/locales/es.js`, `en.js`

**Interfaces:**
- Consumes: `ChatErrorCode` (Task 1), the thrown `ChatStreamError` (Task 6), `authStore` from `lib/auth`.
- Produces: `ErrorState` rendered inside `MessagePrimitive.Error`, with a retry that calls `aui.message.reload()`.

- [ ] **Step 1: Add the i18n keys**

To `es.js` (and the English equivalents to `en.js`):

```js
  // --- errores del chat ---
  "chat.error.reintentar": "Probar de nuevo",
  "chat.error.reintentando": "Probando…",
  "chat.error.rate_limit.titulo": "Demasiadas consultas",
  "chat.error.rate_limit.detalle": "El modelo está limitado por ahora. Probá de nuevo en un momento.",
  "chat.error.session_expired.titulo": "Se cerró tu sesión",
  "chat.error.session_expired.detalle": "Volvé a entrar para seguir hablando con Ángela.",
  "chat.error.session_expired.accion": "Volver a entrar",
  "chat.error.network.titulo": "Sin conexión",
  "chat.error.network.detalle": "No llego al servidor. Revisá tu conexión y probá de nuevo.",
  "chat.error.server.titulo": "No pude responder",
  "chat.error.server.detalle": "Se cortó la consulta. Probá de nuevo en un momento.",
  "chat.error.stream.titulo": "Se cortó la respuesta",
  "chat.error.stream.detalle": "La respuesta se interrumpió a mitad de camino. Probá de nuevo.",
```

- [ ] **Step 2: Write `ErrorState.tsx`**

```tsx
import { AlertTriangle, RotateCw } from "lucide-react";
import { useAui, useAuiState } from "@assistant-ui/react";
import { useT } from "../../lib/i18n";
import { authStore } from "../../lib/auth";
import type { ChatErrorCode } from "../../lib/chat/errors";

const CODES: readonly ChatErrorCode[] = [
  "session_expired", "rate_limit", "network", "server", "stream",
];

/** The failure's code, read off the message's incomplete status. */
function useErrorCode(): ChatErrorCode {
  return useAuiState((s) => {
    const status = s.message.status;
    if (status?.type !== "incomplete" || status.reason !== "error") return "server";
    const err = status.error as { code?: string } | string | undefined;
    const code = typeof err === "object" && err !== null ? err.code : undefined;
    return (CODES as readonly string[]).includes(code ?? "")
      ? (code as ChatErrorCode)
      : "server";
  });
}

/**
 * What the user sees when a run fails. Before this existed, a pre-stream
 * failure was yielded as a normal assistant message ("try again in a moment")
 * with no retry, and a mid-stream failure rendered nothing at all — the
 * bubble just stopped (design doc D5).
 */
export default function ErrorState() {
  const t = useT();
  const aui = useAui();
  const code = useErrorCode();
  const retrying = useAuiState((s) => s.message.status?.type === "running");

  // An expired session cannot be fixed by retrying the same request.
  const isSession = code === "session_expired";

  return (
    <div
      role="alert"
      className="mt-2 rounded-2xl border border-rojo/30 bg-rojo/5 px-3.5 py-2.5"
    >
      <p className="flex items-center gap-2 text-[0.86rem] font-semibold text-rojo-hondo">
        <AlertTriangle size={15} className="shrink-0" />
        {t(`chat.error.${code}.titulo`)}
      </p>
      <p className="mt-1 text-[0.8rem] leading-snug text-tinta-suave">
        {t(`chat.error.${code}.detalle`)}
      </p>
      <button
        type="button"
        disabled={retrying}
        onClick={() =>
          isSession ? authStore.logout({ manual: true }) : aui.message.reload()
        }
        className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-rojo/40 px-3 py-1.5 text-[0.8rem] font-semibold text-rojo-hondo transition-colors hover:bg-rojo/10 disabled:opacity-50"
      >
        {!isSession && (
          <RotateCw
            size={13}
            className={retrying ? "animate-spin motion-reduce:animate-none" : undefined}
          />
        )}
        {isSession
          ? t("chat.error.session_expired.accion")
          : retrying
            ? t("chat.error.reintentando")
            : t("chat.error.reintentar")}
      </button>
    </div>
  );
}
```

`authStore.logout({ manual: true })` is the verified signature (`lib/auth.js:46`). `manual: true` matters: it sets `polpilot.logout.manual` in `sessionStorage`, which suppresses the demo's autologin — without it the user would be bounced straight back into the same dead session.

- [ ] **Step 3: Mount it in `ChatThread`**

Inside `AssistantMessage`, after the bubble `div` closes:

```tsx
      <MessagePrimitive.Error>
        <ErrorState />
      </MessagePrimitive.Error>
```

- [ ] **Step 4: Verify by hand — this is the whole point of the task**

Run backend and frontend. Then, one at a time:

1. **The cap is not an error** — start the backend with `POLPILOT_DEMO_MSG_CAP=1` (verified name, `main.py:1979`) and send two messages. Expected: the *second* shows the cap **notice** (Task 8) and **no** `ErrorState` — the cap is a legitimate state, and this is the exact case that used to render an empty bubble. (The per-IP cap, `POLPILOT_DEMO_IP_CAP`, only applies in demo mode — `_cap_ip()` returns 0 otherwise.)
2. **`session_expired`** — send a message, then in devtools clear the session key `polpilot.session.v1` and force a 401 by editing the stored token. Expected: the "Se cerró tu sesión" card with a **"Volver a entrar"** button and *no* retry.
3. **`network`** — stop the backend, then send a message. Expected: the "Sin conexión" card with a working retry; restart the backend and click retry, and the answer arrives.
4. **`server`** — temporarily `raise RuntimeError("boom")` at the top of `stream_response`, send a message. Expected: the "No pude responder" card, the raw `"boom"` **absent** from the network response, and retry working once the raise is removed.

Undo the temporary `raise` and the env var before committing.

- [ ] **Step 5: Typecheck, test, commit**

Run: `cd frontend && npm run typecheck && npm test`

```bash
git add frontend/src/components/assistant frontend/src/lib/locales
git commit -m "Show a real error state with retry when a chat run fails"
```

---

### Task 10: Thinking indicator with per-tool label and elapsed time

**Files:**
- Create: `frontend/src/lib/chat/useElapsedSince.ts`
- Create: `frontend/src/lib/chat/useElapsedSince.test.ts`
- Create: `frontend/src/components/assistant/ThinkingIndicator.tsx`
- Modify: `frontend/src/components/assistant/ChatThread.tsx` (replace `ThinkingDots`)
- Modify: `frontend/src/lib/locales/es.js`, `en.js`

**Interfaces:**
- Consumes: `toolLabels` (Task 7).
- Produces: `useElapsedSince(startedAt: number | null): number` from `lib/chat/useElapsedSince.ts`; `ThinkingIndicator` (default export) replacing `ThinkingDots`.

**Design correction to the spec:** the spec proposed `useToolCallElapsed` for this. That hook takes **no arguments** and reads `part.timing` from the *current message-part scope*, returning `undefined` outside one — and the thinking row renders before any part exists. Our hand-built adapter parts also carry no `timing`. So Phase 1 uses its own `useElapsedSince`; revisit `useToolCallElapsed` in Phase 3 for per-tool-card durations, once we confirm whether `part.timing` is populated.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/chat/useElapsedSince.test.ts`:

```ts
import { describe, expect, it, vi, afterEach, beforeEach } from "vitest";
import { elapsedLabel } from "./useElapsedSince";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("elapsedLabel", () => {
  it("hides anything under two seconds as noise", () => {
    expect(elapsedLabel(0)).toBe("");
    expect(elapsedLabel(1900)).toBe("");
  });

  it("shows whole seconds", () => {
    expect(elapsedLabel(2000)).toBe("2s");
    expect(elapsedLabel(7400)).toBe("7s");
  });

  it("switches to minutes past sixty seconds", () => {
    expect(elapsedLabel(60000)).toBe("1m 0s");
    expect(elapsedLabel(95000)).toBe("1m 35s");
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm test`
Expected: FAIL — `Failed to resolve import "./useElapsedSince"`.

- [ ] **Step 3: Write `useElapsedSince.ts`**

```ts
import { useEffect, useState } from "react";

/**
 * Wall-clock ms since `startedAt`, ticking once a second. Returns 0 when
 * `startedAt` is null (nothing running).
 *
 * Not assistant-ui's `useToolCallElapsed`: that hook reads `part.timing` from
 * the current message-part scope and returns undefined outside one, but the
 * thinking row renders before any part exists.
 */
export function useElapsedSince(startedAt: number | null): number {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (startedAt == null) return;
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [startedAt]);

  return startedAt == null ? 0 : Math.max(0, now - startedAt);
}

/**
 * Elapsed ms as display text. Under two seconds shows nothing: a timer that
 * flickers on every fast answer is noise, not information.
 */
export function elapsedLabel(ms: number): string {
  if (ms < 2000) return "";
  const total = Math.floor(ms / 1000);
  if (total < 60) return `${total}s`;
  return `${Math.floor(total / 60)}m ${total % 60}s`;
}
```

- [ ] **Step 4: Add the i18n key**

To `es.js` / `en.js`:

```js
  "chat.pensando": "Pensando…",
```

- [ ] **Step 5: Write `ThinkingIndicator.tsx`**

```tsx
import { useAuiState } from "@assistant-ui/react";
import { useT } from "../../lib/i18n";
import { toolLabels } from "./tools/labels";
import { useElapsedSince, elapsedLabel } from "../../lib/chat/useElapsedSince";

/**
 * What the user reads while a run is in flight. Names the tool that is
 * actually running ("Revisando cuentas corrientes…") instead of three
 * anonymous dots, so a slow answer is legible rather than just slow.
 */
export default function ThinkingIndicator({ startedAt }: { startedAt: number }) {
  const t = useT();

  // The label follows the running tool, if there is one.
  const runningTool = useAuiState((s) => {
    const parts = s.message.content ?? [];
    for (let i = parts.length - 1; i >= 0; i -= 1) {
      const p = parts[i] as { type: string; toolName?: string; result?: unknown };
      if (p.type === "tool-call" && p.result === undefined) return p.toolName ?? null;
    }
    return null;
  });

  const label = runningTool ? toolLabels(runningTool).running : t("chat.pensando");
  const elapsed = elapsedLabel(useElapsedSince(startedAt));

  return (
    <div
      className="flex items-center gap-2.5 py-1 text-[0.85rem] text-tinta-suave"
      aria-live="polite"
    >
      <span
        aria-hidden
        className="size-1.5 shrink-0 animate-pulse rounded-full bg-violeta motion-reduce:animate-none"
      />
      <span>{label}</span>
      {elapsed && <span className="tabular-nums text-[0.78rem] opacity-70">{elapsed}</span>}
    </div>
  );
}
```

`aria-live="polite"` here is narrow on purpose — it announces the status line only. Announcing the streaming answer itself is Phase 4's job and needs care to avoid re-reading every token.

- [ ] **Step 6: Replace `ThinkingDots` in `ChatThread.tsx`**

Delete the `ThinkingDots` function. In `AssistantMessage`, capture a start time once per message and show the indicator whenever the run is in flight — not only before the first token, so a long tool call keeps explaining itself:

```tsx
  const isRunning = useAuiState((s) => s.message.status?.type === "running");
  const startedAt = useRef(Date.now()).current;
```

and in the bubble, replacing the `noContentYet ? <ThinkingDots/> : ...` conditional:

```tsx
          {isRunning && <ThinkingIndicator startedAt={startedAt} />}
          {!noContentYet && (
            <MessagePrimitive.Parts components={{ /* as in Task 8 */ }} />
          )}
```

Add `useRef` to the React import.

- [ ] **Step 7: Verify by hand**

Run: `cd frontend && npm test && npm run typecheck`

Then, with both services up, ask something that calls a slow tool (e.g. "¿cuánta plata tengo parada por categoría?"). Confirm:
- the row reads "Pensando…" first, then switches to the running tool's label;
- the elapsed counter appears only after ~2s and ticks;
- with the OS "reduce motion" setting on, the pulsing dot does not animate.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/lib/chat frontend/src/components/assistant frontend/src/lib/locales
git commit -m "Name the running tool and show elapsed time while Angela works"
```

---

## Phase 1 exit criteria

- [ ] `cd frontend && npm run typecheck` exits 0
- [ ] `cd frontend && npm test` — all suites pass
- [ ] `cd backend && py -m pytest -q` — no new failures vs. the pre-Phase-1 baseline
- [ ] `git checkout -- data-demo/` run after the backend suite
- [ ] `grep -rn "part.toolName ===" frontend/src/components/assistant/ChatThread.tsx` → no output
- [ ] Hitting the message cap shows the cap **notice**, not an empty bubble
- [ ] A failed run shows `ErrorState` with a working retry
- [ ] A reply produced without the model is visibly labelled as such
- [ ] `docs/superpowers/specs/2026-09-02-chat-experience-design.md` status line updated to record Phase 1 as landed, and `CLAUDE.md`'s "Status" line in the Ángela chat section updated

## Notes for the Phase 2 planner

- `chatRuntimeProvider.jsx` now builds the adapter with no options (Task 6, Step 6). Phase 2 reintroduces an options object for run context — deliberately, with a real getter this time.
- `frontend/src/types/untyped-modules.d.ts` (Task 7) is a temporary shim. Each declaration should be deleted as its module is converted to TS; `ResultTable` and `MiniChart` go in Phase 3.
- The spec's D5 `notice` kind list is now implemented as exactly `cap | tool_loop_exhausted | fake_model`. Phase 1.5 removes `fake_model` along with `_fallback`.
