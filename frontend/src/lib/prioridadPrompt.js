import { fecha, peso, pesoCorto } from "./format";

const VALUE_LOCALE = { es: "es-AR", en: "en-US" };
const UNIT_KEY = {
  days: "cardneg.unit_days",
  months: "cardneg.unit_months",
  products: "cardneg.unit_products",
};

function labelOf(x) {
  if (typeof x === "string") return x;
  return x?.label || "";
}

function formatPromptValue(value, unit, lang, t) {
  if (value == null || value === "") return null;
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  if (unit === "ars") return pesoCorto(n);
  const formatted = new Intl.NumberFormat(VALUE_LOCALE[lang] || VALUE_LOCALE.es, {
    maximumFractionDigits: Number.isInteger(n) ? 0 : 1,
  }).format(n);
  if (unit === "pct") return `${formatted}%`;
  if (unit === "×") return `×${formatted}`;
  const unitKey = UNIT_KEY[unit];
  return unitKey ? `${formatted} ${t(unitKey)}` : formatted;
}

function addLine(lines, key, value, t) {
  if (value == null || value === "") return;
  lines.push(`${t(key)}: ${value}`);
}

function evidenceLines(evidence, lang, t) {
  return (evidence || []).flatMap((item) => {
    const label = labelOf(item);
    const shown = formatPromptValue(item.value, item.unit, lang, t);
    if (label && shown) return [`- ${label}: ${shown}`];
    if (label) return [`- ${label}`];
    return [];
  });
}

function involvedLines(evidence) {
  const seen = new Set();
  const rows = [];
  for (const item of evidence || []) {
    for (const row of item.records || []) {
      const name = row?.name;
      if (!name || seen.has(name)) continue;
      seen.add(name);
      rows.push(row.amount != null ? `- ${name} (${pesoCorto(row.amount)})` : `- ${name}`);
      if (rows.length >= 8) return rows;
    }
  }
  return rows;
}

/**
 * A thorough, fact-grounded prompt for Ángela: interpret THIS priority in
 * natural language. Numbers come from the card so she narrates measured
 * figures instead of inventing them.
 */
export function buildPrioridadPrompt(item, t, lang = "es") {
  if (!item) return "";
  const insight = item.insight || {};
  const evidence = insight.evidence || [];
  const lines = [t("prioridades.prompt_intro"), ""];

  addLine(lines, "prioridades.prompt_priority", item.titulo, t);

  const amount = item.monto != null ? peso(item.monto) : (item.cifra_texto || item.cifraTexto);
  if (amount) {
    const tag = item.monto_label || item.montoLabel;
    addLine(lines, "prioridades.prompt_at_stake", tag ? `${amount} (${tag})` : amount, t);
  }

  addLine(lines, "prioridades.prompt_observed", insight.pattern?.label || item.resumen, t);
  addLine(lines, "prioridades.prompt_hypothesis", insight.hypothesis?.label, t);
  const move = insight.recommendation?.label || item.titulo;
  addLine(lines, "prioridades.prompt_move", move, t);
  if (insight.recommendation?.detail && insight.recommendation.detail !== move) {
    lines.push(insight.recommendation.detail);
  }
  addLine(lines, "prioridades.prompt_risk", insight.risk?.label, t);

  const ev = evidenceLines(evidence, lang, t);
  if (ev.length) {
    lines.push("", `${t("prioridades.prompt_evidence")}:`);
    lines.push(...ev);
  }

  const involved = involvedLines(evidence);
  if (involved.length) {
    lines.push("", `${t("prioridades.prompt_involved")}:`);
    lines.push(...involved);
  }

  if (item.fuentes?.length) {
    addLine(lines, "prioridades.prompt_sources", item.fuentes.join(" · "), t);
  }
  addLine(lines, "prioridades.prompt_owner", insight.owner?.suggested, t);
  if (insight.deadline?.date) {
    const due = fecha(insight.deadline.date);
    addLine(
      lines,
      "prioridades.prompt_due",
      insight.deadline.basis ? `${due} · ${insight.deadline.basis}` : due,
      t,
    );
  }

  lines.push("", t("prioridades.prompt_ask"));
  return lines.join("\n");
}
