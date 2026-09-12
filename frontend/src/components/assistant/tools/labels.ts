import { t } from "../../../lib/i18n";
import type { ToolLabels } from "./types";

/** "top_inmovilizado" -> "top inmovilizado". The last-resort label. */
export function humanizeToolName(name: string): string {
  return name.replaceAll("_", " ");
}

/** The i18n keys for a tool, derived from its name. */
export function toolLabelKeys(name: string): ToolLabels {
  return { running: `tool.${name}.running`, done: `tool.${name}.done` };
}

/**
 * Resolved, display-ready labels. `t()` falls back to ES and then to the key
 * itself, so an unregistered tool would show "tool.foo.running" — we detect
 * that and humanize the name instead. No tool ever renders a raw key.
 */
export function toolLabels(name: string): ToolLabels {
  const keys = toolLabelKeys(name);
  const running = t(keys.running);
  const done = t(keys.done);
  const readable = humanizeToolName(name);
  return {
    running: running === keys.running ? `${readable}…` : running,
    done: done === keys.done ? readable : done,
  };
}
