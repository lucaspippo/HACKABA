# Showing customers what PolPilot is worth

Date: 2026-08-28
Status: idea backlog — not scheduled

## Why this doc exists

A paying customer needs to see, in their own numbers, that PolPilot is worth
what they pay for it. Today the product computes real impact figures
constantly (`core/oportunidades_neg.py`, `core/anomalias.py`,
`core/saneamiento.py`) but never accumulates them into a "here's what we did
for you" story — every screen shows *current* exposure, never *realized*
outcome. This doc lays out how to close that gap, in order of how much new
infrastructure each idea costs.

**Shipped already** (small, no new infra): the Home page now surfaces
`prioridades.recuperable` — the same canonical "capital recuperable" figure
Mapa and Ángela already use — as a metric tile, framed as "recuperable si
actuás ahora". It's the existing pending-impact rollup, just made visible
where the owner actually starts their day. See `core/priorities.py`'s
`inbox()` and `frontend/src/desktop/sections/Inicio.jsx`.

Everything below is unshipped, ordered roughly cheapest-and-most-honest
first.

## 1. Historical savings from actionables acted upon

This was the original idea: show the customer the money they *would have
lost* without the product, accumulated over time from Risk / Opportunity /
Anomaly / Fix cards they actually acted on.

**It's the right instinct, but it needs infrastructure that doesn't exist
yet.** Every actionable today (`oportunidades_neg.cards()`,
`anomalias.analizar_existentes()`) is a pure function recomputed fresh on
every request: a dict with a static per-type id (not a per-instance UUID),
a `$ monto`, but no status, no first-seen timestamp, no acted-on timestamp,
and no outcome link. A card just stops appearing once its underlying
condition clears — the system can't tell whether that's because the owner
acted, because the customer paid on their own, or because the data moved
for an unrelated reason. (The one place with a real state machine —
`core/piso.py`'s floor reports, `nuevo → resuelto` — doesn't generalize to
these cards.)

So there are really two separate problems, and they're not equally hard:

### 1a. Persisting actionable instances (foundational, do this first)

Turn each card type into a row with a stable identity: first surfaced at,
current status (`pending` / `acted` / `dismissed` / `expired`), and — this
is the part worth being careful about — *how* it left the pending state.
This is valuable on its own, independent of the savings feature: it turns
the whole priorities engine from stateless into an event log, which is
also the natural backing store for "what did Ángela do this week"
(currently faked, see §3 below) and for per-role audit questions ("did
anyone act on the concentración warning from March?").

### 1b. Attributing "acted upon" and valuing the outcome (the hard part)

The risk here isn't engineering effort, it's **credibility**. Two different
kinds of card need two different treatments, and blending them into one
"we saved you $X" number is the fastest way to have a customer catch you
overclaiming:

- **Opportunities / Fixes** (`cobrar_morosos`, `despertar_dormido`,
  `precio_perdida`, …): the $ is closer to a *measurable captured gain*.
  If the debt the card flagged actually got collected, or the mispriced
  SKU actually got corrected and sold at the right price afterward, that's
  checkable against the data. Count these once there's a clear in-app
  action (see below) *and* a subsequent state change confirming it landed.
- **Risks** (`quiebre_inminente`, `concentracion`): the $ is an *avoided
  probabilistic loss* — an estimate of what a stockout or customer
  concentration would have cost, not a fact. These belong in a separately
  labeled "risk exposure avoided" ledger, never summed into the same
  headline as captured gains.

The other half of the attribution problem: don't infer "acted upon" from a
card silently disappearing. Require an actual in-app action — sending the
collections nudge, applying the price fix, approving the reorder — so the
system knows a specific action caused the outcome, rather than crediting
itself for something the customer would have done anyway. This is also
where the existing `core/audit.py` / `audit_events` log becomes useful: it
already records data mutations with before/after state; extending it (or a
sibling table) to record "actionable X, status Y, at time Z" reuses a
pattern the codebase already trusts.

**Recommended sequencing:** (1) persist actionable instances with
timestamps — pure plumbing, valuable standalone; (2) require an in-app
action to mark anything "acted upon" — no inferring from disappearance;
(3) split the ledger into "captured" (opportunities/fixes, verified by a
later state check) vs. "exposure avoided" (risks, explicitly labeled as an
estimate) rather than one blended figure; (4) only then build the
customer-facing "savings" screen on top.

## 2. Roll up pending impact into "estimated savings available now"

Already shipped (see top of this doc). The remaining cheap extension: since
`recuperable()` cards carry enough history to trend, show "this was $X last
week, it's $Y now" — decay framing ("this shrinks/grows if you wait") using
data the analysis cache already recomputes. No new persistence needed for
this specific extension, just diffing two cached snapshots.

## 3. Other ways to convey value (brainstorm)

Roughly ordered by how much new infrastructure each needs.

- **Weekly/monthly impact digest** (email or in-app recap): "N risks
  flagged, N opportunities captured, $X still on the table." A recurring
  artifact is a much stronger retention/renewal lever than a dashboard
  tile nobody revisits on their own — this is the natural product for
  whatever ledger comes out of §1.
- **Time-to-detection framing**: "caught in real time" vs. the PyME's
  prior cadence of finding this at month-end close. No new data needed —
  pure narrative, e.g. in Ángela's copy or the digest above.
- **Action-rate / engagement score**: "you acted on 7 of 9 flagged items
  this month." Falls out directly of the §1a status field — a usage
  metric that also nudges behavior, cheap once that field exists.
- **Data-hygiene trend**: anomalies/fixes applied over time ("your books
  are cleaner every month"), valuable even without a $ figure attached.
  `core/saneamiento.py` and `core/anomalias.py` already produce the raw
  counts; this is mostly a "graph it over time" exercise once instances
  persist.
- **Peer/benchmark framing**: "your margin/collection speed is better
  than X% of similar businesses." Needs cross-tenant aggregation — a
  bigger lift (and one to think through carefully for tenant data
  isolation, given the multi-tenant design in `CLAUDE.md`), but it's the
  most persuasive framing for an owner who has no external reference
  point today.

### A cautionary precedent already in the codebase

`frontend/src/lib/locales/es.js` still has orphaned copy from an earlier
iteration — `inicio.ahorro_titulo` ("Lo que PolPilot te ahorró esta
semana"), with hardcoded placeholder values ("≈ 6 hs", "3 tareas", "1
persona") and a note admitting they're guesses ("Estimado en base a las
tareas de esta semana"). It's unused by any component today. That's the
failure mode to avoid: a "what we saved you" claim that isn't backed by a
real calculation reads as marketing fluff the moment a customer checks it,
and directly conflicts with this codebase's own rule that every number
comes from calculation, never invention (`CLAUDE.md`, "Architecture").
Whatever savings feature ships should either replace that dead copy with
real numbers or remove it — never build the new feature as a reskin of it.

## Open questions before scheduling §1

- Where does "acted upon" get its signal from for each card type — is
  there an in-app action for every opportunity/fix today, or do some
  (e.g. `cliente_frio`, `estrella_caida`) only ever end in "navigate
  elsewhere and do it by phone," which the app can't observe?
- What's the right retention window / undo story for a persisted
  actionable instance — can a dismissed item resurface if the condition
  recurs, and does it get a new instance or reopen the old one?
- Does the "captured" ledger need a human confirmation step ("did this
  actually happen?") before counting, or is a state-based check
  (debt balance dropped, price corrected and sale confirmed) trustworthy
  enough on its own?
