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
  tone = "text-tinta",
}: {
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div className="rounded-xl border border-linea bg-papel/50 px-3 py-2">
      <p className={`plata text-[1.05rem] font-medium leading-none ${tone}`}>{value}</p>
      <p className="mt-1 text-[0.72rem] leading-snug text-tinta-suave">{label}</p>
    </div>
  );
}

// Field names below mirror estado_caja's JSON response (backend/core/caja.py)
// verbatim — not identifiers of ours to translate.
type CashDrawerResult = {
  abierta?: boolean;
  saldo_inicial?: number;
  totales?: { ingresos?: number; egresos?: number; total?: number; por_medio?: Record<string, number> };
};

export function CashDrawerTile({ result }: ToolRenderProps) {
  const err = toolErrorMessage(result);
  if (err) return <ToolErrorText message={err} />;
  const data = result as CashDrawerResult;
  if (!data) return null;
  const totals = data.totales || {};
  const byMethod = Object.entries(totals.por_medio || {}).filter(([, amount]) => amount);
  return (
    <div className="mt-1.5">
      <span
        className={`mb-1.5 inline-flex items-center rounded-full px-2 py-0.5 text-[0.72rem] font-semibold ${
          data.abierta ? "bg-salvia/12 text-salvia" : "bg-papel-hondo text-tinta-suave"
        }`}
      >
        {data.abierta ? t("toolui.caja.abierta") : t("toolui.caja.cerrada")}
      </span>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Tile label={t("toolui.caja.total")} value={peso(totals.total || 0)} />
        <Tile label={t("toolui.caja.ingresos")} value={peso(totals.ingresos || 0)} tone="text-salvia" />
        <Tile label={t("toolui.caja.egresos")} value={peso(totals.egresos || 0)} tone="text-rojo" />
        <Tile label={t("toolui.caja.saldo_inicial")} value={peso(data.saldo_inicial || 0)} />
      </div>
      {byMethod.length > 0 && (
        <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[0.78rem]">
          {byMethod.map(([method, amount]) => (
            <div key={method} className="flex items-center gap-1.5">
              <dt className="capitalize text-tinta-suave">{method.replaceAll("_", " ")}</dt>
              <dd className="tabular-nums text-tinta">{peso(amount)}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

// Field names below mirror resumen_negocio's JSON response
// (backend/core/store.py::_compute_panorama) verbatim.
type BusinessSummaryResult = {
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
export function healthTone(level?: string): string {
  if (level === "en_orden") return "bg-salvia/12 text-salvia";
  if (level === "atencion") return "bg-oro/15 text-oro-tinta";
  return "bg-rojo/10 text-rojo";
}

// Keys match `alertas`' own JSON keys (backend/core/store.py) — not ours to rename.
const ALERT_LABEL_KEYS: Record<string, string> = {
  fantasmas: "toolui.negocio.alertas_fantasmas",
  negativos: "toolui.negocio.alertas_negativos",
  sin_pvp: "toolui.negocio.alertas_sin_pvp",
  balanza: "toolui.negocio.alertas_balanza",
  costo_viejo: "toolui.negocio.alertas_costo_viejo",
};

export function BusinessSummary({ result }: ToolRenderProps) {
  const err = toolErrorMessage(result);
  if (err) return <ToolErrorText message={err} />;
  const data = result as BusinessSummaryResult;
  const summary = data?.resumen;
  if (!summary) return null;
  const alerts = Object.entries(data.alertas || {}).filter(([, alert]) => (alert?.cantidad || 0) > 0);
  return (
    <div className="mt-1.5">
      {summary.salud?.label && (
        <span
          className={`mb-1.5 inline-flex items-center rounded-full px-2 py-0.5 text-[0.72rem] font-semibold ${healthTone(summary.salud.nivel)}`}
        >
          {summary.salud.label}
        </span>
      )}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Tile
          label={t("toolui.negocio.inmovilizado")}
          value={peso(summary.inmovilizado_total || 0)}
          tone="text-hielo"
        />
        <Tile label={t("toolui.negocio.articulos")} value={num(summary.activos || 0)} />
        <Tile label={t("toolui.negocio.stock_cero")} value={num(summary.stock_cero || 0)} />
        <Tile
          label={t("toolui.negocio.stock_negativo")}
          value={num(summary.stock_negativo || 0)}
          tone={summary.stock_negativo ? "text-rojo" : undefined}
        />
      </div>
      {alerts.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {alerts.map(([key, alert]) => (
            <span
              key={key}
              className="inline-flex items-center gap-1 rounded-full border border-linea px-2 py-1 text-[0.74rem] text-tinta-suave"
            >
              {t(ALERT_LABEL_KEYS[key] || key)} <b className="text-tinta">{num(alert?.cantidad || 0)}</b>
              {alert?.impacto_pesos ? <span> · {peso(alert.impacto_pesos)}</span> : null}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export const cashDrawerPresenter: ToolPresenter = { labels: toolLabels("estado_caja"), render: CashDrawerTile };
export const businessSummaryPresenter: ToolPresenter = {
  labels: toolLabels("resumen_negocio"),
  render: BusinessSummary,
};
