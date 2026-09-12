import type { ToolCallMessagePartProps } from "@assistant-ui/react";
import type { ToolArgs } from "../../../lib/chat/toolArgs.generated";

/** i18n KEYS (never literal copy) for a tool's two states. */
export type ToolLabels = { running: string; done: string };

/**
 * "card" wraps the render in the standard tool card; "bare" lets a renderer
 * own its full width (charts and tables in Phase 3); "line" is a single
 * status row — the default for tools with no presenter.
 */
export type ToolChrome = "card" | "bare" | "line";

export type ToolRenderProps<TName extends keyof ToolArgs = keyof ToolArgs> =
  Omit<ToolCallMessagePartProps, "args"> & { args: ToolArgs[TName] };

/**
 * How ONE tool call is presented. A presenter is always an OVERRIDE: a tool
 * without one falls through to a status line plus the shape-based Fallback
 * (tables, charts, errors — not a scalar dump), so a new Python tool still
 * gets a usable UI with zero frontend work (design doc D1).
 *
 * Presenters must be PURE functions of (args, result). Side effects —
 * navigation, widget creation, preferences — belong in ChatPanel's action
 * applier, never here (D2.3).
 */
export type ToolPresenter<TName extends keyof ToolArgs = keyof ToolArgs> = {
  labels: ToolLabels;
  render?: (props: ToolRenderProps<TName>) => React.ReactNode;
  chrome?: ToolChrome;
};
