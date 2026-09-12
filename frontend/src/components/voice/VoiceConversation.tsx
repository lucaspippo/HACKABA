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
import { Mic, MicOff, PhoneOff, Plus } from "lucide-react";
import { useT } from "../../lib/i18n";
import { cn } from "@/lib/utils";

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
  /** Omit to hide the attach affordance entirely (e.g. no upload feature). */
  onAttach?: () => void;
  transcript: VoiceTranscriptItem[];
};

const MARK_ESTADO: Record<VoiceMode, string | undefined> = {
  connecting: "pensando",
  listening: undefined,   // idle mark; the pulsing ring below carries amplitude
  thinking: "pensando",
  speaking: "ejecutando",
};

export function VoiceConversation({
  mode, amplitude, muted = false, onToggleMute, onEnd, onInterrupt, onAttach, transcript,
}: VoiceConversationProps) {
  const t = useT();
  // A gentle floor so the ring never fully disappears between words — a
  // silent orb reads as "frozen", not "listening".
  const level = Math.min(Math.max(amplitude, 0), 1);
  const live = mode === "listening" || mode === "speaking";
  const scale = 1 + level * 0.35;
  const canInterrupt = mode === "speaking" && Boolean(onInterrupt);

  return (
    <div className="relative flex h-full w-full flex-1 flex-col overflow-hidden">
      {/* Ángela's color, not data — an ambient wash, pulsing with whoever's
          talking (the person while listening, Ángela while speaking). */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 bottom-0 h-64 bg-gradient-to-t from-violeta/[0.18] via-violeta/[0.05] to-transparent transition-[opacity,transform] duration-150 ease-out"
        style={{
          opacity: live ? 0.6 + level * 0.4 : 0.6,
          transform: `scaleY(${live ? 1 + level * 0.3 : 1})`,
          transformOrigin: "bottom",
        }}
      />

      <div className="relative flex flex-1 flex-col items-center justify-center gap-6 overflow-y-auto px-4 py-6">
        <button
          type="button"
          onClick={canInterrupt ? onInterrupt : undefined}
          aria-label={canInterrupt ? t("voice.interrupt") : undefined}
          className={cn(
            "relative flex h-28 w-28 items-center justify-center rounded-full",
            canInterrupt ? "cursor-pointer" : "cursor-default",
          )}
        >
          {(mode === "listening" || mode === "speaking") && (
            <span
              className="absolute inset-0 rounded-full bg-violeta/20 transition-transform duration-100 ease-out"
              style={{ transform: `scale(${scale})` }}
              aria-hidden="true"
            />
          )}
          <span
            className={cn("transition-[opacity,filter] duration-300", muted && "opacity-50 saturate-50")}
            style={mode === "speaking" ? { transform: `scale(${1 + level * 0.08})` } : undefined}
          >
            <AngelaMark size={64} estado={MARK_ESTADO[mode]} />
          </span>
        </button>

        <p className="text-sm font-semibold text-tinta-suave">
          {t(`voice.mode_${muted ? "muted" : mode}`)}
        </p>

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
      </div>

      {/* attach (left) · mute (center, primary) · end call (right) */}
      <div className="relative z-10 flex items-center justify-between px-8 pb-6 pt-2">
        {onAttach ? (
          <button onClick={onAttach} aria-label={t("voice.attach")}
            className="grid h-11 w-11 place-items-center rounded-full border border-linea bg-crema text-tinta-suave transition-colors hover:text-tinta">
            <Plus size={18} />
          </button>
        ) : (
          <span className="h-11 w-11" aria-hidden="true" />
        )}

        {onToggleMute && (
          <button onClick={onToggleMute} aria-label={t(muted ? "voice.unmute" : "voice.mute")}
            className={cn(
              "grid h-14 w-14 place-items-center rounded-full border transition-colors",
              muted ? "border-rojo/40 bg-rojo/10 text-rojo" : "border-linea bg-crema text-tinta-suave",
            )}>
            {muted ? <MicOff size={20} /> : <Mic size={20} />}
          </button>
        )}

        {onEnd ? (
          <button onClick={onEnd} aria-label={t("voice.end")}
            className="grid h-11 w-11 place-items-center rounded-full bg-rojo text-crema">
            <PhoneOff size={18} />
          </button>
        ) : (
          <span className="h-11 w-11" aria-hidden="true" />
        )}
      </div>
    </div>
  );
}
