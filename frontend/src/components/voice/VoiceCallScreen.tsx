// Wires a RealtimeVoiceAdapter into its own local runtime and renders it as
// a VoiceConversation. Separate from the app's shared Ángela chat runtime
// (ChatRuntimeProvider) on purpose — a voice call here is its own bounded
// session, not another way into the same persisted thread — so each
// caller (VozAngela's conversational mode, VozVivaRecepcion) mounts one
// of these fresh rather than sharing state.
import { useEffect, useRef, useState } from "react";
import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  useVoiceState,
  useVoiceVolume,
  useVoiceControls,
  type RealtimeVoiceAdapter,
} from "@assistant-ui/react";
import { createChatModelAdapter } from "../../lib/chat/adapter";
import { VoiceConversation, type VoiceMode, type VoiceTranscriptItem } from "./VoiceConversation";

function toMode(
  voice: ReturnType<typeof useVoiceState>,
  thinking: boolean,
): VoiceMode {
  if (!voice || voice.status.type === "starting") return "connecting";
  if (voice.mode === "speaking") return "speaking";
  return thinking ? "thinking" : "listening";
}

type VoiceCallScreenProps = {
  voice: RealtimeVoiceAdapter;
  transcript: VoiceTranscriptItem[];
  onEnd?: () => void;
  onInterrupt?: () => void;
  /** The adapter ended the session on its own (network drop, mic denied,
   * askAngela failing) — distinct from the person tapping "end call". */
  onError?: () => void;
};

function VoiceCallInner({ transcript, onEnd, onInterrupt, onError }: Omit<VoiceCallScreenProps, "voice">) {
  const voice = useVoiceState();
  const amplitude = useVoiceVolume();
  const { connect, disconnect, mute, unmute } = useVoiceControls();
  const connected = useRef(false);

  useEffect(() => {
    if (connected.current) return;
    connected.current = true;
    connect();
  }, [connect]);

  // The adapter can end the session itself (see webSpeechVoiceAdapter.ts's
  // helpers.end calls) — that's not the person tapping "end call", so it
  // needs its own path back to the caller's normal UI.
  const status = voice?.status;
  useEffect(() => {
    if (status?.type !== "ended") return;
    if (status.reason === "error") onError?.();
    else onEnd?.();
  }, [status, onEnd, onError]);

  // No "thinking" in RealtimeVoiceAdapter.Mode (listening|speaking only —
  // see webSpeechVoiceAdapter.ts's comment) — derived here instead: the
  // last thing said was the user's, and we haven't started speaking back.
  const last = transcript[transcript.length - 1];
  const thinking = Boolean(last && last.role === "user" && voice?.mode !== "speaking");

  const handleEnd = () => {
    disconnect();
    onEnd?.();
  };

  return (
    <VoiceConversation
      mode={toMode(voice, thinking)}
      amplitude={amplitude}
      muted={voice?.isMuted ?? false}
      onToggleMute={() => (voice?.isMuted ? unmute() : mute())}
      onEnd={handleEnd}
      onInterrupt={onInterrupt}
      transcript={transcript}
    />
  );
}

export function VoiceCallScreen({ voice, transcript, onEnd, onInterrupt, onError }: VoiceCallScreenProps) {
  const [chatModel] = useState(() => createChatModelAdapter());
  const runtime = useLocalRuntime(chatModel, { adapters: { voice } });

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <VoiceCallInner transcript={transcript} onEnd={onEnd} onInterrupt={onInterrupt} onError={onError} />
    </AssistantRuntimeProvider>
  );
}
