/**
 * THE one place a tool's custom presentation is registered.
 *
 * To give a tool a custom look: add a module in this directory exporting a
 * ToolPresenter, then add one line here. Do NOT add a branch to ChatThread
 * (design doc D1) — it must stay free of per-tool logic.
 *
 * A tool with no entry here is CORRECT and complete: it renders through the
 * shape-based Fallback until a presenter overrides it.
 */
import type { ToolCallMessagePartComponent } from "@assistant-ui/react";
import type { ToolName } from "../../../lib/chat/toolArgs.generated";
import type { ToolPresenter } from "./types";
import { cashDrawerPresenter, businessSummaryPresenter } from "./kpi";
import { accountsReceivablePresenter, itemGroupPresenter, topTiedUpCapitalPresenter } from "./tables";
import { prioritiesPresenter } from "./priorities";
import { seriesPresenter } from "./series";

/**
 * Typed as Partial<Record<ToolName, ...>> on purpose: a key that is not a real
 * tool name in angela.py fails `npm run typecheck`. Without that, a typo would
 * simply mean by_name never fires and the tool silently renders through the
 * Fallback — a bug nobody notices.
 */
export const TOOL_PRESENTERS: Partial<Record<ToolName, ToolPresenter>> = {
  consultar_serie: seriesPresenter,
  cuentas_corrientes: accountsReceivablePresenter,
  listar_grupo: itemGroupPresenter,
  top_inmovilizado: topTiedUpCapitalPresenter,
  listar_prioridades: prioritiesPresenter,
  estado_caja: cashDrawerPresenter,
  resumen_negocio: businessSummaryPresenter,
};

export function presenterFor(name: string): ToolPresenter | undefined {
  return TOOL_PRESENTERS[name as ToolName];
}

/**
 * The registry as MessagePrimitive.Parts's `tools.by_name` map. Derived, so
 * adding a presenter never means touching the Thread.
 */
export function toolComponentsByName(): Record<string, ToolCallMessagePartComponent> {
  const out: Record<string, ToolCallMessagePartComponent> = {};
  for (const [name, presenter] of Object.entries(TOOL_PRESENTERS)) {
    if (presenter.render) {
      out[name] = presenter.render as unknown as ToolCallMessagePartComponent;
    }
  }
  return out;
}
