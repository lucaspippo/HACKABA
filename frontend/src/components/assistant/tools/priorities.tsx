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

const TONO_CHIP: Record<string, string> = {
  rojo: "bg-rojo/10 text-rojo",
  oro: "bg-oro/15 text-oro-tinta",
  salvia: "bg-salvia/12 text-salvia",
};

export function tonoChip(tono?: string): string {
  return TONO_CHIP[tono || ""] || "bg-papel-hondo text-tinta-suave";
}

type Prioridad = {
  id?: string;
  chip?: string;
  titulo?: string;
  resumen?: string;
  monto?: number;
  cifra_texto?: string;
  tono?: string;
};

function Fila({ p }: { p: Prioridad }) {
  return (
    <div className="flex items-start gap-2 border-b border-linea/60 py-2 last:border-0">
      {p.chip && (
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-[0.7rem] font-semibold ${tonoChip(p.tono)}`}>
          {p.chip}
        </span>
      )}
      <div className="min-w-0 flex-1">
        <p className="text-[0.86rem] leading-snug text-tinta">{p.titulo}</p>
        {p.resumen && <p className="text-[0.78rem] leading-snug text-tinta-suave">{p.resumen}</p>}
      </div>
      {(p.cifra_texto || p.monto != null) && (
        <span className="shrink-0 whitespace-nowrap text-[0.82rem] font-medium text-tinta">
          {p.cifra_texto || peso(p.monto || 0)}
        </span>
      )}
    </div>
  );
}

type PrioridadesResult = { act?: Prioridad[]; watch?: Prioridad[] };

export function Prioridades({ result }: ToolRenderProps) {
  const err = toolErrorMessage(result);
  if (err) return <ToolErrorText message={err} />;
  const r = result as PrioridadesResult;
  if (!r) return null;
  const act = r.act || [];
  const watch = r.watch || [];
  if (act.length === 0 && watch.length === 0) return null;
  return (
    <div className="mt-1.5 space-y-2">
      {act.length > 0 && (
        <div>
          <p className="mb-0.5 text-[0.68rem] font-semibold uppercase tracking-[0.1em] text-tinta-suave">
            {t("toolui.prioridades.act")}
          </p>
          {act.map((p, i) => (
            <Fila key={p.id ?? i} p={p} />
          ))}
        </div>
      )}
      {watch.length > 0 && (
        <div>
          <p className="mb-0.5 text-[0.68rem] font-semibold uppercase tracking-[0.1em] text-tinta-suave">
            {t("toolui.prioridades.watch")}
          </p>
          {watch.map((p, i) => (
            <Fila key={p.id ?? i} p={p} />
          ))}
        </div>
      )}
    </div>
  );
}

export const listarPrioridadesPresenter: ToolPresenter = {
  labels: toolLabels("listar_prioridades"),
  render: Prioridades,
};
