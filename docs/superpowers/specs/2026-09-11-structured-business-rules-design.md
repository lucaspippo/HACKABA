# Structured business rules: a deterministic SI/ENTONCES layer alongside free-text memory

Date: 2026-09-11
Status: approved design — ready for implementation planning

## Why

`core/conocimiento.py` is Ángela's business memory today, but every piece is
free text: the LLM narrates it, a human reads it, nothing executes it. For a
class of business rules — "if client X orders more than 100 units, apply a
5% discount"; "if supplier X's delivery reports damage, mark the receipt
partial and notify purchasing"; "if a product has never been ordered by this
client before, or the amount exceeds $X, don't auto-execute, ask a human" —
that's the wrong shape. The condition and the action are precise; asking an
LLM to re-derive the result from a paragraph every time it applies invites
the same request producing two different answers on two different runs.

The fix is the same separation the rest of the product already follows: an
LLM extracts a rule from a conversation once, structures it into a
condition/action pair, and a deterministic engine — plain Python, not a
model call — evaluates it against real facts from then on. Full background
lives in the vault: `PolPilot/Impacto en Angela - Clickie y Lightfield.md`.
This spec is the actionable subset, scoped to three reference use cases used
only to validate the design — not a request to wire them into a real
order/receiving flow, which doesn't exist yet in this codebase.

## Goals

- A rule is stored as a structured condition (a small boolean-tree DSL over
  named fields) and a structured action (a typed list), not prose.
- Every rule records provenance: author, source medium, creation time — and,
  when it replaces an older rule, a version link back to it rather than
  overwriting.
- A rule can reference a real business entity (client/supplier/product) by a
  resolved ID, not a name matched again at evaluation time.
- Given a fact (a dict of field → value), the engine deterministically
  returns which active rules match and what actions they resolve to.
- A rule can carry its own historical test cases and be re-verified against
  them — most useful right after editing it.
- Ángela can propose a rule from a conversation (confirmed by a human before
  it's saved, like `proponer_conocimiento`), list existing rules, and hand
  the engine a fact to evaluate — she never computes the result herself.

## Non-goals (explicitly out of scope for this spec)

- Wiring rule evaluation into any real order-entry, receiving, or
  fulfillment flow. No such flow exists in this codebase yet; the three
  reference use cases are validated with direct engine calls and tests, not
  a live integration into `core/ventas.py` / `core/oportunidades_neg.py`.
- Actually executing an action's side effect (sending a notification,
  mutating an order). The engine resolves *what* the action is; a future
  spec wires it to a real effect once there's a real flow to attach it to.
- Any change to `core/conocimiento.py`'s own schema, matching, or lifecycle.
  The two systems are siblings, connected only by an optional
  `knowledge_piece_id` reference on a rule.
- Any change to `core/memoria.py` (the separate per-user preferences system).
- A general-purpose expression language, rule-authoring UI, or a frontend
  panel. This spec covers the engine and the Ángela chat surface only.
- **Promoting a rule out of `pending` from inside the app.** There is no HTTP
  route and no Ángela tool for `pause` / `activate` / `archive` / `supersede`;
  the engine exposes them, nothing calls them. A rule whose entity resolution
  was ambiguous therefore lands `pending` and stays there until a follow-up
  spec adds a review surface. Recorded here (2026-09-12) as a deliberate
  deferral, not an oversight.
- Decay/staleness scoring for rules (unlike `conocimiento` pieces). A rule is
  either in force or it's been paused/superseded by a human decision — there
  is no "this hasn't been reinforced lately" signal for a SI/ENTONCES rule.

## Language rule for new code

Per `CLAUDE.md`: every new identifier — table/column names, module and
function names, variables, comments, new Ángela tool names — is English.
Comments are added only where the *why* isn't obvious from the code itself;
default to none.

One deliberate exception, confirmed with the user: the stored **values** of
the `node` and `scope` columns (`ventas`, `inventario`, `deposito`,
`proveedores`, `clientes`, `caja`, `equipo`, `contexto`, and
`cliente`/`proveedor`/`categoria`/`empleado`/`global`) reuse the exact
Spanish catalog `core/conocimiento.py` already defines (`NODOS`, `AMBITOS`).
These are shared business-domain vocabulary used system-wide (the 8 Business
Map nodes, `NODO_FEATURE` visibility scoping) — forking them into a second,
English-valued catalog for this one new table would fragment one concept
into two vocabularies and require a translation layer for the
`knowledge_piece_id` cross-reference and visibility reuse, for no benefit.
Every other enum introduced by this spec (`status`, `origin.source`, action
`type`, condition `operator`) is new vocabulary with no legacy tie, so it's
English throughout.

## Storage

New table `business_rules`, migration `0048_business_rules.py`, following
`business_knowledge_pieces`' own conventions (see `0039_business_knowledge_pieces.py`):
PK `(tenant_id, id)`, row-level security tenant-isolation policy, added to
`core/db/tenant_tables.py`.

```
id                 text, "r" + 8 hex chars
tenant_id          uuid, FK tenants(id)
description        text                          -- human-readable summary
condition          jsonb                          -- see DSL below
action             jsonb                          -- see DSL below
node               text   -- ventas/inventario/deposito/proveedores/clientes/caja/equipo/contexto
scope              text   -- cliente/proveedor/categoria/empleado/global
entity_name        text, nullable                 -- display name as given (e.g. "Despensa Doña Elsa")
entity_type        text, nullable                 -- cliente/proveedor/producto
entity_id          text, nullable                 -- resolved real ID, see Entity resolution
origin             jsonb  -- {author, created_at, source}
knowledge_piece_id text, nullable                 -- FK business_knowledge_pieces(id), optional
status             text   -- active/paused/pending/archived/superseded
supersedes         text, nullable                 -- FK to an earlier business_rules.id
superseded_by      text, nullable
version            integer, default 1             -- display only; the chain is the real history
test_cases         jsonb, default '[]'
created_at         timestamptz, default now()
```

Check constraints mirror `conocimiento`'s: `node` against the 8-value
catalog, `scope` against the 5-value catalog, `status` against
`active/paused/pending/archived/superseded`. `scope != 'global'` requires
`entity_name` to be set, same rule `conocimiento.crear` enforces.

`origin.source` ∈ `free_text | voice_note | whatsapp | photo | conversation`.

## Condition/action DSL

**Condition** — a small recursive boolean tree, expressive enough for all
three reference cases without a general expression parser:

```json
{"op": "all", "clauses": [
  {"field": "client_id", "operator": "eq", "value": "$entity"},
  {"field": "quantity", "operator": "gt", "value": 100}
]}
```

`op` ∈ `all` (AND) / `any` (OR). Each entry in `clauses` is either an atomic
clause `{field, operator, value}` or another `{op, clauses}` node (one level
of nesting covers reference case 3's `A OR B` inside an implicit top-level
AND with the rest). `operator` ∈ `eq, ne, gt, gte, lt, lte, in, not_in`.
`field` is looked up directly in the fact dict passed to `evaluate()` — no
schema registry; an unknown field simply never matches.

The literal string `"$entity"` as a clause's `value` is a placeholder for
"the resolved entity_id of this rule" — whoever writes the condition (a
human, or Ángela via `propose_rule`) names the *field* an entity check
belongs on (`client_id`, `supplier_id`, ...) without needing to already know
the real ID, since that's only resolved during `create()` (see Entity
resolution below). `create()` substitutes every `"$entity"` occurrence with
the resolved `entity_id` before storing the condition; a stored rule never
contains the placeholder. A `scope != "global"` rule whose condition has no
`"$entity"` placeholder anywhere is rejected — a rule tied to one entity
that doesn't actually gate on it is very likely a mistake.

**Action** — a list of typed steps, each independently returned to the
caller, never interpreted or executed by the engine itself:

```json
[{"type": "apply_discount", "params": {"percent": 5}},
 {"type": "mark_receipt_partial", "params": {}},
 {"type": "notify", "params": {"target": "purchasing"}},
 {"type": "require_human_confirmation", "params": {}}]
```

`type` is an open-ended string (not DB-constrained) validated at creation
time against a small catalog in `core/rules.py`
(`apply_discount, mark_receipt_partial, notify, require_human_confirmation`)
— extending it later is adding one literal, not a migration.

## Entity resolution

Resolved once, at rule-creation time, never re-resolved at evaluation time.
`core/rules.py` looks the given `entity_name` up against the domain's own
existing lookups depending on `entity_type`:

- `cliente` → normalized substring match over `core/cuentas.py`'s `listar()`.
  (Correction, 2026-09-12: this spec originally said `cuentas.buscar(nombre)`.
  That is wrong and the implementation is right — `buscar()` returns the first
  substring hit and structurally cannot report that a second candidate also
  matched, which would make the "ambiguous → pending" rule below
  unimplementable.)
- `producto` → `core/ventas_cliente.py`'s `buscar_producto(texto)`
- `proveedor` → normalized substring match over `core/proveedores.py`'s
  `listar()` (no name-search helper exists there yet; this spec adds one
  small local match, not a refactor of that module)

A unique match resolves one `entity_id`, substituted into the condition's
`"$entity"` placeholder(s), and the rule is created with whatever `status`
was requested (`active` by default). No match, or more than one candidate,
forces `status="pending"` regardless of what was requested — the same
"needs a human before it's live" outcome `conocimiento`'s unreviewed
proposals already use, so a rule never goes live pointed at the wrong
client. Both cases collapse to the same `None` return from the resolver;
the caller doesn't need to distinguish "not found" from "ambiguous" since
the outcome (pending, human reviews it) is identical either way.

`scope="global"` rules have no `entity_name`/`entity_type`/`entity_id` and
match on their condition's fields alone.

## Engine API (`core/rules.py`)

```
create(*, description, condition, action, node, scope, entity_name=None,
       entity_type=None, origin, knowledge_piece_id=None,
       test_cases=None) -> dict
list_rules(node=None, scope=None, entity_id=None, status=None) -> list[dict]
get(rule_id) -> dict | None
pause(rule_id) / activate(rule_id) / archive(rule_id, *, actor) -> dict | None
supersede(rule_id, *, replacement_id, actor) -> dict | None

evaluate(facts: dict) -> list[{rule_id, description, actions}]
verify(rule_id) -> {ok: bool, results: [{case, expected, actual, ok}]}
```

`evaluate` only considers `status="active"` rules and matches each one's
already-stored `condition` tree against `facts` field by field — plain
recursive tree evaluation, no entity-specific logic at this stage. Entity
scoping isn't a separate step at evaluation time because it was already
baked into the condition at `create()` time (the `"$entity"` substitution
above): a non-global rule's condition already contains a concrete `eq`
clause on its one resolved `entity_id`, so it simply can't match a fact
about a different entity. `evaluate` returns every rule whose full
condition matches, each with its resolved `action`, and performs no side
effects itself.

`verify` replays each of a rule's own `test_cases` — `{"facts": {...},
"expected_action": [...] | null}` — through that single rule's condition and
action, and reports whether the actual resolved action matches what was
expected. This is deliberately scoped to one rule against its own cases, not
a system-wide backtest across the whole ruleset — cheap enough to run right
after an edit, which is the stated use case.

Audit trail reuses `core/audit.py`'s `AuditLog`, same call shape
`conocimiento.py` already uses for `crear`/`edit_piece`/`archive`.

## Ángela integration

Three new tools in `angela.py`'s `TOOLS`, English-named per the confirmed
language decision (the only English tool names among otherwise-Spanish
ones — a deliberate, isolated exception, not a precedent to rename the
rest):

- `propose_rule` — Ángela structures a SI/ENTONCES she heard into
  `{description, condition, action, node, scope, entity_name}`. Like
  `proponer_conocimiento`, this validates (including entity resolution) but
  saves nothing; it returns a proposal for a chip the user taps to confirm,
  persisted through a new `POST /api/rules/confirm` endpoint mirroring the
  existing knowledge-confirm one.
- `evaluate_rule_for` — Ángela passes a fact she's built from the
  conversation (e.g. `{"client_id": "...", "quantity": 150}`) and relays
  `evaluate()`'s matches back in her reply; she never computes the discount
  or decision herself.
- `list_rules` — read-only listing, scoped by the same
  `visibles_para`-equivalent role check `conocimiento` already applies (an
  employee sees a node's rules only if they hold that node's feature, plus
  global and their own).

## Testing

`tests/test_rules.py`, exercising exactly the three reference cases as the
design's validation, per the user's explicit "no implementes de más" scope:

1. Discount by client + quantity — create, evaluate a matching and a
   non-matching fact, confirm the resolved `apply_discount` percent.
2. Receiving tolerance by supplier + damage report — an `any`/`all` mix,
   confirm both `mark_receipt_partial` and `notify` come back together.
3. Escalation to a human — the `any` (`OR`) branch (product never seen for
   this client, or amount over threshold), confirm
   `require_human_confirmation` triggers on either arm independently.

Plus: entity-resolution ambiguity forcing `status="pending"`, `supersede`
creating a new version linked to the old one, and `verify()` catching a
mismatch after an edited action.
