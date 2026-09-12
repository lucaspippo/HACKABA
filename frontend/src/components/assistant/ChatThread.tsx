import { ThreadPrimitive, useAuiState } from "@assistant-ui/react";
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
  const isEmpty = useAuiState((s) => s.thread.isEmpty);
  // Its own bounded session (see VoiceCallScreen) — never appended into `messages`.
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
  const endCall = () => setCall(null);
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
