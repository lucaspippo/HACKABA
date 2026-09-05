import { Pin } from "lucide-react";
import type { ToolPresenter, ToolRenderProps } from "./types";
import { toolLabels } from "./labels";
import { toolErrorMessage, ToolErrorText } from "./toolError";
import MiniChart from "../MiniChart";
import { peso, num } from "../../../lib/format";
import { t } from "../../../lib/i18n";

/**
 * consultar_serie's visual is driven by `meta` (temporal/composicion/unidad/
 * deflactado — D10), never guessed from shape.
 *
 * Limitation: per D8 (not yet implemented), the chat only ever receives a
 * SUMMARY of a series — `primero`/`ultimo`/`max`/`total` for a temporal one,
 * up to 5 `top` points for a dimensional one (angela.py::_consultar_serie_tool).
 * Full-resolution points live only in the pinned widget, so a temporal series
 * renders as a trend (first → last) rather than a line chart until D8 splits
 * the wire payload into a model `result` and a full-resolution UI `display`.
 */

// Field/type names below mirror consultar_serie's JSON response
// (backend/core/consultas.py) verbatim — not identifiers of ours to translate.
type Point = { x: string; y: number };
type SeriesSummary = {
  nombre: string;
  puntos?: number;
  primero?: Point;
  ultimo?: Point;
  max?: number;
  total?: number;
  top?: Point[];
};
type Meta = {
  unidad?: string;
  ventana?: string;
  composicion?: boolean;
  deflactado?: boolean;
  base_ipc?: string;
  temporal?: boolean;
};
type SeriesResult = {
  ok?: boolean;
  motivo?: string;
  alternativa?: string;
  meta?: Meta;
  series?: SeriesSummary[];
  fijado?: boolean;
};

export function formatValue(value: number, unit?: string): string {
  if (unit === "$") return peso(value);
  if (unit === "%") return `${num(value)}%`;
  return num(value);
}

function chartFormat(unit?: string): "moneda" | "porcentaje" | "numero" {
  if (unit === "$") return "moneda";
  if (unit === "%") return "porcentaje";
  return "numero";
}

function SeriesTrend({ series, unit }: { series: SeriesSummary; unit?: string }) {
  if (!series.primero || !series.ultimo) return null;
  const delta = series.ultimo.y - series.primero.y;
  const tone = delta > 0 ? "text-salvia" : delta < 0 ? "text-rojo" : "text-tinta-suave";
  return (
    <div className="rounded-xl border border-linea bg-papel/50 px-3 py-2">
      <p className="text-xs font-semibold text-tinta">{series.nombre}</p>
      <p className="mt-1 flex items-baseline gap-1.5 text-base">
        <span className="tabular-nums text-tinta-suave">{formatValue(series.primero.y, unit)}</span>
        <span className="text-tinta-suave">→</span>
        <span className={`plata tabular-nums font-medium ${tone}`}>{formatValue(series.ultimo.y, unit)}</span>
      </p>
      <p className="mt-0.5 text-xs text-tinta-suave">
        {t("toolui.serie.max")} {formatValue(series.max || 0, unit)} · {t("toolui.serie.total")}{" "}
        {formatValue(series.total || 0, unit)}
      </p>
    </div>
  );
}

function SeriesBars({ series, unit }: { series: SeriesSummary; unit?: string }) {
  if (!Array.isArray(series.top) || series.top.length === 0) return null;
  return (
    <div>
      <p className="mb-1 text-xs font-semibold text-tinta">{series.nombre}</p>
      <MiniChart points={series.top} format={chartFormat(unit)} />
    </div>
  );
}

export function SeriesView({ result }: ToolRenderProps) {
  const data = result as SeriesResult;
  if (!data) return null;

  if (data.ok === false) {
    return (
      <div className="mt-1 text-sm text-rojo-hondo">
        <p>{data.motivo}</p>
        {data.alternativa && <p className="mt-0.5 text-tinta-suave">{data.alternativa}</p>}
      </div>
    );
  }

  // A feature-gate error (e.g. sin_acceso) carries no `ok` key at all.
  const err = toolErrorMessage(result);
  if (err) return <ToolErrorText message={err} />;

  const meta = data.meta || {};
  const series = data.series || [];
  if (series.length === 0) return null;
  const unitIsSymbol = meta.unidad === "$" || meta.unidad === "%";

  return (
    <div className="mt-1.5 space-y-2">
      {(meta.ventana || (meta.unidad && !unitIsSymbol) || (meta.deflactado && meta.base_ipc)) && (
        <p className="text-xs text-tinta-suave">
          {[
            meta.ventana,
            !unitIsSymbol ? meta.unidad : null,
            meta.deflactado && meta.base_ipc ? t("toolui.serie.deflactado", { base: meta.base_ipc }) : null,
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
      )}
      {meta.temporal ? (
        <div className="grid gap-2 sm:grid-cols-2">
          {series.map((item, i) => (
            <SeriesTrend key={i} series={item} unit={meta.unidad} />
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {series.map((item, i) => (
            <SeriesBars key={i} series={item} unit={meta.unidad} />
          ))}
        </div>
      )}
      {data.fijado && (
        <p className="flex items-center gap-1 text-xs text-salvia">
          <Pin size={11} /> {t("toolui.serie.fijado")}
        </p>
      )}
    </div>
  );
}

export const seriesPresenter: ToolPresenter = {
  labels: toolLabels("consultar_serie"),
  render: SeriesView,
};
