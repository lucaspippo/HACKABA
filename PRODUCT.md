# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary users are the owners and staff of small-to-mid Argentine PyMEs (distributors,
retailers, and similar operating businesses) who already run an ERP but can't get
straight answers out of it. The product is used by every role in the business, not
just the owner: in the demo tenant this spans the owner (`aldo`), office/admin staff,
purchasing, warehouse lead and crew, drivers, sales reps (`preventistas`), a branch
manager, and counter staff (`vanesa`, `tomas`, etc. — see `backend/usuarios_demo.py`).
Each role gets a scoped view of the same underlying business, gated server-side by
`features`/`superficies`, not a generic dashboard everyone shares. Usage happens on
both desktop and mobile, mid-task, during the normal working day (checking the
warehouse floor, chasing a debtor, deciding what to reorder).

## Product Purpose

PolPilot is an AI ops manager for PyMEs: it sits on top of the ERP the business
already uses, finds the money that's stuck (dead stock, broken/dirty data, overdue
debtors, stock-outs, missed opportunities), and executes the fix with the owner's
approval. Ángela — the system's AI — talks to each role like a partner who knows the
business by heart, in their own language (bilingual ES/EN per user).

Success is measured business-side: money recovered/unlocked, cash-collection days
reduced, dirty records corrected, stock-outs avoided before they happen — not app
engagement. `backend/core/objetivos_medidos.py` tracks exactly this: real,
live-computed progress against baselines for 7 concrete business objectives (days to
collect, records to fix, dormant stock freed, price/margin gaps, customer
concentration risk, overdue debt collected, at-risk stock replenished).

## Positioning

The mechanism a neighboring "another dashboard on your ERP data" product could not
truthfully copy: every number PolPilot shows comes from deterministic calculation in
`backend/core/`, never from the LLM — Ángela narrates and cites that output, she never
computes or invents a figure. Combined with a non-structured "business knowledge"
layer (`backend/core/conocimiento.py`) that captures the owner's rules, exceptions,
and protocols — the tacit context no ERP holds — so Ángela's read on a situation
reflects how this specific business actually runs, not a generic heuristic.

## Operating Context

- Sits on top of an existing ERP; does not replace it. Multi-tenant by design
  (`POLPILOT_TENANT` + `POLPILOT_DATA_DIR` fully isolate each business's data, users,
  and credentials).
- Two states of the same codebase: a real, DB-backed mode for productive (paying)
  clients, and a fast synthetic demo mode (`data-demo/`'s deterministic generator,
  tenant `demo`) used to showcase the product without a live client. Both share the
  same deterministic core and UI.
- Roles map to real day-to-day business functions (owner, purchasing, warehouse,
  drivers, sales reps, counter, branch manager) and each sees only what's relevant to
  their job.
- Ángela (the AI chat) is optional at runtime — without an `ANTHROPIC_API_KEY`, all
  deterministic analysis still works; only the narrated chat layer is unavailable.
- Bilingual by design (EN|ES), selectable per user profile — this is a real product
  requirement, not a demo flourish.

## Capabilities and Constraints

- Deterministic core (`backend/core/`) covers: sales, cash, collections/receivables,
  data-quality/cleanup (`saneamiento`), business opportunities & alerts, warehouse
  and logistics, pricing/margins, stock rotation and replenishment, vendor/document
  ingestion (invoices, vision), audit trails, goals/objectives tracking, org &
  team/profile management, and more (see `backend/core/` for the full domain list).
- Ángela is a tool-calling LLM orchestrator (`backend/angela.py`) that narrates and
  cites `core/` output — it must never calculate, remember, or reformat a number
  itself. This is a hard architectural invariant, not a style preference.
- FastAPI backend + React/Vite frontend, single process; the frontend has distinct
  desktop and mobile experiences (`frontend/src/desktop`, `frontend/src/mobile`),
  each tuned for its own usage pattern rather than one responsive layout doing both.
- Terminology: "Ángela" is always the product's AI/assistant identity, not a generic
  "AI chat" label, across both product surfaces and code.

## Brand Commitments

Existing visual system already implemented in code (Schibsted Grotesk, Hanken
Grotesk, and DM Mono typefaces bundled locally; per-user accent colors; the "Ángela"
name and mark). Treated as the current implementation to build on, not yet a locked,
independently documented brand system — `/impeccable document` can capture it formally
when needed.

## Evidence on Hand

- The demo tenant (`demo`, "Distribuidora del Litoral") and its entire dataset —
  company, people, customers, vendors, brands, transactions, business-knowledge
  entries — are 100% fictional, generated deterministically by
  `data-demo/generar.py` with a fixed seed. No real client data lives in this repo.
  Future work must never treat demo-tenant content as real evidence, testimonials,
  or benchmarks.
- A second example tenant, `piloto` ("Supermercados Horizonte"), exists as a smaller
  seed used by the test suite (`backend/auth.py`); also fictional.
- No real customer logos, testimonials, case studies, or press exist yet in this
  repo. Do not fabricate any.

## Insight Structure

Every analysis the product presents follows one fixed shape: Pattern →
Hypothesis → Evidence → Assumptions → Risk → Recommended action → Owner →
Deadline. Confidence is always reported on two axes — how much data backs the
finding, and how big the interpretive leap is — because a card can be
data-rich and hypothesis-light, or the reverse, and a single confidence number
would hide which one it is. Every metric states how it was calculated; every
claim expands to the real records behind it, not a paraphrase of them.

The insight LIFECYCLE (`New` / `Confirmed` / `Acted upon` / `Resolved` /
`Proven wrong` / `Still being monitored`) and the action workflow it drives are
the planned next step, not yet implemented — see the "Deferred" section of
`docs/superpowers/specs/2026-09-01-structured-insight-contract-design.md`.

## The Counting Rule

**The unit of a sum is an entity, not a row. And no figure reaches a screen or
a document unless it came out of tested code.**

This is written here, at the same level as the Action Principle, because it has
already gone wrong twice in this repo, in the same shape:

- **The "$900M".** The map summed opportunity cards of every kind into one
  "recoverable capital" headline. Overdue debt, dormant stock and avoided
  overbuying are not the same magnitude, and adding them produced a number
  nobody could reproduce. The fix was `oportunidades_neg.recuperable()`: one
  function, one canonical sum, and `NATURALEZA` deciding what is homogeneous
  enough to add.
- **Debt per truck.** A design document reported $168,700,000 of receivables on
  one delivery run. Two customers had two stops each that day and one balance
  each, so a third of the figure was the same customer counted twice. The real
  number is $111,800,000. It was caught by writing the code, not by re-reading
  the document — see `core/cobranza.exposicion_en_ruta` and the first two tests
  in `tests/test_deuda_en_ruta.py`.

Twice is not bad luck. It is a pattern, and it has a shape worth naming:
**a list of rows is not a list of the things the rows are about.** Stops are
not customers, order lines are not products, lots are not SKUs, notes are not
authors. Whenever a total is labelled with an entity — customers, vendors,
products — the sum and the count both have to be over that entity.

### How to apply it

1. **Name the unit before writing the sum.** If the answer is "money per
   customer", deduplicate by customer, at every level of the aggregation: a
   customer can repeat inside one group *and* across groups, and the group
   totals and the grand total need different deduplication.
2. **Only add what is homogeneous, and say what kind of money it is.** Debt
   that already exists is exposure and is *surfaced*, not recovered; goods
   about to expire are a loss *avoided*, not capital freed. `NATURALEZA` is
   how a card declares which one it is, and `recuperable()` is the only thing
   allowed to add them up. A figure whose kind is not declared does not get
   summed with anything.
3. **The figure comes from `core/`, with a test that pins it.** Not from a
   `reduce` in a component, not from an ad-hoc script, not from a number
   computed while writing an analysis. A screen renders totals; it never
   derives them. When a document quotes a figure, it quotes what the code
   returns — build it first, then write it down.
4. **Pin the canonical numbers.** The ones the business repeats out loud belong
   in a test that fails when they move (see `tests/test_cruces.py`'s
   "los canónicos no se mueven"). A number nobody guards is a number that
   drifts.

## The Action Principle

**A process that ends in a report is unfinished.** PolPilot sits on top of the
system of record; it is not another one. The ERP already shows every table the
business has. What the ERP cannot do is decide, and the one thing this product
sells is that a decision gets *made and executed* — with the owner's approval —
without leaving the screen where it was seen.

This principle is stated here at the level of detail `DESIGN.md` gives a
border radius, because its absence is how the surface drifted: each ERP-shaped
screen was added for a reasonable local reason, and nothing written said "this
puts us on Odoo's home ground".

### What it means

- **The unit of the product is a decision, not a record.** A screen earns its
  place in the navigation by the decision someone closes there — approve,
  assign, correct, send, discard — and by that decision changing the system
  (persisted, attributed, audited). A screen that only lets someone *look* is
  evidence, and evidence lives one click behind the decision that needs it.
- **A table is evidence, never the destination.** Tables are unbeatable for
  sweeping many rows to find the one that is wrong; the chat is useless for
  that. Keep the table — but the door to it is the problem ("5 groups of broken
  data", "8 lots expiring"), not the menu, and it opens *focused on the row
  that motivated the visit*, never on row 1 of 430.
- **Every role lands on its work queue.** `frontend/src/lib/roles.js` gives
  seven roles a tool view: tasks derived from real signals, the actions to
  close them, the questions of their trade. The owner is a role too. A landing
  screen with five reads and zero closable actions (`Inicio`) is a report.
- **"Approve" must do something.** A button that sets local state and shows a
  toast is a lie about the product's core promise. The done-state of any
  action is a fact computed in `core/` from persisted data — never client
  state, never narrated by the LLM (see the propose → approve → done pattern
  in `docs/superpowers/specs/2026-09-01-angela-proposal-pattern-design.md`).
- **The ERP owns the record; we own the decision.** Creating, editing and
  deleting master data (products, sales, receipts, vendors, locations,
  purchase orders) in this product competes with the system of record on
  integrity — the ground where a 20-year-old ERP wins. We read those; we
  write back *decisions* through the connector, with the audit trail intact.

  Stated as the line that settles every future argument about where a write
  belongs: **the ERP stores what happened. PolPilot stores what somebody
  decided, who decided it, and why.** A fact reported from the floor ("eight
  boxes came in broken", "I counted 34 fewer") is not a stock movement — it is
  the evidence that the ERP's stock is wrong. The adjustment is the ERP's, and
  it happens when a person approves it. This is what `core/piso.py` already
  enforces in its own words ("reporting does NOT modify stock or the ERP"), and
  what keeps the whole mobile surface honest: **no floor screen writes to the
  ERP.** Every one of them writes a fact or a decision.

  The tempting exception is order picking, where reserving stock would feel
  natural. Reserving is the ERP's job; what we record is that the picker
  assembled 2 of the 4 requested and flagged the shortfall to whoever can act
  on it.

### How to apply it when a screen is proposed

Before a new section enters `CATALOGO` (`frontend/src/desktop/DesktopApp.jsx`)
or `MODULOS` (`backend/auth.py`), answer in writing:

1. **What decision closes here?** Name the verb (approve / assign / correct /
   send / discard) and the table or blob it changes. If the honest answer is
   "the user looks", it is evidence: reachable from a finding, not from the
   sidebar.
2. **Does the ERP already have this screen under this name?** If Odoo's or
   Tango's standard menu has it (Products, Receipts, Internal Transfers,
   Locations, Purchase Orders, Vendors, Sales), we are inviting a comparison we
   lose. Either it becomes evidence behind a finding, or it must do something
   the ERP cannot — and that something is the screen's headline.
3. **Which role lands here, and how often?** Mark the answer as a hypothesis
   unless it comes from a real user. A screen without a role is a report.
4. **What does the user get back for changing a habit?** Every change we ask
   for must return something they do not have today, on the same screen, in
   the same moment. "It looks nicer" is not a return.
5. **Where is the evidence?** Every number on the new screen must open to the
   real rows behind it (the Insight Structure above). If the screen *is* the
   rows, go back to question 1.
6. **Is it a module?** If a screen can be seen by someone, the owner must be
   able to take it away in "Quién ve qué". A section that rides on another
   module's flag (as seven ERP screens once rode on `inventario`) breaks the
   role promise made in *Product Principles*.

### Named rules

- **Report Rule:** a screen with reads and no persisted, attributed action is
  evidence. It may exist; it may not be a top-level destination.
- **Focus Rule:** a table opened from a finding opens filtered and scrolled to
  the row that motivated the visit. Row 1 is a bug.
- **Toast Rule:** no success message without a persisted change behind it. A
  toast is the *receipt* for an action, never the action.
- **Home-Ground Rule:** an ERP menu name is a reason to hide, not to add.
- **Owner Rule:** `es_admin` is a role with a work queue, not an exemption
  from one.
- **Record Rule:** the ERP stores what happened; we store what somebody
  decided, who decided it, and why. A floor report is evidence that a record
  is wrong, never the correction itself — so no floor screen writes to the ERP.
- **Counting Rule:** the unit of a sum is an entity, not a row, and no figure
  reaches a screen or a document unless it came out of tested code. See *The
  Counting Rule* above — it has already cost us twice.

## Product Principles

- Every number the user sees traces to a deterministic calculation in `core/`; the
  LLM narrates, cites, and never invents or recomputes a figure.
- Each role sees their own scoped slice of the business, not a shared generic view —
  design and data access follow the real org chart.
- Demo and production are the same product on the same architecture, isolated by
  tenant — never a special-cased "demo path" that diverges from what a paying client
  runs.
- Bilingual (ES/EN) is a first-class product requirement, not a translation
  afterthought — content is authored in both languages at the source.
- Desktop and mobile are each designed for their own usage moment, not one layout
  compressed to fit both.
