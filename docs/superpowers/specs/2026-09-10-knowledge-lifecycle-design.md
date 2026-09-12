# Knowledge lifecycle: provenance, editing, decay, archive

Date: 2026-09-10
Status: approved design — ready for implementation planning

## Why

`core/conocimiento.py` is the "what Aldo taught Ángela" layer — the part of
the product that literally backs the "PolPilot learns your business"
promise. The skeleton (staging, approve/reject, active/paused, an
append-only audit log) is solid, but several loops are open: the DB already
tracks who taught a piece and when (`origen.quien`/`origen.cuando`) but no
screen shows it; nothing can be edited (only deleted and retyped); nothing
ever decays or gets flagged stale (`confidence.py`'s `sources_stale` signal
is hardcoded `False`); and anything retired is hard-deleted, losing history.

Full background, code citations, and the competitive benchmark (mem0,
Letta/MemGPT, Zep/Graphiti, LangMem, ChatGPT Memory, Claude's memory tool,
AWS AgentCore) live in the vault:
`PolPilot/Memoria de Angela - Investigacion y Propuesta.md`. This spec is
the actionable subset of that research, scoped to one sub-project.

A second, follow-up spec ("Priorities bridge") will cover making a
knowledge piece citable as `evidence()` inside a structured `insight` and
wiring it into `confidence.split_for` — deliberately out of scope here so
this spec doesn't touch `core/insight.py`'s shape, which other builders and
the frontend already consume.

## Goals

- Show provenance (who/when) everywhere a piece appears.
- Let an admin or the piece's own author edit its text, and create pieces
  manually from `KnowledgePanel.tsx` (the backend endpoint already exists).
- Make staleness real: a deterministic, explainable, read-time-only decay
  score per piece, replacing nothing-computed-ever.
- Replace hard-delete-on-retire with a real archive state, so nothing a
  tenant ever confirmed disappears without a trace.
- Let a same-entity conflict between two pieces surface for human review
  instead of silently overwriting or duplicating.
- Let a chat-taught rule request a real operational effect (not just
  narrative context) when the conversation implies one, with an explicit
  second confirmation.

## Non-goals (explicitly out of scope for this spec)

- Anything touching `core/insight.py`, `core/priorities.py`'s `_compose`/
  `_derive`, or `core/confidence.py`'s `split_for` internals — that's the
  Priorities-bridge spec.
- A proactive Priorities-card notification for stale pieces (v1 is
  panel-only, per product decision).
- The onboarding wizard (Fase 6 in the research doc) — a later, smaller
  sub-project.
- Any change to `core/memoria.py` (the separate per-user personalization
  system) — not this layer.
- Generalizing `patrones.py` or LLM-based knowledge extraction from free
  text — see `docs/auto-learn-knowledge-brain.md`, already ruled adjacent
  and explicitly not this.

## Language rule for new code

Per `CLAUDE.md`: every new identifier (function names, migration column
names, new endpoint paths' Python handlers, new frontend props/types,
comments) is English, even inside `core/conocimiento.py`/`angela.py`
files that otherwise use Spanish identifiers for existing code — those
existing names (`crear`, `listar`, `aprobar`, `pausar`, `activar`,
`borrar`, `aplicables`, `para`) are **not** renamed. The one deliberate
exception: the new `estado` enum values (`revisar`, `superada`,
`archivada`) stay Spanish, extending the existing `activo`/`pausado`/
`pendiente` set — these are business-domain data values compared
throughout already-Spanish code, not code identifiers, and mixing
languages inside one enum would be worse than either pure choice.
Product-facing copy (UI strings, i18n values) stays bilingual ES/EN as
already established.

## Cross-cutting design decisions (confirmed with the user)

1. **Edit/archive/reconfirm permission**: `es_admin` OR
   `actor == piece.origen.quien` (string match against the author on
   record). Anyone else doesn't see the controls at all — no new
   permission catalog, reuses the existing `es_admin` check plus one
   equality test.
2. **Non-admin edit re-enters staging**: if the editor is the author but
   not admin, the edited piece's `estado` flips to `pendiente` — same
   trust model as a brand-new proposal. An admin's edit does not
   re-stage (the admin's edit *is* the approval).
3. **Stale-review delivery is passive (v1)**: a filter/badge inside
   `KnowledgePanel.tsx`. No new notification surface, no Priorities card.
4. **Conflict detection is a concrete rule, never an LLM judgment**: two
   pieces conflict when `entidad` (normalized) + `nodo` + `efecto` match
   but `texto`/`params` differ. This is intentionally narrow — it will
   miss genuinely semantic conflicts, which is the correct failure mode
   for "never invent a number": false negatives (a real conflict not
   caught) are safe, false positives (two unrelated pieces marked
   conflicting) would erode trust in the panel.
5. **Decay is read-time only**: `confidence`/`evidence_count`/
   `last_reinforced_at` are stored, but "is this stale right now" is
   always `f(stored values, today)`, recomputed on every read — a cron
   or background job never mutates the row. This keeps the audit trail
   honest (the stored `confidence` only moves on an explicit
   reinforcement event) and matches the pattern used by every serious
   system in the benchmark (mem0, Graphiti, AWS AgentCore).

## Data model changes

### Migration `0045_business_knowledge_decay` (PR 4)

```python
op.add_column("business_knowledge_pieces",
    sa.Column("confidence", sa.Numeric, nullable=False, server_default="0.7"))
op.add_column("business_knowledge_pieces",
    sa.Column("evidence_count", sa.Integer, nullable=False, server_default="1"))
op.add_column("business_knowledge_pieces",
    sa.Column("last_reinforced_at", sa.TIMESTAMP(timezone=True), nullable=False,
              server_default=sa.text("created_at")))  # backfilled from created_at
op.add_column("business_knowledge_pieces",
    sa.Column("half_life_days", sa.Integer, nullable=True))  # NULL = use tipo default
```

`confidence` ∈ [0, 1]. `half_life_days` is a per-piece override; when
`NULL`, the reader falls back to a default keyed by `tipo`:

| `tipo` | default half-life | why |
|---|---|---|
| `regla` | 180 days | ties to a concrete figure that can silently go stale |
| `excepcion` | 120 days | tied to a specific, possibly-time-boxed situation |
| `protocolo` | 365 days | operating procedure, changes rarely |
| `contexto` | 270 days | in between — most of these are narrative context |

These live as a `dict[str, int]` constant next to the existing `TIPOS`
catalog in `core/conocimiento.py`, not in the migration — the migration
only adds the override column.

### Migration `0046_business_knowledge_archive_states` (PR 5)

```python
op.add_column("business_knowledge_pieces",
    sa.Column("superseded_by", sa.Text, nullable=True))
op.drop_constraint("business_knowledge_pieces_estado_check", "business_knowledge_pieces")
op.create_check_constraint(
    "business_knowledge_pieces_estado_check", "business_knowledge_pieces",
    "estado IN ('activo', 'pausado', 'pendiente', 'revisar', 'superada', 'archivada')")
```

`superseded_by` is a soft reference to another piece's `id` (same
tenant); not a DB foreign key, matching how the table already has no FK
from `origen.hallazgo_id` — keeps the migration reversible without
needing to null out references on downgrade.

## Function-level design (`core/conocimiento.py`)

New functions (English names, alongside the existing Spanish ones —
none of the existing functions are renamed):

```python
def decay_score(piece: dict, *, today: date | None = None) -> float:
    """Confidence right now: exponential half-life decay from
    last_reinforced_at, never mutating the stored row. Pure function of
    (piece, today) — same inputs, same output, always.
        confidence(t) = piece["confidence"] * 2 ** (-(age_days) / half_life)
    where age_days = (today - last_reinforced_at).days and half_life is
    piece["half_life_days"] or DEFAULT_HALF_LIFE[piece["tipo"]].
    """

def freshness(piece: dict, *, today: date | None = None) -> str:
    """"fresco" | "atencion" | "revisar" — a traffic-light bucket over
    decay_score(), for display. Same three-tone vocabulary grafo.py and
    priorities.py already use for riesgo/tono, not a new palette."""

def needs_review(piece: dict, *, today: date | None = None,
                  threshold: float = 0.35) -> bool:
    """True when decay_score() has crossed the review floor. Does NOT
    change estado by itself — a background scheduler (or, simplest for
    v1, a computed property read at list-time) surfaces this; nothing
    silently downgrades a piece's real estado."""

def reinforce(pid: str) -> dict | None:
    """Bump evidence_count, reset last_reinforced_at = today, nudge
    confidence up by a DECREASING amount (repeated reinforcement has
    diminishing returns — piece used often approaches but never resets
    past 1.0). Called by marcar_aplicada() (existing) and by an explicit
    "reconfirm" action from the review queue."""

def find_conflict(*, texto: str, nodo: str, entidad: str | None,
                   efecto: str) -> dict | None:
    """An existing ACTIVE piece with the same (entidad, nodo, efecto)
    but different texto/params, or None. Deterministic substring/exact
    match on entidad (same normalization as find_duplicate), never an
    LLM judgment. Distinct from find_duplicate: a duplicate says the same
    thing about the same place; a conflict says something DIFFERENT
    about the same (entidad, nodo, efecto) triple."""

def edit_piece(pid: str, *, actor: str, is_admin: bool, texto: str | None = None,
               texto_en: str | None = None, tipo: str | None = None,
               ambito: str | None = None, efecto: str | None = None,
               params: dict | None = None) -> dict:
    """Validates changed fields against the existing catalog (reuses
    _validar), writes via business_knowledge_repo, logs before/after via
    AuditLog("editar_conocimiento"). If not is_admin, sets
    estado="pendiente" regardless of the piece's prior state (re-enters
    staging). Raises PermissionError if actor is neither admin nor
    piece["origen"]["quien"]; ConocimientoInvalido on a bad field, same
    as crear()."""

def archive(pid: str, *, actor: str, motivo: str | None = None) -> dict | None:
    """Moves an activo/pausado/revisar piece to estado="archivada".
    Replaces borrar() as the normal retirement path for anything that
    was ever active. Audited ("archivar_conocimiento"). Permission: same
    admin-or-author rule as edit_piece."""

def supersede(pid: str, *, replacement_id: str, actor: str) -> dict | None:
    """Moves pid to estado="superada", superseded_by=replacement_id.
    Used from the review-queue "replace" action. Audited."""

def reconfirm(pid: str, *, actor: str) -> dict | None:
    """The review-queue "still valid" action: calls reinforce(pid) and,
    if the piece was in estado="revisar", moves it back to "activo"."""
```

`aplicables()`/`para()` (existing) gain one more excluded state: today
they require `estado == "activo"`; that check doesn't change (`revisar`,
`superada`, `archivada` are all already excluded by not being `"activo"`)
— **no change needed there**, confirmed by re-reading `conocimiento.py:152-163`.

`listar()` (existing) needs one new optional filter,
`incluir_archivadas: bool = False`, so the default listing (panel, grafo)
keeps excluding archived/superseded pieces without a caller having to
remember to filter them out — mirrors how `pendiente` is already excluded
by default today.

## API endpoints (`backend/main.py`)

| Method + path | PR | Notes |
|---|---|---|
| `GET /api/conocimiento/{pid}/historial` | 1 | Filters `audit.py`'s events by this piece's id; admin or author only |
| `PATCH /api/conocimiento/{pid}` | 2 | Body: any subset of editable fields; calls `edit_piece` |
| `POST /api/conocimiento/{pid}/archivar` | 5 | Body: optional `motivo`; calls `archive` |
| `POST /api/conocimiento/{pid}/reemplazar` | 5 | Body: `replacement_id`; calls `supersede` |
| `POST /api/conocimiento/{pid}/reconfirmar` | 5 | Calls `reconfirm` |

All new routes follow the existing ones' pattern in `main.py` (same
auth/tenant middleware, same error-shape on `ConocimientoInvalido`/
`PermissionError`).

## MCP (PR 1)

`consultar_conocimiento` — read-only, delegates to
`angela._run_tool` like every other MCP tool (`mcp_server.py`'s existing
pattern), gated by the same `features` mechanism. Returns active pieces
visible to the requesting user's role (reuses `visibles_para`). No write
tool is added — matches `MCP.md`'s existing read-only posture.

## Frontend changes

- **`KnowledgePanel.tsx`** (PRs 1-5): provenance line per piece
  ("taught by Aldo, 12 Aug"); a pencil/edit affordance opening an inline
  or modal form (reuses the create form's fields, PR 2); a "create" button
  opening that same form empty; an age/last-applied badge + "needs
  review" filter chip (PR 3); a freshness traffic-light dot (PR 4); a
  "Review" tab separate from the main list, showing `needs_review()`
  pieces and conflict pairs with reconfirm/replace/archive actions, plus
  an "Archived" tab (PR 5).
- **`knowledgeStore.ts`** (PR 1): the `KnowledgePiece` type gains
  `origen: {quien: string, cuando: string}` — currently absent from the
  frontend type though present in the backend payload.
- **`KnowledgeCite.tsx`** (PR 1): citation gains "taught by X, date" in
  the citation source metadata.
- **`memory-chips.tsx`** (PRs 1, 6): chip gains provenance-on-hover (PR
  1); for PR 6, a proposed chip whose piece carries a non-narrative
  `efecto` shows a secondary choice ("remember as context" vs. "also
  apply this rule") before the save action commits.

## `proponer_conocimiento` upgrade (PR 6)

Today (`angela.py:1838-1854`) the tool always forces
`tipo="contexto"`, `efecto="contexto_para_angela"`. The upgrade:

1. The tool's `input_schema` gains an optional `efecto_sugerido` enum
   (same five values as `EFECTOS`) and `tipo_sugerido` — the model may
   propose a real effect when the conversation implies one ("suprime
   la alerta de balanza para esta báscula" clearly implies
   `suprime_alerta`, not narrative context).
2. `validate_proposal` (existing) already validates any `tipo`/`efecto`
   against the catalog — no change needed there. The change is only in
   what `angela.py`'s tool-call handler is willing to pass through
   un-downgraded.
3. The confirm step becomes two-part when a real effect is proposed: the
   chip shows both options explicitly (per the frontend section above);
   confirming "just remember" still forces `contexto_para_angela`
   server-side regardless of what was proposed (never trust the client
   to have picked correctly) — confirming "also apply" passes the
   proposed real `efecto`/`tipo` through to `crear()`.
4. The system prompt section (`angela.py:553-570`) gets a short addendum
   telling Ángela when it's appropriate to suggest a real effect vs.
   stay narrative — mirroring the existing "uno por respuesta, solo si
   es DURADERO" discipline already there for proposing at all.

## Testing

- `core/conocimiento.py`: new `tests/test_conocimiento_lifecycle.py`
  (new file, doesn't disturb `test_conocimiento_confirmar.py`'s existing
  coverage) — `decay_score()` math (a table of age/half-life → expected
  score, including the "never negative, approaches 0" edge), `edit_piece`
  permission branches (admin / author / neither), `find_conflict`
  (matching triple + differing text → conflict; matching triple + same
  text → not a conflict, that's `find_duplicate`'s job), the full
  archive/supersede/reconfirm state transitions, and that `aplicables()`/
  `para()` correctly exclude every new non-`activo` state.
- `backend/main.py` routes: extend the existing conocimiento route test
  file with the five new endpoints — success + each permission-denied
  path.
- `mcp_server.py`: one test confirming `consultar_conocimiento` respects
  `features` gating, matching the existing pattern for other MCP tools.
- Frontend: extend `knowledgeStore.test.ts` for the `origen` field;
  component-level tests for the new edit form, review tab, and the PR 6
  two-choice chip follow whatever pattern the existing
  `memory-chips`/`KnowledgePanel` tests (if any) already use.

## Rollout sequence (unchanged from the approved design)

1. Provenance display + `grafo.py` pause-bug fix + history read + MCP
   read tool (no migration)
2. Edit + manual create UI (no migration)
3. Aging visibility (no migration)
4. Real decay + conflict detection (migration 0045)
5. Archive state machine (migration 0046)
6. Chat-taught rules can request a real effect (no migration)

Each ships as its own small PR, reviewable and revertible independently,
matching the repo's existing branch-per-concern history.
