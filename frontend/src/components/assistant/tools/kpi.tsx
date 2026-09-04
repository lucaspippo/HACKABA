import type { ToolPresenter, ToolRenderProps } from "./types";
import { toolLabels } from "./labels";
import { toolErrorMessage, ToolErrorText } from "./toolError";
import { peso, num } from "../../../lib/format";
import { t } from "../../../lib/i18n";

/**
 * estado_caja / resumen_negocio previously rendered empty in chat: their
 * numbers live under `totales`/`resumen`/`alertas`, and Fallback's
 * GenericResult only reads top-level scalar keys.
 */

export function Tile({
  label,
  value,
  tono = "text-tinta",
}: {
  label: string;
  value: string;
  tono?: string;
}) {
  return (
    <div className="rounded-xl border border-linea bg-papel/50 px-3 py-2">
      <p className={`plata text-[1.05rem] font-medium leading-none ${tono}`}>{value}</p>
      <p className="mt-1 text-[0.72rem] leading-snug text-tinta-suave">{label}</p>
    </div>
  );
}

type CajaResult = {
  abierta?: boolean;
  saldo_inicial?: number;
  totales?: { ingresos?: number; egresos?: number; total?: number; por_medio?: Record<string, number> };
};

export function CajaTile({ result }: ToolRenderProps) {
  const err = toolErrorMessage(result);
  if (err) return <ToolErrorText message={err} />;
  const r = result as CajaResult;
  if (!r) return null;
  const tot = r.totales || {};
  const porMedio = Object.entries(tot.por_medio || {}).filter(([, v]) => v);
  return (
    <div className="mt-1.5">
      <span
        className={`mb-1.5 inline-flex items-center rounded-full px-2 py-0.5 text-[0.72rem] font-semibold ${
          r.abierta ? "bg-salvia/12 text-salvia" : "bg-papel-hondo text-tinta-suave"
        }`}
      >
        {r.abierta ? t("toolui.caja.abierta") : t("toolui.caja.cerrada")}
      </span>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Tile label={t("toolui.caja.total")} value={peso(tot.total || 0)} />
        <Tile label={t("toolui.caja.ingresos")} value={peso(tot.ingresos || 0)} tono="text-salvia" />
        <Tile label={t("toolui.caja.egresos")} value={peso(tot.egresos || 0)} tono="text-rojo" />
        <Tile label={t("toolui.caja.saldo_inicial")} value={peso(r.saldo_inicial || 0)} />
      </div>
      {porMedio.length > 0 && (
        <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[0.78rem]">
          {porMedio.map(([medio, v]) => (
            <div key={medio} className="flex items-center gap-1.5">
              <dt className="capitalize text-tinta-suave">{medio.replaceAll("_", " ")}</dt>
              <dd className="tabular-nums text-tinta">{peso(v)}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

type NegocioResult = {
  resumen?: {
    inmovilizado_total?: number;
    activos?: number;
    stock_cero?: number;
    stock_negativo?: number;
    salud?: { nivel?: string; label?: string };
  };
  alertas?: Record<string, { cantidad?: number; impacto_pesos?: number } | undefined>;
};

/** Only en_orden/atencion are known levels; anything else reads as a problem. */
export function saludTono(nivel?: string): string {
  if (nivel === "en_orden") return "bg-salvia/12 text-salvia";
  if (nivel === "atencion") return "bg-oro/15 text-oro-tinta";
  return "bg-rojo/10 text-rojo";
}

const ALERTA_LABEL_KEY: Record<string, string> = {
  fantasmas: "toolui.negocio.alertas_fantasmas",
  negativos: "toolui.negocio.alertas_negativos",
  sin_pvp: "toolui.negocio.alertas_sin_pvp",
  balanza: "toolui.negocio.alertas_balanza",
  costo_viejo: "toolui.negocio.alertas_costo_viejo",
};

export function NegocioResumen({ result }: ToolRenderProps) {
  const err = toolErrorMessage(result);
  if (err) return <ToolErrorText message={err} />;
  const r = result as NegocioResult;
  const res = r?.resumen;
  if (!res) return null;
  const alertas = Object.entries(r.alertas || {}).filter(([, v]) => (v?.cantidad || 0) > 0);
  return (
    <div className="mt-1.5">
      {res.salud?.label && (
        <span
          className={`mb-1.5 inline-flex items-center rounded-full px-2 py-0.5 text-[0.72rem] font-semibold ${saludTono(res.salud.nivel)}`}
        >
          {res.salud.label}
        </span>
      )}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Tile label={t("toolui.negocio.inmovilizado")} value={peso(res.inmovilizado_total || 0)} tono="text-hielo" />
        <Tile label={t("toolui.negocio.articulos")} value={num(res.activos || 0)} />
        <Tile label={t("toolui.negocio.stock_cero")} value={num(res.stock_cero || 0)} />
        <Tile
          label={t("toolui.negocio.stock_negativo")}
          value={num(res.stock_negativo || 0)}
          tono={res.stock_negativo ? "text-rojo" : undefined}
        />
      </div>
      {alertas.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {alertas.map(([k, v]) => (
            <span
              key={k}
              className="inline-flex items-center gap-1 rounded-full border border-linea px-2 py-1 text-[0.74rem] text-tinta-suave"
            >
              {t(ALERTA_LABEL_KEY[k] || k)} <b className="text-tinta">{num(v?.cantidad || 0)}</b>
              {v?.impacto_pesos ? <span> · {peso(v.impacto_pesos)}</span> : null}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export const estadoCajaPresenter: ToolPresenter = { labels: toolLabels("estado_caja"), render: CajaTile };
export const resumenNegocioPresenter: ToolPresenter = { labels: toolLabels("resumen_negocio"), render: NegocioResumen };
