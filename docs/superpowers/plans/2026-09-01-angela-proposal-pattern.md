# Ángela Proposal Pattern Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the restock card's one-off "Ángela proposes a purchase order" block into a reusable propose → approve → done pattern whose executed state is a real, server-derived fact visible to every user.

**Architecture:** Execution state is *derived*, never mirrored — a resolver registry keyed on `propuesta["tipo"]` asks the owning domain module whether this proposal already produced a real record, so `purchase_orders` stays the single source of truth. `priorities.py` attaches the result as an `action_taken` field on the card; executed cards stay visible, sort last, and drop out of the "to do" badge. On the client, a new generic `AngelaProposal` component renders three states (pending / working / done) from that field.

**Tech Stack:** FastAPI + SQLAlchemy Core (`text()` queries, JSONB columns) on Python 3.12+; React 18 + Vite + Tailwind on Node 20+; pytest; recharts.

**Spec:** `docs/superpowers/specs/2026-09-01-angela-proposal-pattern-design.md`

## Global Constraints

- **English-only code.** All new identifiers, comments, docstrings and i18n *keys* must be English (repo `CLAUDE.md`). Product-facing UI *copy* stays Spanish. Do **not** rename pre-existing Spanish identifiers (`propuestaTrabajando`, `onAprobarPropuesta`, `item.origen`, the `origen` request-body field, `_to_orden`'s Spanish dict keys) as a side effect.
- **Deterministic core.** Every number and every state fact comes from `backend/core/` computation. The LLM never computes, remembers or reformats one.
- **Never mirror domain state.** `action_taken` is derived per request from `purchase_orders`. Do not add a table, column, or cache that stores "this card was acted on".
- **Design system** (repo `DESIGN.md`): one hairline border weight (`border-linea`), only soft ambient shadows (`sombra-papel`/`sombra-alta`), `rounded-xl` for controls, `--radius-card` for cards, money in `DM Mono` via `.plata`. Semantic colours are fixed: `rojo` = real problem, `oro` = attention, `salvia` = in-order/upside, `violeta`/Ángela Blue = Ángela.
- **Both locales.** Every new i18n key must be added to `es` and `en` in the same commit — `backend/i18n.py` (`CATALOGO`) for backend keys, `frontend/src/lib/locales/{es,en}.js` for frontend keys.
- **Run tests from `backend/`** with `py -m pytest` (this environment has no `python`/`python3` on PATH). Tests write into the data dir; after a full run restore seeds with `git checkout -- data-demo/`.
- **Pre-existing failures, do not "fix":** `tests/test_p27.py::test_demo_set_cerrado_completo` and `::test_demo_numeros_canonicos_del_guion` already fail on `main` (demo dataset no longer yields a `cliente_frio` card).

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/core/db/purchase_orders_repo.py` | **Modify.** Fix `find_draft`; add `find_for_origin`. Persistence only. |
| `backend/core/ordenes.py` | **Modify.** Add `find_for_origin` wrapper resolving the tenant, mirroring `preparar`/`listar`. |
| `backend/core/proposal_state.py` | **Create.** Resolver registry: given a proposal, return its executed action or `None`. Knows no persistence. |
| `backend/core/priorities.py` | **Modify.** Attach `action_taken`; de-rank executed cards; exclude them from `badge`. |
| `backend/i18n.py` | **Modify.** Done-state labels. |
| `frontend/src/components/AngelaProposal.jsx` | **Create.** The reusable three-state component. Domain-agnostic. |
| `frontend/src/components/CardNegocio.jsx` | **Modify.** Delete private `Propuesta`; consume `AngelaProposal`; accept `actionTaken`. |
| `frontend/src/sections/Prioridades.jsx` | **Modify.** Pass `actionTaken`; row badge. |
| `frontend/src/mobile/InsightsMobile.jsx` | **Modify.** Pass `actionTaken`; row badge. |
| `frontend/src/lib/locales/{es,en}.js` | **Modify.** Done-state copy. |

Task order is dependency order: 1 (repo correctness) → 2 (lookup) → 3 (resolver) → 4 (card contract) → 5 (rank/badge) → 6 (component) → 7 (wiring) → 8 (row badge).

---

### Task 1: Make `find_draft` honour `codigo`

Fixes the documented bug that makes `ordenes.preparar()` non-idempotent, so a second approval returns the existing order instead of minting a duplicate.

**Files:**
- Modify: `backend/core/db/purchase_orders_repo.py:40-60` (`find_draft`)
- Test: `backend/tests/test_purchase_orders_repo.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `find_draft(tenant_id: str, *, codigo: int | None, origen: str) -> dict | None` — unchanged signature, corrected behaviour. Matches a `borrador` order whose `items[0]["codigo"] == codigo`. `items` is a JSONB column and reads back as a decoded `list[dict]`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_purchase_orders_repo.py`:

```python
def _draft(numero, codigo, origen="quiebre_inminente"):
    return {
        "numero": numero, "fecha": "2026-08-24", "proveedor": "Molinos SA",
        "estado": "borrador", "origen": origen, "motivo": "",
        "preparada_por": "Ángela", "aprobada_por": "emilio",
        "preparada": "2026-08-24T10:00:00",
        "items": [{"codigo": codigo, "producto": "Harina", "cantidad": 50}],
    }


def test_find_draft_matches_on_item_codigo(db_tenant):
    purchase_orders_repo.create(db_tenant, _draft("OC-2026-0901", 7))
    found = purchase_orders_repo.find_draft(db_tenant, codigo=7,
                                            origen="quiebre_inminente")
    assert found is not None
    assert found["numero"] == "OC-2026-0901"


def test_find_draft_ignores_other_codigo_same_origin(db_tenant):
    purchase_orders_repo.create(db_tenant, _draft("OC-2026-0901", 7))
    assert purchase_orders_repo.find_draft(
        db_tenant, codigo=8, origen="quiebre_inminente") is None


def test_find_draft_ignores_other_origin(db_tenant):
    purchase_orders_repo.create(db_tenant, _draft("OC-2026-0901", 7, origen="sobrecompra"))
    assert purchase_orders_repo.find_draft(
        db_tenant, codigo=7, origen="quiebre_inminente") is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && py -m pytest tests/test_purchase_orders_repo.py -k find_draft -v`
Expected: `test_find_draft_matches_on_item_codigo` FAILS (`assert None is not None`) because of the `if codigo is not None: return None` early-out. The other two pass vacuously.

- [ ] **Step 3: Fix `find_draft`**

Replace the whole function body (keep the name and signature):

```python
def find_draft(tenant_id: str, *, codigo: int | None, origen: str) -> dict | None:
    """The one existing draft order for (codigo, origen), if any — preparar()
    in core/ordenes.py uses this to stay idempotent.

    `codigo` lives inside the JSONB `items` payload, not in a column, so the
    match happens in Python over the drafts sharing this origin. That set is
    tiny, and it avoids both a schema migration and JSON-in-SQL differences
    between the SQLite and Postgres backends.
    """
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(
            text(f"SELECT {', '.join(_COLS)} FROM purchase_orders "
                 "WHERE status = 'borrador' AND origin = :origen"),
            {"origen": origen},
        ).mappings().all()
    for row in rows:
        orden = _to_orden(row)
        items = orden.get("items") or []
        if items and items[0].get("codigo") == codigo:
            return orden
    return None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && py -m pytest tests/test_purchase_orders_repo.py -v`
Expected: all PASS, including the 4 pre-existing tests.

- [ ] **Step 5: Verify no caller regressed**

Run: `cd backend && py -m pytest tests/test_p38.py tests/test_inventario_crud.py -q`
Expected: PASS. (`test_p38.py` exercises `preparar()`; `test_inventario_crud.py` exercises `crear_manual`.)

- [ ] **Step 6: Commit**

```bash
git add backend/core/db/purchase_orders_repo.py backend/tests/test_purchase_orders_repo.py
git commit -m "Fix find_draft so preparar() is actually idempotent

find_draft returned None whenever codigo was not None, a bug carried over
verbatim from the JSON->Postgres migration. The restock card always passes
a real codigo, so every approval created a new order: approving the same
finding twice produced duplicate purchase orders. Match items[0].codigo in
Python over the drafts for this origin."
```

---

### Task 2: `find_for_origin` — the executed-order lookup

`find_draft` only sees `borrador`. Once a user approves the order in `OrdenesCompra` it becomes `aprobada`/`recibida`, and the card must still read as acted-upon.

**Files:**
- Modify: `backend/core/db/purchase_orders_repo.py` (add after `find_draft`)
- Modify: `backend/core/ordenes.py` (add after `preparar`)
- Test: `backend/tests/test_purchase_orders_repo.py`

**Interfaces:**
- Consumes: `_COLS`, `_to_orden`, `tenant_connection` from Task 1's module.
- Produces:
  - `purchase_orders_repo.find_for_origin(tenant_id: str, *, origen: str, codigo: int | None) -> dict | None` — any order for `(origin, codigo)` whose `status != 'cancelada'`, newest first.
  - `ordenes.find_for_origin(*, origen: str, codigo: int | None) -> dict | None` — tenant-resolving wrapper. This is what Task 3 calls.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_purchase_orders_repo.py`:

```python
def test_find_for_origin_matches_any_non_cancelled_status(db_tenant):
    for estado, numero in (("aprobada", "OC-2026-0902"), ("recibida", "OC-2026-0903")):
        purchase_orders_repo.create(db_tenant, {**_draft(numero, 7), "estado": estado})
        found = purchase_orders_repo.find_for_origin(
            db_tenant, origen="quiebre_inminente", codigo=7)
        assert found is not None, estado
        assert found["estado"] == estado


def test_find_for_origin_ignores_cancelled(db_tenant):
    purchase_orders_repo.create(
        db_tenant, {**_draft("OC-2026-0904", 7), "estado": "cancelada"})
    assert purchase_orders_repo.find_for_origin(
        db_tenant, origen="quiebre_inminente", codigo=7) is None


def test_find_for_origin_matches_draft_too(db_tenant):
    purchase_orders_repo.create(db_tenant, _draft("OC-2026-0905", 7))
    found = purchase_orders_repo.find_for_origin(
        db_tenant, origen="quiebre_inminente", codigo=7)
    assert found["numero"] == "OC-2026-0905"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && py -m pytest tests/test_purchase_orders_repo.py -k find_for_origin -v`
Expected: FAIL with `AttributeError: module 'core.db.purchase_orders_repo' has no attribute 'find_for_origin'`.

- [ ] **Step 3: Add the repo query**

In `backend/core/db/purchase_orders_repo.py`, immediately after `find_draft`:

```python
def find_for_origin(tenant_id: str, *, origen: str, codigo: int | None) -> dict | None:
    """Any order this origin already produced for `codigo`, whatever its
    status — unlike find_draft, which only sees 'borrador'.

    A card stays "acted upon" after someone advances its order to aprobada or
    recibida; only a cancelada order releases it back to open work.
    """
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(
            text(f"SELECT {', '.join(_COLS)} FROM purchase_orders "
                 "WHERE origin = :origen AND status <> 'cancelada' "
                 "ORDER BY prepared_at DESC"),
            {"origen": origen},
        ).mappings().all()
    for row in rows:
        orden = _to_orden(row)
        items = orden.get("items") or []
        if items and items[0].get("codigo") == codigo:
            return orden
    return None
```

- [ ] **Step 4: Add the `core/ordenes.py` wrapper**

In `backend/core/ordenes.py`, immediately after `preparar()`:

```python
def find_for_origin(*, origen: str, codigo: int | None) -> dict | None:
    """The order this finding already produced, if any. Read-only: the
    caller uses it to tell whether a proposal was already executed."""
    from core.db import purchase_orders_repo, tenant as _tenant
    return purchase_orders_repo.find_for_origin(
        _tenant.current_tenant_id(), origen=origen, codigo=codigo)
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd backend && py -m pytest tests/test_purchase_orders_repo.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/core/db/purchase_orders_repo.py backend/core/ordenes.py backend/tests/test_purchase_orders_repo.py
git commit -m "Add find_for_origin: the order a finding already produced

find_draft only sees 'borrador', so a card whose order was since approved or
received would read as untouched. find_for_origin matches any status except
cancelada, which correctly releases the card back to open work."
```

---

### Task 3: `core/proposal_state.py` — the resolver registry

**Files:**
- Create: `backend/core/proposal_state.py`
- Test: `backend/tests/test_proposal_state.py`

**Interfaces:**
- Consumes: `ordenes.find_for_origin` (Task 2).
- Produces: `proposal_state.for_proposal(proposal: dict, origin_id: str) -> dict | None`, returning
  `{"type": str, "label": str, "actor": str, "date": str, "status": str, "navigate": str}`.
  `actor` is the order's `aprobada_por` (the human who pressed approve) — **not** `preparada_por`, which is always the literal `"Ángela"`. `date` is the order's `preparada` ISO timestamp; the client formats it.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_proposal_state.py`:

```python
"""Resolving whether a card's proposal was already executed."""
from __future__ import annotations

from core import proposal_state


def test_unknown_proposal_type_returns_none_without_raising():
    assert proposal_state.for_proposal({"tipo": "no_such_type"}, "whatever") is None


def test_missing_proposal_returns_none():
    assert proposal_state.for_proposal(None, "quiebre_inminente") is None


def test_purchase_order_proposal_resolves_to_the_order(monkeypatch):
    monkeypatch.setattr(
        proposal_state, "_find_order",
        lambda origen, codigo: {
            "numero": "OC-2026-0901", "estado": "borrador",
            "aprobada_por": "Aldo", "preparada_por": "Ángela",
            "preparada": "2026-07-07T09:14:02",
        })
    got = proposal_state.for_proposal(
        {"tipo": "orden_compra", "codigo": 7}, "quiebre_inminente")
    assert got == {
        "type": "orden_compra",
        "label": "OC-2026-0901",
        "actor": "Aldo",
        "date": "2026-07-07T09:14:02",
        "status": "borrador",
        "navigate": "ordenes_compra",
    }


def test_purchase_order_proposal_none_when_no_order(monkeypatch):
    monkeypatch.setattr(proposal_state, "_find_order", lambda origen, codigo: None)
    assert proposal_state.for_proposal(
        {"tipo": "orden_compra", "codigo": 7}, "quiebre_inminente") is None


def test_resolver_failure_is_swallowed(monkeypatch):
    def boom(origen, codigo):
        raise RuntimeError("db down")
    monkeypatch.setattr(proposal_state, "_find_order", boom)
    assert proposal_state.for_proposal(
        {"tipo": "orden_compra", "codigo": 7}, "quiebre_inminente") is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && py -m pytest tests/test_proposal_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.proposal_state'`.

- [ ] **Step 3: Write the module**

Create `backend/core/proposal_state.py`:

```python
"""Has this proposal already been executed?

Ángela leaves an action assembled and waits for a human yes (see
core/autonomia.py: stock, plata and permisos are pinned to `pide_ok` and no
setting loosens them). Once someone approves, the card must say so — to that
person on reload, and to every other user, so nobody acts on it twice.

That fact is DERIVED, never stored: each proposal type declares how to find
the real record it produces, and the domain table stays the single source of
truth. Nothing is mirrored here, so nothing can drift out of sync with it.

Adding a proposal type means adding one resolver that calls that type's own
core/ module — this file never touches a repo or a tenant id.
"""
from __future__ import annotations


def _find_order(origen: str, codigo):
    """Indirection so tests can substitute the lookup without a database."""
    from . import ordenes
    return ordenes.find_for_origin(origen=origen, codigo=codigo)


def _resolve_purchase_order(proposal: dict, origin_id: str) -> dict | None:
    orden = _find_order(origin_id, proposal.get("codigo"))
    if not orden:
        return None
    return {
        "type": "orden_compra",
        "label": orden["numero"],
        # The human who pressed approve. `preparada_por` is always "Ángela",
        # so using it here would credit the agent for the person's decision.
        "actor": orden.get("aprobada_por") or "",
        "date": orden.get("preparada") or "",
        "status": orden.get("estado") or "",
        "navigate": "ordenes_compra",
    }


RESOLVERS = {"orden_compra": _resolve_purchase_order}


def for_proposal(proposal: dict | None, origin_id: str) -> dict | None:
    """The executed action for this proposal, or None if it hasn't run yet.

    Never raises: a card whose resolver fails renders as not-yet-acted-on,
    which is the safe direction — the worst case is showing the proposal
    again, and preparar() is idempotent per (origen, codigo).
    """
    if not proposal:
        return None
    resolver = RESOLVERS.get(proposal.get("tipo"))
    if not resolver:
        return None
    try:
        return resolver(proposal, origin_id)
    except Exception:  # noqa: BLE001 — a lookup failure must not blank the inbox
        return None
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && py -m pytest tests/test_proposal_state.py -v`
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/core/proposal_state.py backend/tests/test_proposal_state.py
git commit -m "Add proposal_state: derive whether a proposal was executed

One resolver per propuesta tipo, each asking that type's own core/ module
whether the real record exists. The domain table stays the source of truth;
nothing is mirrored, so nothing drifts."
```

---

### Task 4: Attach `action_taken` to cards

**Files:**
- Modify: `backend/core/priorities.py:285-301` (`_compose`)
- Test: `backend/tests/test_priorities.py`

**Interfaces:**
- Consumes: `proposal_state.for_proposal` (Task 3).
- Produces: every card dict gains an `action_taken` key — the resolver payload from Task 3, or `None`. Cards without a `propuesta` always get `None`.

Note both `quiebre_inminente` and `sobrecompra` declare `tipo: "orden_compra"` (`core/oportunidades_neg.py` lines ~615 and ~970), so this single resolver covers both.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_priorities.py`:

```python
def test_compose_marks_cards_whose_proposal_already_ran(monkeypatch):
    from core import proposal_state
    monkeypatch.setattr(
        proposal_state, "_find_order",
        lambda origen, codigo: {
            "numero": "OC-2026-0901", "estado": "borrador",
            "aprobada_por": "Aldo", "preparada": "2026-07-07T09:14:02",
        } if origen == "quiebre_inminente" else None)

    con = _item("quiebre_inminente", propuesta={"tipo": "orden_compra", "codigo": 7})
    sin = _item("despertar_dormido")
    for it in priorities.with_action_taken([con, sin]):
        if it["id"] == "quiebre_inminente":
            assert it["action_taken"]["label"] == "OC-2026-0901"
            assert it["action_taken"]["actor"] == "Aldo"
        else:
            assert it["action_taken"] is None


def test_cards_without_a_proposal_are_never_marked():
    out = priorities.with_action_taken([_item("caja_inusual")])
    assert out[0]["action_taken"] is None
```

`_item` is the existing helper at the top of this file; it forwards `**extra` onto the item dict, so `propuesta=` lands correctly.

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && py -m pytest tests/test_priorities.py -k action_taken -v`
Expected: FAIL with `AttributeError: module 'core.priorities' has no attribute 'with_action_taken'`.

- [ ] **Step 3: Add `with_action_taken` and call it from `_compose`**

In `backend/core/priorities.py`, add above `_compose`:

```python
def with_action_taken(items: list[dict]) -> list[dict]:
    """Mark each card whose proposal already produced a real record.

    Derived per request from the domain table (see core/proposal_state.py),
    so every user sees the same answer and a reload never resurrects a
    proposal somebody already approved.
    """
    from . import proposal_state
    for it in items:
        it["action_taken"] = proposal_state.for_proposal(it.get("propuesta"), it["id"])
    return items
```

Then inside `_compose`, extend the existing per-item loop so it reads:

```python
    for it in merged:
        it["drill"]["confidence"] = confidence.level_for(it["drill"], lang)
    with_action_taken(merged)
```

Add `"action_taken": None` to the dict returned by `_item(...)` (alongside `"band": None`) so the key always exists even for cards that never pass through `_compose`.

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && py -m pytest tests/test_priorities.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/core/priorities.py backend/tests/test_priorities.py
git commit -m "Attach action_taken to every card carrying a proposal

Composed alongside confidence, inside the analisis_cache boundary, so it is
computed once per request like every other derived card field."
```

---

### Task 5: De-rank executed cards and drop them from the badge

**Files:**
- Modify: `backend/core/priorities.py` (`split_and_rank`'s `act_key`, and `badge_of`/`inbox`)
- Test: `backend/tests/test_priorities.py`

**Interfaces:**
- Consumes: the `action_taken` key (Task 4).
- Produces: `act` ordered with executed cards last; `inbox()["badge"]` and `badge_of()` counting only `act` cards with `action_taken` falsy.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_priorities.py`:

```python
def test_executed_cards_sort_after_open_ones():
    done = _item("quiebre_inminente", monto=999_999)   # would otherwise rank first
    done["action_taken"] = {"label": "OC-2026-0901"}
    open_ = _item("despertar_dormido", monto=1)
    open_["action_taken"] = None
    act, _watch = priorities.split_and_rank([done, open_])
    assert [i["id"] for i in act] == ["despertar_dormido", "quiebre_inminente"]


def test_badge_counts_only_open_act_cards():
    done = _item("quiebre_inminente")
    done["action_taken"] = {"label": "OC-2026-0901"}
    open_ = _item("despertar_dormido")
    open_["action_taken"] = None
    act, watch = priorities.split_and_rank([done, open_])
    assert priorities.badge_of({"act": act, "watch": watch}) == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && py -m pytest tests/test_priorities.py -k "executed_cards_sort or badge_counts" -v`
Expected: both FAIL — ordering puts the big-`monto` done card first, and `badge_of` returns 2.

- [ ] **Step 3: Implement**

In `split_and_rank`, make `action_taken` the leading term of `act_key`:

```python
    def act_key(it):
        # Executed cards stay visible but sink below open work.
        done = 1 if it.get("action_taken") else 0
        leak = 0 if it["id"] in LEAK_TODAY else 1
        has_monto = 0 if (it.get("monto") or 0) > 0 else 1
```

and put `done` first in the tuple the function returns (keep the remaining terms in their current order).

Replace `badge_of` and the `badge` value in `inbox`:

```python
def badge_of(inbox: dict) -> int:
    """Open work only — a card whose proposal was already executed is done,
    and counting it would keep nagging about finished work."""
    return sum(1 for c in (inbox.get("act") or []) if not c.get("action_taken"))
```

In `inbox()`, change `"badge": len(act),` to `"badge": badge_of({"act": act}),`.

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && py -m pytest tests/test_priorities.py tests/test_priorities_drill.py -v`
Expected: all PASS.

- [ ] **Step 5: Check the wider suite for badge assumptions**

Run: `cd backend && py -m pytest tests/test_p38.py tests/test_p43.py tests/test_cruces.py -q`
Expected: PASS, except the two known pre-existing `test_cruces` failures listed in Global Constraints. If a *different* test asserts an exact `badge`, update it — the new meaning is intended.

- [ ] **Step 6: Commit**

```bash
git add backend/core/priorities.py backend/tests/test_priorities.py
git commit -m "Sink executed cards in the ranking and out of the badge

An executed card stays in the list so the team sees it was handled, but it
sorts below open work and no longer counts toward 'things to do today'."
```

---

### Task 6: The reusable `AngelaProposal` component

**Files:**
- Create: `frontend/src/components/AngelaProposal.jsx`
- Modify: `frontend/src/lib/locales/es.js`, `frontend/src/lib/locales/en.js`

**Interfaces:**
- Consumes: `AngelaMark` from `../components/AngelaMark`; `useT` from `../lib/i18n`.
- Produces: default export `AngelaProposal({ proposal, onApprove, working, actionTaken, onDismiss })` where
  `proposal = { title, detail }`, `actionTaken = { label, actor, date, status, onOpen } | null`.
  Renders `null` when there is no `proposal` and no `actionTaken`.

- [ ] **Step 1: Add the i18n keys**

In `frontend/src/lib/locales/es.js`, beside the existing `cardneg.*` keys:

```js
  "angelaprop.titulo": "Ángela propone",
  "angelaprop.aprobar": "Aprobar",
  "angelaprop.despues": "Después",
  "angelaprop.trabajando": "Preparando…",
  "angelaprop.nota": "Aprobar la deja armada y firmada por vos. No sale a ningún lado hasta que la mandes.",
  "angelaprop.hecho_por": "Aprobada por {actor}",
  "angelaprop.ver": "Ver la orden",
```

The same keys in `frontend/src/lib/locales/en.js`:

```js
  "angelaprop.titulo": "Ángela suggests",
  "angelaprop.aprobar": "Approve",
  "angelaprop.despues": "Later",
  "angelaprop.trabajando": "Preparing…",
  "angelaprop.nota": "Approving leaves it drafted and signed by you. It goes nowhere until you send it.",
  "angelaprop.hecho_por": "Approved by {actor}",
  "angelaprop.ver": "View the order",
```

Keys are English-with-Spanish-values per the Global Constraints; `angelaprop` is a new namespace because the component is no longer specific to `cardneg`.

- [ ] **Step 2: Write the component**

Create `frontend/src/components/AngelaProposal.jsx`:

```jsx
import { useState } from "react";
import { Check, ArrowRight } from "lucide-react";
import AngelaMark from "./AngelaMark";
import { useT } from "../lib/i18n";

// The propose -> approve -> done pattern, reusable by any surface where
// Ángela leaves an action assembled and waits for a human yes.
//
// It is deliberately domain-agnostic: it never mentions purchase orders. The
// caller supplies the copy (`proposal`) and, when the action has already run,
// the record it produced (`actionTaken`) — which comes from the server, not
// from local state, so the done view survives a reload and looks the same to
// every user.
export default function AngelaProposal({ proposal, onApprove, working,
                                         actionTaken, onDismiss }) {
  const t = useT();
  const [postponed, setPostponed] = useState(false);

  // Done wins over pending: if the record exists, the decision is made.
  if (actionTaken) {
    return (
      <div className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1 rounded-xl border border-salvia/25 bg-salvia/[0.06] px-3.5 py-2.5 text-[0.84rem]">
        <Check size={15} className="shrink-0 text-salvia" />
        <span className="plata font-semibold text-tinta">{actionTaken.label}</span>
        {actionTaken.actor && (
          <span className="text-tinta-suave">
            · {t("angelaprop.hecho_por", { actor: actionTaken.actor })}
          </span>
        )}
        {actionTaken.onOpen && (
          <button type="button" onClick={actionTaken.onOpen}
            className="ml-auto inline-flex items-center gap-1 font-semibold text-tinta-suave hover:text-tinta">
            {t("angelaprop.ver")} <ArrowRight size={13} />
          </button>
        )}
      </div>
    );
  }

  if (!proposal || postponed) return null;

  return (
    <div className="mt-4 rounded-xl border border-violeta/25 bg-violeta/[0.05] p-4">
      <p className="flex items-center gap-1.5 text-[0.84rem] font-semibold text-violeta">
        <AngelaMark size={14} /> {t("angelaprop.titulo")}
      </p>
      <p className="mt-1 font-display text-[1rem] font-bold leading-tight">{proposal.title}</p>
      {proposal.detail && (
        <p className="mt-1 text-[0.88rem] leading-snug text-tinta">{proposal.detail}</p>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button onClick={onApprove} disabled={working}
          className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.84rem] font-semibold text-crema disabled:opacity-50">
          <Check size={15} /> {working ? t("angelaprop.trabajando") : t("angelaprop.aprobar")}
        </button>
        <button onClick={() => { setPostponed(true); onDismiss?.(); }} disabled={working}
          className="rounded-full border border-linea px-4 py-2 text-[0.84rem] font-semibold text-tinta-suave hover:text-tinta disabled:opacity-50">
          {t("angelaprop.despues")}
        </button>
      </div>
      <p className="mt-2 text-[0.72rem] leading-snug text-tinta-suave">{t("angelaprop.nota")}</p>
    </div>
  );
}
```

Point 2 of the brief is fixed here: the pending header uses `AngelaMark`, not the generic `Sparkles` the old block used.

- [ ] **Step 3: Verify it compiles**

Run: `cd frontend && npx vite build`
Expected: `✓ built`. (The component is not imported yet; this only proves it parses.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/AngelaProposal.jsx frontend/src/lib/locales/es.js frontend/src/lib/locales/en.js
git commit -m "Add AngelaProposal: the reusable propose -> approve -> done block

Domain-agnostic and driven by server state rather than local state, so the
done view survives a reload and reads the same for every user. Uses Ángela's
mark instead of a generic sparkle."
```

---

### Task 7: Consume it in `CardNegocio` and wire both screens

**Files:**
- Modify: `frontend/src/components/CardNegocio.jsx` (delete `Propuesta`, render `AngelaProposal`)
- Modify: `frontend/src/sections/Prioridades.jsx` (`drillProps`)
- Modify: `frontend/src/mobile/InsightsMobile.jsx` (`rowOf` and the `DrillNegocio` call)

**Interfaces:**
- Consumes: `AngelaProposal` (Task 6); `action_taken` on the card (Task 4).
- Produces: `DrillNegocio` accepts a new `actionTaken` prop and no longer renders the removed `Propuesta`. Existing props `propuesta`, `onAprobarPropuesta`, `propuestaTrabajando` keep their current Spanish names (pre-existing; renaming them is out of scope). `propuestaResultado` is removed — the done state now comes from `actionTaken`.

- [ ] **Step 1: Replace `Propuesta` in `CardNegocio.jsx`**

Delete the whole private `Propuesta` function. Add the import at the top:

```jsx
import AngelaProposal from "./AngelaProposal";
```

Remove `propuestaResultado` from the `DrillNegocio` signature and add `actionTaken`, leaving the other props untouched:

```jsx
                               propuesta, onAprobarPropuesta, actionTaken,
                               propuestaTrabajando, variante = "overlay",
```

Replace the `<Propuesta ... />` call site with:

```jsx
        <AngelaProposal
          proposal={propuesta && { title: propuesta.titulo, detail: propuesta.detalle }}
          onApprove={onAprobarPropuesta}
          working={propuestaTrabajando}
          actionTaken={actionTaken}
        />
```

If `Sparkles` is now unused in this file, drop it from the lucide import.

- [ ] **Step 2: Wire desktop**

In `frontend/src/sections/Prioridades.jsx`, inside `drillProps`, delete the `propuestaResultado: propResultado[item.id],` line and add:

```jsx
      actionTaken: item.action_taken && {
        ...item.action_taken,
        onOpen: () => onNavegar?.(item.action_taken.navigate, item.action_taken.label),
      },
```

In `aprobarPropuesta`, replace the `setPropResultado(...)` line with a reload so the server's `action_taken` drives the done row:

```jsx
      toast(r.mensaje);
      cargar();
```

Then delete the now-unused `propResultado`/`setPropResultado` state declaration.

- [ ] **Step 3: Wire mobile**

In `frontend/src/mobile/InsightsMobile.jsx`, add to `rowOf`'s returned object:

```jsx
    actionTaken: it.action_taken,
```

In the `DrillNegocio` call, delete `propuestaResultado={proposalResult[abierta.id]}` and add:

```jsx
          actionTaken={abierta.actionTaken && {
            ...abierta.actionTaken,
            onOpen: () => onNavegar?.(abierta.actionTaken.navigate, abierta.actionTaken.label),
          }}
```

In `approveProposal`, replace the `setProposalResult(...)` line with `reload();`, then delete the unused `proposalResult`/`setProposalResult` state.

- [ ] **Step 4: Verify the build and that nothing still references the removed prop**

```bash
cd frontend && npx vite build
grep -rn "propuestaResultado\|propResultado\|proposalResult\|<Propuesta" src/
```
Expected: build succeeds; the grep prints nothing.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/CardNegocio.jsx frontend/src/sections/Prioridades.jsx frontend/src/mobile/InsightsMobile.jsx
git commit -m "Render proposals through AngelaProposal on both screens

The done state now comes from the server's action_taken instead of local
component state, so it survives reload and is visible to every user, and the
verbose API prose message is no longer rendered."
```

---

### Task 8: Row badge on both lists

**Files:**
- Modify: `frontend/src/sections/Prioridades.jsx` (`WorkRow`)
- Modify: `frontend/src/mobile/InsightsMobile.jsx` (`Fila`)
- Modify: `frontend/src/lib/locales/es.js`, `frontend/src/lib/locales/en.js`

**Interfaces:**
- Consumes: `item.action_taken` (desktop) / `item.actionTaken` (mobile — `rowOf` renames it in Task 7).
- Produces: no new exports.

- [ ] **Step 1: Add the i18n key**

`es.js`: `"prioridades.hecho": "Hecho",`
`en.js`: `"prioridades.hecho": "Done",`

- [ ] **Step 2: Badge the desktop row**

In `WorkRow`, after the chip span, add:

```jsx
        {item.action_taken && (
          <span className="ml-1 inline-flex items-center gap-1 rounded-full bg-salvia/12 px-2 py-0.5 text-[0.68rem] font-semibold text-salvia">
            <Check size={10} /> {t("prioridades.hecho")} · {item.action_taken.label}
          </span>
        )}
```

`WorkRow` currently takes no `t`, so add `const t = useT();` as its first line (`useT` is already imported in this file). `Check` is already imported from lucide here.

Mute the row when done by extending its existing className with:

```jsx
${item.action_taken ? "opacity-60" : ""}
```

- [ ] **Step 3: Badge the mobile row**

In `Fila`, add `const t = useT();` as its first line, add `Check` to the lucide import at the top of the file, and after the chip span add:

```jsx
        {item.actionTaken && (
          <span className="ml-1 inline-flex items-center gap-1 rounded-full bg-salvia/12 px-2 py-0.5 text-[0.68rem] font-semibold text-salvia">
            <Check size={10} /> {t("prioridades.hecho")}
          </span>
        )}
```

Mobile omits the order number: the row is narrower and the drill shows it.

- [ ] **Step 4: Verify the build**

Run: `cd frontend && npx vite build`
Expected: `✓ built`.

- [ ] **Step 5: Full backend suite**

Run: `cd backend && py -m pytest -q`
Expected: only the two pre-existing `test_p27` failures from Global Constraints. Then restore seeds: `git checkout -- data-demo/`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/sections/Prioridades.jsx frontend/src/mobile/InsightsMobile.jsx frontend/src/lib/locales/es.js frontend/src/lib/locales/en.js
git commit -m "Badge executed priorities in both lists

The done state is legible from the list without opening the drill, so a
second user can see the work was handled before acting on it."
```

---

## Manual verification

No frontend test runner is configured (no eslint config, no test script in `frontend/package.json`), so the component states are checked by hand once:

```bash
cd backend && POLPILOT_DEMO_TODAY=2026-07-07 py -m uvicorn main:app --port 8000
cd frontend && npm run dev
```

On `/prioridades`, open the restock card and confirm:

1. The proposal shows Ángela's mark, not a sparkle.
2. Approving swaps it for a one-line done row — order number, approver, link — with no prose paragraph.
3. **Reloading the page keeps the done row** (this is the bug being fixed).
4. The list row carries a "Hecho · OC-…" pill and is muted.
5. Clicking the link lands on `/ordenes_compra` with that order highlighted.
6. The header count and sidebar badge each dropped by one.
7. Approving a second time (or from another browser session) does **not** create a second order — check the count in `/ordenes_compra`.
8. Cancelling the order in `/ordenes_compra` returns the card to open work on the next load.
