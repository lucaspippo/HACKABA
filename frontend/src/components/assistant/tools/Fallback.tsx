import type { ToolCallMessagePartProps } from "@assistant-ui/react";
import ResultTable from "../ResultTable";
import MiniChart from "../MiniChart";
import { peso } from "../../../lib/format";
import { toolErrorMessage, ToolErrorText } from "./toolError";

/**
 * The DEFAULT tool renderer: dispatches on the SHAPE of the result, not on the
 * tool name, so a new Python tool still gets a table or a chart with zero
 * frontend work (design doc D1). Scalar dumps (`ok: true` plus a sentence)
 * do NOT get a key/value widget — those belong on the status line, which is
 * the wording the model already sent.
 */
export default function ToolFallback({ toolName, result }: ToolCallMessagePartProps) {
  if (result == null) return null;

  const err = toolErrorMessage(result);
  if (err) return <ToolErrorText message={err} />;

  if (typeof result !== "object" || Array.isArray(result)) {
    if (Array.isArray(result) && result.length && typeof result[0] === "object") {
      return <ResultTable rows={result} />;
    }
    return null;
  }

  const r = result as Record<string, unknown>;

  if (toolName === "navegar_a" && r.navegado_a) {
    return (
      <p className="mt-1 text-sm text-tinta-suave">
        → te llevé a <b className="text-tinta">{String(r.navegado_a)}</b>
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
          <p className="mt-1 text-sm text-tinta">
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

  return null;
}
