# Ángela's proposals: a reusable propose → approve → done pattern

Date: 2026-09-01
Status: approved, pending implementation plan

## Context

On `/prioridades`, the restock card (`quiebre_inminente`) is the one place
where Ángela leaves an action already assembled — a purchase order with
product, quantity, supplier and the reasoning — and waits for a human "yes".
The mechanism is real: `POST /api/orden-compra/preparar` →
`core/ordenes.preparar()` writes a draft order and records it in the audit log
with the approving actor.

The presentation and the lifecycle around it are not finished:

1. The proposal UI is a private component (`Propuesta`) buried inside
   `frontend/src/components/CardNegocio.jsx`, not reusable by other cards or
   other parts of the app.
2. It is branded with a generic `<Sparkles>` icon rather than Ángela's mark,
   contradicting the product rule that Ángela is a named identity, not a
   generic "AI" (repo `PRODUCT.md`).
3. Approval works, but:
   - the success state renders the API's full prose message (`r.mensaje`),
     which is verbose and is not a reusable UI pattern;
   - the "done" state lives only in local React state (`propuestaResultado`),
     so a reload shows the proposal again as though nothing happened;
   - the card offers no link to the order that was created, so there is no
     traceability from the page where the decision was made;
   - the priority itself carries no status, so another user sees an untouched
     card and can act on it a second time.

Per the deterministic-core invariant (repo `CLAUDE.md`), the state of "was
this executed?" must be a fact computed in `backend/core/` from real data,
never inferred in the client or narrated by the LLM.

## The defect underneath point 3

`core/ordenes.preparar()` documents itself as idempotent by `(codigo, origen)`
so that approving the same finding twice returns the existing order rather
than duplicating it. It is not idempotent. `core/db/purchase_orders_repo.py`:

```python
def find_draft(tenant_id: str, *, codigo: int | None, origen: str) -> dict | None:
    ...
    if codigo is not None:
        return None
```

The docstring records this as a knowingly-preserved bug from the JSON →
Postgres migration ("not this migration's job to change behavior, only where
it's stored — preserved exactly, including the bug"): the pre-existing JSON
logic compared `o.get("codigo")` against the stored order's own top-level
key, which `preparar()` never sets (`codigo` only ever lands inside
`items[0]["codigo"]`), so the check was always `None == codigo`.

`quiebre_inminente` always passes a real `codigo` (`art.get("codigo")`).
Therefore `find_draft` always returns `None` for it, and `preparar()` always
creates a new order.

Consequence today: the missing status is not merely cosmetic. A second user —
or the same user in a later session — approving the same card silently creates
a **duplicate purchase order**. Fixing this is a prerequisite for the rest of
this spec; the status work is what exposes it.

## Infrastructure that already exists and should be used, not rebuilt

- `core/auditoria.py` already registers `preparar_orden_compra` as
  `{"clase": "stock", "gate": "aprobacion"}`, and `ordenes.preparar()` already
  writes an audit record naming the approving actor. Traceability needs the
  card to *link into* what is already recorded, not new plumbing.
- `core/autonomia.py` already models how proposals are presented, with
  `plata`, `stock` and `permisos` pinned to `pide_ok` and not loosenable by
  any setting. A purchase order is `stock`; it correctly always requires an
  explicit human yes. This spec does not change autonomy policy.
- `frontend/src/desktop/sections/OrdenesCompra.jsx` already lists orders by
  state (`borrador`/`aprobada`/`recibida`/`cancelada`) and already accepts a
  `highlight` prop (`DesktopApp.jsx:543`), with rows keyed by order number.
  So `onNavegar("ordenes_compra", numero)` deep-links to a specific order with
  no new navigation code.

## Decisions taken

Three forks were resolved before design:

1. **State of record: derive from the domain table.** Each proposal type
   declares how to look up its own execution. `purchase_orders` remains the
   single source of truth; nothing is mirrored into a parallel ledger, so
   nothing can drift. Rejected: a generic card-action ledger (dual-write, can
   disagree with the real table) and overloading `pattern_feedback` (which
   means "the owner's opinion of this finding", not "this was executed").
2. **Card lifecycle: stays, marked done, drops rank.** An executed card keeps
   a visible "done" marker with its order number and remains in the list so
   the team can see it was handled, but sorts below open work. Rejected: a
   third "Resuelto hoy" band, and filtering executed cards out entirely
   (which loses the in-place "we handled this" signal).
3. **Blast radius: build the component and contract generically; adopt it for
   the purchase-order proposal type only.** Other propose-then-approve
   surfaces (`cobranza`, `vencimientos`, `piso`) are not refactored here.

Consequence of (3) worth stating explicitly: the resolver registry keys on
`propuesta["tipo"]`, and **both** `quiebre_inminente` and `sobrecompra` use
`tipo: "orden_compra"` (`core/oportunidades_neg.py` lines ~615 and ~970).
A single resolver therefore covers both cards; excluding `sobrecompra` would
require writing extra code to suppress correct behavior. Both are in scope.

## Design

### 1. Make `preparar()` genuinely idempotent

In `core/db/purchase_orders_repo.py`, remove the `if codigo is not None:
return None` early-out. Select draft orders by `origin` (a very small set per
origin) and compare `items[0]["codigo"]` in Python.

Rationale for filtering in Python rather than SQL: matching a value inside a
JSON column portably across the SQLite and Postgres backends this repo
targets is awkward, and adding an indexed `codigo` column is a schema
migration this change does not otherwise need. The candidate set is drafts
sharing one origin — small enough that the scan is irrelevant.

Note the behavior this preserves: if the origin's card previously proposed
product A and now proposes product B, `find_draft(codigo=B)` correctly returns
`None` and a second order is created. Two different products genuinely need
two orders; idempotency is per `(origin, codigo)`, not per origin.

### 2. `core/proposal_state.py` — resolve execution from the domain table

A new module owning one question: *has this proposal already been executed?*

```python
RESOLVERS = {"orden_compra": _resolve_purchase_order}

def for_proposal(proposal: dict, origin_id: str) -> dict | None:
    """The executed action for this proposal, or None. Reads the domain
    table; never writes, never mirrors."""
```

`_resolve_purchase_order` must **not** reuse `find_draft`: once a user
approves the order inside `OrdenesCompra`, its status advances
`borrador → aprobada → recibida`, and the card must still read as
acted-upon. It therefore needs a new repo query:

```python
def find_for_origin(tenant_id, *, origen: str, codigo: int | None) -> dict | None:
    """Any non-cancelled order for (origin, codigo), whatever its status."""
```

A `cancelada` order does not count as executed — the card legitimately
returns to open work.

Layering: the resolver calls `ordenes.find_for_origin()`, a thin wrapper that
resolves the current tenant and delegates to the repo — mirroring how
`ordenes.preparar()`/`ordenes.listar()` already wrap
`purchase_orders_repo`. `proposal_state.py` never touches a repo or a tenant
id directly, so adding a resolver for a future proposal type means calling
that type's own `core/` module, not learning the persistence layer.

### 3. Card contract: the `action_taken` field

`priorities._compose` attaches to every card carrying a `propuesta`:

```python
"action_taken": {
    "type":     "orden_compra",
    "label":    "OC-2026-0901",   # order["numero"]; also the highlight target
    "actor":    "Aldo",           # order["aprobada_por"] — who pressed approve,
                                  # NOT ["preparada_por"], which is always "Ángela"
    "date":     "2026-07-07T09:14:02",  # order["preparada"] (ISO timestamp);
                                        # the client formats it for display
    "status":   "borrador",       # order["estado"]
    "navigate": "ordenes_compra",
} | None
```

Field names are English per the repo coding standard, even though neighbouring
card fields (`titulo`, `resumen`, `drill`, `propuesta`) are pre-existing
Spanish; the standard applies to new code and forbids blanket-renaming
existing identifiers as a side effect.

Every value here is data, not prose — an order number, a person's name, a
timestamp, a status enum. All display copy ("Aprobada por …", "Ver la orden")
lives in the frontend locales, so this field needs no `backend/i18n.py` keys
and the status can reuse the existing `ordenes.estado_*` strings the orders
screen already renders.

This is composed in `_compose`, i.e. inside the `analisis_cache` boundary
alongside `confidence`, so it is computed once per request like every other
derived card field.

### 4. Ranking and the badge

- `split_and_rank`'s `act_key` gains a leading sort term: cards with
  `action_taken` sort last within `act`. They stay visible; nothing vanishes.
- `badge_of()` and `inbox()["badge"]` stop counting executed cards. "N things
  to do today" should not include work already done. This feeds the sidebar
  dot (`DesktopApp.jsx`), the `Inicio` KPI tile, and the `prioridades.sub_count`
  page header.
- `recuperable` is deliberately **unchanged**: a draft purchase order has not
  recovered any money, and it is a canonical cross-screen number with its own
  tests (`opn.recuperable`).

### 5. `components/AngelaProposal.jsx` — the reusable component

Extracted from `CardNegocio.jsx` into its own file, because the goal is reuse
beyond this card. The contract is generic — it knows nothing about purchase
orders:

```
proposal     { title, detail }
onApprove    () => Promise
working      bool
actionTaken  { label, actor, date, status, onOpen } | null
onDismiss    () => void
```

Three states:

- **pending** — `AngelaMark` + title + detail + [Aprobar] [Después] + the
  existing "no sale a ningún lado hasta que la mandes" note.
- **working** — approve button disabled, working label.
- **done** — one compact line: check + `OC-2026-0901 · Aldo · hoy` + an arrow
  opening the order. This replaces rendering the API's prose message.

Point 2 is fixed here: `<Sparkles>` becomes `<AngelaMark>`.

Point 3's verbosity is fixed by never rendering `r.mensaje`. On approval the
done row renders optimistically from the response's `orden` object; on the
next load the server's `action_taken` produces the identical row, so the state
survives reload and is identical for every user.

Styling follows the existing system per `DESIGN.md`: one hairline border, soft
ambient shadow, `rounded-xl` controls, and the violet/Ángela accent already
used by the current `Propuesta` block.

### 6. Row badge

`WorkRow` (`sections/Prioridades.jsx`) and `Fila` (`mobile/InsightsMobile.jsx`)
render a muted "Hecho · OC-…" pill when `action_taken` is set, and de-emphasise
the row, so the state is legible from the list without opening the drill.

### 7. Wiring

`drillProps` in `Prioridades.jsx` and `rowOf`/the `DrillNegocio` call in
`InsightsMobile.jsx` pass `actionTaken` through, mapping `navigate` + `label`
onto `onOpen: () => onNavegar("ordenes_compra", label)`. Both screens already
thread the other drill props after the earlier parity fix, so this follows the
established path.

## Testing

Backend (`backend/tests/`):

- `find_draft` with a real `codigo` returns the existing draft. **This test
  fails against current code** — it is the regression guard for the documented
  bug.
- `preparar()` invoked twice with the same `(codigo, origen)` yields exactly
  one order; invoked with a different `codigo` under the same origin yields
  two.
- `find_for_origin` returns the order for statuses `borrador`, `aprobada` and
  `recibida`, and `None` for `cancelada`.
- `proposal_state.for_proposal` returns `None` for an unknown proposal type
  rather than raising.
- `inbox()` sets `action_taken` on the restock card once an order exists for
  it, and leaves it `None` otherwise.
- `inbox()["badge"]` drops by one when a card becomes executed.
- Executed cards sort after open cards within `act`.

Frontend: no test runner is configured in `frontend/` (no eslint config, no
test script), so verification is `npx vite build` plus manual check of the
three component states. Adding a frontend test harness is out of scope.

Existing suite: `tests/test_p27.py::test_demo_set_cerrado_completo` and
`::test_demo_numeros_canonicos_del_guion` already fail on `main` for an
unrelated reason (the demo dataset no longer produces a `cliente_frio` card).
Confirmed pre-existing against a stashed tree; not to be "fixed" by this work.

## Out of scope

- **"Después" remains a local dismiss.** Making it a real, audited, per-user
  snooze needs its own persistence and visibility decision. The component
  exposes `onDismiss` so it can be wired later without redesign.
- Refactoring `cobranza`, `vencimientos` and `piso` onto `AngelaProposal`.
- Any change to `autonomia.py` policy or to the `recuperable` calculation.
- Renaming pre-existing Spanish identifiers (`propuestaTrabajando`,
  `onAprobarPropuesta`, `item.origen`, the `origen` request-body field) or the
  backend API wire format.
- A frontend test harness.

## Files touched

| File | Change |
|---|---|
| `backend/core/db/purchase_orders_repo.py` | fix `find_draft`; add `find_for_origin` |
| `backend/core/proposal_state.py` | new — resolver registry |
| `backend/core/ordenes.py` | expose the origin lookup used by the resolver |
| `backend/core/priorities.py` | attach `action_taken`; rank and badge changes |
| `frontend/src/components/AngelaProposal.jsx` | new — the reusable component |
| `frontend/src/components/CardNegocio.jsx` | drop private `Propuesta`, consume the new one, pass `actionTaken` |
| `frontend/src/sections/Prioridades.jsx` | pass `actionTaken`; row badge |
| `frontend/src/mobile/InsightsMobile.jsx` | pass `actionTaken`; row badge |
| `frontend/src/lib/locales/{es,en}.js` | done-state copy |
| `backend/tests/` | the cases above |
