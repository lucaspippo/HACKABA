import { useState } from "react";
import { X } from "lucide-react";
import { num } from "../lib/format";
import { ACCION, accionDe } from "../lib/prioridadAccion";
import { useT } from "../lib/i18n";

const VISIBLE_CAP = 5;

// Auditoría-style action pills: icon + label + count, one at a time, click again to clear.
// Capped at VISIBLE_CAP (the working-memory guideline) — a busy tenant with
// the full 12-verb vocabulary present collapses the rest behind "+N más"
// instead of a wall of scrolling pills.
export default function FiltrosAccion({ items, filtro, onFiltro }) {
  const t = useT();
  const [expanded, setExpanded] = useState(false);
  const counts = {};
  const label = {};
  for (const it of items) {
    const k = accionDe(it);
    counts[k] = (counts[k] || 0) + 1;
    if (!label[k]) label[k] = t(`prioridades.accion_${k}`) || it.chip || k;
  }
  const ranked = Object.keys(counts)
    .filter((k) => ACCION[k])
    .sort((a, b) => counts[b] - counts[a]);
  if (ranked.length < 2) return null;
  const overflow = !expanded && ranked.length > VISIBLE_CAP
    ? ranked.slice(VISIBLE_CAP)
    : [];
  const pills = expanded ? ranked : ranked.slice(0, VISIBLE_CAP);

  return (
    <div className="flex flex-nowrap items-center gap-1.5 overflow-x-auto pb-0.5 [scrollbar-width:none] sm:flex-wrap sm:overflow-visible [&::-webkit-scrollbar]:hidden">
      {pills.map((k) => {
        const { icon: Icon } = ACCION[k];
        const on = filtro === k;
        return (
          <button
            key={k}
            type="button"
            aria-pressed={on}
            onClick={() => onFiltro(on ? null : k)}
            className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-[0.78rem] font-semibold transition-colors ${
              on ? "border-violeta bg-violeta/[0.06] text-violeta"
                 : "border-linea text-tinta-suave hover:text-tinta"
            }`}
          >
            <Icon size={12} /> {label[k]}
            <span className={on ? "text-violeta/70" : "text-tinta-suave/70"}>{num(counts[k])}</span>
          </button>
        );
      })}
      {overflow.length > 0 && (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="inline-flex shrink-0 items-center gap-1 rounded-full border border-linea px-3 py-1.5 text-[0.78rem] font-semibold text-tinta-suave hover:text-tinta"
        >
          {t("prioridades.filter_more", { n: overflow.length })}
        </button>
      )}
      {filtro && (
        <button
          type="button"
          onClick={() => onFiltro(null)}
          className="inline-flex shrink-0 items-center gap-1 text-[0.8rem] font-semibold text-tinta-suave hover:text-tinta"
        >
          <X size={12} /> {t("prioridades.limpiar")}
        </button>
      )}
    </div>
  );
}
