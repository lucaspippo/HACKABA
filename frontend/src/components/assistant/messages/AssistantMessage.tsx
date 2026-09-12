import { MessagePrimitive, useAuiState } from "@assistant-ui/react";
import { useRef } from "react";
import AngelaMark from "../../AngelaMark";
import ErrorState from "../ErrorState";
import ThinkingIndicator from "../ThinkingIndicator";
import MarkdownText from "../MarkdownText";
import ReplyAnnouncer from "../ReplyAnnouncer";
import { hasVisibleBody } from "../messageBody";
import { useT } from "../../../lib/i18n";
import type { Notice } from "../../../lib/chat/protocol";
import MessageNotices from "./MessageNotices";
import MessageExtras from "./MessageExtras";
import type { ExecutingHandler } from "./MessageExtras";
import { TOOL_COMPONENTS } from "./toolComponents";
import ReadAloudControl from "./read-aloud";

export default function AssistantMessage({ onExecutingChange }: { onExecutingChange?: ExecutingHandler }) {
  const t = useT();
  const isRunning = useAuiState((s) => s.message.status?.type === "running");
  const startedAt = useRef(Date.now()).current;
  const partCount = useAuiState((s) => s.message.content?.length ?? 0);
  const noticeCount = useAuiState(
    (s) => (s.message.metadata?.custom?.notices as Notice[] | undefined)?.length ?? 0,
  );
  const spokenText = useAuiState((s) =>
    (s.message.content ?? [])
      .filter((p): p is { type: "text"; text: string } => p.type === "text")
      .map((p) => p.text)
      .join(" ")
      .trim(),
  );
  const noContentYet = isRunning && partCount === 0 && noticeCount === 0;
  return (
    <MessagePrimitive.Root className="flex gap-2.5">
      <AngelaMark size={28} estado={undefined} />
      <div className="max-w-[88%]">
        {hasVisibleBody({ partCount, noticeCount, isRunning }) && (
          <div
            aria-busy={isRunning}
            className="rounded-2xl rounded-tl-md border border-linea bg-crema px-3.5 py-2.5 text-base leading-snug text-tinta sombra-papel"
          >
            {isRunning && <ThinkingIndicator startedAt={startedAt} />}
            {!noContentYet && (
              <MessagePrimitive.Parts
                components={{
                  Text: MarkdownText,
                  tools: TOOL_COMPONENTS,
                }}
              />
            )}
            <MessageNotices />
            <MessageExtras onExecutingChange={onExecutingChange} />
          </div>
        )}
        {!isRunning && spokenText && (
          <ReadAloudControl text={spokenText} />
        )}
        <ReplyAnnouncer text={spokenText} isRunning={isRunning} label={t("chat.reply_ready")} />
        <MessagePrimitive.Error>
          <ErrorState />
        </MessagePrimitive.Error>
      </div>
    </MessagePrimitive.Root>
  );
}
