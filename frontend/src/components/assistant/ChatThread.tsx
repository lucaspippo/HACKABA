import {
  ThreadPrimitive,
  MessagePrimitive,
  useAui,
  useAuiState,
  ComposerPrimitive,
} from "@assistant-ui/react";
import { useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Send, AlertCircle } from "lucide-react";
import AngelaMark from "../AngelaMark";
import ToolCallCard from "./ToolCallCard";
import ErrorState from "./ErrorState";
import ThinkingIndicator from "./ThinkingIndicator";
import { toolComponentsByName } from "./tools/registry";
import PlanChecklist from "./PlanChecklist";
import DocCard from "./DocCard";
import MemoryChips from "./MemoryChips";
import { api } from "../../lib/api";
import { toast } from "../../lib/toastStore";
import { useT } from "../../lib/i18n";
import type { Notice } from "../../lib/chat/protocol";

type ExecutingHandler = (running: boolean) => void;

function UserMessage() {
  return (
    <MessagePrimitive.Root className="flex justify-end">
      <div className="max-w-[85%] whitespace-pre-line rounded-2xl rounded-tr-md bg-tinta px-3.5 py-2.5 text-[0.95rem] leading-snug text-crema">
        <MessagePrimitive.Parts />
      </div>
    </MessagePrimitive.Root>
  );
}

/**
 * proponer_conocimiento is shown as a MemoryChips pill by MessageExtras, so
 * the raw tool call renders as nothing here. This is a PRESENTATION choice
 * for one tool and therefore belongs in the by_name map, not in a branch.
 */
const SUPPRESSED = { proponer_conocimiento: () => null };

const TOOL_COMPONENTS = {
  Fallback: ToolCallCard,
  by_name: { ...SUPPRESSED, ...toolComponentsByName() },
};

type MemoryChip = { id: string; pid: string; text: string; change: string };

// `useAuiState` is a `useSyncExternalStore` selector: its return value MUST
// be referentially stable across calls with unchanged state, or React
// re-renders forever ("getSnapshot should be cached"). A literal `?? []`/`?? {}`
// fallback allocates a NEW array/object every call, which is just as much of
// a footgun as `.filter().map()` — reuse this constant instead of a literal.
const EMPTY_ARRAY: readonly never[] = [];

// A message's "extras" (plan checklist, document card, memory chips) are
// NOT content parts — they travel in metadata.custom.actions (the same
// shape /api/angela has always returned) or, for memory chips, get pulled
// out of the tool-call parts themselves. Read here, with the message
// already in scope via MessagePrimitive.Root.
function MessageExtras({ onExecutingChange }: { onExecutingChange?: ExecutingHandler }) {
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

/**
 * A degraded-mode explanation (message cap, no model, tool loop exhausted).
 * Visually distinct on purpose: the v1 bug was a reply produced WITHOUT the
 * model being indistinguishable from a real one (design doc D5/D9).
 */
function MessageNotices() {
  const t = useT();
  const notices = (useAuiState((s) => s.message.metadata?.custom?.notices) ?? []) as Notice[];
  if (notices.length === 0) return null;
  return (
    <div className="mt-2 space-y-1.5">
      {notices.map((n, i) => {
        // The wire carries only `kind`; the copy is ours. An unrecognised
        // kind falls back to a generic line rather than rendering blank.
        const key = `chat.notice.${n.kind}`;
        const text = t(key);
        return (
          <p
            key={i}
            className="flex items-start gap-2 rounded-xl border border-oro/40 bg-oro/5 px-2.5 py-1.5 text-[0.78rem] leading-snug text-oro-tinta"
          >
            <AlertCircle size={14} className="mt-0.5 shrink-0" />
            <span>{text === key ? t("chat.notice.generico") : text}</span>
          </p>
        );
      })}
    </div>
  );
}

function AssistantMessage({ onExecutingChange }: { onExecutingChange?: ExecutingHandler }) {
  const isRunning = useAuiState((s) => s.message.status?.type === "running");
  const startedAt = useRef(Date.now()).current;
  const noContentYet = useAuiState(
    (s) =>
      s.message.status?.type === "running" &&
      (s.message.content?.length ?? 0) === 0 &&
      ((s.message.metadata?.custom?.notices as Notice[] | undefined)?.length ?? 0) === 0,
  );
  return (
    <MessagePrimitive.Root className="flex gap-2.5">
      <AngelaMark size={28} estado={undefined} />
      <div className="max-w-[88%]">
        <div className="whitespace-pre-line rounded-2xl rounded-tl-md border border-linea bg-crema px-3.5 py-2.5 text-[0.95rem] leading-snug text-tinta sombra-papel">
          {isRunning && <ThinkingIndicator startedAt={startedAt} />}
          {!noContentYet && (
            <MessagePrimitive.Parts
              components={{
                Text: ({ text }: { text: string }) => <span>{text}</span>,
                tools: TOOL_COMPONENTS,
              }}
            />
          )}
          <MessageNotices />
          <MessageExtras onExecutingChange={onExecutingChange} />
        </div>
        <MessagePrimitive.Error>
          <ErrorState />
        </MessagePrimitive.Error>
      </div>
    </MessagePrimitive.Root>
  );
}

function Composer({ leading }: { leading?: ReactNode }) {
  const t = useT();
  const isRunning = useAuiState((s) => s.thread.isRunning);
  return (
    <ComposerPrimitive.Root className="flex items-center gap-2 rounded-full border border-linea bg-crema p-1.5 pl-2 sombra-papel">
      {leading}
      <ComposerPrimitive.Input
        placeholder={isRunning ? t("angela.ph_trabajando") : t("angela.ph_input")}
        rows={1}
        className="flex-1 resize-none bg-transparent text-[0.95rem] outline-none placeholder:text-tinta-suave/70 disabled:opacity-60"
      />
      <ComposerPrimitive.Send asChild>
        <button
          disabled={isRunning}
          aria-label={t("common.enviar")}
          className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-violeta text-crema transition-transform active:scale-90 disabled:opacity-40"
        >
          <Send size={18} />
        </button>
      </ComposerPrimitive.Send>
    </ComposerPrimitive.Root>
  );
}

// The Thread: assistant-ui handles streaming/state; the look mirrors the
// previous chat (bg-crema, sombra-papel, rounded bubbles) so switching engines
// doesn't show on the visible surface.
export default function ChatThread({
  onExecutingChange,
  composerLeading,
}: {
  onExecutingChange?: ExecutingHandler;
  composerLeading?: ReactNode;
}) {
  return (
    <ThreadPrimitive.Root className="flex h-full flex-col">
      <ThreadPrimitive.Viewport className="flex-1 space-y-3 overflow-y-auto pb-2">
        <ThreadPrimitive.Messages>
          {({ message }) =>
            message.role === "user" ? (
              <UserMessage />
            ) : (
              <AssistantMessage onExecutingChange={onExecutingChange} />
            )
          }
        </ThreadPrimitive.Messages>
      </ThreadPrimitive.Viewport>
      <Composer leading={composerLeading} />
    </ThreadPrimitive.Root>
  );
}
