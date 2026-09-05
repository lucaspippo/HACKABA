import { useAuiState } from "@assistant-ui/react";
import { useT } from "../../lib/i18n";
import { toolLabels } from "./tools/labels";
import { useElapsedSince, elapsedLabel } from "../../lib/chat/useElapsedSince";

/**
 * What the user reads while a run is in flight. Names the tool that is
 * actually running ("Revisando cuentas corrientes…") instead of three
 * anonymous dots, so a slow answer is legible rather than just slow.
 */
export default function ThinkingIndicator({ startedAt }: { startedAt: number }) {
  const t = useT();

  // The label follows the running tool, if there is one.
  const runningTool = useAuiState((s) => {
    const parts = s.message.content ?? [];
    for (let i = parts.length - 1; i >= 0; i -= 1) {
      const p = parts[i] as { type: string; toolName?: string; result?: unknown };
      if (p.type === "tool-call" && p.result === undefined) return p.toolName ?? null;
    }
    return null;
  });

  const label = runningTool ? toolLabels(runningTool).running : t("chat.pensando");
  const elapsed = elapsedLabel(useElapsedSince(startedAt));

  return (
    <div
      className="flex items-center gap-2.5 py-1 text-sm text-tinta-suave"
      aria-live="polite"
    >
      <span
        aria-hidden
        className="size-1.5 shrink-0 animate-pulse rounded-full bg-violeta motion-reduce:animate-none"
      />
      <span>{label}</span>
      {elapsed && <span className="tabular-nums text-xs opacity-70">{elapsed}</span>}
    </div>
  );
}
