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
