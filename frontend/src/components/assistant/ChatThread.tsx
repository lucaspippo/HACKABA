import { ThreadPrimitive, ComposerPrimitive, useAuiState } from "@assistant-ui/react";
import type { ReactNode } from "react";
import { Send } from "lucide-react";
import { useT } from "../../lib/i18n";
import UserMessage from "./messages/UserMessage";
import AssistantMessage from "./messages/AssistantMessage";
import type { ExecutingHandler } from "./messages/MessageExtras";

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

export default function ChatThread({
  onExecutingChange,
  composerLeading,
  emptyState,
}: {
  onExecutingChange?: ExecutingHandler;
  composerLeading?: ReactNode;
  emptyState?: ReactNode;
}) {
  const isEmpty = useAuiState((s) => s.thread.isEmpty);
  return (
    <ThreadPrimitive.Root className="flex h-full flex-col">
      <ThreadPrimitive.Viewport className="flex flex-1 flex-col overflow-y-auto pb-2">
        {isEmpty && emptyState ? (
          <div className="flex flex-1 flex-col items-center justify-center px-4 py-6 text-center">
            {emptyState}
          </div>
        ) : (
          <div className="space-y-3">
            <ThreadPrimitive.Messages>
              {({ message }) =>
                message.role === "user" ? (
                  <UserMessage />
                ) : (
                  <AssistantMessage onExecutingChange={onExecutingChange} />
                )
              }
            </ThreadPrimitive.Messages>
          </div>
        )}
      </ThreadPrimitive.Viewport>
      <Composer leading={composerLeading} />
    </ThreadPrimitive.Root>
  );
}
