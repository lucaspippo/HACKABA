---
name: PolPilot
description: The AI ops manager for PyMEs — a calm, white-based system where every color means exactly one thing.
colors:
  papel: "#fbfbfa"
  papel-hondo: "#f4f3f0"
  crema: "#ffffff"
  tinta: "#21201d"
  tinta-suave: "#6e6a63"
  linea: "#e9e7e2"
  angela-blue: "#2a5cdf"
  angela-blue-deep: "#1d3fae"
  angela-blue-soft: "#eaf0fd"
  rojo: "#d2372b"
  rojo-hondo: "#a82a20"
  oro: "#de7c1a"
  oro-tinta: "#96560a"
  salvia: "#2f7d5b"
  hielo: "#2b7a8c"
  hielo-claro: "#e9f1f4"
typography:
  display:
    fontFamily: "Schibsted Grotesk, system-ui, sans-serif"
    fontWeight: 700
  body:
    fontFamily: "Hanken Grotesk, system-ui, sans-serif"
    fontWeight: 400
  label:
    fontFamily: "Hanken Grotesk, system-ui, sans-serif"
    fontWeight: 600
  mono:
    fontFamily: "DM Mono, ui-monospace, monospace"
    fontWeight: 400
rounded:
  sm: "0.5rem"
  md: "0.75rem"
  card: "1.25rem"
  full: "9999px"
spacing:
  sm: "0.5rem"
  md: "0.875rem"
  lg: "1.25rem"
components:
  button-primary:
    backgroundColor: "{colors.tinta}"
    textColor: "{colors.crema}"
    rounded: "{rounded.md}"
    padding: "10px 16px"
  button-primary-disabled:
    backgroundColor: "{colors.tinta}"
    textColor: "{colors.crema}"
    rounded: "{rounded.md}"
    padding: "10px 16px"
  input:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.md}"
    padding: "10px 14px"
  card-negocio:
    backgroundColor: "{colors.crema}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.card}"
    padding: "20px"
  status-pill:
    backgroundColor: "{colors.crema}"
    rounded: "{rounded.full}"
    padding: "4px 12px"
---

# Design System: PolPilot

## Overview

**Creative North Star: "Aire"**

Aire ("Air") is a white-based system built on an unusual amount of negative space for
a business-operations product. Where most ERP-adjacent dashboards compress dense data
into boxes and borders, PolPilot spaces things out and lets weight and air carry
hierarchy instead. The system is calm on purpose: it exists to deliver bad news
(overdue debt, broken data, stock-outs) and pending decisions clearly, without
visual noise competing for the owner's attention.

The organizing law of the palette is **one color, one meaning, no exceptions**. Red
is never decorative — it only ever means an active, real problem. Gold only ever
means a decision waiting on the owner. Green only ever means something is in order.
Ángela Blue only ever means the AI agent — its sphere, its actions, its highlights —
because in this product the brand and the agent are treated as the same thing. This
is a deliberate constraint the codebase enforces in comments; new work must not
borrow a semantic color for decoration or for an unrelated state.

Numbers get the same discipline: every peso in the app renders in `DM Mono` with
tabular figures, so digits never visually shift as values update — a financial-grade
detail invisible until it's missing.

**Key Characteristics:**
- White-and-space first; color is reserved and meaningful, never ambient decoration.
- Restrained, precise component language — dark-ink primary actions, soft hairline
  borders, near-flat elevation.
- Money is always monospaced with tabular figures; it's the one place typography
  breaks from the humanist sans.
- Desktop and mobile are two tuned experiences of the same tokens, not one
  responsive layout — see Layout.

## Colors

The palette is almost entirely neutral (warm off-white, never beige) with five
strictly single-purpose accents layered on top.

### Primary
- **Ángela Blue** (`#2a5cdf`; legacy token `--color-violeta`): the AI agent's
  exclusive color — the sphere, agent actions, navigation highlights, focus rings.
  Never used for anything the agent didn't do or isn't doing. Deep variant
  `angela-blue-deep` (`#1d3fae`) for gradients/depth inside the sphere; soft variant
  `angela-blue-soft` (`#eaf0fd`) for tinted backgrounds behind agent-authored content
  (e.g. the drafted-proposal panel in `CardNegocio.jsx`).

### Secondary
- **Rojo** (`#d2372b`): a real, active problem — never a generic "error" state or a
  destructive-action button. Deep variant `rojo-hondo` (`#a82a20`) for readable text
  on tinted red backgrounds.
- **Oro** (`#de7c1a`): a decision pending the owner's action — the single most
  important state in the product, since it's the one thing only a human can resolve.
  `oro-tinta` (`#96560a`) is the readable-text pairing, used the way `rojo-hondo`
  pairs with `rojo`.
- **Salvia** (`#2f7d5b`): success / in-order. The "nothing to do here" state.
- **Hielo** (`#2b7a8c`): the product's own concept of "frozen capital" — dormant
  stock, locked-up data — plus general informational/data accents. `hielo-claro`
  (`#e9f1f4`) is its tinted-background pairing.

### Neutral
- **Papel** (`#fbfbfa`): base page background — a white with just enough warm gray
  to avoid reading as beige or as stark white.
- **Papel Hondo** (`#f4f3f0`): secondary/sunken surfaces (e.g. skeleton base).
- **Crema** (`#ffffff`): elevated surfaces — cards, panels, the login sheet — pure
  white so they lift visibly off `papel`.
- **Tinta** (`#21201d`): primary text, and also the primary button's fill —
  the darkest neutral in the system doubles as the "confident action" color.
- **Tinta Suave** (`#6e6a63`): secondary/supporting text — labels, captions,
  metadata lines.
- **Línea** (`#e9e7e2`): hairline borders and dividers — the only border weight in
  the system; there is no heavier border token.

### Named Rules
**The One Meaning Rule.** Every semantic color (rojo, oro, salvia, hielo, Ángela
Blue) has exactly one meaning across the entire product. A component must never
reuse red for something that isn't an active problem, or blue for something the
agent didn't do — even when a different meaning would "look right" in isolation.

**The Silver Rule.** Money (`.plata`) is always `DM Mono` with tabular figures,
never the sans body font — the digits must never visually shift as values change.

## Typography

**Display Font:** Schibsted Grotesk (with `system-ui, sans-serif` fallback)
**Body Font:** Hanken Grotesk (with `system-ui, sans-serif` fallback)
**Label/Mono Font:** DM Mono (with `ui-monospace, monospace` fallback), used
exclusively for money and other tabular figures

**Character:** A confident, slightly condensed grotesque (Schibsted) for titles and
figures paired with a humanist, highly legible grotesque (Hanken) for body copy and
UI text — both sans, both quiet; the pairing reads as precise rather than
expressive. DM Mono is reserved entirely for money and never used as a "techy"
decorative accent elsewhere.

### Hierarchy
- **Display** (Schibsted Grotesk, 700–800, ~1.05rem–1.5rem in observed usage,
  tight leading): card titles, section titles, the login card headline — short,
  high-confidence labels, not long-form headlines.
- **Body** (Hanken Grotesk, 400, ~0.82rem–0.95rem, snug leading): descriptive text,
  card body copy, form labels' companion text.
- **Label** (Hanken Grotesk, 600, ~0.62rem–0.8rem, often uppercase with wide
  tracking for the smallest labels, e.g. `tracking-[0.14em]` on the brand-for line):
  chips, nav labels, field labels, status pills.
- **Money** (DM Mono, 400–500, tabular-nums, tight tracking `-0.02em`): every peso
  figure in the app, from small inline amounts to the large `Cifra` display in
  `CardNegocio`.

### Named Rules
**The Tabular Numbers Rule.** `body` sets `font-variant-numeric: tabular-nums`
globally — every digit in the app, not just money, holds its column width so KPIs,
tables, and axis labels never jitter as numbers update.

## Layout

Desktop and mobile are deliberately different layouts sharing one token set, not one
responsive grid stretched between breakpoints.

- **Desktop density trick:** at ≥1024px, `html { font-size: 80% }` scales the entire
  rem-based Tailwind v4 scale (type, spacing, radius, containers) uniformly — "100%
  zoom looks like 75–80%" without `transform:scale`, which would break hit-testing,
  `position:fixed`, tooltips, and the React Flow canvas. Mobile stays at 100%.
- **Extra wide breakpoint:** `--breakpoint-3xl: 85rem` (1360px) exists specifically
  so dense desktop grids (the findings row, Evolution/Alerts/Opportunities) can step
  up to their widest column count on very wide monitors; evaluated in rem against a
  fixed 16px, independent of the density scale above.
- **Mobile bottom nav:** `position: fixed; bottom: 0`, respects
  `env(safe-area-inset-bottom)`, equal-width grid columns
  (`repeat(n, minmax(0,1fr))`), Ángela's tab always present at center as a raised
  circular button; `<main>` carries `pb-24` so content never sits under the bar.
- **Cards over grids of boxes:** the recurring content unit is a single flexible
  card shape (`CardNegocio`), reused across sections by changing accent and chip
  rather than building a new layout per section.

## Elevation & Depth

Nearly flat by default; shadows are extremely soft and appear only to signal
hierarchy or interaction, never as a decorative base state.

### Shadow Vocabulary
- **sombra-papel** (`0 1px 2px rgba(33,32,29,.03), 0 6px 20px -14px rgba(33,32,29,.1)`):
  the resting elevation for cards sitting on `papel` — barely perceptible lift.
- **sombra-alta** (`0 1px 3px rgba(33,32,29,.04), 0 14px 40px -20px rgba(33,32,29,.16)`):
  the elevated/floating state — used for the login card and similar "sheet above the
  page" surfaces.
- **card-hover** (adds `0 2px 4px rgba(33,32,29,.05), 0 12px 32px -14px rgba(33,32,29,.16)`
  plus `translateY(-2px)`): interactive cards lift further on hover — elevation as
  direct feedback that the card is clickable.

### Named Rules
**The Ambient-Only Rule.** Shadows are diffuse and low-contrast at every step; there
is no hard-edged or high-contrast drop shadow anywhere in the system. Depth reads as
atmosphere, not as a UI chrome effect.

## Shapes

- **Cards:** `--radius-card: 1.25rem` (20px) — noticeably softer than the default
  Tailwind scale, distinguishing content cards from smaller controls.
- **Buttons and inputs:** `rounded-xl` (0.75rem / 12px) — soft but tighter than
  cards, so cards read as containers and buttons/inputs read as controls inside them.
- **Pills/chips/avatars/the Ángela sphere:** fully rounded (`rounded-full`).
- **Borders:** a single hairline weight everywhere (`border-linea`, 1px); there is
  no secondary heavier border token — emphasis comes from color or shadow, not
  border weight.

## Components

Restrained and precise: dark-ink primary actions, soft hairline borders, near-flat
elevation. Hierarchy comes from spacing and weight, not from ornament.

### Buttons
- **Shape:** `rounded-xl` (12px).
- **Primary:** background `tinta` (#21201d), text `crema` (white), padding
  `10px 16px`, `font-semibold`; the darkest neutral doubling as the confident-action
  color rather than an accent hue.
- **Hover / Focus:** `active:scale-[0.99]` on press; focus-visible uses a two-ring
  treatment — an inner ring matching the background, then a 4px Ángela Blue ring at
  40% opacity — applied globally via `:focus-visible`, keyboard-navigation only.
- **Disabled:** `opacity-40`, no color change.

### Chips / Status Pills
- **Style:** `bg-crema`, fully rounded, `ring-1` in the semantic color at low
  opacity, colored dot + colored text matching the state (`StatusPill.jsx`) — never
  a filled background block; always the ring + dot pairing.
- **State:** three fixed states only — `requiere_accion` (rojo), `atencion` (oro),
  `en_orden` (salvia) — mapped directly to the one-meaning-per-color rule, not a
  generic severity scale.

### Cards / Containers (CardNegocio)
- **Corner Style:** `--radius-card` (20px).
- **Background:** `crema` on `border-linea`, `sombra-papel` at rest.
- **Anatomy (fixed order, reused everywhere):** type chip (icon + semantic color) →
  title in Display font → one line of supporting data → the large monospace figure
  → optional "Crucé: [sources]" trust line → the action row. The accent color and
  chip are the only things that vary between sections (Alerts vs. Opportunities);
  the layout itself never forks.
- **Interactive lift:** `card-hover` — shadow deepens and the card rises 2px on
  hover, signaling clickability without a border or background change.

### Inputs / Fields
- **Style:** `bg-papel`, `border-linea`, `rounded-xl`, padding `10px 14px`.
- **Focus:** border shifts to `tinta` at 40% opacity — no glow, no color change,
  matching the system's restraint (contrast with the vivid focus ring used on
  buttons/nav, which is deliberately louder because it signals keyboard navigation
  specifically).
- **Error:** inline message below the field, `bg-rojo/10` background,
  `text-rojo-hondo`, never a red border on the field itself.

### Navigation (Mobile Bottom Nav)
- Fixed to the viewport bottom, `bg-crema/95` with `backdrop-blur`, single hairline
  top border. Equal-width slots; each renders icon + micro-label
  (`0.62rem`, `font-semibold`). Active tab: Ángela Blue icon + label, heavier icon
  stroke width (2.4 vs 2) — weight and color carry the active state, never a
  background pill.
- Ángela's slot is structurally different from the rest: a raised circular button
  (`h-9 w-9`, `bg-violeta`/Ángela Blue, `rounded-full`) that floats above the bar's
  baseline — the one destination that is always present regardless of role.

### The Ángela Sphere (signature component)
The product's one deliberately expressive element against an otherwise restrained
system: a radial-gradient orb (light source top-left, Ángela Blue core fading to a
deep navy edge) with three named animation states — `esfera--idle` (slow breathing
scale), `esfera--pensando` (faster scale + brightness pulse, "thinking"),
`esfera--esperando` (a gold ring pulse layered on top — the one place gold appears
on a blue element, because a pending decision can occur while the agent is
otherwise idle). `prefers-reduced-motion` collapses all of these to a static frame.

## Do's and Don'ts

### Do:
- **Do** keep every semantic color (rojo, oro, salvia, hielo, Ángela Blue) to its
  single fixed meaning — check `index.css`'s color comments before introducing a new
  use.
- **Do** render money in `DM Mono` with tabular figures via the `.plata` class, never
  in the body sans font.
- **Do** reuse the `CardNegocio` anatomy (chip → title → data line → figure →
  sources → action) for any new business-finding surface rather than inventing a
  new card layout.
- **Do** keep shadows soft and ambient (`sombra-papel` / `sombra-alta` /
  `card-hover`); depth is atmosphere, not chrome.
- **Do** design desktop and mobile as separate tuned experiences of the same tokens
  (`frontend/src/desktop`, `frontend/src/mobile`), not one responsive layout.

### Don't:
- **Don't** use red, gold, green, or Ángela Blue decoratively or for a state outside
  their fixed meaning — no "error red" buttons, no gold-as-warning-brand accents.
- **Don't** introduce a second border weight or a hard-edged shadow; the system has
  exactly one hairline border and only diffuse, low-contrast shadows.
- **Don't** style the Ángela sphere's motion states as generic loading spinners —
  idle/thinking/waiting are named, purposeful states, not decoration.
- **Don't** collapse the mobile bottom nav's fixed five-slot, equal-width grid into
  a scrolling or variable-width tab bar.
