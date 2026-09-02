# Auto-learning knowledge brain

Date: 2026-09-02
Status: research — no implementation scheduled

## Why this doc exists

One of PolPilot's core pitches (`PRODUCT.md`'s Positioning section) is a
"business knowledge" layer that captures what no ERP tracks — the owner's
rules, exceptions, and tacit context — so Ángela's read on a situation
reflects how *this* business actually runs. Today that layer is built, but
it is not self-learning: `core/conocimiento.py` only stores what a human
types in by hand, and `core/patrones.py` — the module that looks for
correlations nobody asked to have calculated — only finds the two shapes of
correlation a developer wrote Python for (`combo_no_percibido`,
`faltante_caja_patron`). Adding a third shape means shipping code, not the
system noticing something new on its own.

## North Star problem

**Discover a new class of business-relevant pattern in a tenant's data or
unstructured record, without a developer having pre-declared what shape
that pattern looks like — and do it without ever letting Ángela assert a
figure or a rule that hasn't been either deterministically computed or
confirmed by the owner.**

That second clause is the hard constraint. It's why PolPilot can't just
bolt on generic ML: the whole positioning rests on "every number comes from
calculation, never from the model" (`CLAUDE.md`), so any auto-discovery
system has to produce *candidates* that pass through the same kind of
statistical gate and human-confirmation loop the product already uses
(`core/patrones.py`'s support thresholds, `core/pattern_feedback.py`'s
accept/dismiss), never a system that starts acting on what it finds by
itself.

## Where the current system actually sits

Two modules already do adjacent, narrower things — worth being precise
about what each one is, because neither is "self-learning" today:

- **`core/patrones.py`** — statistics, not learning. It re-derives *values*
  (which product pair, which weekday) from live data on every run, but a
  developer chose the two hypothesis shapes and hardcoded their thresholds
  (`MIN_LIFT`, `MIN_COOCCURRENCES`, `SHORTFALL_RATIO_THRESHOLD`, ...). It
  cannot notice a correlation of a shape nobody wrote a function for.
- **`core/conocimiento.py`** — a database, not a learner. The owner (or an
  admin) writes a `regla`/`excepcion`/`protocolo`/`contexto` piece by hand;
  the system's only "intelligence" is applying it consistently afterward
  (`aplicables()`, `para()`) and counting `veces_aplicada`.
- **`core/pattern_feedback.py`** — the one piece of real feedback loop
  already in production: the owner's accept/dismiss on any finding (from
  either module above) is persisted per-fingerprint and suppresses that
  exact instance going forward. This is the shared plumbing any
  auto-discovery system should plug into, not replace.

## The landscape: four disciplines, not one algorithm

"Self-learning rule engine" is not a single technique — the literature
splits cleanly into four approaches with different strengths, and each
maps to a different part of PolPilot.

### 1. Generic unsupervised anomaly detection

Isolation Forest, Local Outlier Factor, autoencoders. Runs over an
arbitrary numeric feature matrix and scores "how isolated is this point,"
with no per-type thresholds — the algorithm decides what's statistically
weird, not a developer.

- [Isolation Forest: a complete guide](https://medium.com/@yanivbohbot5/anomaly-detection-with-isolation-forest-a-complete-guide-d42da77510a6)
- [Applied ML anomaly detection in enterprise purchase processes](https://arxiv.org/pdf/2405.14754)
- [Survey and benchmark of anomaly detection in business processes (IEEE TKDE 2024)](https://dl.acm.org/doi/10.1109/TKDE.2024.3484159)

**Strength:** truly type-agnostic; finds shapes nobody predicted.
**Weakness:** tells you a point is anomalous, not *why*, and not whether a
human would call it business-relevant — needs a narration + triage layer
on top, and is prone to noise/alert fatigue without one.

### 2. Process mining / conformance checking

Discovers the actual process model directly from event logs (orders, cash
closes, deliveries — exactly PolPilot's ingested data shape), then
automatically flags where real execution deviates from the discovered
norm. This is the closest commercial analog to "learn the normal shape of
operations, then flag deviations," and it's a mature, productized
discipline (Celonis is built entirely around it).

- [How process mining works (Celonis)](https://www.celonis.com/insights/topics/how-does-process-mining-work)
- [Conformance checking (Wikipedia)](https://en.wikipedia.org/wiki/Conformance_checking)
- [A systematic review of anomaly detection for business process event logs](https://link.springer.com/article/10.1007/s12599-023-00794-y)

**Strength:** purpose-built for ERP-shaped transactional event streams;
discovers the process model itself, not just point anomalies.
**Weakness:** heavier infrastructure (needs a proper event-log
representation with case IDs and timestamps); most tooling assumes
structured workflow logs, which PolPilot's data would need shaping into.

### 3. Weak supervision / automatic rule induction

Snorkel popularized combining many noisy, human-written "labeling
functions" into a single probabilistic signal instead of trusting any one
rule outright. Snuba goes a step further and *automatically generates* the
candidate heuristics from a small labeled seed plus the unlabeled data —
the automation is in the *search for rule candidates*, not just in scoring
ones a human already wrote.

- [Essential guide to weak supervision (Snorkel AI)](https://snorkel.ai/data-centric-ai/weak-supervision/)
- [Snuba: Automating Weak Supervision to Label Training Data](https://www.vldb.org/pvldb/vol12/p223-varma.pdf)

**Strength:** realistic middle ground between "dev writes each
`patrones.py` function" and "fully unsupervised" — still bounded and
auditable, calibrates each candidate rule's reliability instead of
trusting it blindly.
**Weakness:** needs a labeled seed (some ground truth of "this mattered,
this didn't") to bootstrap from — for PolPilot, `pattern_feedback.py`'s
accept/dismiss history is exactly that seed, but it doesn't exist yet at
volume for every tenant.

### 4. LLM-driven knowledge construction

The piece that maps onto `conocimiento.py`'s unstructured side. Two
threads:

- **GraphRAG** (Microsoft): an LLM reads unstructured text and
  automatically extracts entities, relationships, and *claims*, builds a
  graph, and summarizes clusters of it — literally "turn free text into
  structured business knowledge," unsupervised.
  [GraphRAG overview (Microsoft Research)](https://www.microsoft.com/en-us/research/blog/graphrag-new-tool-for-complex-data-discovery-now-on-github/)
- **Agent memory / reflection architectures** (Generative Agents,
  Reflexion, ExpeL, Voyager's skill library, MemGPT/Letta): the agent logs
  raw experience, periodically *reflects* to synthesize higher-level,
  reusable rules from recurring patterns, and stores them in a growing
  indexed library — new rules accumulate without a developer adding each
  one.
  [Memory for autonomous LLM agents: mechanisms, evaluation, emerging frontiers](https://arxiv.org/html/2603.07670v1)
  ·
  [Voyager-style self-evolving skill libraries](https://arxiv.org/html/2605.27366v1)

**Strength:** the only approach of the four that operates on *unstructured
text* (owner notes, WhatsApp transcripts already ingested via
`core/whatsapp_channel.py`/`core/transcripcion.py`) rather than structured
tables — directly targets the "non-structured data" half of the product's
North Star, not just the deterministic-numbers half.
**Weakness:** LLM extraction is not deterministic and can hallucinate a
relationship that isn't real — under PolPilot's "never assert an
unconfirmed figure" rule, every extracted candidate must land as a
*pending* `conocimiento` piece the owner confirms, never one that gets
`efecto` privileges (adjusts a threshold, suppresses an alert) on its own.

## The pattern every serious system in this space shares

Across all four disciplines, two gates recur, and PolPilot already has
primitive versions of both:

1. **A statistical/confidence bar before a candidate becomes a "finding"**
   — Snuba and process-mining conformance checkers compute this
   automatically; `patrones.py`'s `MIN_LIFT`/`MIN_COOCCURRENCES` is a
   hand-tuned instance of the same idea, just not generalized.
2. **A human confirmation step before a discovery becomes a trusted,
   acted-upon rule** — none of the four disciplines auto-promote a raw
   discovery into something the system acts on unsupervised;
   `pattern_feedback.py`'s accept/dismiss loop is PolPilot's version of
   this gate, and it's the piece any new discovery engine should plug into
   rather than duplicate.

## Two upgrade paths (not yet scoped into a plan)

The four disciplines above collapse into two concrete directions for this
codebase, matching its existing split between the deterministic-numbers
side and the unstructured-knowledge side:

- **Generalize `patrones.py`** (disciplines 2 and 3: process mining +
  weak-supervision-style rule search) — stop writing one Python function
  per correlation shape; run a generic scanner over dimension
  combinations/sequences with the same statistical gate already in place,
  and let Ángela narrate whatever clears the bar.
- **Extend `conocimiento.py` with LLM-drafted, owner-confirmed pieces**
  (discipline 4) — extract candidate knowledge from unstructured text
  already flowing through the product, land it as an unconfirmed piece,
  and only grant it `efecto` privileges once the owner confirms it —
  consistent with the "Ángela never invents a number" rule.

Neither direction is scoped into a design or implementation plan yet —
this doc is the research grounding for whichever gets picked next.
