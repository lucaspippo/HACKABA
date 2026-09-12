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

/**
 * Ángela is a woman — the Web Speech API has no gender field on a voice, so
 * this matches on the names browsers/OSes actually ship for their female
 * voices, preferring one in the reply's own language. Falls back to
 * whatever the browser defaults to (still fine, just not chosen) when
 * voices haven't loaded yet or none match — never throws.
 */
const FEMALE_VOICE_PATTERN =
  /female|mujer|woman|zira|samantha|victoria|paulina|mónica|monica|helena|sabina|laura|elena|catalina|lucia|carmen|maría|maria/i;

function pickFemaleVoice(lang: string): SpeechSynthesisVoice | undefined {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return void 0;
  const voices = window.speechSynthesis.getVoices();
  if (voices.length === 0) return void 0;
  const langPrefix = lang.slice(0, 2).toLowerCase();
  const inLang = voices.filter((v) => v.lang.toLowerCase().startsWith(langPrefix));
  return (
    inLang.find((v) => FEMALE_VOICE_PATTERN.test(v.name)) ??
    voices.find((v) => FEMALE_VOICE_PATTERN.test(v.name)) ??
    inLang[0]
  );
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
          if ("speechSynthesis" in window) window.speechSynthesis.cancel();
          helpers.emitTranscript({ role: "user", text, isFinal: true });
          options.onTranscript?.({ role: "user", text });
          const previousHistory = history;
          history = [...previousHistory, { role: "user", content: text }];
          // Narrate slow tool calls as they start (e.g. "Revisando el stock...")
          // instead of leaving Ángela silent until the whole answer is ready —
          // spoken, never added to the transcript, since it isn't part of the
          // narrated answer itself.
          const narratedLabels = new Set<string>();
          try {
            const answer = await askAngela(text, {
              token: authStore.getSnapshot()?.token,
              channel: options.channel ?? "voz",
              history: previousHistory,
              signal: abortSignal,
              onToolCall: (label) => {
                if (narratedLabels.has(label)) return;
                narratedLabels.add(label);
                speak(label, { isFinal: false });
              },
            });
            if (disposed) return;
            history = [...history, { role: "assistant", content: answer }];
            helpers.emitTranscript({ role: "assistant", text: answer, isFinal: true });
            options.onTranscript?.({ role: "assistant", text: answer });
            speak(answer, { isFinal: true });
          } catch (e) {
            if (!disposed) helpers.end("error", e);
          }
        };

        /** isFinal: false is an interim narration (e.g. a tool-call label) —
         * queued after whatever's already speaking, never interrupting it,
         * and doesn't resume listening on its own when it finishes. */
        const speak = (text: string, { isFinal }: { isFinal: boolean } = { isFinal: true }) => {
          if (disposed) return;
          if (!text.trim() || !("speechSynthesis" in window)) { if (isFinal) startListening(); return; }
          const u = new SpeechSynthesisUtterance(text);
          u.lang = document.documentElement.lang || "es-AR";
          u.voice = pickFemaleVoice(u.lang) ?? null;
          u.onend = () => { if (!disposed && isFinal) startListening(); };
          u.onerror = () => { if (!disposed && isFinal) startListening(); };
          helpers.emitMode("speaking");
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
