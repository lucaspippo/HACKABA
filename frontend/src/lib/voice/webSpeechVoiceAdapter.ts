/**
 * A RealtimeVoiceAdapter (@assistant-ui/react) built on the Web Speech API
 * instead of a real realtime socket. There's no live provider connection
 * here — each "turn" is recognize → askAngela (lib/chat/simpleAsk.ts) →
 * speak, chained in a loop — but wrapping it in the same adapter shape the
 * platform expects means the UI (useVoiceState/useVoiceVolume/
 * useVoiceControls + VoiceConversation) is IDENTICAL to a true realtime
 * session like GPT-Live-1's (see gptLiveVoiceAdapter.ts). One state machine,
 * two very different things behind it.
 *
 * `RealtimeVoiceAdapter.Mode` only has "listening"/"speaking" — there's no
 * "thinking" to emit while askAngela is in flight. Callers that want a
 * "thinking" UI state derive it themselves (transcript's last item is from
 * the user, but mode hasn't flipped to "speaking" yet) — see VozAngela.jsx.
 */
import { createVoiceSession, type RealtimeVoiceAdapter } from "@assistant-ui/react";
import { askAngela } from "../chat/simpleAsk";
import { authStore } from "../auth";
import type { ChatTurn } from "../chat/adapter";

type SpeechRecognitionCtor = new () => any;

function recognitionCtor(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  return (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition || null;
}

export function isWebSpeechVoiceSupported(): boolean {
  return !!recognitionCtor() && typeof window !== "undefined" && "speechSynthesis" in window;
}

export type WebSpeechVoiceOptions = {
  /** Tagged onto every /api/angela/stream call for transcript grouping (see PR1). */
  channel?: string;
  /** A question already captured before the call screen opened (VozAngela's
   * one-shot classifier already has it) — answered immediately instead of
   * making the person repeat themselves into an empty mic. */
  initialQuestion?: string;
  /**
   * VoiceSessionState (useVoiceState()) carries status/isMuted/mode only —
   * no transcript. Callers that want to render one (VoiceConversation does)
   * get it through this callback instead of trying to read it off the
   * runtime, since RealtimeVoiceAdapter.Session's own onTranscript is
   * consumed internally and isn't re-exposed to hook consumers.
   */
  onTranscript?: (item: { role: "user" | "assistant"; text: string }) => void;
};

export function createWebSpeechVoiceAdapter(options: WebSpeechVoiceOptions = {}): RealtimeVoiceAdapter {
  return {
    connect: ({ abortSignal }) =>
      createVoiceSession({ abortSignal }, async (helpers) => {
        const Recognition = recognitionCtor();
        let history: ChatTurn[] = [];
        let muted = false;
        let disposed = false;
        let recognition: any = null;

        const startListening = () => {
          if (disposed || muted) return;
          if (!Recognition) { helpers.end("error", new Error("Web Speech not supported")); return; }
          const r = new Recognition();
          r.lang = "es-AR";
          r.interimResults = false;
          r.continuous = false;
          r.onresult = (e: any) => {
            const text = Array.from(e.results).map((x: any) => x[0].transcript).join("").trim();
            if (text) handleUserTurn(text);
          };
          r.onerror = (e: any) => {
            if (e?.error === "not-allowed") { helpers.end("error", new Error("microphone permission denied")); return; }
            // "no-speech" and anything else recoverable: just listen again.
            if (!disposed && !muted) startListening();
          };
          recognition = r;
          helpers.emitMode("listening");
          r.start();
        };

        const handleUserTurn = async (text: string) => {
          try { recognition?.stop(); } catch { /* already stopped */ }
          helpers.emitTranscript({ role: "user", text, isFinal: true });
          options.onTranscript?.({ role: "user", text });
          const previousHistory = history;
          history = [...previousHistory, { role: "user", content: text }];
          try {
            const answer = await askAngela(text, {
              token: authStore.getSnapshot()?.token,
              channel: options.channel ?? "voz",
              history: previousHistory,
              signal: abortSignal,
            });
            if (disposed) return;
            history = [...history, { role: "assistant", content: answer }];
            helpers.emitTranscript({ role: "assistant", text: answer, isFinal: true });
            options.onTranscript?.({ role: "assistant", text: answer });
            speak(answer);
          } catch (e) {
            if (!disposed) helpers.end("error", e);
          }
        };

        const speak = (text: string) => {
          if (disposed) return;
          if (!text.trim() || !("speechSynthesis" in window)) { startListening(); return; }
          const u = new SpeechSynthesisUtterance(text);
          u.lang = document.documentElement.lang || "es-AR";
          u.onend = () => { if (!disposed) startListening(); };
          u.onerror = () => { if (!disposed) startListening(); };
          helpers.emitMode("speaking");
          window.speechSynthesis.cancel();
          window.speechSynthesis.speak(u);
        };

        helpers.setStatus({ type: "running" });
        if (options.initialQuestion?.trim()) {
          handleUserTurn(options.initialQuestion.trim());
        } else {
          startListening();
        }

        return {
          disconnect: () => {
            disposed = true;
            try { recognition?.stop(); } catch { /* already stopped */ }
            if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel();
            helpers.end("finished");
          },
          mute: () => {
            muted = true;
            try { recognition?.stop(); } catch { /* already stopped */ }
          },
          unmute: () => {
            muted = false;
            startListening();
          },
        };
      }),
  };
}
