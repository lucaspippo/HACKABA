import type { ToolCallMessagePartProps } from "@assistant-ui/react";
import ResultTable from "../ResultTable";
import MiniChart from "../MiniChart";
import { peso, num } from "../../../lib/format";

const MONEY_KEY = /monto|inmovilizado|precio|costo|saldo|total|plata|deuda/i;

/** A "small" object (a few scalar keys) as a compact key/value grid. */
function GenericResult({ result }: { result: Record<string, unknown> }) {
  const entries = Object.entries(result).filter(
    ([, v]) =>
      v == null || typeof v === "string" || typeof v === "number" || typeof v === "boolean",
  );
  if (entries.length === 0) return null;
  return (
    <dl className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1 text-[0.8rem]">
      {entries.slice(0, 8).map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="capitalize text-tinta-suave">{k.replaceAll("_", " ")}</dt>
          <dd className="tabular-nums text-tinta">
            {typeof v === "number"
              ? MONEY_KEY.test(k)
                ? peso(v)
                : num(v)
              : String(v ?? "—")}
          </dd>
        </div>
      ))}
    </dl>
  );
}

/**
 * The DEFAULT tool renderer: dispatches on the SHAPE of the result, not on the
 * tool name, so any of angela.py's 50 tools gets a reasonable UI without a
 * presenter. A presenter in the registry is an override of this, never a
 * prerequisite for a tool to render (design doc D1) — do not "simplify" this
 * away by requiring one per tool.
 */
export default function ToolFallback({ toolName, result }: ToolCallMessagePartProps) {
  if (result == null) return null;

  if (typeof result !== "object" || Array.isArray(result)) {
    if (Array.isArray(result) && result.length && typeof result[0] === "object") {
      return <ResultTable rows={result} />;
    }
    return <p className="mt-1 text-[0.82rem] text-tinta">{String(result)}</p>;
  }

  const r = result as Record<string, unknown>;

  if (toolName === "navegar_a" && r.navegado_a) {
    return (
      <p className="mt-1 text-[0.82rem] text-tinta-suave">
        → te llevé a <b className="text-tinta">{String(r.navegado_a)}</b>
      </p>
    );
  }

  if (r.error || r.motivo) {
    return (
      <p className="mt-1 text-[0.82rem] text-rojo-hondo">
        {String(r.error || r.motivo)}
      </p>
    );
  }

  const items = Array.isArray(r.items)
    ? r.items
    : Array.isArray(r.recordatorios)
      ? r.recordatorios
      : null;
  if (items && items.length && typeof items[0] === "object") {
    return (
      <>
        {r.total_inmovilizado_listado != null && (
          <p className="mt-1 text-[0.82rem] text-tinta">
            Total: <b>{peso(r.total_inmovilizado_listado as number)}</b>
          </p>
        )}
        <ResultTable rows={items} />
      </>
    );
  }

  if (Array.isArray(r.series)) {
    const withTop = (r.series as Array<{ top?: unknown[] }>).find(
      (s) => Array.isArray(s.top) && s.top.length,
    );
    if (withTop) return <MiniChart points={withTop.top} />;
  }

  return <GenericResult result={r} />;
}
