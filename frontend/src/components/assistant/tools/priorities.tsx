import type { ToolPresenter, ToolRenderProps } from "./types";
import { toolLabels } from "./labels";
import { toolErrorMessage, ToolErrorText } from "./toolError";
import { peso } from "../../../lib/format";
import { t } from "../../../lib/i18n";

/**
 * listar_prioridades' result has no top-level `items` array, so Fallback's
 * GenericResult dropped `act`/`watch` and rendered only `badge`/`orden` — the
 * actual priority list never showed. `tono` mirrors the rojo/oro/salvia
 * vocabulary used elsewhere (see desktop/sections/Inicio.jsx).
 */

// Keys/values below are the actual `tono` values angela.py sends — not ours to rename.
const TONE_CHIP_CLASSES: Record<string, string> = {
  rojo: "bg-rojo/10 text-rojo",
  oro: "bg-oro/15 text-oro-tinta",
  salvia: "bg-salvia/12 text-salvia",
};

export function toneChipClass(tone?: string): string {
  return TONE_CHIP_CLASSES[tone || ""] || "bg-papel-hondo text-tinta-suave";
}

// Field names below mirror one priority's JSON shape (backend/angela.py::_slim).
type Priority = {
  id?: string;
  chip?: string;
  titulo?: string;
  resumen?: string;
  monto?: number;
  cifra_texto?: string;
  tono?: string;
};

function PriorityRow({ priority }: { priority: Priority }) {
  return (
    <div className="flex items-start gap-2 border-b border-linea/60 py-2 last:border-0">
      {priority.chip && (
        <span
          className={`shrink-0 rounded-full px-2 py-0.5 text-[0.7rem] font-semibold ${toneChipClass(priority.tono)}`}
        >
          {priority.chip}
        </span>
      )}
      <div className="min-w-0 flex-1">
        <p className="text-[0.86rem] leading-snug text-tinta">{priority.titulo}</p>
        {priority.resumen && <p className="text-[0.78rem] leading-snug text-tinta-suave">{priority.resumen}</p>}
      </div>
      {(priority.cifra_texto || priority.monto != null) && (
        <span className="shrink-0 whitespace-nowrap text-[0.82rem] font-medium text-tinta">
          {priority.cifra_texto || peso(priority.monto || 0)}
        </span>
      )}
    </div>
  );
}

// `act`/`watch` are the response's own top-level keys (backend/core/priorities.py).
type PrioritiesResult = { act?: Priority[]; watch?: Priority[] };

export function Priorities({ result }: ToolRenderProps) {
  const err = toolErrorMessage(result);
  if (err) return <ToolErrorText message={err} />;
  const data = result as PrioritiesResult;
  if (!data) return null;
  const act = data.act || [];
  const watch = data.watch || [];
  if (act.length === 0 && watch.length === 0) return null;
  return (
    <div className="mt-1.5 space-y-2">
      {act.length > 0 && (
        <div>
          <p className="mb-0.5 text-[0.68rem] font-semibold uppercase tracking-[0.1em] text-tinta-suave">
            {t("toolui.prioridades.act")}
          </p>
          {act.map((priority, i) => (
            <PriorityRow key={priority.id ?? i} priority={priority} />
          ))}
        </div>
      )}
      {watch.length > 0 && (
        <div>
          <p className="mb-0.5 text-[0.68rem] font-semibold uppercase tracking-[0.1em] text-tinta-suave">
            {t("toolui.prioridades.watch")}
          </p>
          {watch.map((priority, i) => (
            <PriorityRow key={priority.id ?? i} priority={priority} />
          ))}
        </div>
      )}
    </div>
  );
}

export const prioritiesPresenter: ToolPresenter = {
  labels: toolLabels("listar_prioridades"),
  render: Priorities,
};
