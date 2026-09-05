import { useAui, useAuiState } from "@assistant-ui/react";
import { useMemo, useState } from "react";
import PlanChecklist from "../PlanChecklist";
import DocCard from "../DocCard";
import MemoryChips from "../MemoryChips";
import { api } from "../../../lib/api";
import { toast } from "../../../lib/toastStore";
import { useT } from "../../../lib/i18n";

export type ExecutingHandler = (running: boolean) => void;

type MemoryChip = { id: string; pid: string; text: string; change: string };

// useAuiState is a useSyncExternalStore selector: its return value MUST be
// referentially stable across calls with unchanged state, or React re-renders
// forever. A literal `?? []` allocates a new array every call, so reuse this.
const EMPTY_ARRAY: readonly never[] = [];

// A message's "extras" (plan checklist, document card, memory chips) are
// NOT content parts — they travel in metadata.custom.actions (the same
// shape /api/angela has always returned) or, for memory chips, get pulled
// out of the tool-call parts themselves. Read here, with the message
// already in scope via MessagePrimitive.Root.
export default function MessageExtras({ onExecutingChange }: { onExecutingChange?: ExecutingHandler }) {
  const t = useT();
  const aui = useAui();
  const actions = (useAuiState((s) => s.message.metadata?.custom?.actions) ??
    []) as Array<{ type: string } & Record<string, unknown>>;
  const options = (useAuiState((s) => s.message.metadata?.custom?.options) ?? []) as Array<{
    label: string;
    enviar: string;
  }>;
  const isRunning = useAuiState((s) => s.thread.isRunning);
  // `s.message.content` is a reference the store already owns and only
  // changes identity when the content actually changes — safe to hand
  // straight to useAuiState. The `.filter().map()` that used to live INSIDE
  // that selector allocated a new array (and new objects) on every call,
  // which broke useSyncExternalStore's referential-stability requirement
  // and caused an infinite render loop; it's derived with useMemo instead.
  const content = useAuiState((s) => s.message.content) ?? EMPTY_ARRAY;
  const propuestas = useMemo(
    () =>
      (
        content as unknown as Array<{
          type: string;
          toolName?: string;
          toolCallId?: string;
          result?: { ok?: boolean; pieza?: { id: string; texto: string } };
        }>
      )
        .filter((p) => p.type === "tool-call" && p.toolName === "proponer_conocimiento" && p.result?.ok)
        .map((p) => ({
          id: p.toolCallId!,
          pid: p.result!.pieza!.id,
          text: p.result!.pieza!.texto,
          change: "added",
        })),
    [content],
  );
  const [olvidadas, setOlvidadas] = useState(() => new Set<string>());
  const chips = propuestas.filter((c) => !olvidadas.has(c.id));
  const onForget = async (chip: { id: string; pid: string }) => {
    setOlvidadas((prev) => new Set(prev).add(chip.id)); // optimista: no esperamos al server para ocultarla
    try {
      await api.conocimientoRechazar(chip.pid);
    } catch (e) {
      setOlvidadas((prev) => {
        const next = new Set(prev);
        next.delete(chip.id);
        return next;
      });
      toast(t("memoria_chips.error"), "error");
    }
  };
  const plan = actions.find((a) => a.type === "plan_progreso");
  const docAction = actions.find((a) => a.type === "documento");
  return (
    <>
      {plan && (
        <PlanChecklist
          plan={{ pasos: plan.pasos as unknown[] | undefined, resumen: plan.resumen as string | undefined }}
          onExecutingChange={onExecutingChange}
        />
      )}
      {docAction?.documento != null && <DocCard documento={docAction.documento} t={t} />}
      {chips.length > 0 && <MemoryChips chips={chips as MemoryChip[]} onForget={onForget} />}
      {options.length > 0 && (
        <div className="mt-2 flex flex-col gap-1.5">
          {options.map((op, k) => (
            <button
              key={k}
              onClick={() => aui.thread.append(op.enviar)}
              disabled={isRunning}
              className="rounded-xl border border-violeta/30 bg-crema px-3 py-2 text-left text-[0.86rem] font-semibold text-violeta transition-colors hover:bg-violeta hover:text-crema disabled:opacity-50"
            >
              {op.label}
            </button>
          ))}
        </div>
      )}
    </>
  );
}
