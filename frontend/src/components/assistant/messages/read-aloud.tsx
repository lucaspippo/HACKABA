import { useState } from "react";
import { Volume2, X } from "lucide-react";
import { ReadAloud } from "../read-aloud";
import { isReadAloudSupported, useReadAloud } from "../useReadAloud";
import { useT } from "../../../lib/i18n";

function Panel({ text, onClose }: { text: string; onClose: () => void }) {
  const t = useT();
  const { words, spokenIndex, playing, rate, elapsed, toggle, cycleRate } = useReadAloud(text);
  return (
    <div className="mt-2 flex items-start gap-1">
      <ReadAloud
        words={words}
        spokenIndex={spokenIndex}
        playing={playing}
        rate={rate}
        elapsed={elapsed}
        onToggle={toggle}
        onRateChange={cycleRate}
        labels={{
          play: t("chat.readaloud.play"),
          pause: t("chat.readaloud.pause"),
          progress: t("chat.readaloud.progress"),
          speed: (r) => t("chat.readaloud.speed", { rate: String(r) }),
        }}
      />
      <button
        type="button"
        aria-label={t("chat.readaloud.close")}
        onClick={onClose}
        className="grid size-7 shrink-0 place-items-center rounded-full text-tinta-suave outline-none transition-colors hover:bg-papel hover:text-tinta focus-visible:ring-2 focus-visible:ring-violeta"
      >
        <X size={14} />
      </button>
    </div>
  );
}

export default function ReadAloudControl({ text }: { text: string }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  if (!isReadAloudSupported() || !text) return null;

  if (open) return <Panel text={text} onClose={() => setOpen(false)} />;

  return (
    <button
      type="button"
      aria-label={t("chat.readaloud.play")}
      onClick={() => setOpen(true)}
      className="grid size-7 shrink-0 place-items-center rounded-full text-tinta-suave outline-none transition-colors hover:bg-papel hover:text-tinta focus-visible:ring-2 focus-visible:ring-violeta"
    >
      <Volume2 size={14} />
    </button>
  );
}
