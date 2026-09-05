import { ThreadPrimitive, useAuiState } from "@assistant-ui/react";
import type { ReactNode } from "react";
import Composer from "./composer/composer";
import UserMessage from "./messages/UserMessage";
import AssistantMessage from "./messages/AssistantMessage";
import type { ExecutingHandler } from "./messages/MessageExtras";

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
