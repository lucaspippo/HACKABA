import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Search, MessageCircle, CornerDownLeft } from "lucide-react";
import { useT } from "../lib/i18n";

// "Ir a X" reemplaza la necesidad de escanear el sidebar entero para saltar
// de sección; la fila de Ángela al final es la misma acción que antes hacía
// el submit del form (preguntar(texto)) — no se pierde, se reorganiza.
export default function CommandPalette({ open, onClose, secciones, catalogo, vistaHerramienta, onNavegar, onPreguntar }) {
  const t = useT();
  const [q, setQ] = useState("");
  const [activo, setActivo] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => {
    if (open) { setQ(""); setActivo(0); requestAnimationFrame(() => inputRef.current?.focus()); }
  }, [open]);

  const resultados = useMemo(() => {
    const qn = q.trim().toLowerCase();
    return secciones
      .map((id) => ({ id, label: t(id === "panel" && vistaHerramienta ? "mnav.mi_dia" : catalogo[id].lk), icon: catalogo[id].icon }))
      .filter((r) => !qn || r.label.toLowerCase().includes(qn));
  }, [q, secciones, catalogo, vistaHerramienta, t]);

  // La fila de Ángela vive SIEMPRE al final: con o sin query, preguntarle
  // algo a Ángela es una acción válida, no un fallback de "no encontré nada".
  const filas = [
    ...resultados.map((r) => ({ tipo: "ir", ...r })),
    { tipo: "preguntar", id: "__preguntar__" },
  ];

  const elegir = (fila) => {
    if (!fila) return;
    if (fila.tipo === "ir") onNavegar(fila.id);
    else onPreguntar(q.trim() || t("nav.buscador"));
    onClose();
  };

  const onKeyDown = (e) => {
    if (e.key === "Escape") { onClose(); return; }
    if (e.key === "ArrowDown") { e.preventDefault(); setActivo((i) => Math.min(i + 1, filas.length - 1)); return; }
    if (e.key === "ArrowUp") { e.preventDefault(); setActivo((i) => Math.max(i - 1, 0)); return; }
    if (e.key === "Enter") { e.preventDefault(); elegir(filas[activo]); }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-start justify-center bg-tinta/30 pt-[12vh]"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 420, damping: 32 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-lg overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-alta"
          >
            <div className="flex items-center gap-3 border-b border-linea px-4 py-3">
              <Search size={17} className="shrink-0 text-tinta-suave" />
              <input
                ref={inputRef}
                value={q}
                onChange={(e) => { setQ(e.target.value); setActivo(0); }}
                onKeyDown={onKeyDown}
                placeholder={t("nav.buscador")}
                className="flex-1 bg-transparent text-[0.95rem] outline-none placeholder:text-tinta-suave/80"
              />
              <kbd className="rounded-md border border-linea px-1.5 py-0.5 text-[0.7rem] font-semibold text-tinta-suave">Esc</kbd>
            </div>
            <div className="max-h-[22rem] overflow-y-auto p-2">
              {resultados.length > 0 && (
                <p className="px-2.5 pb-1 pt-1 text-[0.72rem] font-semibold uppercase tracking-[0.12em] text-tinta-suave">
                  {t("palette.ir_a")}
                </p>
              )}
              {resultados.map((r, i) => {
                const Icon = r.icon;
                const sel = i === activo;
                return (
                  <button
                    key={r.id}
                    onMouseEnter={() => setActivo(i)}
                    onClick={() => elegir(filas[i])}
                    className={`flex w-full items-center gap-3 rounded-xl px-2.5 py-2 text-left text-[0.9rem] font-medium ${
                      sel ? "bg-violeta-suave text-violeta-hondo" : "text-tinta hover:bg-papel-hondo/60"
                    }`}
                  >
                    <Icon size={16} className={sel ? "text-violeta" : "text-tinta-suave"} />
                    <span className="flex-1">{r.label}</span>
                    {sel && <CornerDownLeft size={13} className="text-violeta" />}
                  </button>
                );
              })}
              {(() => {
                const i = filas.length - 1;
                const sel = i === activo;
                return (
                  <button
                    onMouseEnter={() => setActivo(i)}
                    onClick={() => elegir(filas[i])}
                    className={`mt-1 flex w-full items-center gap-3 rounded-xl border-t border-linea px-2.5 py-2 pt-3 text-left text-[0.9rem] font-medium ${
                      sel ? "bg-violeta-suave text-violeta-hondo" : "text-tinta hover:bg-papel-hondo/60"
                    }`}
                  >
                    <MessageCircle size={16} className={sel ? "text-violeta" : "text-tinta-suave"} />
                    <span className="min-w-0 flex-1 truncate">
                      {q.trim() ? t("palette.preguntar_con", { q: q.trim() }) : t("palette.preguntar")}
                    </span>
                    {sel && <CornerDownLeft size={13} className="text-violeta" />}
                  </button>
                );
              })()}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
