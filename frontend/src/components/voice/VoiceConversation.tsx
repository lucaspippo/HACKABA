// The shared voice-call screen: one visual language for every "live" voice
// surface (VozAngela's conversational mode, VozVivaRecepcion's GPT-Live-1
// reception). Driven entirely by props — no assistant-ui hooks in here —
// so it works the same whether the session behind it is a real realtime
// socket (GPT-Live-1) or a chained Web Speech recognize/ask/speak loop
// wrapped in a RealtimeVoiceAdapter (see lib/voice/*).
//
// AngelaMark is the one established visual identity for Ángela ("violeta
// is Ángela, never data" — DESIGN.md); this reuses it as the orb rather
// than inventing a second mark, with `amplitude` driving a CSS scale on
// top of AngelaMark's own states.
import AngelaMark from "../AngelaMark";
import { Mic, MicOff, PhoneOff } from "lucide-react";
import { useT } from "../../lib/i18n";

export type VoiceMode = "connecting" | "listening" | "thinking" | "speaking";

export type VoiceTranscriptItem = {
  id: string;
  role: "user" | "assistant";
  text: string;
};

export type VoiceConversationProps = {
  mode: VoiceMode;
  /** 0..1, how loud the current speaker is right now. */
  amplitude: number;
  muted?: boolean;
  onToggleMute?: () => void;
  onEnd?: () => void;
  /** Only meaningful while `mode === "speaking"`: cut Ángela off. */
  onInterrupt?: () => void;
  transcript: VoiceTranscriptItem[];
};

const MARK_ESTADO: Record<VoiceMode, string | undefined> = {
  connecting: "pensando",
  listening: undefined,   // idle mark; the pulsing ring below carries amplitude
  thinking: "pensando",
  speaking: "ejecutando",
};

export function VoiceConversation({
  mode, amplitude, muted = false, onToggleMute, onEnd, onInterrupt, transcript,
}: VoiceConversationProps) {
  const t = useT();
  // A gentle floor so the ring never fully disappears between words — a
  // silent orb reads as "frozen", not "listening".
  const scale = 1 + Math.min(Math.max(amplitude, 0), 1) * 0.35;

  return (
    <div className="flex flex-col items-center gap-6 py-6">
      <div className="relative flex h-28 w-28 items-center justify-center">
        {mode === "listening" && (
          <span
            className="absolute inset-0 rounded-full bg-violeta/20 transition-transform duration-100 ease-out"
            style={{ transform: `scale(${scale})` }}
            aria-hidden="true"
          />
        )}
        <AngelaMark size={64} estado={MARK_ESTADO[mode]} />
      </div>

      <p className="text-sm font-semibold text-tinta-suave">{t(`voice.mode_${mode}`)}</p>

      {transcript.length > 0 && (
        <div className="max-h-48 w-full space-y-2 overflow-y-auto px-1">
          {transcript.map((item) => (
            <p key={item.id}
              className={`rounded-xl px-3.5 py-2 text-sm leading-snug ${
                item.role === "user"
                  ? "ml-6 bg-violeta-suave text-tinta"
                  : "mr-6 bg-papel-hondo text-tinta"}`}>
              {item.text}
            </p>
          ))}
        </div>
      )}

      <div className="flex items-center gap-3">
        {onToggleMute && (
          <button onClick={onToggleMute} aria-label={t(muted ? "voice.unmute" : "voice.mute")}
            className={`grid h-11 w-11 place-items-center rounded-full border ${
              muted ? "border-rojo/40 bg-rojo/10 text-rojo" : "border-linea bg-crema text-tinta-suave"}`}>
            {muted ? <MicOff size={18} /> : <Mic size={18} />}
          </button>
        )}
        {mode === "speaking" && onInterrupt && (
          <button onClick={onInterrupt}
            className="rounded-full border border-linea bg-crema px-4 py-2.5 text-sm font-semibold text-tinta-suave">
            {t("voice.interrupt")}
          </button>
        )}
        {onEnd && (
          <button onClick={onEnd} aria-label={t("voice.end")}
            className="grid h-11 w-11 place-items-center rounded-full bg-rojo text-crema">
            <PhoneOff size={18} />
          </button>
        )}
      </div>
    </div>
  );
}
