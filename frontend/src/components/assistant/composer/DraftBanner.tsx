import { RotateCcw, X } from "lucide-react";
import { useT } from "../../../lib/i18n";
import { fecha } from "../../../lib/format";

export default function DraftBanner({
  savedAt,
  preview,
  onRestore,
  onDiscard,
}: {
  savedAt: number;
  preview: string;
  onRestore: () => void;
  onDiscard: () => void;
}) {
  const t = useT();
  return (
    <div className="mb-2 flex items-center gap-2 rounded-2xl border border-linea bg-crema px-3 py-2 sombra-papel">
      <div className="min-w-0 flex-1">
        <p className="text-[0.78rem] font-semibold text-tinta">
          {t("chat.draft.title")}
          {savedAt > 0 && <span className="ml-1.5 font-normal text-tinta-suave">{fecha(savedAt)}</span>}
        </p>
        <p className="truncate text-[0.78rem] text-tinta-suave">{preview}</p>
      </div>
      <button
        type="button"
        onClick={onRestore}
        className="flex shrink-0 items-center gap-1.5 rounded-full border border-violeta/30 px-2.5 py-1 text-[0.78rem] font-semibold text-violeta outline-none transition-colors hover:bg-violeta hover:text-crema focus-visible:ring-2 focus-visible:ring-violeta"
      >
        <RotateCcw size={13} />
        {t("chat.draft.restore")}
      </button>
      <button
        type="button"
        aria-label={t("chat.draft.discard")}
        onClick={onDiscard}
        className="grid size-7 shrink-0 place-items-center rounded-full text-tinta-suave outline-none transition-colors hover:bg-papel hover:text-tinta focus-visible:ring-2 focus-visible:ring-violeta"
      >
        <X size={14} />
      </button>
    </div>
  );
}
