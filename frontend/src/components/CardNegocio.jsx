import {
  ArrowRight, BarChart3, BookOpen, CalendarClock, ChevronDown, ChevronRight,
  Compass, Lightbulb, Link2, ScanSearch, ShieldAlert, TrendingDown,
  TrendingUp, UserRound, X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { CuerpoConsulta } from "./Widget";
import AngelaProposal from "./AngelaProposal";
import { fecha, pesoCorto, peso } from "../lib/format";
import { useLang, useT } from "../lib/i18n";

// P27·C — LA anatomía de card de negocio, una sola para Alertas y
// Oportunidades: chip de tipo (lucide + color semántico) → título en lenguaje
// de dueño → una línea de dato → la cifra grande (tabular-nums) → "Crucé:
// [fuentes]" → acción. La diferencia entre secciones es el ACENTO (rojo/oro/
// azul vs verde) y el chip — nunca dos layouts distintos.

// Acento semántico: rojo = pérdida activa/riesgo serio · oro = atención ·
// azul = informativa · salvia = oportunidad (upside).
export const ACENTO = {
  rojo: { chip: "bg-rojo/10 text-rojo", cifra: "text-rojo", borde: "border-rojo/25" },
  oro: { chip: "bg-oro/15 text-oro-tinta", cifra: "text-oro-tinta", borde: "border-oro/30" },
  azul: { chip: "bg-hielo/15 text-hielo", cifra: "text-hielo", borde: "border-hielo/25" },
  salvia: { chip: "bg-salvia/12 text-salvia", cifra: "text-salvia", borde: "border-salvia/25" },
};

// La cifra grande: plata formateada o un conteo crudo (hay alertas sin $ —
// ahí la verdad grande es el número de ítems, no un peso inventado).
function Cifra({ monto, texto, cls, label }) {
  if (monto == null && !texto) return null;
  return (
    <p className={`plata mt-3 text-2xl font-medium ${cls}`}>
      {monto != null ? pesoCorto(monto) : texto}
      {/* P30·A2 — etiqueta del $ cuando NO es plata a cobrar (facturación, etc.) */}
      {label && <span className="ml-1.5 align-middle text-2xs font-normal text-tinta-suave">{label}</span>}
    </p>
  );
}

export function CardNegocio({ tono = "salvia", icon: Icon, chip, chipCls, titulo,
                              dato, monto, montoLabel, cifraTexto, fuentes, accion, onClick }) {
  const t = useT();
  const a = ACENTO[tono] || ACENTO.salvia;
  return (
    <button onClick={onClick}
      className="card-hover flex flex-col rounded-[var(--radius-card)] border border-linea bg-crema p-5 text-left sombra-papel">
      <span className={`inline-flex items-center gap-1.5 self-start rounded-full px-2.5 py-1 text-xs font-semibold ${chipCls || a.chip}`}>
        {Icon && <Icon size={12} />} {chip}
      </span>
      <p className="mt-2.5 font-display text-lg font-bold leading-tight">{titulo}</p>
      {dato && <p className="mt-1 flex-1 text-sm leading-snug text-tinta-suave">{dato}</p>}
      <Cifra monto={monto} texto={cifraTexto} cls={a.cifra} label={montoLabel} />
      {fuentes?.length > 0 && (
        <p className="mt-2 text-xs leading-snug text-tinta-suave/80">
          {t("cardneg.cruce")} {fuentes.join(" · ")}
        </p>
      )}
      <span className="mt-2 inline-flex items-center gap-1 self-start text-sm font-semibold text-tinta">
        {accion || t("cardneg.ver_por_que")} <ArrowRight size={13} />
      </span>
    </button>
  );
}

// The drill-down, identical in BOTH sections: one structured insight
// (backend/core/insight.py) read in the order the owner reasons — pattern →
// hypothesis → evidence → risk → recommendation → assumptions → caveats —
// plus the actions each section assembles (adoptar / Ángela / ir).

// Closing the loop on a finding (core/pattern_feedback.py, shared by
// core/patrones.py and core/oportunidades_neg.py alike): the owner's
// reaction to the SPECIFIC instance shown, so it doesn't resurface. Purely
// presentational like the rest of this file — the caller owns the actual
// API call and decides whether this card's id can take feedback at all.
const FEEDBACK_ACTIONS = [
  { action: "accepted", lk: "aprendizaje.feedback_aceptado" },
  { action: "already_knew", lk: "aprendizaje.feedback_ya_sabia" },
  { action: "dismissed", lk: "aprendizaje.feedback_descartado" },
];

// "dismissed" specifically drops the finding for good (core/pattern_feedback.py
// removes it from ever resurfacing) — unlike "accepted"/"already_knew", which
// are soft. That asymmetry earns it a one-tap confirm; the others stay
// single-click so the common path isn't slowed down.
export function FindingFeedback({ onFeedback, busy }) {
  const t = useT();
  const [confirming, setConfirming] = useState(false);
  return (
    <div className="mt-8 rounded-xl border border-linea bg-papel-hondo/40 p-4">
      <p className="text-sm font-semibold text-tinta">{t("aprendizaje.feedback_pregunta")}</p>
      <div className="mt-2.5 flex flex-wrap gap-2">
        {FEEDBACK_ACTIONS.map((f) => {
          if (f.action === "dismissed" && confirming) {
            return (
              <span key={f.action} className="inline-flex items-center gap-1.5">
                <button disabled={busy} onClick={() => onFeedback("dismissed")}
                  className="rounded-full border border-rojo/40 bg-rojo/10 px-3.5 py-1.5 text-sm font-semibold text-rojo disabled:opacity-50">
                  {t("aprendizaje.feedback_dismiss_confirm")}
                </button>
                <button disabled={busy} onClick={() => setConfirming(false)}
                  className="text-sm font-semibold text-tinta-suave hover:text-tinta">
                  {t("aprendizaje.feedback_cancel")}
                </button>
              </span>
            );
          }
          return (
            <button key={f.action} disabled={busy}
              onClick={() => (f.action === "dismissed" ? setConfirming(true) : onFeedback(f.action))}
              className="rounded-full border border-linea bg-crema px-3.5 py-1.5 text-sm font-semibold text-tinta hover:border-violeta/40 hover:text-violeta disabled:opacity-50">
              {t(f.lk)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// Evidence pills: the same clickable treatment for both "Fuentes" (which
// section the numbers came from) and "Involucrados" (which specific record).
// Fuentes all point at the card's single `navegar` target (there's no
// per-source routing yet) — still a real jump, not a fabricated one.
function FuentePill({ label, onClick }) {
  const clickable = !!onClick;
  const Tag = clickable ? "button" : "span";
  return (
    <Tag
      type={clickable ? "button" : undefined}
      onClick={onClick}
      className={`inline-flex items-center gap-1 rounded-full border border-linea bg-crema px-2.5 py-1 text-xs font-medium text-tinta-suave ${
        clickable ? "transition-colors hover:border-hielo/40 hover:text-hielo" : ""
      }`}
    >
      {label}
      {clickable && <ArrowRight size={11} />}
    </Tag>
  );
}

// A small, neutral pill reading the shared confidence signal every card's
// drill now carries (backend/core/confidence.py) — not tied to `tono`,
// since confidence is about the evidence, not the finding's severity.
const CONFIDENCE_STYLE = {
  high: "border-salvia/30 text-salvia",
  medium: "border-oro/30 text-oro-tinta",
  low: "border-tinta-suave/30 text-tinta-suave",
};

// `axis` names WHICH confidence this is — data or hypothesis (see
// backend/core/confidence.py). The two can disagree, and when they do that
// disagreement is the most informative thing on the card, so the axis name
// rides inside the badge instead of being implied by position.
function ConfidenceBadge({ confidence, axis }) {
  const t = useT();
  if (!confidence?.level) return null;
  const cls = CONFIDENCE_STYLE[confidence.level] || CONFIDENCE_STYLE.low;
  return (
    <span
      title={confidence.reason}
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs ${cls}`}
    >
      {axis && <span className="opacity-70">{t(`cardneg.conf_${axis}`)}</span>}
      <span className="font-semibold">{t(`cardneg.conf_level_${confidence.level}`)}</span>
    </span>
  );
}

// The badge's `reason` was only readable via a hover title — invisible on
// touch. Repeat it as plain text so the trust-building copy actually reaches
// mobile users, not just desktop hover.
function ConfidenceReason({ confidence }) {
  if (!confidence?.level || !confidence?.reason) return null;
  return (
    <p className="mt-1 text-xs leading-snug text-tinta-suave">{confidence.reason}</p>
  );
}

// How many raw signals (alerts/opportunities/patterns) got merged into this
// one card (core/priorities.py::merge_duplicates). Collapsed by default —
// this is provenance for someone auditing "why does this exist", not
// something that belongs in the primary reading path.
function BasedOn({ origins = [] }) {
  const t = useT();
  const [expanded, setExpanded] = useState(false);
  if (origins.length < 2) return null;
  return (
    <div className="mt-3 text-xs text-tinta-suave">
      <button type="button" onClick={() => setExpanded((v) => !v)}
        className="inline-flex items-center gap-1 font-semibold hover:text-tinta">
        <Link2 size={11} /> {t("cardneg.based_on", { n: origins.length })}
      </button>
      {expanded && (
        <ul className="mt-1.5 space-y-0.5 pl-4">
          {origins.map((o, i) => <li key={i} className="list-disc">{o}</li>)}
        </ul>
      )}
    </div>
  );
}

function InvolucradoRow({ iv, onClick }) {
  // kind is required, not just id: an id without a recognized kind has
  // nowhere to navigate, and a clickable-looking row that silently no-ops
  // on click is worse than a plain text row.
  const clickable = !!onClick && iv.id != null && !!iv.kind;
  const Tag = clickable ? "button" : "div";
  return (
    <Tag
      type={clickable ? "button" : undefined}
      onClick={clickable ? () => onClick(iv) : undefined}
      className={`flex w-full items-baseline justify-between gap-3 border-b border-linea/60 px-3 py-2 text-left text-sm last:border-0 ${
        clickable ? "transition-colors hover:bg-papel-hondo/50" : ""
      }`}
    >
      <span className="min-w-0 flex-1">{iv.name}{iv.detail && <span className="text-tinta-suave"> — {iv.detail}</span>}</span>
      <span className="flex shrink-0 items-center gap-1">
        {iv.amount != null && <span className="plata font-medium text-hielo">{pesoCorto(iv.amount)}</span>}
        {clickable && <ChevronRight size={14} className="text-tinta-suave" />}
      </span>
    </Tag>
  );
}

// --- the structured insight (backend/core/insight.py) ---------------------
//
// The drill used to be a flat run of prose sentences that repeated the same
// fact in several of them. It now reads the insight in the order the owner
// actually reasons: what we saw → what we think it means → the evidence, each
// claim openable down to the rows behind it → the risk → the move → what we
// assumed and what would change our mind.

const SECTION_LABEL = "text-xs font-semibold uppercase tracking-wide text-tinta-suave";

// One section: heading, an optional aside (the confidence badges), body.
// More air above the heading than below it, so a section reads as a unit.
function DrillSection({ title, aside, children }) {
  return (
    <section className="mt-5">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <h3 className={SECTION_LABEL}>{title}</h3>
        {aside}
      </div>
      {children}
    </section>
  );
}

// Landmark for the work-queue brief: icon + heading, then more air than
// DrillSection so each cognitive chunk (move / reading / proof) rests
// as its own block instead of a run-on document.
function IconSection({ icon: Icon, title, aside, children }) {
  return (
    <section className="mt-8 first:mt-0">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <h3 className={`inline-flex items-center gap-1.5 ${SECTION_LABEL}`}>
          {Icon && <Icon size={13} aria-hidden="true" />}
          {title}
        </h3>
        {aside}
      </div>
      <div className="mt-2.5">{children}</div>
    </section>
  );
}

function shownValue(item, lang, t) {
  const formatted = formatValue(item.value, item.unit, lang);
  if (!formatted) return null;
  const unitKey = UNIT_KEY[item.unit];
  if (item.unit === "pct") return `${formatted}%`;
  if (item.unit === "×") return `×${formatted}`;
  if (unitKey) return `${formatted} ${t(unitKey)}`;
  return formatted;
}

// Primary metrics as a quiet strip — numbers first, labels second — so the
// owner scans the proof without re-reading a stacked list of the same facts.
function MetricStrip({ items }) {
  const t = useT();
  const lang = useLang();
  if (!items.length) return null;
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {items.map((item, i) => {
        const shown = shownValue(item, lang, t);
        const dev = item.deviation;
        const DevIcon = dev?.direction === "down" ? TrendingDown : TrendingUp;
        return (
          <div key={item.id ?? i} className="min-w-0 rounded-xl bg-papel-hondo/50 px-3 py-2.5">
            {shown && (
              <p className={`text-lg font-semibold leading-none text-tinta ${item.unit === "ars" ? "plata" : ""}`}>
                {shown}
              </p>
            )}
            <p className="mt-1.5 text-xs leading-snug text-tinta-suave">{item.label}</p>
            {dev && (
              <p className="mt-1 inline-flex items-center gap-0.5 text-xs font-semibold text-tinta-suave">
                <DevIcon size={11} aria-hidden="true" />{dev.pct}%
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

// Assumptions, alternatives and falsifiers are all {label} objects; tolerate
// a bare string so one stale builder cannot blank a whole section.
const labelOf = (x) => (typeof x === "string" ? x : x?.label || "");

const VALUE_LOCALE = { es: "es-AR", en: "en-US" };
const UNIT_KEY = {
  days: "cardneg.unit_days",
  months: "cardneg.unit_months",
  products: "cardneg.unit_products",
};

// Evidence values arrive RAW on purpose: the backend ships typed data so the
// client can format it for the reader's locale. Money follows the Silver Rule
// (`.plata`, DM Mono, tabular); everything else is a plain localized number.
function formatValue(value, unit, lang) {
  if (value == null || value === "") return null;
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  // One rule for money in this panel: the headline figure is the only
  // full number; every figure in the body (evidence, metrics, exposure)
  // is abbreviated. Three formats side by side read as three currencies.
  if (unit === "ars") return pesoCorto(n);
  return new Intl.NumberFormat(VALUE_LOCALE[lang] || VALUE_LOCALE.es, {
    maximumFractionDigits: Number.isInteger(n) ? 0 : 1,
  }).format(n);
}

// "¿Cómo se calculó?" on every metric. Native <details> so it is keyboard-
// and screen-reader-correct without any state of its own.
function MethodDisclosure({ method, methods }) {
  const t = useT();
  // `methods`: every distinct method behind a block of evidence, in ONE
  // disclosure — three identical "¿Cómo se calculó?" under three metrics
  // read as noise, and the answer was the same sentence each time.
  const lista = methods
    ? Array.from(new Map(methods.filter((m) => m?.label).map((m) => [m.label, m])).values())
    : (method?.label ? [method] : []);
  if (!lista.length) return null;
  return (
    <details className="group mt-1.5">
      <summary className="inline-flex cursor-pointer list-none items-center gap-1 text-xs font-semibold text-tinta-suave hover:text-tinta [&::-webkit-details-marker]:hidden">
        <ChevronRight size={11} className="transition-transform duration-150 group-open:rotate-90" />
        {t("cardneg.drill_method")}
      </summary>
      {lista.length === 1 ? (
        <p className="mt-1 pl-[15px] text-xs leading-snug text-tinta-suave">{lista[0].label}</p>
      ) : (
        <ul className="mt-1 space-y-1 pl-[15px] text-xs leading-snug text-tinta-suave">
          {lista.map((m, i) => <li key={m.key || i} className="list-disc">{m.label}</li>)}
        </ul>
      )}
    </details>
  );
}

// A P21 chart carried by one piece of evidence — the same box the drill used
// to give the card's single `grafico`, now owned by the claim it supports.
function EvidenceChart({ chart }) {
  const t = useT();
  if (!chart) return null;
  const serie = chart.series?.[0];
  return (
    <div className="mt-2 rounded-xl border border-linea bg-papel p-3">
      {(serie?.nombre || chart.meta?.unidad) && (
        <div className="mb-1 flex items-baseline justify-between gap-2">
          {serie?.nombre && <p className="truncate text-sm font-semibold text-tinta">{serie.nombre}</p>}
          {chart.meta?.unidad && <p className="shrink-0 text-2xs text-tinta-suave">{chart.meta.unidad}</p>}
        </div>
      )}
      <CuerpoConsulta resultado={chart} t={t} />
      {chart.meta?.ventana && <p className="mt-1 text-xs text-tinta-suave">{chart.meta.ventana}</p>}
    </div>
  );
}

// One claim: its label, the number that carries it, how far that number sits
// from its baseline, how it was computed, and the exact records behind it.
function EvidenceItem({ item, onVerInvolucrado, sinMetodo = false }) {
  const t = useT();
  const lang = useLang();
  const formatted = formatValue(item.value, item.unit, lang);
  const unitKey = UNIT_KEY[item.unit];
  // `pct` and `×` are symbols, not words, so they are special-cased here
  // instead of going through UNIT_KEY. `×` sits BEFORE the number, matching
  // how the card header already prints a multiplier ("×1,8").
  const shown = formatted && (item.unit === "pct" ? `${formatted}%`
    : item.unit === "×" ? `×${formatted}`
    : unitKey ? `${formatted} ${t(unitKey)}` : formatted);
  const dev = item.deviation;
  const DevIcon = dev?.direction === "down" ? TrendingDown : TrendingUp;
  const records = item.records || [];
  return (
    <div className="border-t border-linea/60 pt-3 first:border-t-0 first:pt-0">
      <div className="flex items-baseline justify-between gap-3">
        <p className="min-w-0 flex-1 text-sm leading-snug text-tinta">{item.label}</p>
        {shown && (
          <span className={`shrink-0 text-sm font-semibold text-tinta ${item.unit === "ars" ? "plata" : ""}`}>
            {shown}
          </span>
        )}
      </div>
      {(dev || item.baseline?.label) && (
        <p className="mt-1 flex flex-wrap items-center gap-x-1.5 text-xs text-tinta-suave">
          {dev && (
            <span className="inline-flex items-center gap-0.5 font-semibold">
              <DevIcon size={12} aria-hidden="true" />{dev.pct}%
            </span>
          )}
          {item.baseline?.label && t("cardneg.drill_vs", { baseline: item.baseline.label })}
        </p>
      )}
      {!sinMetodo && <MethodDisclosure method={item.method} />}
      <EvidenceChart chart={item.chart} />
      {records.length > 0 && (
        <div className="mt-2 overflow-hidden rounded-xl border border-linea">
          {records.map((r, i) => <InvolucradoRow key={r.id ?? i} iv={r} onClick={onVerInvolucrado} />)}
        </div>
      )}
    </div>
  );
}

// Primary evidence is what makes the conclusion true and stays open;
// supporting evidence is context and waits behind one tap, so the panel opens
// on the load-bearing facts instead of on everything at once.
function Evidence({ items, onVerInvolucrado, metodoUnico = false }) {
  const t = useT();
  const [expanded, setExpanded] = useState(false);
  const [primary, supporting] = useMemo(() => [
    items.filter((e) => e.weight === "primary"),
    items.filter((e) => e.weight !== "primary"),
  ], [items]);
  // A card whose builder marked nothing primary would otherwise open empty.
  const lead = primary.length ? primary : supporting;
  const rest = primary.length ? supporting : [];
  return (
    <div className="mt-2 space-y-3">
      {lead.map((e, i) => (
        <EvidenceItem key={e.id ?? `p${i}`} item={e} onVerInvolucrado={onVerInvolucrado} sinMetodo={metodoUnico} />
      ))}
      {expanded && rest.map((e, i) => (
        <EvidenceItem key={e.id ?? `s${i}`} item={e} onVerInvolucrado={onVerInvolucrado} sinMetodo={metodoUnico} />
      ))}
      {metodoUnico && <MethodDisclosure methods={(expanded ? items : lead).map((e) => e.method)} />}
      {rest.length > 0 && (
        <button type="button" onClick={() => setExpanded((v) => !v)}
          className="inline-flex items-center gap-1 text-sm font-semibold text-tinta-suave hover:text-tinta">
          <ChevronDown size={13} className={`transition-transform duration-150 ${expanded ? "rotate-180" : ""}`} />
          {expanded ? t("cardneg.drill_less") : t("cardneg.drill_more", { n: rest.length })}
        </button>
      )}
    </div>
  );
}

// Supporting evidence + the shared method note, kept behind one tap so the
// brief opens on the load-bearing numbers and names.
function AccionSupporting({ rest, all, lead, onVerInvolucrado }) {
  const t = useT();
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="space-y-3">
      {expanded && rest.map((e, i) => (
        <EvidenceItem key={e.id ?? `s${i}`} item={e} onVerInvolucrado={onVerInvolucrado} sinMetodo />
      ))}
      <MethodDisclosure methods={(expanded ? all : lead).map((e) => e.method)} />
      {rest.length > 0 && (
        <button type="button" onClick={() => setExpanded((v) => !v)}
          className="inline-flex items-center gap-1 text-sm font-semibold text-tinta-suave hover:text-tinta">
          <ChevronDown size={13} className={`transition-transform duration-150 ${expanded ? "rotate-180" : ""}`} />
          {expanded ? t("cardneg.drill_less") : t("cardneg.drill_more", { n: rest.length })}
        </button>
      )}
    </div>
  );
}

// Alternatives and falsifiers answer the same question — "what would change"
// this?" — so they share one collapsed block instead of two headings the
// owner has to read past on the way to the action.
function Caveats({ alternatives = [], falsifiers = [] }) {
  const t = useT();
  if (!alternatives.length && !falsifiers.length) return null;
  return (
    <details className="group mt-5 border-t border-linea pt-3">
      <summary className={`inline-flex cursor-pointer list-none items-center gap-1 ${SECTION_LABEL} hover:text-tinta [&::-webkit-details-marker]:hidden`}>
        <ChevronRight size={11} className="transition-transform duration-150 group-open:rotate-90" />
        {t("cardneg.drill_caveats")}
      </summary>
      <div className="mt-2 space-y-2 pl-[15px]">
        {alternatives.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-tinta">{t("cardneg.drill_alternatives")}</p>
            <ul className="mt-1 space-y-1">
              {alternatives.map((c, i) => (
                <li key={i} className="text-sm leading-snug text-tinta-suave">{labelOf(c)}</li>
              ))}
            </ul>
          </div>
        )}
        {falsifiers.length > 0 && (
          <ul className="space-y-1">
            {falsifiers.map((c, i) => (
              <li key={i} className="text-sm leading-snug text-tinta-suave">{labelOf(c)}</li>
            ))}
          </ul>
        )}
      </div>
    </details>
  );
}

// Who this lands on and by when — a footer line, because it frames the whole
// card rather than belonging to any one part of the reasoning. "Sin dueño
// sugerido" is the honest state when no single teammate covers the modules
// (core/insight_owner.py returns None rather than guessing).
function OwnerLine({ owner, deadline }) {
  const t = useT();
  if (!owner && !deadline?.date) return null;
  const late = deadline?.urgency === "overdue" || deadline?.urgency === "today";
  return (
    <div className="mt-5 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-linea pt-3 text-xs text-tinta-suave">
      <span className="inline-flex items-center gap-1.5">
        <UserRound size={13} aria-hidden="true" />
        {owner ? t("cardneg.drill_owner", { name: owner.suggested }) : t("cardneg.drill_no_owner")}
        {owner?.role && <span className="text-tinta-suave/80">· {owner.role}</span>}
      </span>
      {deadline?.date && (
        <span className={`inline-flex items-center gap-1.5 ${late ? "font-semibold text-rojo-hondo" : ""}`}>
          <CalendarClock size={13} aria-hidden="true" />
          {t("cardneg.drill_due", { date: fecha(deadline.date) })}
          {deadline.basis && <span className="font-normal text-tinta-suave/80">· {deadline.basis}</span>}
        </span>
      )}
    </div>
  );
}

export function DrillNegocio({ tono = "salvia", titulo, monto, montoLabel, cifraTexto,
                               insight, macro, fuentes = [], acciones, onCerrar,
                               propuesta, onAprobarPropuesta, actionTaken,
                               propuestaTrabajando, variante = "overlay",
                               chip, chipIcon: ChipIcon, chipCls,
                               // "clasico": the reasoning order (pattern → hypothesis →
                               // evidence → action), unchanged for every screen that
                               // already used it. "accion": what happens → what to do →
                               // the evidence, with the reasoning folded — the order a
                               // work queue is read in (Prioridades opts in).
                               layout = "clasico",
                               onFeedback, feedbackBusy, origins = [],
                               onVerFuentes, onVerInvolucrado }) {
  const t = useT();
  const a = ACENTO[tono] || ACENTO.salvia;
  const panel = variante === "panel";
  const dialogRef = useRef(null);

  // One structured object in place of the six prose props this drill used to
  // take (backend/core/insight.py). Destructured with defaults so a card that
  // is still loading, or one that honestly has no hypothesis, renders the
  // parts it does have instead of nothing.
  const {
    pattern, hypothesis, evidence = [], assumptions = [], alternatives = [],
    falsifiers = [], risk, recommendation, owner, deadline, confidence,
  } = insight || {};
  // The proposal lives on the recommendation now; `propuesta` stays as the
  // envelope-level fallback. AngelaProposal is unchanged, so normalize the
  // two key styles here rather than there.
  const rawProposal = recommendation?.proposal || propuesta;
  const proposal = rawProposal && {
    title: rawProposal.title ?? rawProposal.titulo,
    detail: rawProposal.detail ?? rawProposal.detalle,
  };
  const dataBadge = <ConfidenceBadge confidence={confidence?.data} axis="data" />;
  // On nine cards `risk.exposure`, `monto` and the primary metric are
  // literally the same expression, so the panel printed one figure three
  // times. Compare the RAW numbers the backend ships — never the formatted
  // strings, which Python and Intl render differently — so this can only
  // ever hide a figure that really is the header figure.
  const showExposure = risk?.exposure != null &&
    !(monto != null && Number(risk.exposure) === Number(monto));

  // Every caller passes an inline arrow for `onCerrar`, so its identity
  // changes on each render. Depending on it would re-run this effect —
  // yanking focus back to the dialog — on any parent re-render (toggling the
  // working flag while approving, for one). Keep the latest handler in a ref
  // and depend only on `panel`, so focus is set once when the dialog opens.
  const onCerrarRef = useRef(onCerrar);
  onCerrarRef.current = onCerrar;

  // Self-contained so every caller (desktop panel+overlay, mobile overlay)
  // gets the same behavior instead of each screen re-implementing Escape and
  // initial focus: on open, move focus into the dialog; Esc closes it.
  useEffect(() => {
    if (panel) return;
    dialogRef.current?.focus();
    const onKey = (e) => { if (e.key === "Escape") onCerrarRef.current?.(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [panel]);
  const cabecera = (
        <div className="flex items-start justify-between gap-3">
          <div>
            {chip && (
              <span className={`mb-2 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${chipCls || a.chip}`}>
                {ChipIcon && <ChipIcon size={12} />} {chip}
              </span>
            )}
            <h2 className="font-display text-xl font-bold leading-tight">{titulo}</h2>
            {(monto != null || cifraTexto) && (
              <p className={`plata mt-1 text-3xl font-medium ${a.cifra}`}>
                {monto != null ? peso(monto) : cifraTexto}
                {montoLabel && <span className="ml-2 align-middle text-xs font-normal text-tinta-suave">{montoLabel}</span>}
              </p>
            )}
          </div>
          {!panel && onCerrar && (
            <button onClick={onCerrar} aria-label={t("cardneg.close")}
              className="text-tinta-suave hover:text-tinta"><X size={20} /></button>
          )}
        </div>
  );

  const bloqueAccion = (risk?.label || recommendation?.label || recommendation?.detail || proposal || actionTaken) && (
    <DrillSection title={t("cardneg.drill_recommend")}>
      {risk?.label && (
        <p className={`rounded-lg px-3 py-2 text-sm leading-snug ${
          risk.level === "high"
            ? "border border-rojo/25 bg-rojo/[0.06] text-rojo-hondo"
            : "bg-papel-hondo/50 text-tinta"
        }`}>
          {risk.label}
          {showExposure && (
            <span className="plata ml-1.5 font-semibold">{pesoCorto(risk.exposure)}</span>
          )}
        </p>
      )}
      {recommendation?.label && (
        <p className={`text-sm font-semibold leading-snug text-tinta ${risk?.label ? "mt-2" : "mt-1.5"}`}>{recommendation.label}</p>
      )}
      {recommendation?.detail && (
        <p className="mt-1 text-sm leading-snug text-tinta-suave">{recommendation.detail}</p>
      )}
      <AngelaProposal
        proposal={proposal}
        onApprove={onAprobarPropuesta}
        working={propuestaTrabajando}
        actionTaken={actionTaken}
      />
    </DrillSection>
  );

  // The work-queue brief. Same facts as clasico, grouped so the owner can
  // rest between chunks: identity → the move → the reading → the proof →
  // provenance. Hierarchy still comes from type, air and one hairline —
  // the soft wells are only for the decision and the metric scan.
  const moveLabel = recommendation?.label || titulo;
  const [primaryEvidence, supportingEvidence] = useMemo(() => [
    evidence.filter((e) => e.weight === "primary"),
    evidence.filter((e) => e.weight !== "primary"),
  ], [evidence]);
  const leadEvidence = primaryEvidence.length ? primaryEvidence : supportingEvidence;
  const restEvidence = primaryEvidence.length ? supportingEvidence : [];
  const metricItems = leadEvidence.filter((e) => e.value != null && e.value !== "");
  const sameAsHeader = (e) => monto != null && e.unit === "ars" && Number(e.value) === Number(monto);
  const stripItems = metricItems.length > 1
    ? metricItems
    : metricItems.filter((e) => !sameAsHeader(e));
  const involvedBlocks = leadEvidence.filter((e) => (e.records || []).length > 0);
  const leadCharts = leadEvidence.filter((e) => e.chart);
  const late = deadline?.urgency === "overdue" || deadline?.urgency === "today";
  const DEADLINE_CHIP = {
    overdue: "bg-rojo/10 text-rojo",
    today: "bg-oro/15 text-oro-tinta",
  };

  const contenidoAccion = (
    <>
        <header>
          <div className="flex flex-wrap items-center gap-1.5">
            {chip && (
              <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${chipCls || a.chip}`}>
                {ChipIcon && <ChipIcon size={12} />} {chip}
              </span>
            )}
            {deadline?.urgency && DEADLINE_CHIP[deadline.urgency] && (
              <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${DEADLINE_CHIP[deadline.urgency]}`}>
                <CalendarClock size={11} aria-hidden="true" />
                {t(deadline.urgency === "overdue" ? "prioridades.overdue" : "prioridades.due_today")}
              </span>
            )}
            <span className="ml-auto inline-flex flex-wrap items-center gap-1.5">
              {dataBadge}
              <ConfidenceBadge confidence={confidence?.hypothesis} axis="hypothesis" />
            </span>
            {!panel && onCerrar && (
              <button onClick={onCerrar} aria-label={t("cardneg.close")}
                className="text-tinta-suave hover:text-tinta"><X size={20} /></button>
            )}
          </div>
          <h2 className="mt-4 font-display text-2xl font-bold leading-tight">{titulo}</h2>
          {(monto != null || cifraTexto) && (
            <p className={`plata mt-3 text-3xl font-medium ${a.cifra}`}>
              {monto != null ? peso(monto) : cifraTexto}
              <span className="ml-2 align-middle font-sans text-xs font-normal text-tinta-suave">
                {montoLabel || t("cardneg.drill_at_stake")}
              </span>
            </p>
          )}
          {pattern?.label && (
            <p className="mt-4 max-w-2xl text-base leading-relaxed text-tinta-suave">{pattern.label}</p>
          )}
          {pattern?.since && <p className="mt-1 text-xs text-tinta-suave">{pattern.since}</p>}
          {macro?.inflacion != null && (
            <p className="mt-3 rounded-xl border border-hielo/25 bg-hielo/[0.06] px-3 py-2 text-sm text-hielo">
              {t("cardneg.drill_macro", { ipc: macro.inflacion, fuente: macro.fuente || "", fecha: macro.fecha || "" })}
            </p>
          )}
          {(owner || deadline?.date) && (
            <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-tinta-suave">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-papel-hondo/60 px-2.5 py-1">
                <UserRound size={12} aria-hidden="true" />
                {owner ? t("cardneg.drill_owner", { name: owner.suggested }) : t("cardneg.drill_no_owner")}
                {owner?.role && <span className="text-tinta-suave/80">· {owner.role}</span>}
              </span>
              {deadline?.date && (
                <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 ${
                  late ? "bg-rojo/10 font-semibold text-rojo-hondo" : "bg-papel-hondo/60"
                }`}>
                  <CalendarClock size={12} aria-hidden="true" />
                  {t("cardneg.drill_due", { date: fecha(deadline.date) })}
                  {deadline.basis && <span className="font-normal text-tinta-suave/80">· {deadline.basis}</span>}
                </span>
              )}
            </div>
          )}
        </header>

        {(risk?.label || recommendation?.label || recommendation?.detail || proposal || actionTaken || moveLabel) && (
          <IconSection icon={Compass} title={t("cardneg.drill_recommend")}>
            <div className="rounded-2xl border border-linea bg-papel-hondo/35 px-4 py-3.5">
              {recommendation?.label && recommendation.label !== titulo && (
                <p className="text-base font-semibold leading-snug text-tinta">{recommendation.label}</p>
              )}
              {(recommendation?.detail || (!recommendation?.label && moveLabel)) && (
                <p className={`text-sm leading-relaxed ${recommendation?.label && recommendation.label !== titulo ? "mt-1.5 text-tinta-suave" : "text-base font-semibold leading-snug text-tinta"}`}>
                  {recommendation?.detail || moveLabel}
                </p>
              )}
              {risk?.label && (
                <p className={`mt-3 inline-flex items-start gap-2 rounded-xl px-3 py-2 text-sm leading-snug ${
                  risk.level === "high"
                    ? "border border-rojo/25 bg-rojo/[0.06] text-rojo-hondo"
                    : "bg-crema text-tinta"
                }`}>
                  <ShieldAlert size={14} className={`mt-0.5 shrink-0 ${risk.level === "high" ? "text-rojo" : "text-tinta-suave"}`} aria-hidden="true" />
                  <span>
                    {risk.label}
                    {showExposure && (
                      <span className="plata ml-1.5 font-semibold">{pesoCorto(risk.exposure)}</span>
                    )}
                  </span>
                </p>
              )}
              <AngelaProposal
                proposal={proposal}
                onApprove={onAprobarPropuesta}
                working={propuestaTrabajando}
                actionTaken={actionTaken}
              />
            </div>
          </IconSection>
        )}

        {hypothesis?.label && (
          <IconSection icon={Lightbulb} title={t("cardneg.drill_read")}>
            <p className="max-w-2xl text-sm leading-relaxed text-tinta">{hypothesis.label}</p>
            <ConfidenceReason confidence={confidence?.data} />
            <ConfidenceReason confidence={confidence?.hypothesis} />
          </IconSection>
        )}

        {evidence.length > 0 && (
          <IconSection icon={BarChart3} title={t("cardneg.drill_evidence")} aside={dataBadge}>
            <div className="space-y-5">
              <MetricStrip items={stripItems} />
              {involvedBlocks.map((e, i) => (
                <div key={e.id ?? `inv${i}`}>
                  <p className="mb-2 inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-tinta-suave">
                    <ScanSearch size={12} aria-hidden="true" />
                    {e.label || t("cardneg.drill_involved")}
                  </p>
                  <div className="overflow-hidden rounded-xl border border-linea">
                    {e.records.map((r, ri) => (
                      <InvolucradoRow key={r.id ?? ri} iv={r} onClick={onVerInvolucrado} />
                    ))}
                  </div>
                </div>
              ))}
              {leadCharts.map((e, i) => (
                <EvidenceChart key={e.id ?? `ch${i}`} chart={e.chart} />
              ))}
              <AccionSupporting
                rest={restEvidence}
                all={evidence}
                lead={leadEvidence}
                onVerInvolucrado={onVerInvolucrado}
              />
            </div>
          </IconSection>
        )}

        {(assumptions.length > 0 || alternatives.length > 0 || falsifiers.length > 0 || origins.length > 1) && (
          <details className="group mt-8 border-t border-linea pt-4">
            <summary className={`inline-flex cursor-pointer list-none items-center gap-1.5 ${SECTION_LABEL} hover:text-tinta [&::-webkit-details-marker]:hidden`}>
              <ChevronRight size={11} className="transition-transform duration-150 group-open:rotate-90" />
              {t("cardneg.drill_por_que")}
            </summary>
            <div className="mt-3 max-w-2xl space-y-4">
              {assumptions.length > 0 && (
                <div>
                  <p className={SECTION_LABEL}>{t("cardneg.drill_assumptions")}</p>
                  <ul className="mt-2 space-y-2">
                    {assumptions.map((s, i) => (
                      <li key={i} className="text-sm leading-relaxed text-tinta-suave">
                        {labelOf(s)}
                        {s?.if_wrong && <span className="mt-0.5 block text-tinta-suave/80">{s.if_wrong}</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <Caveats alternatives={alternatives} falsifiers={falsifiers} />
              <BasedOn origins={origins} />
            </div>
          </details>
        )}

        {fuentes.length > 0 && (
          <IconSection icon={BookOpen} title={t("cardneg.drill_fuentes")}>
            <div className="flex flex-wrap gap-1.5">
              {fuentes.map((f, i) => (
                <FuentePill key={i} label={f} onClick={onVerFuentes} />
              ))}
            </div>
          </IconSection>
        )}
        {onFeedback && <FindingFeedback onFeedback={onFeedback} busy={feedbackBusy} />}
    </>
  );

  const contenidoClasico = (
    <>
        {cabecera}

        {/* 1 · What we observed — the finding itself, no interpretation in it. */}
        {(pattern?.label || macro?.inflacion != null) && (
          <DrillSection title={t("cardneg.drill_pattern")}>
            {/* A step larger than every other body line in the panel: the
                observation is what the owner came here to read. */}
            {pattern?.label && (
              <p className="mt-1.5 text-base leading-snug text-tinta">{pattern.label}</p>
            )}
            {pattern?.since && (
              <p className="mt-1 text-xs text-tinta-suave">{pattern.since}</p>
            )}
            {macro?.inflacion != null && (
              <p className="mt-2 rounded-lg border border-hielo/25 bg-hielo/[0.06] px-3 py-2 text-sm text-hielo">
                {t("cardneg.drill_macro", { ipc: macro.inflacion, fuente: macro.fuente || "", fecha: macro.fecha || "" })}
              </p>
            )}
          </DrillSection>
        )}

        {/* 2 · What we think it means. Several cards honestly have no reading
            of the pattern; those show no hypothesis and no hypothesis badge,
            rather than dressing the observation up as a conclusion. */}
        {hypothesis?.label && (
          <DrillSection
            title={t("cardneg.drill_hypothesis")}
            aside={(
              <span className="flex flex-wrap items-center gap-1.5">
                {dataBadge}
                <ConfidenceBadge confidence={confidence?.hypothesis} axis="hypothesis" />
              </span>
            )}
          >
            <p className="mt-1.5 text-sm leading-snug text-tinta">{hypothesis.label}</p>
            {/* Repeated as text because the badges' `reason` is only a hover
                title — invisible on touch, which is half these users. */}
            <ConfidenceReason confidence={confidence?.data} />
            <ConfidenceReason confidence={confidence?.hypothesis} />
          </DrillSection>
        )}

        {/* 3 · The evidence, each claim openable down to its own records. */}
        {evidence.length > 0 && (
          <DrillSection
            title={t("cardneg.drill_evidence")}
            aside={hypothesis?.label ? null : dataBadge}
          >
            <Evidence items={evidence} onVerInvolucrado={onVerInvolucrado} />
          </DrillSection>
        )}

        {/* 4 · What it costs to do nothing, as the lead line, then what to do.
            Risk and recommendation are causally paired — risk is typically one
            short line, too light to earn its own section header — so they
            share this section instead of each getting one. */}
        {/* P38·B — Aprobar no ejecuta contra nadie: deja el borrador
            firmado. Human-in-the-loop visible. */}
        {bloqueAccion}

        {/* 5 · What we took for granted, and what would change our mind. */}
        {assumptions.length > 0 && (
          <DrillSection title={t("cardneg.drill_assumptions")}>
            <ul className="mt-1.5 space-y-1.5">
              {assumptions.map((s, i) => (
                <li key={i} className="rounded-lg bg-papel-hondo/50 px-3 py-2 text-sm leading-snug text-tinta-suave">
                  {labelOf(s)}
                  {s?.if_wrong && <span className="mt-0.5 block text-tinta-suave/80">{s.if_wrong}</span>}
                </li>
              ))}
            </ul>
          </DrillSection>
        )}

        <Caveats alternatives={alternatives} falsifiers={falsifiers} />

        {/* 6 · Who it lands on, by when, and where the numbers came from. */}
        <OwnerLine owner={owner} deadline={deadline} />

        {fuentes.length > 0 && (
          <DrillSection title={t("cardneg.drill_fuentes")}>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {fuentes.map((f, i) => (
                <FuentePill key={i} label={f} onClick={onVerFuentes} />
              ))}
            </div>
          </DrillSection>
        )}

        <BasedOn origins={origins} />

        {onFeedback && <FindingFeedback onFeedback={onFeedback} busy={feedbackBusy} />}
    </>
  );
  const contenido = layout === "accion" ? contenidoAccion : contenidoClasico;
  const pie = acciones && (
    <div className="shrink-0 border-t border-linea bg-crema px-6 py-4">
      <div className="flex flex-wrap items-center gap-2">{acciones}</div>
    </div>
  );
  const briefPad = layout === "accion"
    ? (panel ? "px-8 py-8 pb-12" : "px-5 py-6 pb-10")
    : "p-6";
  if (panel) {
    return (
      <div className="flex h-full flex-col">
        <div className={`flex-1 overflow-y-auto ${briefPad}`}>{contenido}</div>
        {pie}
      </div>
    );
  }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-tinta/40 p-4" onClick={onCerrar}>
      <div ref={dialogRef} role="dialog" aria-modal="true" aria-label={titulo} tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        className={`flex max-h-[88vh] w-full flex-col overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-alta outline-none ${
          layout === "accion" ? "max-w-2xl" : "max-w-xl"
        }`}>
        <div className={`flex-1 overflow-y-auto ${briefPad}`}>{contenido}</div>
        {pie}
      </div>
    </div>
  );
}
