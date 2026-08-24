import { AnimatePresence, motion } from "framer-motion";
import { Check, AlertTriangle } from "lucide-react";
import { useToasts } from "../lib/toastStore";

// Confirmación visible de cada acción — estilo papel, abajo al centro.
export default function Toasts() {
  const items = useToasts();
  return (
    <div aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-5 z-50 flex flex-col items-center gap-2 px-4">
      <AnimatePresence>
        {items.map((t) => (
          <motion.div
            key={t.id}
            initial={{ opacity: 0, y: 16, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.25 }}
            className={`pointer-events-auto flex max-w-md items-center gap-2.5 rounded-full border bg-crema px-4 py-2.5 text-[0.86rem] shadow-[0_14px_36px_-14px_rgba(27,25,22,0.35)] ${
              t.tipo === "error" ? "border-rojo/30" : "border-salvia/30"
            }`}
          >
            <span className={`grid h-5 w-5 shrink-0 place-items-center rounded-full text-crema ${t.tipo === "error" ? "bg-rojo" : "bg-salvia"}`}>
              {t.tipo === "error" ? <AlertTriangle size={11} /> : <Check size={11} />}
            </span>
            {t.texto}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
