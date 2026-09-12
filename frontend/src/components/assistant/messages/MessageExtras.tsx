import { useAui, useAuiState } from "@assistant-ui/react";
import { useMemo, useState } from "react";
import PlanChecklist from "../PlanChecklist";
import DocCard from "../DocCard";
import { MemoryChips, type MemoryChange } from "../memory-chips";
import { api } from "../../../lib/api";
import { toast } from "../../../lib/toastStore";
import { useT } from "../../../lib/i18n";
import { proposalsFromContent } from "./proposals";

export type ExecutingHandler = (running: boolean) => void;

type ChipDecision = MemoryChange | "dismissed";

// useAuiState is a useSyncExternalStore selector: its return value MUST be
// referentially stable across calls with unchanged state, or React re-renders
// forever. A literal `?? []` allocates a new array every call, so reuse this.
const EMPTY_ARRAY: readonly never[] = [];

function keptState(state: unknown): MemoryChange {
  return state === "activo" || state === "active" ? "saved" : "pending";
}

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
  const proposals = useMemo(() => proposalsFromContent(content), [content]);
  const [decided, setDecided] = useState(() => new Map<string, ChipDecision>());
  const chips = proposals
    .filter((p) => decided.get(p.id) !== "dismissed")
    .map((p) => ({
      id: p.id,
      text: p.text,
      change: (decided.get(p.id) ?? (p.alreadySaved ? "existing" : "proposed")) as MemoryChange,
      narrativeAlternative:
        p.kind === "knowledge" && p.narrativeAlternative
          ? { id: `${p.id}:context`, text: p.text }
          : undefined,
    }));

  const onSave = async (id: string) => {
    const isNarrativeChoice = id.endsWith(":context");
    const found = proposals.find((p) => (isNarrativeChoice ? `${p.id}:context` === id : p.id === id));
    if (!found) return;
    try {
      if (found.kind === "rule") {
        const r = await api.rulesConfirm(found.rule);
        setDecided((prev) => new Map(prev).set(found.id, keptState(r.state)));
        return;
      }
      const proposal = isNarrativeChoice ? found.narrativeAlternative ?? found.knowledge : found.knowledge;
      const r = await api.knowledgeConfirm(proposal);
      setDecided((prev) => new Map(prev).set(found.id, keptState(r.state)));
    } catch {
      toast(t("chat.memory.save_error"), "error");
    }
  };
  const onDismiss = (id: string) => setDecided((prev) => new Map(prev).set(id, "dismissed"));
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
      {chips.length > 0 && (
        <MemoryChips
          className="mt-2"
          chips={chips}
          onSave={onSave}
          onDismiss={onDismiss}
          labels={{
            memory: t("chat.memory.header"),
            remembered: (n) => t("chat.memory.kept_n", { n: String(n) }),
            save: (text) => t("chat.memory.save", { text }),
            dismiss: (text) => t("chat.memory.dismiss", { text }),
            keep: t("chat.memory.keep"),
            discard: t("chat.memory.discard"),
            saved: t("chat.memory.saved"),
            pending: t("chat.memory.pending"),
            applyRuleLabel: t("chat.memory.apply_rule"),
            contextOnlyLabel: t("chat.memory.context_only"),
          }}
        />
      )}
      {options.length > 0 && (
        <div className="mt-2 flex flex-col gap-1.5">
          {options.map((op, k) => (
            <button
              key={k}
              onClick={() => aui.thread.append(op.enviar)}
              disabled={isRunning}
              className="rounded-xl border border-violeta/30 bg-crema px-3 py-2 text-left text-sm font-semibold text-violeta transition-colors hover:bg-violeta hover:text-crema disabled:opacity-50"
            >
              {op.label}
            </button>
          ))}
        </div>
      )}
    </>
  );
}
