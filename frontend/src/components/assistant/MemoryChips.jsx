import { AnimatePresence, motion } from "framer-motion";
import { Brain, X } from "lucide-react";
import { useT } from "../../lib/i18n";

// Same "conocimiento" accent as MapaNegocio.jsx's Brain glyph (K_COLOR) — one
// visual language for "this is business knowledge" across the app, whether
// it's the Mapa panel or a chip inline in the chat.
const K_COLOR = "#a86b1e";

// One pill per fact Ángela proposed to remember this turn — the chat-native
// front end for core/conocimiento.py's "pendiente" staging state (see
// ChatThread.jsx's MessageExtras, which reads these off the
// proponer_conocimiento tool-call parts). Anatomy and behavior follow
// assistant-ui's memory-chips element: a header that reads "memoria" until
// something new shows up, then "recordado N"; each pill mounts with a brief
// fade+scale and never replays once it's on screen; only two color states
// (existing vs. just-added), never three.
//
// `chips`: [{ id, text, change: "added" | "existing" }]
// `onForget(chip)`: called when the pill's forget button is pressed. Here
// that means "retract this proposal" (core/conocimiento.py's rechazar) —
// nothing has been confirmed as real knowledge yet, so forgetting it is
// cheap, not an undo of something already in effect.
export default function MemoryChips({ chips, onForget }) {
  const t = useT();
  const nuevos = chips.filter((c) => c.change !== "existing").length;

  return (
    <div data-slot="memory-chips" className="mt-2 flex flex-col gap-1.5">
      <div className="flex items-center gap-1.5 text-[0.72rem] font-semibold text-tinta-suave">
        <Brain size={13} aria-hidden style={{ color: K_COLOR }} />
        <span>{nuevos > 0 ? t("memoria_chips.recordado_n", { n: nuevos }) : t("memoria_chips.memoria")}</span>
      </div>
      {chips.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          <AnimatePresence initial={false}>
            {chips.map((chip) => (
              <motion.span
                key={chip.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ duration: 0.3 }}
                className={`inline-flex max-w-[280px] items-center gap-1.5 rounded-full border px-3 py-1 text-[0.78rem] ${
                  chip.change === "existing"
                    ? "border-linea bg-papel/60 text-tinta-suave"
                    : "border-violeta/25 bg-violeta/[0.06] text-tinta"
                }`}
              >
                <span className="truncate">{chip.text}</span>
                <button
                  type="button"
                  aria-label={t("memoria_chips.olvidar", { texto: chip.text })}
                  onClick={() => onForget?.(chip)}
                  className="shrink-0 rounded-full p-0.5 text-tinta-suave/70 transition-colors hover:bg-tinta/10 hover:text-tinta"
                >
                  <X size={11} />
                </button>
              </motion.span>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
