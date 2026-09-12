import { ThreadPrimitive, useAui, useAuiState } from "@assistant-ui/react";
import type { ReactNode } from "react";
import { useState } from "react";
import Composer from "./composer/composer";
import UserMessage from "./messages/UserMessage";
import AssistantMessage from "./messages/AssistantMessage";
import type { ExecutingHandler } from "./messages/MessageExtras";
import { VoiceCallScreen } from "../voice/VoiceCallScreen";
import type { VoiceTranscriptItem } from "../voice/VoiceConversation";
import {
  createWebSpeechVoiceAdapter,
  isWebSpeechVoiceSupported,
} from "../../lib/voice/webSpeechVoiceAdapter";
import type { RealtimeVoiceAdapter } from "@assistant-ui/react";

type Call = { adapter: RealtimeVoiceAdapter; transcript: VoiceTranscriptItem[] };

export default function ChatThread({
  onExecutingChange,
  composerLeading,
  emptyState,
  onAttach,
}: {
  onExecutingChange?: ExecutingHandler;
  composerLeading?: ReactNode;
  emptyState?: ReactNode;
  /** Opens the app's document-upload flow; omit to hide the call's attach button. */
  onAttach?: () => void;
}) {
  const aui = useAui();
  const isEmpty = useAuiState((s) => s.thread.isEmpty);
  // Its own bounded RealtimeVoiceAdapter session while live (see VoiceCallScreen);
  // on end, its transcript is replayed into this thread as real messages (below)
  // so the call reads back as an ordinary, persisted part of the conversation.
  const [call, setCall] = useState<Call | null>(null);

  const startCall = () => {
    if (!isWebSpeechVoiceSupported()) return;
    const adapter = createWebSpeechVoiceAdapter({
      channel: "voz",
      onTranscript: (item) =>
        setCall((prev) =>
          prev && {
            ...prev,
            transcript: [...prev.transcript, { id: `${prev.transcript.length}`, ...item }],
          },
        ),
    });
    setCall({ adapter, transcript: [] });
  };
  // Replays the call's own transcript verbatim — never re-asks Ángela — so
  // what lands in the thread is exactly what was said out loud, not a
  // second, possibly different, answer. Each append needs an explicit
  // parentId: without one, the repository links it off the root instead of
  // the previous message, so only the last append in the batch would ever
  // end up reachable from the thread head.
  //
  // A message completing triggers the runtime's own thread-title generation
  // (see assistant-ui's subscribeToTitleGeneration), which writes back to
  // the thread-list store — appending again before that settles can lose
  // the race entirely (assistant-ui throws "resetHead: Branch not found",
  // the just-added message gone before its own append call returns).
  // Confirming the message actually landed, and retrying otherwise, makes
  // replay resilient to that instead of silently dropping turns.
  const appendVerbatim = async (item: VoiceTranscriptItem, parentId: string | null) => {
    for (let attempt = 0; attempt < 8; attempt++) {
      try {
        await aui.thread.append({
          role: item.role,
          content: [{ type: "text", text: item.text }],
          parentId,
          ...(item.role === "user" ? { startRun: false } : {}),
        });
      } catch {
        // Fall through to the landed-check below: a rejected append can
        // still have partially applied before the race hit it.
      }
      const last = aui.thread.getState().messages.at(-1);
      const landed = last && last.content[0]?.type === "text" && last.content[0].text === item.text;
      if (landed) return last!.id;
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
    return null;
  };
  const replayCallTranscript = async (items: VoiceTranscriptItem[]) => {
    let parentId = aui.thread.getState().messages.at(-1)?.id ?? null;
    for (const item of items) {
      const newId = await appendVerbatim(item, parentId);
      if (newId) parentId = newId;
      // Give the title-generation write a moment to settle before the next
      // append, rather than racing it every single turn.
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
  };
  const endCall = () => {
    setCall((prev) => {
      const items = prev?.transcript ?? [];
      if (items.length > 0) void replayCallTranscript(items);
      return null;
    });
  };
  const attachFromCall = onAttach
    ? () => {
        endCall();
        onAttach();
      }
    : undefined;

  return (
    <ThreadPrimitive.Root className="flex h-full flex-col">
      {call ? (
        <div className="flex flex-1 flex-col overflow-hidden">
          <VoiceCallScreen
            voice={call.adapter}
            transcript={call.transcript}
            onEnd={endCall}
            onError={endCall}
            onAttach={attachFromCall}
          />
        </div>
      ) : (
        <>
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
          <Composer leading={composerLeading} onStartCall={startCall} />
        </>
      )}
    </ThreadPrimitive.Root>
  );
}
