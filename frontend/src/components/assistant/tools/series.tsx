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

type Punto = { x: string; y: number };
type SerieResumen = {
  nombre: string;
  puntos?: number;
  primero?: Punto;
  ultimo?: Punto;
  max?: number;
  total?: number;
  top?: Punto[];
};
type Meta = {
  unidad?: string;
  ventana?: string;
  composicion?: boolean;
  deflactado?: boolean;
  base_ipc?: string;
  temporal?: boolean;
};
type SerieResult = {
  ok?: boolean;
  motivo?: string;
  alternativa?: string;
  meta?: Meta;
  series?: SerieResumen[];
  fijado?: boolean;
};

export function fmtValor(v: number, unidad?: string): string {
  if (unidad === "$") return peso(v);
  if (unidad === "%") return `${num(v)}%`;
  return num(v);
}

function chartFormat(unidad?: string): "moneda" | "porcentaje" | "numero" {
  if (unidad === "$") return "moneda";
  if (unidad === "%") return "porcentaje";
  return "numero";
}

function TendenciaSerie({ s, unidad }: { s: SerieResumen; unidad?: string }) {
  if (!s.primero || !s.ultimo) return null;
  const delta = s.ultimo.y - s.primero.y;
  const tono = delta > 0 ? "text-salvia" : delta < 0 ? "text-rojo" : "text-tinta-suave";
  return (
    <div className="rounded-xl border border-linea bg-papel/50 px-3 py-2">
      <p className="text-[0.78rem] font-semibold text-tinta">{s.nombre}</p>
      <p className="mt-1 flex items-baseline gap-1.5 text-[0.95rem]">
        <span className="tabular-nums text-tinta-suave">{fmtValor(s.primero.y, unidad)}</span>
        <span className="text-tinta-suave">→</span>
        <span className={`plata tabular-nums font-medium ${tono}`}>{fmtValor(s.ultimo.y, unidad)}</span>
      </p>
      <p className="mt-0.5 text-[0.72rem] text-tinta-suave">
        {t("toolui.serie.max")} {fmtValor(s.max || 0, unidad)} · {t("toolui.serie.total")}{" "}
        {fmtValor(s.total || 0, unidad)}
      </p>
    </div>
  );
}

function BarritasSerie({ s, unidad }: { s: SerieResumen; unidad?: string }) {
  if (!Array.isArray(s.top) || s.top.length === 0) return null;
  return (
    <div>
      <p className="mb-1 text-[0.78rem] font-semibold text-tinta">{s.nombre}</p>
      <MiniChart points={s.top} format={chartFormat(unidad)} />
    </div>
  );
}

export function SerieTool({ result }: ToolRenderProps) {
  const r = result as SerieResult;
  if (!r) return null;

  if (r.ok === false) {
    return (
      <div className="mt-1 text-[0.82rem] text-rojo-hondo">
        <p>{r.motivo}</p>
        {r.alternativa && <p className="mt-0.5 text-tinta-suave">{r.alternativa}</p>}
      </div>
    );
  }

  // A feature-gate error (e.g. sin_acceso) carries no `ok` key at all.
  const err = toolErrorMessage(result);
  if (err) return <ToolErrorText message={err} />;

  const meta = r.meta || {};
  const series = r.series || [];
  if (series.length === 0) return null;
  const unidadEsSimbolo = meta.unidad === "$" || meta.unidad === "%";

  return (
    <div className="mt-1.5 space-y-2">
      {(meta.ventana || (meta.unidad && !unidadEsSimbolo) || (meta.deflactado && meta.base_ipc)) && (
        <p className="text-[0.72rem] text-tinta-suave">
          {[
            meta.ventana,
            !unidadEsSimbolo ? meta.unidad : null,
            meta.deflactado && meta.base_ipc ? t("toolui.serie.deflactado", { base: meta.base_ipc }) : null,
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
      )}
      {meta.temporal ? (
        <div className="grid gap-2 sm:grid-cols-2">
          {series.map((s, i) => (
            <TendenciaSerie key={i} s={s} unidad={meta.unidad} />
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {series.map((s, i) => (
            <BarritasSerie key={i} s={s} unidad={meta.unidad} />
          ))}
        </div>
      )}
      {r.fijado && (
        <p className="flex items-center gap-1 text-[0.76rem] text-salvia">
          <Pin size={11} /> {t("toolui.serie.fijado")}
        </p>
      )}
    </div>
  );
}

export const consultarSeriePresenter: ToolPresenter = {
  labels: toolLabels("consultar_serie"),
  render: SerieTool,
};
