import { ActionBarPrimitive, useAuiState } from "@assistant-ui/react";
import { Square, Volume2 } from "lucide-react";
import { useT } from "../../../lib/i18n";

export default function ReadAloudButton() {
  const t = useT();
  const canSpeak = useAuiState((s) => s.thread.capabilities.speech);
  const speaking = useAuiState((s) => s.message.speech !== undefined);
  if (!canSpeak) return null;

  const label = speaking ? t("chat.readaloud.stop") : t("chat.readaloud.play");
  const Primitive = speaking ? ActionBarPrimitive.StopSpeaking : ActionBarPrimitive.Speak;

  return (
    <Primitive asChild>
      <button
        type="button"
        aria-label={label}
        className="grid size-7 shrink-0 place-items-center rounded-full text-tinta-suave outline-none transition-colors hover:bg-papel hover:text-tinta focus-visible:ring-2 focus-visible:ring-violeta"
      >
        {speaking ? <Square size={13} className="fill-current" /> : <Volume2 size={14} />}
      </button>
    </Primitive>
  );
}
