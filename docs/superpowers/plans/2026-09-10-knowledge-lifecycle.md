# Knowledge Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `core/conocimiento.py` pieces real provenance display, edit/create UI, deterministic decay, and a proper archive state — replacing the current hardcoded-`False` staleness signal and hard-delete-on-retire.

**Architecture:** Six small, independently-mergeable PRs stacked in order (use `gh stack` — see below). No new tables; extends `business_knowledge_pieces` with two migrations (PR 4, PR 5). All new business logic lives in `core/conocimiento.py` and `core/db/business_knowledge_repo.py`, following those files' existing narrow-function style. All new endpoints follow the repo's established `POST /api/conocimiento/{pid}/<action>` pattern (never PATCH/PUT — grep of `backend/main.py` confirms the codebase never uses those verbs for this resource).

**Tech Stack:** FastAPI + SQLAlchemy Core (raw `text()` queries, no ORM) + Postgres w/ RLS, pytest + `TestClient`, React + TypeScript frontend, Tailwind, `lucide-react` icons.

**Spec:** `docs/superpowers/specs/2026-09-10-knowledge-lifecycle-design.md`

## Global Constraints

- Every new Python/TS identifier (function, column, endpoint handler, prop, type) is in English. Existing Spanish identifiers in `core/conocimiento.py` (`crear`, `listar`, `aprobar`, `pausar`, `activar`, `borrar`, `aplicables`, `para`) are **not** renamed.
- New `estado` values (`revisar`, `superada`, `archivada`) stay Spanish, extending the existing `activo`/`pausado`/`pendiente` set.
- Every date/"today" reference uses `core.fechas.hoy()` — **never** `datetime.date.today()` — so the product's deterministic "today" (`POLPILOT_DEMO_TODAY`) stays authoritative.
- Decay is computed at read time only. No task in this plan ever mutates a stored `confidence`/`last_reinforced_at` outside an explicit reinforcement event (`marcar_aplicada`, `reconfirm`).
- Every backend test file that touches `business_knowledge_pieces` starts with the `limpio` fixture pattern already established in `tests/test_conocimiento_confirmar.py` (`limpiar_tabla_tenant("business_knowledge_pieces")`, autouse, before and after).
- All new user-facing copy gets both an `en` and `es` key in `frontend/src/lib/locales/{en,js}.js` — the repo has zero exceptions to this today.
- Run backend tests with `../.venv/Scripts/python.exe -m pytest` from `backend/`, never bare `python` (see repo `CLAUDE.md` — bare `python` on this dev box lacks `python-dotenv` and silently breaks config loading).

## Stacking with `gh stack`

Each task below ends with its own commit on its own branch, stacked on the previous one:

```bash
# Once, before Task 1:
gh stack init   # targets main

# After each task's final commit:
gh stack add pr<N>-<short-name>   # e.g. pr1-knowledge-provenance
```

After all six tasks, `gh stack submit` opens all six PRs at once, each based on the one below it. Merging PR 1 auto-rebases the rest (`gh stack sync`).

---

### Task 1: Provenance display, grafo pause-bug fix, audit history, MCP read tool

**Files:**
- Modify: `backend/core/conocimiento.py:200-208` (`resumen_pieza`)
- Modify: `backend/core/grafo.py:471`
- Modify: `backend/core/audit.py`, `backend/core/db/audit_repo.py`
- Modify: `backend/main.py` (new route, near `conocimiento_detalle` at line 3448)
- Modify: `backend/angela.py` (new tool + dispatch + `TOOL_FEATURE` — no entry needed, see below)
- Modify: `backend/mcp_server.py:46-55` (`READ_ONLY_TOOLS`)
- Modify: `backend/i18n.py` (one new error key)
- Modify: `frontend/src/components/assistant/knowledgeStore.ts`
- Modify: `frontend/src/components/assistant/KnowledgePanel.tsx`
- Modify: `frontend/src/components/assistant/KnowledgeCite.tsx`
- Modify: `frontend/src/components/assistant/memory-chips.tsx`
- Modify: `frontend/src/lib/locales/en.js`, `frontend/src/lib/locales/es.js`
- Modify: `frontend/src/lib/api.js`
- Test: `backend/tests/test_conocimiento_confirmar.py` (extend), new `backend/tests/test_conocimiento_historial.py`, new `backend/tests/test_grafo_conocimiento.py` (or extend existing grafo test file if one covers this block — check `backend/tests/test_arquitectura.py`/`test_cruces.py` first; add there if a `grafo.py` conocimiento test already exists, else create the new file)

**Interfaces:**
- Produces: `conocimiento.resumen_pieza(p)` now includes `"quien"` key (str or `None`). `AuditLog.list_for(ref_id: str) -> list[dict]` (each dict: `{id, actor, accion, antes, despues, cuando}`, same shape as `AuditLog.list()`'s items). `audit_repo.list_events_for_ref(tenant_id: str, ref_id: str) -> list[dict]`.
- Consumes: nothing from later tasks.

- [ ] **Step 1: Failing test — `resumen_pieza` carries `quien`**

```python
# backend/tests/test_conocimiento_confirmar.py — add to the file
def test_resumen_pieza_carries_who_taught_it():
    pieza = conocimiento.crear(
        texto="Regla con autor", tipo="contexto", ambito="global",
        nodo="caja", efecto="contexto_para_angela",
        origen={"quien": "aldo", "cuando": "2026-09-10"})
    resumen = conocimiento.resumen_pieza(pieza)
    assert resumen["quien"] == "aldo"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_conocimiento_confirmar.py::test_resumen_pieza_carries_who_taught_it -v`
Expected: FAIL with `KeyError: 'quien'`

- [ ] **Step 3: Implement**

```python
# backend/core/conocimiento.py:200-208 — replace resumen_pieza
def resumen_pieza(p: dict) -> dict:
    """La forma compacta que viaja al frontend en `conocimiento_aplicado`: lo que
    el mapa necesita para el chip, el panel 'Lo que Aldo me enseñó' y el nodo del
    camino de conocimiento. Lleva ambos idiomas — el frontend elige por idioma."""
    origen = p.get("origen") or {}
    return {"id": p["id"], "tipo": p["tipo"], "texto": p["texto"],
            "texto_en": p.get("texto_en"), "nodo": p["nodo"], "efecto": p["efecto"],
            "efecto_profundo": p.get("efecto_profundo", False),
            "veces_aplicada": p.get("veces_aplicada", 0),
            "cuando": origen.get("cuando"), "quien": origen.get("quien")}
```

- [ ] **Step 4: Run to verify it passes**

Run: same command as Step 2. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/core/conocimiento.py backend/tests/test_conocimiento_confirmar.py
git commit -m "feat: surface who taught a knowledge piece in resumen_pieza"
```

- [ ] **Step 6: Failing test — grafo excludes paused pieces**

First, find grafo's existing test coverage: `grep -rn "conocimiento" backend/tests/test_arquitectura.py backend/tests/test_cruces.py`. If a test file already exercises `grafo.construir()` with `conocimiento` fixtures, add the test there; otherwise create `backend/tests/test_grafo_conocimiento.py` following the fixture pattern of whichever existing grafo test file is closest (same `limpiar_tabla_tenant` + tenant setup as `test_conocimiento_confirmar.py`).

```python
def test_paused_knowledge_does_not_appear_connected_on_the_map():
    from core import conocimiento, grafo
    pieza = conocimiento.crear(
        texto="Regla pausada", tipo="regla", ambito="cliente",
        nodo="clientes", efecto="ajusta_umbral", entidad="Despensa Doña Elsa")
    conocimiento.pausar(pieza["id"])
    g = grafo.construir()
    cliente = next((n for n in g["nodos"] if n["tipo"] == "cliente"
                    and "Elsa" in n["nombre"]), None)
    assert cliente is not None
    assert pieza["id"] not in (cliente.get("conocimiento") or [])
```

- [ ] **Step 7: Run to verify it fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_grafo_conocimiento.py -v` (or wherever Step 6 landed it)
Expected: FAIL — the piece still shows up (current `incluir_pausadas=True` default bug).

- [ ] **Step 8: Implement**

```python
# backend/core/grafo.py:470-471 — change
        from . import conocimiento
        for p in conocimiento.listar(incluir_pausadas=False):
```

(was: `for p in conocimiento.listar():`)

- [ ] **Step 9: Run to verify it passes**

Same command as Step 7. Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add backend/core/grafo.py backend/tests/test_grafo_conocimiento.py
git commit -m "fix: grafo no longer shows a paused knowledge piece as connected"
```

- [ ] **Step 11: Failing test — audit history filtered by piece id**

```python
# backend/tests/test_conocimiento_historial.py (new file)
import pytest
from fastapi.testclient import TestClient

import auth
import main
from core import conocimiento
from core.audit import AuditLog
from tests.conftest import limpiar_tabla_tenant

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def limpio():
    limpiar_tabla_tenant("business_knowledge_pieces")
    limpiar_tabla_tenant("audit_events")
    yield
    limpiar_tabla_tenant("business_knowledge_pieces")
    limpiar_tabla_tenant("audit_events")


@pytest.fixture(scope="module")
def token():
    creds = auth.cargar_o_generar_credenciales()
    return client.post("/api/login", json={"username": "emilio", "password": creds["emilio"]}).json()["token"]


def test_list_for_returns_only_events_about_this_piece():
    p1 = conocimiento.crear(texto="Pieza uno", tipo="contexto", ambito="global",
                            nodo="caja", efecto="contexto_para_angela")
    p2 = conocimiento.crear(texto="Pieza dos", tipo="contexto", ambito="global",
                            nodo="caja", efecto="contexto_para_angela")
    AuditLog().record("aldo", "editar_conocimiento", {"id": p1["id"]}, {"id": p1["id"], "texto": "cambiado"})
    AuditLog().record("aldo", "editar_conocimiento", {"id": p2["id"]}, {"id": p2["id"], "texto": "otro cambio"})
    eventos = AuditLog().list_for(p1["id"])
    assert len(eventos) == 1
    assert eventos[0]["despues"]["id"] == p1["id"]


def test_historial_endpoint_needs_a_session():
    p = conocimiento.crear(texto="x", tipo="contexto", ambito="global",
                           nodo="caja", efecto="contexto_para_angela")
    assert client.get(f"/api/conocimiento/{p['id']}/historial").status_code in (401, 403)


def test_historial_endpoint_returns_events(token):
    p = conocimiento.crear(texto="x", tipo="contexto", ambito="global",
                           nodo="caja", efecto="contexto_para_angela")
    AuditLog().record("aldo", "editar_conocimiento", {"id": p["id"]}, {"id": p["id"], "texto": "y"})
    r = client.get(f"/api/conocimiento/{p['id']}/historial",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()["eventos"]) == 1
```

- [ ] **Step 12: Run to verify it fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_conocimiento_historial.py -v`
Expected: FAIL — `AuditLog` has no `list_for`, and the route doesn't exist (404).

- [ ] **Step 13: Implement — repo, wrapper, route**

```python
# backend/core/db/audit_repo.py — add after list_events()
def list_events_for_ref(tenant_id: str, ref_id: str) -> list[dict]:
    """Every event whose before/after JSON references this id — a knowledge
    piece's own audit trail, filtered server-side."""
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(
            text("SELECT id, actor, action, before, after, created_at "
                 "FROM audit_events "
                 "WHERE (before ->> 'id' = :ref_id) OR (after ->> 'id' = :ref_id) "
                 "ORDER BY id"),
            {"ref_id": ref_id},
        ).mappings().all()
    return [_to_evento(r) for r in rows]
```

```python
# backend/core/audit.py — add to class AuditLog, after list()
    def list_for(self, ref_id: str) -> list[dict]:
        from core.db import audit_repo, tenant as _tenant
        tid = _tenant.current_tenant_id()
        audit_repo.seed_if_empty(tid, _seed_inicial())
        return audit_repo.list_events_for_ref(tid, ref_id)
```

```python
# backend/main.py — add after conocimiento_detalle (line ~3453)
@app.get("/api/conocimiento/{pid}/historial")
def conocimiento_historial(pid: str, u: dict = Depends(usuario_actual)):
    p = conocimiento.detalle(pid)
    if not p or p not in conocimiento.visibles_para(u, [p]):
        raise HTTPException(status_code=404, detail=i18n.t("api.conocimiento_inexistente", _lang(u)))
    from core.audit import AuditLog
    return {"eventos": AuditLog().list_for(pid)}
```

- [ ] **Step 14: Run to verify it passes**

Same command as Step 12. Expected: PASS (3 passed).

- [ ] **Step 15: Commit**

```bash
git add backend/core/db/audit_repo.py backend/core/audit.py backend/main.py backend/tests/test_conocimiento_historial.py
git commit -m "feat: add per-piece audit history endpoint"
```

- [ ] **Step 16: Failing test — MCP read tool for knowledge**

```python
# backend/tests/test_conocimiento_confirmar.py — add
def test_consultar_conocimiento_returns_active_pieces():
    conocimiento.crear(texto="Visible", tipo="contexto", ambito="global",
                       nodo="caja", efecto="contexto_para_angela")
    angela._set_sesion(usuario="emilio", rol="dueño", features=None, idioma="es")
    result, action = angela._run_tool("consultar_conocimiento", {})
    assert action is None
    assert any(p["texto"] == "Visible" for p in result["piezas"])


def test_consultar_conocimiento_respects_role_scope():
    conocimiento.crear(texto="Solo depósito", tipo="regla", ambito="global",
                       nodo="deposito", efecto="contexto_para_angela")
    angela._set_sesion(usuario="vendedor", rol="mostrador",
                       features={"cuentas"}, idioma="es")
    result, _ = angela._run_tool("consultar_conocimiento", {})
    assert result["piezas"] == []
```

```python
# backend/tests/test_ops_endpoints.py or a new backend/tests/test_mcp_conocimiento.py —
# follow whichever existing test file already exercises another READ_ONLY_TOOLS
# entry end-to-end through mcp_server.py (grep "READ_ONLY_TOOLS" in backend/tests/
# to find it) and add one case there:
def test_consultar_conocimiento_is_in_the_read_only_catalog():
    import mcp_server
    assert "consultar_conocimiento" in mcp_server.READ_ONLY_TOOLS
```

- [ ] **Step 17: Run to verify it fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_conocimiento_confirmar.py -k consultar_conocimiento -v`
Expected: FAIL — `KeyError`/unknown tool name (no dispatch branch yet).

- [ ] **Step 18: Implement — the tool + dispatch + MCP exposure**

```python
# backend/angela.py — add to the TOOLS list, near proponer_conocimiento (~line 900)
    {
        "name": "consultar_conocimiento",
        "description": "List the business rules/exceptions/protocols/context already taught "
        "to Ángela (read-only) — what this user is allowed to see, same scoping as the "
        "Knowledge panel. Use this before answering a question about a customer/supplier/"
        "product exception instead of guessing whether a rule exists.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nodo": {"type": "string", "enum": ["ventas", "inventario", "deposito",
                                                    "proveedores", "clientes", "caja",
                                                    "equipo", "contexto"]},
                "entidad": {"type": "string", "description": "filter to a specific customer/supplier/product, if given"},
            },
        },
    },
```

```python
# backend/angela.py — add a dispatch branch near leer_preferencias (~line 1835)
    if name == "consultar_conocimiento":
        from core import conocimiento
        piezas = conocimiento.listar(nodo=args.get("nodo"), entidad=args.get("entidad"),
                                     incluir_pausadas=False)
        piezas = conocimiento.visibles_para(_usuario_para_manual(), piezas)
        return {"piezas": [conocimiento.resumen_pieza(p) for p in piezas]}, None
```

No `TOOL_FEATURE` entry is added for `consultar_conocimiento` — it's intentionally unrestricted at the tool-catalog level (matching `proponer_conocimiento`, which also has none) because `visibles_para` already does fine-grained node/feature scoping internally.

```python
# backend/mcp_server.py:46-55 — add "consultar_conocimiento" to READ_ONLY_TOOLS
READ_ONLY_TOOLS = [
    "resumen_negocio", "plata_en", "buscar_productos", "top_inmovilizado",
    "listar_grupo", "cuentas_corrientes", "scoring_credito", "consultar_deposito",
    "consultar_cruces", "consultar_manual", "consultar_envios", "consultar_evolucion",
    "consultar_pronostico", "consultar_contexto_macro", "estado_caja",
    "capital_recuperable", "listar_prioridades", "analisis_rotacion",
    "analisis_estacionalidad", "analisis_push_pull", "consultar_compras",
    "objetivos_negocio", "mis_recordatorios", "leer_preferencias", "recuperar",
    "recuperar_contexto_negocio", "normalizaciones_staging", "consultar_serie",
    "consultar_conocimiento",
]
```

- [ ] **Step 19: Run to verify it passes**

Run the Step 17 command, plus: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_conocimiento_confirmar.py -k consultar_conocimiento -v` and the new MCP catalog test file's command.
Expected: all PASS.

- [ ] **Step 20: Commit**

```bash
git add backend/angela.py backend/mcp_server.py backend/tests/test_conocimiento_confirmar.py
git commit -m "feat: expose business knowledge read-only via consultar_conocimiento (chat + MCP)"
```

- [ ] **Step 21: Frontend — provenance in the store, panel, chips, and citation**

```typescript
// frontend/src/components/assistant/knowledgeStore.ts — extend the type (near line 4)
export type KnowledgePiece = {
  id: string;
  texto: string;
  nodo: string;
  entidad?: string | null;
  estado: string;
  quien?: string | null;
  cuando?: string | null;
};
```

```tsx
{/* frontend/src/components/assistant/KnowledgePanel.tsx — Piece type (line 9-17) gains
    the same two fields as KnowledgePiece above: quien, cuando. */}

{/* In the rendered row (around line 199, next to the nodo/entidad spans), add: */}
{piece.quien && (
  <span className="text-2xs text-tinta-suave">
    · {t("chat.knowledge.taught_by", { who: piece.quien, when: piece.cuando ?? "" })}
  </span>
)}
```

```javascript
// frontend/src/lib/locales/en.js — add near the other chat.knowledge.* keys
  "chat.knowledge.taught_by": "taught by {who}, {when}",
```

```javascript
// frontend/src/lib/locales/es.js — add near the other chat.knowledge.* keys
  "chat.knowledge.taught_by": "enseñado por {who}, {when}",
```

```tsx
{/* frontend/src/components/assistant/KnowledgeCite.tsx — extend the Citation's
    `source` object (currently domain/title/snippet) with the provenance line */}
      source={{
        domain: t("chat.cite.source"),
        title: piece.entidad ? `${piece.nodo} · ${piece.entidad}` : piece.nodo,
        snippet: piece.texto,
        detail: piece.quien
          ? t("chat.knowledge.taught_by", { who: piece.quien, when: piece.cuando ?? "" })
          : undefined,
      }}
```

(If `Citation`'s prop type doesn't already accept a `detail` field on `source`, add it there too — check `frontend/src/components/assistant/inline-citation.tsx`'s `source` prop type first and extend it minimally to accept an optional `detail?: string`, rendered the same way `snippet` already is, one line below it.)

- [ ] **Step 22: Manually verify in the running app**

Run `python start_demo.py` from the repo root, open the chat as `aldo`, open "What Ángela knows about the business" (the Brain icon), and confirm each row shows "taught by X, date". Then ask Ángela something that cites a rule (e.g. about Despensa Doña Elsa's tolerance) and confirm the citation card also shows the provenance line.

- [ ] **Step 23: Commit**

```bash
git add frontend/src/components/assistant/knowledgeStore.ts frontend/src/components/assistant/KnowledgePanel.tsx frontend/src/components/assistant/KnowledgeCite.tsx frontend/src/lib/locales/en.js frontend/src/lib/locales/es.js
git commit -m "feat: show who taught a rule and when, in the panel and in citations"
```

- [ ] **Step 24: Add to the stack**

```bash
gh stack add pr1-knowledge-provenance
```

---

### Task 2: Edit + manual create UI

**Files:**
- Modify: `backend/core/conocimiento.py` (new `edit_piece`)
- Modify: `backend/core/db/business_knowledge_repo.py` (new `update_content`)
- Modify: `backend/main.py` (new `ConocimientoEditar` model + route + `_editor_o_403` helper)
- Modify: `backend/i18n.py` (one new error key)
- Modify: `frontend/src/lib/api.js` (`conocimientoEditar`, `conocimientoCrear`)
- Modify: `frontend/src/components/assistant/KnowledgePanel.tsx` (create button + form, edit affordance)
- Modify: `frontend/src/lib/locales/en.js`, `frontend/src/lib/locales/es.js`
- Test: `backend/tests/test_conocimiento_confirmar.py` (extend)

**Interfaces:**
- Consumes: nothing new from Task 1 beyond what already existed.
- Produces: `conocimiento.edit_piece(pid, *, actor, is_admin, texto=None, texto_en=None, tipo=None, ambito=None, efecto=None, entidad=None, params=None) -> dict | None`. `business_knowledge_repo.update_content(tenant_id, piece_id, *, texto, texto_en, tipo, ambito, efecto, entidad, params, estado) -> dict | None`.

- [ ] **Step 1: Failing test — admin edit stays active, author-non-admin edit re-stages**

```python
# backend/tests/test_conocimiento_confirmar.py — add
def test_admin_edit_keeps_the_piece_active():
    pieza = conocimiento.crear(texto="Original", tipo="contexto", ambito="global",
                               nodo="caja", efecto="contexto_para_angela",
                               origen={"quien": "aldo", "cuando": "2026-09-10"})
    out = conocimiento.edit_piece(pieza["id"], actor="aldo", is_admin=True,
                                  texto="Editado por el admin")
    assert out["texto"] == "Editado por el admin"
    assert out["estado"] == "activo"


def test_author_non_admin_edit_re_enters_staging():
    pieza = conocimiento.crear(texto="Original", tipo="contexto", ambito="global",
                               nodo="caja", efecto="contexto_para_angela",
                               origen={"quien": "vendedor", "cuando": "2026-09-10"})
    out = conocimiento.edit_piece(pieza["id"], actor="vendedor", is_admin=False,
                                  texto="Editado por el autor")
    assert out["texto"] == "Editado por el autor"
    assert out["estado"] == "pendiente"


def test_edit_validates_like_crear():
    pieza = conocimiento.crear(texto="Original", tipo="contexto", ambito="global",
                               nodo="caja", efecto="contexto_para_angela")
    with pytest.raises(conocimiento.ConocimientoInvalido):
        conocimiento.edit_piece(pieza["id"], actor="aldo", is_admin=True, tipo="no-existe")


def test_edit_returns_none_for_a_missing_piece():
    assert conocimiento.edit_piece("no-existe", actor="aldo", is_admin=True, texto="x") is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_conocimiento_confirmar.py -k edit_piece -v`
Expected: FAIL — `AttributeError: module 'core.conocimiento' has no attribute 'edit_piece'`

- [ ] **Step 3: Implement — repo function**

```python
# backend/core/db/business_knowledge_repo.py — add after create()
def update_content(tenant_id: str, piece_id: str, *, texto: str, texto_en: str | None,
                   tipo: str, ambito: str, efecto: str, entidad: str | None,
                   params: dict, estado: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "UPDATE business_knowledge_pieces SET "
                "texto = :texto, texto_en = :texto_en, tipo = :tipo, ambito = :ambito, "
                "efecto = :efecto, entidad = :entidad, params = :params, estado = :estado "
                f"WHERE id = :id RETURNING {', '.join(_COLS)}"
            ),
            {"texto": texto, "texto_en": texto_en, "tipo": tipo, "ambito": ambito,
             "efecto": efecto, "entidad": entidad, "params": json.dumps(params or {}),
             "estado": estado, "id": piece_id},
        ).mappings().one_or_none()
    return _to_piece(row) if row else None
```

- [ ] **Step 4: Implement — `conocimiento.edit_piece`**

```python
# backend/core/conocimiento.py — add after crear() (after line 306)
def edit_piece(pid: str, *, actor: str, is_admin: bool, texto: str | None = None,
               texto_en: str | None = None, tipo: str | None = None,
               ambito: str | None = None, efecto: str | None = None,
               entidad: str | None = None, params: dict | None = None) -> dict | None:
    """Merges the given fields onto the existing piece, validates the result
    against the same catalog crear() enforces, persists, and audits before/
    after. An admin's edit keeps the piece's current estado; anyone else's
    (only the piece's own author reaches here — main.py enforces that) sends
    it back to "pendiente" for re-review, same trust model as a fresh
    proposal. Returns None if pid doesn't exist."""
    actual = detalle(pid)
    if not actual:
        return None
    nuevo_texto = texto if texto is not None else actual["texto"]
    if not (nuevo_texto or "").strip():
        raise ConocimientoInvalido("el texto no puede estar vacío")
    nuevo_ambito = ambito or actual["ambito"]
    nueva_entidad = entidad if entidad is not None else actual.get("entidad")
    nuevo_tipo = tipo or actual["tipo"]
    nuevo_efecto = efecto or actual["efecto"]
    _validar(nuevo_tipo, nuevo_ambito, actual["nodo"], nuevo_efecto, actual["estado"])
    if nuevo_ambito != "global" and not (nueva_entidad or "").strip():
        raise ConocimientoInvalido("una pieza no-global necesita una entidad concreta")
    nuevo_estado = actual["estado"] if is_admin else "pendiente"
    from core.db import business_knowledge_repo
    from core.db import tenant as _tenant
    pieza = business_knowledge_repo.update_content(
        _tenant.current_tenant_id(), pid, texto=nuevo_texto.strip(),
        texto_en=(texto_en if texto_en is not None else actual.get("texto_en")),
        tipo=nuevo_tipo, ambito=nuevo_ambito, efecto=nuevo_efecto,
        entidad=(nueva_entidad or "").strip() or None,
        params=(params if params is not None else actual.get("params") or {}),
        estado=nuevo_estado)
    from .audit import AuditLog
    AuditLog(DATA_DIR).record(actor, "editar_conocimiento", actual, pieza)
    return pieza
```

- [ ] **Step 5: Run to verify it passes**

Same command as Step 2. Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/core/db/business_knowledge_repo.py backend/core/conocimiento.py backend/tests/test_conocimiento_confirmar.py
git commit -m "feat: add conocimiento.edit_piece with admin/author staging rule"
```

- [ ] **Step 7: Failing test — the endpoint and its permission boundary**

```python
# backend/tests/test_conocimiento_confirmar.py — add
def test_edit_endpoint_needs_admin_or_author(tokens):
    pieza = conocimiento.crear(texto="Original", tipo="contexto", ambito="global",
                               nodo="caja", efecto="contexto_para_angela",
                               origen={"quien": "deposito", "cuando": "2026-09-10"})
    # vendedor is neither admin nor the author "deposito"
    r = client.post(f"/api/conocimiento/{pieza['id']}/editar",
                    json={"texto": "intento ajeno"},
                    headers={"Authorization": f"Bearer {tokens['vendedor']}"})
    assert r.status_code == 403
    # deposito IS the author
    r = client.post(f"/api/conocimiento/{pieza['id']}/editar",
                    json={"texto": "editado por su autor"},
                    headers={"Authorization": f"Bearer {tokens['deposito']}"})
    assert r.status_code == 200
    assert r.json()["pieza"]["texto"] == "editado por su autor"


def test_edit_endpoint_404s_on_a_missing_piece(tokens):
    r = client.post("/api/conocimiento/no-existe/editar", json={"texto": "x"},
                    headers={"Authorization": f"Bearer {tokens['emilio']}"})
    assert r.status_code == 404
```

- [ ] **Step 8: Run to verify it fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_conocimiento_confirmar.py -k edit_endpoint -v`
Expected: FAIL — 404 Not Found (no route registered).

- [ ] **Step 9: Implement — route**

```python
# backend/i18n.py — add near api.conocimiento_no_pendiente
    "api.conocimiento_sin_permiso": {
        "es": "Solo el dueño o quien la enseñó puede editar esta pieza.",
        "en": "Only the owner or whoever taught it can edit this piece.",
    },
```

```python
# backend/main.py — add near _revisor_o_404 (line ~3547)
def _editor_o_403(pid: str, u: dict) -> dict:
    p = conocimiento.detalle(pid)
    if not p or p not in conocimiento.visibles_para(u, [p]):
        raise HTTPException(status_code=404, detail=i18n.t("api.conocimiento_inexistente", _lang(u)))
    if not (u.get("es_admin") or (p.get("origen") or {}).get("quien") == u["username"]):
        raise HTTPException(status_code=403, detail=i18n.t("api.conocimiento_sin_permiso", _lang(u)))
    return p


class ConocimientoEditar(BaseModel):
    texto: str | None = None
    texto_en: str | None = None
    tipo: str | None = None
    ambito: str | None = None
    efecto: str | None = None
    entidad: str | None = None
    params: dict | None = None


@app.post("/api/conocimiento/{pid}/editar")
def conocimiento_editar(pid: str, req: ConocimientoEditar, u: dict = Depends(usuario_actual)):
    _editor_o_403(pid, u)
    try:
        pieza = conocimiento.edit_piece(
            pid, actor=u["username"], is_admin=bool(u.get("es_admin")),
            texto=req.texto, texto_en=req.texto_en, tipo=req.tipo, ambito=req.ambito,
            efecto=req.efecto, entidad=req.entidad, params=req.params)
    except conocimiento.ConocimientoInvalido as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "pieza": pieza}
```

- [ ] **Step 10: Run to verify it passes**

Same command as Step 8. Expected: PASS (2 passed).

- [ ] **Step 11: Commit**

```bash
git add backend/i18n.py backend/main.py backend/tests/test_conocimiento_confirmar.py
git commit -m "feat: add POST /api/conocimiento/{pid}/editar"
```

- [ ] **Step 12: Frontend — create button/form and edit affordance in `KnowledgePanel.tsx`**

```javascript
// frontend/src/lib/api.js — add near knowledgeConfirm (line ~203)
  conocimientoCrear: (pieza) => post("/api/conocimiento", pieza),
  conocimientoEditar: (pid, campos) => post(`/api/conocimiento/${encodeURIComponent(pid)}/editar`, campos),
```

```tsx
{/* frontend/src/components/assistant/KnowledgePanel.tsx —
    1. Import Pencil and Plus from lucide-react alongside the existing icons (line 2).
    2. Add local state for the create/edit form: */}
  const [editing, setEditing] = useState<Piece | null>(null); // null = create mode when formOpen
  const [formOpen, setFormOpen] = useState(false);

{/* 3. A "create" button next to the search bar (after the search <div>, before the
       node-filter chips, around line 145): */}
        <button
          type="button"
          onClick={() => { setEditing(null); setFormOpen(true); }}
          className="mb-2.5 flex items-center gap-1 rounded-full bg-tinta px-2.5 py-1 text-xs text-crema"
        >
          <Plus size={12} /> {t("chat.knowledge.create")}
        </button>

{/* 4. On each row (next to the existing admin-only Pause/Delete buttons, around line 255),
       an edit affordance visible to admin OR the piece's own author: */}
                {(isAdmin || piece.quien === useSession()?.usuario?.username)
                  && piece.estado !== "pendiente" && (
                  <PieceAction
                    label={t("chat.knowledge.edit")}
                    onClick={() => { setEditing(piece); setFormOpen(true); }}
                  >
                    <Pencil size={12} />
                  </PieceAction>
                )}

{/* 5. The form itself (a simple modal/inline block — follow whatever modal
       primitive frontend/src/components/assistant already uses elsewhere,
       e.g. check feedback-dialog.tsx for the pattern this codebase prefers;
       render it just before the closing </div> of the panel):
       fields: texto, texto_en, tipo (select from conocimiento.TIPOS: regla/
       excepcion/protocolo/contexto), ambito (select), nodo (select, create-only —
       not editable), efecto (select), entidad (text, required unless ambito
       is global). On submit: */}
  const submitForm = async (fields: Record<string, string>) => {
    if (editing) {
      const updated = await api.conocimientoEditar(editing.id, fields);
      setPieces((prev) => prev.map((p) => (p.id === editing.id ? updated.pieza : p)));
    } else {
      const created = await api.conocimientoCrear(fields);
      setPieces((prev) => [...prev, created.pieza]);
    }
    setFormOpen(false);
  };
```

```javascript
// frontend/src/lib/locales/en.js — add
  "chat.knowledge.create": "Add rule",
  "chat.knowledge.edit": "Edit",
```

```javascript
// frontend/src/lib/locales/es.js — add
  "chat.knowledge.create": "Agregar regla",
  "chat.knowledge.edit": "Editar",
```

- [ ] **Step 13: Manually verify in the running app**

`python start_demo.py`, log in as `aldo`, open the Knowledge panel, create a new rule via the form, confirm it appears active immediately (admin path). Log in as `deposito`, edit one of their own taught pieces, confirm it flips to "pendiente" and shows in the review queue.

- [ ] **Step 14: Commit**

```bash
git add frontend/src/lib/api.js frontend/src/components/assistant/KnowledgePanel.tsx frontend/src/lib/locales/en.js frontend/src/lib/locales/es.js
git commit -m "feat: manual create and edit UI in the Knowledge panel"
```

- [ ] **Step 15: Add to the stack**

```bash
gh stack add pr2-knowledge-edit-create
```

---

### Task 3: Aging visibility

**Files:**
- Modify: `backend/core/conocimiento.py` (new `age_days`, `days_since_applied` helpers)
- Modify: `backend/main.py` (`conocimiento_listar`/`conocimiento_detalle` responses — no change needed, `origen.cuando` already travels; this task is about deriving a display-ready age, not new storage)
- Modify: `frontend/src/components/assistant/KnowledgePanel.tsx` (age badge, "needs attention" filter)
- Modify: `frontend/src/lib/locales/en.js`, `frontend/src/lib/locales/es.js`
- Test: `backend/tests/test_conocimiento_confirmar.py` (extend)

**Interfaces:**
- Consumes: `piece["origen"]["cuando"]` (ISO date string, already present), `piece["veces_aplicada"]` (already present) — no new backend storage.
- Produces: `conocimiento.age_days(piece, *, today=None) -> int | None` (`None` if `origen.cuando` is missing).

- [ ] **Step 1: Failing test — age in days**

```python
# backend/tests/test_conocimiento_confirmar.py — add
from datetime import date

def test_age_days_counts_from_origen_cuando():
    pieza = conocimiento.crear(texto="x", tipo="contexto", ambito="global",
                               nodo="caja", efecto="contexto_para_angela",
                               origen={"quien": "aldo", "cuando": "2026-08-01"})
    assert conocimiento.age_days(pieza, today=date(2026, 9, 10)) == 40


def test_age_days_is_none_without_origen():
    pieza = conocimiento.crear(texto="x", tipo="contexto", ambito="global",
                               nodo="caja", efecto="contexto_para_angela")
    assert conocimiento.age_days(pieza) is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_conocimiento_confirmar.py -k age_days -v`
Expected: FAIL — `AttributeError`.

- [ ] **Step 3: Implement**

```python
# backend/core/conocimiento.py — add after resumen_pieza()
def age_days(p: dict, *, today=None) -> int | None:
    """Days since this piece was taught, or None if origen.cuando is
    missing (a piece seeded without provenance)."""
    cuando = (p.get("origen") or {}).get("cuando")
    if not cuando:
        return None
    from datetime import date as _date
    from . import fechas
    ref = today or fechas.hoy()
    try:
        taught = _date.fromisoformat(cuando[:10])
    except ValueError:
        return None
    return (ref - taught).days
```

- [ ] **Step 4: Run to verify it passes**

Same command as Step 2. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/core/conocimiento.py backend/tests/test_conocimiento_confirmar.py
git commit -m "feat: add conocimiento.age_days"
```

- [ ] **Step 6: Frontend — age badge and filter**

```tsx
{/* frontend/src/components/assistant/KnowledgePanel.tsx — the Piece type gains
    an optional derived field the panel computes client-side (no backend change
    needed: origen.cuando is already on the piece via Step 21 of Task 1). Add a
    small pure helper near the top of the file: */}
function ageDays(cuando?: string | null): number | null {
  if (!cuando) return null;
  const taught = new Date(cuando);
  if (Number.isNaN(taught.getTime())) return null;
  return Math.floor((Date.now() - taught.getTime()) / 86_400_000);
}

{/* In the row render (next to the "cuando" line from Task 1 Step 21), add: */}
{(() => {
  const days = ageDays(piece.cuando);
  return days !== null && days > 60 ? (
    <span className="rounded-full bg-oro/[0.07] px-1.5 py-0.5 text-2xs text-oro-tinta/80">
      {t("chat.knowledge.age_days", { n: String(days) })}
    </span>
  ) : null;
})()}

{/* A "needs attention" toggle next to the node-filter chips: */}
  const [onlyAging, setOnlyAging] = useState(false);
// ...
  const shown = pieces
    .filter((p) => matches(p, query) && (!node || p.nodo === node))
    .filter((p) => !onlyAging || (ageDays(p.cuando) ?? 0) > 60);
```

```javascript
// frontend/src/lib/locales/en.js
  "chat.knowledge.age_days": "{n} days old",
  "chat.knowledge.only_aging": "Aging only",
```

```javascript
// frontend/src/lib/locales/es.js
  "chat.knowledge.age_days": "hace {n} días",
  "chat.knowledge.only_aging": "Solo antiguas",
```

- [ ] **Step 7: Manually verify in the running app**

`python start_demo.py`, open the Knowledge panel — the seeded demo pieces (taught between 5 Jun and 6 Jul 2026, per `KNOWLEDGE_SINTETICO.md`) should show age badges given the dataset's "today" is 2026-07-07 (recent, likely under the 60-day threshold — confirm by temporarily lowering the threshold to 5 in a throwaway edit, verify the badge appears, then revert).

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/assistant/KnowledgePanel.tsx frontend/src/lib/locales/en.js frontend/src/lib/locales/es.js
git commit -m "feat: show a piece's age and a filter for aging pieces"
```

- [ ] **Step 9: Add to the stack**

```bash
gh stack add pr3-knowledge-aging-badge
```

---

### Task 4: Real decay + deterministic conflict detection

**Files:**
- Create: `backend/migrations/versions/0045_business_knowledge_decay.py`
- Modify: `backend/core/db/business_knowledge_repo.py` (`_COLS`, `_to_piece`, `create`, new `update_reinforcement`)
- Modify: `backend/core/conocimiento.py` (`DEFAULT_HALF_LIFE`, `decay_score`, `freshness`, `needs_review`, `reinforce`, `find_conflict`; extend `crear`'s call to check conflicts)
- Modify: `backend/main.py` (`conocimiento_crear` surfaces a conflict instead of silently creating a duplicate operational rule)
- Modify: `backend/i18n.py`
- Test: `backend/tests/test_conocimiento_confirmar.py` (extend), new `backend/tests/test_conocimiento_decay.py`

**Interfaces:**
- Consumes: `piece["confidence"]`, `piece["last_reinforced_at"]`, `piece["half_life_days"]`, `piece["evidence_count"]` (new columns, this task's migration).
- Produces: `conocimiento.decay_score(piece, *, today=None) -> float`, `conocimiento.freshness(piece, *, today=None) -> str` (`"fresco" | "atencion" | "revisar"`), `conocimiento.needs_review(piece, *, today=None, threshold=0.35) -> bool`, `conocimiento.reinforce(pid) -> dict | None`, `conocimiento.find_conflict(*, texto, nodo, entidad, efecto) -> dict | None`. These four are used by sub-project 2 (Priorities bridge) — their signatures are load-bearing for that plan, do not change them without updating `docs/superpowers/plans/2026-09-10-priorities-knowledge-bridge.md`.

- [ ] **Step 1: Write the migration**

```python
# backend/migrations/versions/0045_business_knowledge_decay.py
"""add decay columns to business_knowledge_pieces

Revision ID: 0045
Revises: 0044
Create Date: 2026-09-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("business_knowledge_pieces",
        sa.Column("confidence", sa.Numeric, nullable=False, server_default="0.7"))
    op.add_column("business_knowledge_pieces",
        sa.Column("evidence_count", sa.Integer, nullable=False, server_default="1"))
    op.add_column("business_knowledge_pieces",
        sa.Column("last_reinforced_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("created_at")))
    op.add_column("business_knowledge_pieces",
        sa.Column("half_life_days", sa.Integer, nullable=True))


def downgrade() -> None:
    op.drop_column("business_knowledge_pieces", "half_life_days")
    op.drop_column("business_knowledge_pieces", "last_reinforced_at")
    op.drop_column("business_knowledge_pieces", "evidence_count")
    op.drop_column("business_knowledge_pieces", "confidence")
```

- [ ] **Step 2: Run the migration and verify**

Run: `cd backend && ../.venv/Scripts/python.exe -m alembic upgrade head`
Expected: no errors, `alembic_version` now at `0045`. Then confirm the test DB picks it up: `tests/dbsetup.py` migrates `polpilot_test` automatically on the next pytest run.

- [ ] **Step 3: Update the repo layer's `_COLS`/`_to_piece`/`create`**

```python
# backend/core/db/business_knowledge_repo.py — replace _COLS (line 14-15)
_COLS = ("id", "texto", "texto_en", "tipo", "ambito", "entidad", "nodo",
         "efecto", "efecto_profundo", "params", "origen", "estado",
         "veces_aplicada", "confidence", "evidence_count",
         "last_reinforced_at", "half_life_days")
```

```python
# _to_piece — add the four new fields to the returned dict (after "veces_aplicada")
        "veces_aplicada": row["veces_aplicada"],
        "confidence": float(row["confidence"]),
        "evidence_count": row["evidence_count"],
        "last_reinforced_at": row["last_reinforced_at"].isoformat() if row["last_reinforced_at"] else None,
        "half_life_days": row["half_life_days"],
```

```python
# create() — add optional params with sensible defaults (signature + INSERT + params dict)
def create(tenant_id: str, *, id: str, texto: str, tipo: str, ambito: str,
          nodo: str, efecto: str, entidad: str | None = None,
          texto_en: str | None = None, efecto_profundo: bool = False,
          params: dict | None = None, origen: dict | None = None,
          estado: str = "activo", veces_aplicada: int = 0,
          confidence: float = 0.7, evidence_count: int = 1,
          half_life_days: int | None = None) -> dict:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "INSERT INTO business_knowledge_pieces "
                "(id, tenant_id, texto, texto_en, tipo, ambito, entidad, nodo, "
                " efecto, efecto_profundo, params, origen, estado, veces_aplicada, "
                " confidence, evidence_count, half_life_days) "
                "VALUES (:id, :tid, :texto, :texto_en, :tipo, :ambito, :entidad, :nodo, "
                " :efecto, :efecto_profundo, :params, :origen, :estado, :veces_aplicada, "
                " :confidence, :evidence_count, :half_life_days) "
                f"RETURNING {', '.join(_COLS)}"
            ),
            {"id": id, "tid": tenant_id, "texto": texto, "texto_en": texto_en,
             "tipo": tipo, "ambito": ambito, "entidad": entidad, "nodo": nodo,
             "efecto": efecto, "efecto_profundo": efecto_profundo,
             "params": json.dumps(params or {}), "origen": json.dumps(origen or {}),
             "estado": estado, "veces_aplicada": veces_aplicada,
             "confidence": confidence, "evidence_count": evidence_count,
             "half_life_days": half_life_days},
        ).mappings().one()
    return _to_piece(row)
```

```python
# add after increment_applied()
def update_reinforcement(tenant_id: str, piece_id: str, *, confidence: float,
                         evidence_count: int) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "UPDATE business_knowledge_pieces SET "
                "confidence = :confidence, evidence_count = :evidence_count, "
                "last_reinforced_at = now() "
                f"WHERE id = :id RETURNING {', '.join(_COLS)}"
            ),
            {"confidence": confidence, "evidence_count": evidence_count, "id": piece_id},
        ).mappings().one_or_none()
    return _to_piece(row) if row else None
```

- [ ] **Step 4: Failing test — decay math**

```python
# backend/tests/test_conocimiento_decay.py (new file)
import pytest
from datetime import date

from core import conocimiento
from tests.conftest import limpiar_tabla_tenant


@pytest.fixture(autouse=True)
def limpio():
    limpiar_tabla_tenant("business_knowledge_pieces")
    yield
    limpiar_tabla_tenant("business_knowledge_pieces")


def _pieza(tipo="regla", half_life_days=None):
    return conocimiento.crear(texto="x", tipo=tipo, ambito="global", nodo="caja",
                              efecto="contexto_para_angela", half_life_days=half_life_days)


def test_decay_score_at_zero_age_equals_stored_confidence():
    p = _pieza()
    assert conocimiento.decay_score(p, today=date.fromisoformat(p["last_reinforced_at"][:10])) == pytest.approx(0.7)


def test_decay_score_halves_at_one_half_life():
    p = _pieza(half_life_days=100)
    ref = date.fromisoformat(p["last_reinforced_at"][:10])
    aged = date(ref.year, ref.month, ref.day) + __import__("datetime").timedelta(days=100)
    assert conocimiento.decay_score(p, today=aged) == pytest.approx(0.35, abs=0.01)


def test_decay_score_uses_tipo_default_when_no_override():
    regla = _pieza(tipo="regla")  # default half-life 180
    protocolo = _pieza(tipo="protocolo")  # default half-life 365
    ref = date.fromisoformat(regla["last_reinforced_at"][:10])
    aged = ref + __import__("datetime").timedelta(days=180)
    assert conocimiento.decay_score(regla, today=aged) == pytest.approx(0.35, abs=0.01)
    assert conocimiento.decay_score(protocolo, today=aged) > 0.45  # decayed less


def test_needs_review_crosses_the_default_threshold():
    p = _pieza(half_life_days=10)
    ref = date.fromisoformat(p["last_reinforced_at"][:10])
    far = ref + __import__("datetime").timedelta(days=60)
    assert conocimiento.needs_review(p, today=far) is True
    assert conocimiento.needs_review(p, today=ref) is False


def test_freshness_buckets():
    p = _pieza(half_life_days=100)
    ref = date.fromisoformat(p["last_reinforced_at"][:10])
    assert conocimiento.freshness(p, today=ref) == "fresco"
    far = ref + __import__("datetime").timedelta(days=200)
    assert conocimiento.freshness(p, today=far) == "revisar"


def test_reinforce_resets_last_reinforced_at_and_bumps_confidence():
    p = _pieza()
    before = p["confidence"]
    out = conocimiento.reinforce(p["id"])
    assert out["confidence"] > before
    assert out["evidence_count"] == p["evidence_count"] + 1


def test_reinforce_has_diminishing_returns_and_never_exceeds_one():
    p = _pieza()
    pid = p["id"]
    last = p["confidence"]
    for _ in range(20):
        out = conocimiento.reinforce(pid)
        bump = out["confidence"] - last
        assert bump >= 0
        last = out["confidence"]
    assert last <= 1.0
```

- [ ] **Step 5: Run to verify it fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_conocimiento_decay.py -v`
Expected: FAIL — no `decay_score`/`freshness`/`needs_review`/`reinforce` yet.

- [ ] **Step 6: Implement decay/reinforce**

```python
# backend/core/conocimiento.py — add near TIPOS (after line 44)
DEFAULT_HALF_LIFE = {"regla": 180, "excepcion": 120, "protocolo": 365, "contexto": 270}
```

```python
# backend/core/conocimiento.py — add after age_days() (from Task 3)
def decay_score(p: dict, *, today=None) -> float:
    """Confidence right now: exponential half-life decay from
    last_reinforced_at, read-time only — never mutates the stored row.
        confidence(t) = stored_confidence * 2 ** (-age_days / half_life)
    """
    from datetime import date as _date
    from . import fechas
    ref = today or fechas.hoy()
    reinforced = _date.fromisoformat(p["last_reinforced_at"][:10])
    age = max(0, (ref - reinforced).days)
    half_life = p.get("half_life_days") or DEFAULT_HALF_LIFE[p["tipo"]]
    return float(p["confidence"]) * (2 ** (-age / half_life))


def freshness(p: dict, *, today=None) -> str:
    """"fresco" | "atencion" | "revisar" — the traffic-light bucket over
    decay_score(), same three-tone vocabulary grafo.py/priorities.py
    already use for riesgo/tono."""
    score = decay_score(p, today=today)
    if score >= 0.55:
        return "fresco"
    if score >= 0.35:
        return "atencion"
    return "revisar"


def needs_review(p: dict, *, today=None, threshold: float = 0.35) -> bool:
    """True once decay_score() crosses the review floor. Does NOT change
    estado by itself."""
    return decay_score(p, today=today) < threshold


def reinforce(pid: str) -> dict | None:
    """Bumps evidence_count and resets last_reinforced_at = today, nudging
    confidence up by a decreasing amount so repeated reinforcement
    approaches but never exceeds 1.0. Called by marcar_aplicada() and by
    the review-queue "still valid" action (see reconfirm(), Task 5)."""
    p = detalle(pid)
    if not p:
        return None
    bump = (1.0 - float(p["confidence"])) * 0.2
    nuevo = min(1.0, float(p["confidence"]) + bump)
    from core.db import business_knowledge_repo
    from core.db import tenant as _tenant
    return business_knowledge_repo.update_reinforcement(
        _tenant.current_tenant_id(), pid, confidence=nuevo,
        evidence_count=p["evidence_count"] + 1)
```

- [ ] **Step 7: Run to verify decay/reinforce tests pass**

Same command as Step 5. Expected: all decay/reinforce tests PASS.

- [ ] **Step 8: Failing test — conflict detection**

```python
# backend/tests/test_conocimiento_decay.py — add
def test_find_conflict_matches_same_triple_different_text():
    conocimiento.crear(texto="Tolerale 30 días", tipo="regla", ambito="cliente",
                       nodo="clientes", efecto="ajusta_umbral", entidad="Doña Elsa",
                       params={"tolerancia_dias": 30})
    conflict = conocimiento.find_conflict(
        texto="Tolerale 45 días", nodo="clientes", entidad="Doña Elsa",
        efecto="ajusta_umbral")
    assert conflict is not None
    assert conflict["params"]["tolerancia_dias"] == 30


def test_find_conflict_is_none_for_identical_text():
    conocimiento.crear(texto="Tolerale 30 días", tipo="regla", ambito="cliente",
                       nodo="clientes", efecto="ajusta_umbral", entidad="Doña Elsa")
    assert conocimiento.find_conflict(
        texto="Tolerale 30 días", nodo="clientes", entidad="Doña Elsa",
        efecto="ajusta_umbral") is None


def test_find_conflict_is_none_for_a_different_efecto():
    conocimiento.crear(texto="Tolerale 30 días", tipo="regla", ambito="cliente",
                       nodo="clientes", efecto="ajusta_umbral", entidad="Doña Elsa")
    assert conocimiento.find_conflict(
        texto="Otra regla", nodo="clientes", entidad="Doña Elsa",
        efecto="suprime_alerta") is None
```

- [ ] **Step 9: Run to verify it fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_conocimiento_decay.py -k find_conflict -v`
Expected: FAIL — no `find_conflict`.

- [ ] **Step 10: Implement `find_conflict`**

```python
# backend/core/conocimiento.py — add after find_duplicate() (after line 276)
def find_conflict(*, texto: str, nodo: str, entidad: str | None,
                  efecto: str) -> dict | None:
    """An existing ACTIVE piece with the same (entidad, nodo, efecto) but
    DIFFERENT texto — a deterministic, narrow check (never an LLM
    judgment): same substring-normalized entidad match as find_duplicate,
    but flags a difference instead of a match. Distinct from
    find_duplicate: a duplicate says the same thing about the same place;
    a conflict says something different about the same (entidad, nodo,
    efecto) triple."""
    target = _norm(texto)
    for p in listar(nodo=nodo, efecto=efecto, incluir_pausadas=False):
        if (_norm(p.get("entidad")) == _norm(entidad)
                and _norm(p.get("texto")) != target):
            return p
    return None
```

- [ ] **Step 11: Run to verify it passes**

Same command as Step 9. Expected: PASS.

- [ ] **Step 12: Commit**

```bash
git add backend/migrations/versions/0045_business_knowledge_decay.py backend/core/db/business_knowledge_repo.py backend/core/conocimiento.py backend/tests/test_conocimiento_decay.py
git commit -m "feat: read-time decay scoring and deterministic conflict detection"
```

- [ ] **Step 13: Wire conflict detection into the create endpoint**

```python
# backend/i18n.py — add
    "api.conocimiento_conflicto": {
        "es": "Ya hay una regla distinta para {entidad} en {nodo} ({efecto}): "
              "\"{texto}\". Revisala antes de crear una nueva.",
        "en": "There's already a different rule for {entidad} in {nodo} ({efecto}): "
              "\"{texto}\". Review it before creating a new one.",
    },
```

```python
# backend/main.py — conocimiento_crear (line 3512-3522), add the check before conocimiento.crear
@app.post("/api/conocimiento")
def conocimiento_crear(req: ConocimientoNuevo, u: dict = Depends(require_admin)):
    from core import fechas
    conflicto = conocimiento.find_conflict(
        texto=req.texto, nodo=req.nodo, entidad=req.entidad, efecto=req.efecto)
    if conflicto:
        raise HTTPException(status_code=409, detail=i18n.t(
            "api.conocimiento_conflicto", _lang(u), entidad=req.entidad or "",
            nodo=req.nodo, efecto=req.efecto, texto=conflicto["texto"]))
    try:
        pieza = conocimiento.crear(
            texto=req.texto, tipo=req.tipo, ambito=req.ambito, nodo=req.nodo,
            efecto=req.efecto, entidad=req.entidad, params=req.params,
            origen={"quien": u["username"], "cuando": fechas.hoy().isoformat()})
    except conocimiento.ConocimientoInvalido as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "pieza": pieza}
```

- [ ] **Step 14: Failing-then-passing test for the 409**

```python
# backend/tests/test_conocimiento_confirmar.py — add
def test_create_endpoint_blocks_a_conflicting_rule(tokens):
    conocimiento.crear(texto="Tolerale 30 días", tipo="regla", ambito="cliente",
                       nodo="clientes", efecto="ajusta_umbral", entidad="Doña Elsa")
    r = client.post("/api/conocimiento", json={
        "texto": "Tolerale 45 días", "tipo": "regla", "ambito": "cliente",
        "nodo": "clientes", "efecto": "ajusta_umbral", "entidad": "Doña Elsa"},
        headers={"Authorization": f"Bearer {tokens['emilio']}"})
    assert r.status_code == 409
```

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_conocimiento_confirmar.py -k conflicting -v`
Expected: FAIL then, after Step 13's code is in place, PASS.

- [ ] **Step 15: Commit**

```bash
git add backend/i18n.py backend/main.py backend/tests/test_conocimiento_confirmar.py
git commit -m "feat: block creating a knowledge piece that conflicts with an existing one"
```

- [ ] **Step 16: Add to the stack**

```bash
gh stack add pr4-knowledge-decay
```

---

### Task 5: Archive state machine

**Files:**
- Create: `backend/migrations/versions/0046_business_knowledge_archive_states.py`
- Modify: `backend/core/db/business_knowledge_repo.py` (`_COLS`, `_to_piece`, new `set_superseded`)
- Modify: `backend/core/conocimiento.py` (`archive`, `supersede`, `reconfirm`; `listar`'s new `incluir_archivadas` param; `rechazar`/`borrar` docstring note — behavior for pending-rejection is unchanged, only the new normal-retirement path changes)
- Modify: `backend/main.py` (three new routes)
- Modify: `backend/i18n.py`
- Modify: `frontend/src/lib/api.js`, `frontend/src/components/assistant/KnowledgePanel.tsx` (Review + Archived tabs)
- Modify: `frontend/src/lib/locales/en.js`, `frontend/src/lib/locales/es.js`
- Test: `backend/tests/test_conocimiento_decay.py` (extend)

**Interfaces:**
- Consumes: `conocimiento.needs_review`/`freshness` from Task 4.
- Produces: `conocimiento.archive(pid, *, actor, motivo=None) -> dict | None`, `conocimiento.supersede(pid, *, replacement_id, actor) -> dict | None`, `conocimiento.reconfirm(pid, *, actor) -> dict | None`, `conocimiento.listar(..., incluir_archivadas: bool = False)`.

- [ ] **Step 1: Write the migration**

```python
# backend/migrations/versions/0046_business_knowledge_archive_states.py
"""add archive/supersede states to business_knowledge_pieces

Revision ID: 0046
Revises: 0045
Create Date: 2026-09-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("business_knowledge_pieces",
        sa.Column("superseded_by", sa.Text, nullable=True))
    op.drop_constraint("business_knowledge_pieces_estado_check", "business_knowledge_pieces")
    op.create_check_constraint(
        "business_knowledge_pieces_estado_check", "business_knowledge_pieces",
        "estado IN ('activo', 'pausado', 'pendiente', 'revisar', 'superada', 'archivada')")


def downgrade() -> None:
    op.drop_constraint("business_knowledge_pieces_estado_check", "business_knowledge_pieces")
    op.create_check_constraint(
        "business_knowledge_pieces_estado_check", "business_knowledge_pieces",
        "estado IN ('activo', 'pausado', 'pendiente')")
    op.drop_column("business_knowledge_pieces", "superseded_by")
```

- [ ] **Step 2: Run and verify**

Run: `cd backend && ../.venv/Scripts/python.exe -m alembic upgrade head`
Expected: no errors, head now `0046`.

- [ ] **Step 3: Repo layer**

```python
# backend/core/db/business_knowledge_repo.py — _COLS gains "superseded_by"
_COLS = ("id", "texto", "texto_en", "tipo", "ambito", "entidad", "nodo",
         "efecto", "efecto_profundo", "params", "origen", "estado",
         "veces_aplicada", "confidence", "evidence_count",
         "last_reinforced_at", "half_life_days", "superseded_by")
```

```python
# _to_piece — add "superseded_by": row["superseded_by"],
```

```python
# add after update_reinforcement()
def set_superseded(tenant_id: str, piece_id: str, *, superseded_by: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "UPDATE business_knowledge_pieces SET estado = 'superada', "
                "superseded_by = :sup_by "
                f"WHERE id = :id RETURNING {', '.join(_COLS)}"
            ),
            {"sup_by": superseded_by, "id": piece_id},
        ).mappings().one_or_none()
    return _to_piece(row) if row else None
```

- [ ] **Step 4: Failing test — archive/supersede/reconfirm + listar filtering**

```python
# backend/tests/test_conocimiento_decay.py — add
def test_archive_moves_an_active_piece_out_of_aplicables():
    p = conocimiento.crear(texto="x", tipo="regla", ambito="cliente", nodo="clientes",
                           efecto="ajusta_umbral", entidad="Doña Elsa")
    conocimiento.archive(p["id"], actor="aldo")
    assert conocimiento.detalle(p["id"])["estado"] == "archivada"
    assert conocimiento.para("Doña Elsa", nodo="clientes") == []


def test_listar_excludes_archived_by_default():
    p = conocimiento.crear(texto="x", tipo="contexto", ambito="global",
                           nodo="caja", efecto="contexto_para_angela")
    conocimiento.archive(p["id"], actor="aldo")
    assert conocimiento.listar() == []
    assert len(conocimiento.listar(incluir_archivadas=True)) == 1


def test_supersede_links_the_replacement():
    old = conocimiento.crear(texto="Tolerale 30 días", tipo="regla", ambito="cliente",
                             nodo="clientes", efecto="ajusta_umbral", entidad="Doña Elsa")
    new = conocimiento.crear(texto="Tolerale 45 días", tipo="regla", ambito="cliente",
                             nodo="clientes", efecto="ajusta_umbral", entidad="Doña Elsa")
    conocimiento.supersede(old["id"], replacement_id=new["id"], actor="aldo")
    assert conocimiento.detalle(old["id"])["estado"] == "superada"
    assert conocimiento.detalle(old["id"])["superseded_by"] == new["id"]


def test_reconfirm_reinforces_and_reactivates_from_revisar():
    p = conocimiento.crear(texto="x", tipo="contexto", ambito="global",
                           nodo="caja", efecto="contexto_para_angela")
    conocimiento.set_estado(p["id"], "revisar")
    out = conocimiento.reconfirm(p["id"], actor="aldo")
    assert out["estado"] == "activo"
    assert out["evidence_count"] == p["evidence_count"] + 1
```

- [ ] **Step 5: Run to verify it fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_conocimiento_decay.py -k "archive or supersede or reconfirm" -v`
Expected: FAIL.

- [ ] **Step 6: Implement**

```python
# backend/core/conocimiento.py — ESTADOS gains the three new values (line 53)
ESTADOS = {"activo", "pausado", "pendiente", "revisar", "superada", "archivada"}
```

```python
# listar() — add incluir_archivadas param (line 101-132), replace signature and
# the final append-guard
def listar(nodo: str | None = None, tipo: str | None = None,
           entidad: str | None = None, ambito: str | None = None,
           incluir_pausadas: bool = True, estado: str | None = None,
           incluir_archivadas: bool = False) -> list[dict]:
    piezas = _todas()
    out = []
    for p in piezas:
        if nodo and p.get("nodo") != nodo:
            continue
        if tipo and p.get("tipo") != tipo:
            continue
        if ambito and p.get("ambito") != ambito:
            continue
        if entidad and _norm(p.get("entidad")) != _norm(entidad):
            continue
        if estado:
            if p.get("estado") != estado:
                continue
        elif not incluir_pausadas:
            if p.get("estado") != "activo":
                continue
        elif p.get("estado") == "pendiente":
            continue
        elif not incluir_archivadas and p.get("estado") in ("archivada", "superada"):
            continue
        out.append(p)
    return out
```

```python
# add after rechazar() (after line 352)
def archive(pid: str, *, actor: str, motivo: str | None = None) -> dict | None:
    """Retires a piece that was ever active/paused/revisar — replaces
    borrar() as the normal path so nothing that was once confirmed
    disappears without a trace. borrar() stays for a rejected pendiente
    proposal (nothing to preserve) and explicit admin purges."""
    pieza = set_estado(pid, "archivada")
    if pieza:
        from .audit import AuditLog
        AuditLog(DATA_DIR).record(actor, "archivar_conocimiento", None,
                              {"id": pieza["id"], "nodo": pieza["nodo"], "motivo": motivo})
    return pieza


def supersede(pid: str, *, replacement_id: str, actor: str) -> dict | None:
    from core.db import business_knowledge_repo
    from core.db import tenant as _tenant
    pieza = business_knowledge_repo.set_superseded(
        _tenant.current_tenant_id(), pid, superseded_by=replacement_id)
    if pieza:
        from .audit import AuditLog
        AuditLog(DATA_DIR).record(actor, "reemplazar_conocimiento", None,
                              {"id": pieza["id"], "superseded_by": replacement_id})
    return pieza


def reconfirm(pid: str, *, actor: str) -> dict | None:
    """The review-queue "still valid" action: reinforces the piece and,
    if it was in estado="revisar", brings it back to "activo"."""
    p = detalle(pid)
    if not p:
        return None
    pieza = reinforce(pid)
    if p["estado"] == "revisar":
        pieza = set_estado(pid, "activo")
    from .audit import AuditLog
    AuditLog(DATA_DIR).record(actor, "reconfirmar_conocimiento", None, {"id": pid})
    return pieza
```

`aplicables()`/`para()` need no change: both already require `estado == "activo"` exactly (via `incluir_pausadas=False`), and `"revisar"`/`"superada"`/`"archivada"` are all excluded by not being `"activo"`.

- [ ] **Step 7: Run to verify it passes**

Same command as Step 5. Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/core/conocimiento.py backend/core/db/business_knowledge_repo.py backend/tests/test_conocimiento_decay.py
git commit -m "feat: archive/supersede/reconfirm state transitions"
```

- [ ] **Step 9: Endpoints**

```python
# backend/i18n.py — add
    "api.conocimiento_replacement_inexistente": {
        "es": "La pieza de reemplazo no existe.",
        "en": "The replacement piece doesn't exist.",
    },
```

```python
# backend/main.py — add after conocimiento_rechazar (after line 3574)
class ConocimientoArchivar(BaseModel):
    motivo: str | None = None


@app.post("/api/conocimiento/{pid}/archivar")
def conocimiento_archivar(pid: str, req: ConocimientoArchivar, u: dict = Depends(usuario_actual)):
    p = _editor_o_403(pid, u)
    pieza = conocimiento.archive(pid, actor=u["username"], motivo=req.motivo)
    return {"ok": True, "pieza": pieza}


class ConocimientoReemplazar(BaseModel):
    replacement_id: str


@app.post("/api/conocimiento/{pid}/reemplazar")
def conocimiento_reemplazar(pid: str, req: ConocimientoReemplazar, u: dict = Depends(usuario_actual)):
    _editor_o_403(pid, u)
    if not conocimiento.detalle(req.replacement_id):
        raise HTTPException(status_code=400,
                           detail=i18n.t("api.conocimiento_replacement_inexistente", _lang(u)))
    pieza = conocimiento.supersede(pid, replacement_id=req.replacement_id, actor=u["username"])
    return {"ok": True, "pieza": pieza}


@app.post("/api/conocimiento/{pid}/reconfirmar")
def conocimiento_reconfirmar(pid: str, u: dict = Depends(usuario_actual)):
    _editor_o_403(pid, u)
    pieza = conocimiento.reconfirm(pid, actor=u["username"])
    return {"ok": True, "pieza": pieza}
```

- [ ] **Step 10: Endpoint tests, run, commit**

```python
# backend/tests/test_conocimiento_confirmar.py — add
def test_archive_endpoint_needs_admin_or_author(tokens):
    pieza = conocimiento.crear(texto="x", tipo="contexto", ambito="global",
                               nodo="caja", efecto="contexto_para_angela",
                               origen={"quien": "aldo", "cuando": "2026-09-10"})
    r = client.post(f"/api/conocimiento/{pieza['id']}/archivar", json={},
                    headers={"Authorization": f"Bearer {tokens['vendedor']}"})
    assert r.status_code == 403
    r = client.post(f"/api/conocimiento/{pieza['id']}/archivar", json={},
                    headers={"Authorization": f"Bearer {tokens['emilio']}"})
    assert r.status_code == 200
    assert r.json()["pieza"]["estado"] == "archivada"


def test_reconfirmar_endpoint(tokens):
    pieza = conocimiento.crear(texto="x", tipo="contexto", ambito="global",
                               nodo="caja", efecto="contexto_para_angela")
    conocimiento.set_estado(pieza["id"], "revisar")
    r = client.post(f"/api/conocimiento/{pieza['id']}/reconfirmar", json=None,
                    headers={"Authorization": f"Bearer {tokens['emilio']}"})
    assert r.status_code == 200
    assert r.json()["pieza"]["estado"] == "activo"
```

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_conocimiento_confirmar.py -k "archive_endpoint or reconfirmar_endpoint" -v`
Expected: FAIL then PASS after Step 9's code.

```bash
git add backend/i18n.py backend/main.py backend/tests/test_conocimiento_confirmar.py
git commit -m "feat: archive/replace/reconfirm endpoints"
```

- [ ] **Step 11: Frontend — Review and Archived tabs**

```javascript
// frontend/src/lib/api.js — add
  conocimientoArchivar: (pid, motivo) => post(`/api/conocimiento/${encodeURIComponent(pid)}/archivar`, { motivo }),
  conocimientoReemplazar: (pid, replacementId) => post(`/api/conocimiento/${encodeURIComponent(pid)}/reemplazar`, { replacement_id: replacementId }),
  conocimientoReconfirmar: (pid) => post(`/api/conocimiento/${encodeURIComponent(pid)}/reconfirmar`, {}),
```

```tsx
{/* frontend/src/components/assistant/KnowledgePanel.tsx —
    1. Add a tab switcher above the search bar: "Active" (default, current
       behavior) | "Review" (estado === "revisar" or needs_review) |
       "Archived" (estado in "archivada"/"superada").
    2. In the "Review" tab, each row gets two actions instead of the
       admin-only pause/delete set: Reconfirm (api.conocimientoReconfirmar)
       and Archive (api.conocimientoArchivar) — both available to admin OR
       the piece's own author, same _editor_o_403 rule as edit.
    3. In the "Archived" tab, rows are read-only except a "why" line if
       piece.estado === "superada", showing superseded_by (resolve the
       replacement's texto via a second lookup, or extend the piece
       payload's resumen to include a nested {id, texto} for
       superseded_by — simplest: extend resumen_pieza() to also emit
       "superseded_by_texto" when applicable, mirroring how "quien"/"cuando"
       were added in Task 1). */}
```

```python
# backend/core/conocimiento.py — resumen_pieza() gains one more optional field
def resumen_pieza(p: dict) -> dict:
    origen = p.get("origen") or {}
    sup_texto = None
    if p.get("superseded_by"):
        sup = detalle(p["superseded_by"])
        sup_texto = sup["texto"] if sup else None
    return {"id": p["id"], "tipo": p["tipo"], "texto": p["texto"],
            "texto_en": p.get("texto_en"), "nodo": p["nodo"], "efecto": p["efecto"],
            "efecto_profundo": p.get("efecto_profundo", False),
            "veces_aplicada": p.get("veces_aplicada", 0),
            "cuando": origen.get("cuando"), "quien": origen.get("quien"),
            "superseded_by_texto": sup_texto}
```

```javascript
// frontend/src/lib/locales/en.js
  "chat.knowledge.tab_active": "Active",
  "chat.knowledge.tab_review": "Review",
  "chat.knowledge.tab_archived": "Archived",
  "chat.knowledge.reconfirm": "Still valid",
  "chat.knowledge.archive": "Archive",
  "chat.knowledge.superseded_by": "replaced by: {text}",
```

```javascript
// frontend/src/lib/locales/es.js
  "chat.knowledge.tab_active": "Activas",
  "chat.knowledge.tab_review": "Revisar",
  "chat.knowledge.tab_archived": "Archivadas",
  "chat.knowledge.reconfirm": "Sigue vigente",
  "chat.knowledge.archive": "Archivar",
  "chat.knowledge.superseded_by": "reemplazada por: {text}",
```

- [ ] **Step 12: Test the resumen_pieza extension**

```python
# backend/tests/test_conocimiento_confirmar.py — add
def test_resumen_pieza_includes_the_replacement_text():
    old = conocimiento.crear(texto="Vieja", tipo="regla", ambito="global",
                             nodo="caja", efecto="contexto_para_angela")
    new = conocimiento.crear(texto="Nueva", tipo="regla", ambito="global",
                             nodo="caja", efecto="contexto_para_angela")
    conocimiento.supersede(old["id"], replacement_id=new["id"], actor="aldo")
    resumen = conocimiento.resumen_pieza(conocimiento.detalle(old["id"]))
    assert resumen["superseded_by_texto"] == "Nueva"
```

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_conocimiento_confirmar.py -k superseded_by_texto -v`
Expected: FAIL then PASS.

- [ ] **Step 13: Manually verify in the running app**

`python start_demo.py`, create two conflicting rules via the admin path (accepting the 409 conflict flow from Task 4 by editing one afterward instead), archive one, confirm it disappears from Active and appears under Archived with no further effect on `aplicables()`.

- [ ] **Step 14: Commit**

```bash
git add backend/core/conocimiento.py backend/tests/test_conocimiento_confirmar.py frontend/src/lib/api.js frontend/src/components/assistant/KnowledgePanel.tsx frontend/src/lib/locales/en.js frontend/src/lib/locales/es.js
git commit -m "feat: Review and Archived tabs in the Knowledge panel"
```

- [ ] **Step 15: Add to the stack**

```bash
gh stack add pr5-knowledge-archive
```

---

### Task 6: Chat-taught rules can request a real effect

**Files:**
- Modify: `backend/angela.py` (`proponer_conocimiento`'s `input_schema`, dispatch, system prompt section)
- Modify: `backend/core/conocimiento.py` (no change needed — `validate_proposal` already validates any `tipo`/`efecto` from the catalog)
- Modify: `frontend/src/components/assistant/memory-chips.tsx` (secondary choice on a chip whose proposal carries a real effect)
- Modify: `frontend/src/lib/locales/en.js`, `frontend/src/lib/locales/es.js`
- Test: `backend/tests/test_conocimiento_confirmar.py` (extend)

**Interfaces:**
- Consumes: `conocimiento.validate_proposal` (unchanged), `conocimiento.EFECTOS`/`TIPOS` catalogs (unchanged).
- Produces: `MemoryChip` type in `memory-chips.tsx` gains an optional `suggestedEffect?: {efecto: string, tipo: string}` and a second confirm path.

- [ ] **Step 1: Failing test — the tool can propose a real effect, and confirming "just remember" still forces context**

```python
# backend/tests/test_conocimiento_confirmar.py — add
def test_the_tool_can_propose_a_real_effect():
    angela._set_sesion(usuario="emilio", rol="dueño", features=None, idioma="es")
    result, _ = angela._run_tool("proponer_conocimiento", {
        "texto": "Suprimí la alerta de balanza 2, desvía menos de 1%",
        "nodo": "deposito", "efecto_sugerido": "suprime_alerta",
        "tipo_sugerido": "excepcion"})
    assert result["proposal"]["efecto"] == "suprime_alerta"
    assert result["proposal"]["tipo"] == "excepcion"


def test_confirming_just_context_still_forces_narrative_effect(tokens):
    r = client.post("/api/conocimiento/confirm", json={
        "texto": "Suprimí la alerta de balanza 2", "nodo": "deposito",
        "tipo": "contexto", "efecto": "contexto_para_angela"},  # client explicitly chose "just remember"
        headers={"Authorization": f"Bearer {tokens['emilio']}"})
    assert r.json()["piece"]["efecto"] == "contexto_para_angela"


def test_confirming_apply_the_rule_passes_the_real_effect_through(tokens):
    r = client.post("/api/conocimiento/confirm", json={
        "texto": "Suprimí la alerta de balanza 2", "nodo": "deposito",
        "tipo": "excepcion", "efecto": "suprime_alerta"},  # client explicitly chose "also apply"
        headers={"Authorization": f"Bearer {tokens['emilio']}"})
    assert r.json()["piece"]["efecto"] == "suprime_alerta"
```

Note: the third test already passes today (`validate_proposal`/`crear` already accept any catalog value — the only real change is what the MODEL is allowed to *suggest* and what the CHIP UI *offers*, not a new server-side capability). Only the first test is new backend behavior.

- [ ] **Step 2: Run to verify the first test fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_conocimiento_confirmar.py -k "real_effect or just_context or apply_the_rule" -v`
Expected: `test_the_tool_can_propose_a_real_effect` FAILS (`efecto_sugerido` ignored, proposal still forced to `contexto_para_angela`); the other two already PASS.

- [ ] **Step 3: Implement — tool schema and dispatch**

```python
# backend/angela.py — proponer_conocimiento's input_schema (~line 910), add two properties
        "input_schema": {
            "type": "object",
            "properties": {
                "texto": {"type": "string", "description": "the rule/exception/context, in the words of whoever told you"},
                "nodo": {"type": "string", "enum": ["ventas", "inventario", "deposito", "proveedores",
                                                    "clientes", "caja", "equipo", "contexto"],
                        "description": "which area of the business this is about"},
                "entidad": {"type": "string", "description": "a specific customer/supplier/category/employee, if it applies (empty = a global rule)"},
                "ambito": {"type": "string", "enum": ["cliente", "proveedor", "categoria", "empleado", "global"]},
                "efecto_sugerido": {"type": "string",
                    "enum": ["ajusta_umbral", "suprime_alerta", "genera_alerta", "requiere_aprobacion"],
                    "description": "ONLY set this when the conversation clearly implies an operational "
                    "effect, not just narrative context (e.g. 'suppress this alert', 'always flag this "
                    "product as critical'). Omit it for anything that's just useful background."},
                "tipo_sugerido": {"type": "string", "enum": ["regla", "excepcion", "protocolo"],
                    "description": "the kind of rule, only meaningful together with efecto_sugerido."},
            },
            "required": ["texto", "nodo"],
        },
```

```python
# backend/angela.py — the dispatch branch (~line 1838), add the suggestion through
    if name == "proponer_conocimiento":
        from core import conocimiento
        if not memoria.vista(_usuario_actual()).get("knowledge_capture", True):
            return {"ok": False, "motivo": "capture_off"}, None
        efecto_sugerido = args.get("efecto_sugerido")
        try:
            proposal = conocimiento.validate_proposal(
                texto=args.get("texto", ""), tipo=args.get("tipo_sugerido") or "contexto",
                ambito=args.get("ambito") or ("global" if not args.get("entidad") else "categoria"),
                nodo=args.get("nodo", ""),
                efecto=efecto_sugerido or "contexto_para_angela",
                entidad=args.get("entidad"))
        except conocimiento.ConocimientoInvalido as e:
            return {"ok": False, "motivo": str(e)}, None
        existing = conocimiento.find_duplicate(texto=proposal["texto"], nodo=proposal["nodo"],
                                               entidad=proposal["entidad"])
        if existing:
            return {"ok": True, "proposal": proposal, "already_saved": existing["id"]}, None
        result = {"ok": True, "proposal": proposal}
        if efecto_sugerido:
            result["also_narrative"] = {**proposal, "tipo": "contexto", "efecto": "contexto_para_angela"}
        return result, None
```

`also_narrative` gives the frontend the "just remember as context" alternative payload pre-built, so the chip's second choice doesn't need to re-derive it client-side.

- [ ] **Step 4: System prompt addendum**

```python
# backend/angela.py — after the existing proponer_conocimiento guidance (~line 570)
- Si lo que te dicen implica un efecto operativo real (suprimir una alerta puntual,
subir un producto al tope de crítico, exigir aprobación antes de actuar) y no solo
contexto, pasá 'efecto_sugerido' y 'tipo_sugerido' — el chip le va a ofrecer a la
persona elegir entre "solo recordalo" y "aplicalo también". Si tenés dudas, NO
pases efecto_sugerido: es mejor ofrecer de menos (contexto) que de más (una regla
que ajusta un número sin que la persona lo haya pedido explícitamente).
```

- [ ] **Step 5: Run to verify it passes**

Same command as Step 2. Expected: all three PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/angela.py backend/tests/test_conocimiento_confirmar.py
git commit -m "feat: proponer_conocimiento can suggest a real effect, with a two-choice confirm"
```

- [ ] **Step 7: Frontend — the two-choice chip**

```tsx
{/* frontend/src/components/assistant/memory-chips.tsx —
    1. Extend the MemoryChip interface: */}
export interface MemoryChip {
  id: string;
  text: string;
  change: MemoryChange;
  narrativeAlternative?: { id: string; text: string }; // present only when the
    // model suggested a real effect — "id" here is a client-side key, not a
    // server id (nothing is saved yet on either branch)
}

{/* 2. In the "proposed" branch's action buttons, when narrativeAlternative is
       set, render TWO save buttons instead of one Check icon: */}
            {chip.change === "proposed" && (
              <>
                {chip.narrativeAlternative ? (
                  <>
                    <button
                      type="button"
                      aria-label={labels.saveAsRule?.(chip.text) ?? labels.save(chip.text)}
                      onClick={() => onSave?.(chip.id)}
                      className={cn(ghostButton, "px-1.5 text-2xs")}
                    >
                      {labels.applyRuleLabel}
                    </button>
                    <button
                      type="button"
                      aria-label={labels.saveAsContext?.(chip.text) ?? labels.save(chip.text)}
                      onClick={() => onSave?.(chip.narrativeAlternative!.id)}
                      className={cn(ghostButton, "px-1.5 text-2xs")}
                    >
                      {labels.contextOnlyLabel}
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    aria-label={labels.save(chip.text)}
                    onClick={() => onSave?.(chip.id)}
                    className={cn(ghostButton, "size-4 shrink-0")}
                  >
                    <CheckIcon className="size-2.5" />
                  </button>
                )}
                <button
                  type="button"
                  aria-label={labels.dismiss(chip.text)}
                  onClick={() => onDismiss?.(chip.id)}
                  className={cn(ghostButton, "size-4 shrink-0")}
                >
                  <XIcon className="size-2.5" />
                </button>
              </>
            )}
```

```typescript
// MemoryChipsLabels interface — add
export interface MemoryChipsLabels {
  memory: string;
  remembered: (n: number) => string;
  save: (text: string) => string;
  dismiss: (text: string) => string;
  saved: string;
  pending: string;
  applyRuleLabel: string;
  contextOnlyLabel: string;
  saveAsRule?: (text: string) => string;
  saveAsContext?: (text: string) => string;
}
```

(The call site that builds `MemoryChip[]` from a `proponer_conocimiento` tool result — find it via `grep -rn "MemoryChips" frontend/src/components/assistant/ | grep -v memory-chips.tsx` — reads the tool result's `also_narrative` field from Step 3 and sets `narrativeAlternative` when present; `onSave` for the narrative-alternative id calls `api.knowledgeConfirm` with that alternative's `tipo`/`efecto` instead of the primary proposal's.)

```javascript
// frontend/src/lib/locales/en.js
  "chat.memory.apply_rule": "Also apply this rule",
  "chat.memory.context_only": "Just remember",
```

```javascript
// frontend/src/lib/locales/es.js
  "chat.memory.apply_rule": "También aplicarla",
  "chat.memory.context_only": "Solo recordarlo",
```

- [ ] **Step 8: Manually verify in the running app**

`python start_demo.py`, log in as `aldo`, tell Ángela something that implies a real effect ("suprimí la alerta de balanza 2, siempre desvía menos de 1%") and confirm the chip offers both "También aplicarla" and "Solo recordarlo", and that each produces the right `efecto` on the resulting piece (check via the Knowledge panel after confirming).

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/assistant/memory-chips.tsx frontend/src/lib/locales/en.js frontend/src/lib/locales/es.js
git commit -m "feat: chat can offer a real effect alongside remember-as-context"
```

- [ ] **Step 10: Add to the stack and submit**

```bash
gh stack add pr6-chat-real-effect
gh stack submit
```

---

## Self-Review Notes

- **Spec coverage:** every numbered item in the spec's six-PR rollout has a matching Task above. The spec's `PATCH /api/conocimiento/{pid}` was deliberately changed to `POST /api/conocimiento/{pid}/editar` during planning — the codebase never uses PATCH/PUT for this resource (verified against every existing route in `main.py`); substance unchanged, only the verb/path adapted to match convention.
- **Permission model:** `edit_piece`/`archive`/`supersede`/`reconfirm` deliberately do NOT enforce permissions themselves (no `is_admin`/`actor` gate inside `archive`/`supersede`/`reconfirm` beyond taking `actor` for the audit record) — enforcement lives in `main.py`'s `_editor_o_403`, matching the existing separation established by `_revisor_o_404`/`aprobar`/`rechazar`. `edit_piece` is the one exception (it does take `is_admin` to decide the resulting `estado`) because that's a business rule about the DATA (what state results), not an access check.
- **Type consistency check:** `decay_score`/`freshness`/`needs_review` signatures match exactly between this plan and the follow-up `2026-09-10-priorities-knowledge-bridge.md` plan (`insight.knowledge()` reads `conocimiento.freshness(piece)`/`conocimiento.needs_review(piece)` — same names, same single positional `piece` dict argument).
