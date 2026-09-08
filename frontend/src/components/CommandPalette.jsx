import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Search, MessageCircle, CornerDownLeft, Package, Users, Truck,
         ShoppingCart, PackageCheck, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { useT } from "../lib/i18n";

// One icon per kind of thing, so the row says WHAT it is before it is read.
const ICONO_TIPO = {
  producto: Package, cliente: Users, proveedor: Truck,
  orden_compra: ShoppingCart, pedido: PackageCheck,
};

// "Ir a X" reemplaza la necesidad de escanear el sidebar entero para saltar
// de sección; la fila de Ángela al final es la misma acción que antes hacía
// el submit del form (preguntar(texto)) — no se pierde, se reorganiza.
export default function CommandPalette({ open, onClose, secciones, catalogo, vistaHerramienta, onNavegar, onPreguntar }) {
  const t = useT();
  const [q, setQ] = useState("");
  const [activo, setActivo] = useState(0);
  const [datos, setDatos] = useState([]);
  const [pregunta, setPregunta] = useState(false);
  const [buscando, setBuscando] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    if (open) { setQ(""); setActivo(0); setDatos([]); setPregunta(false);
                requestAnimationFrame(() => inputRef.current?.focus()); }
  }, [open]);

  // The data half. Debounced because this types a letter at a time, and
  // ignoring a stale answer matters more than the debounce: without the
  // `vivo` flag a slow "le" can land after a fast "leche" and show the wrong
  // rows under the right query.
  useEffect(() => {
    const texto = q.trim();
    if (!open || texto.length < 2) { setDatos([]); setPregunta(false); setBuscando(false); return undefined; }
    let vivo = true;
    setBuscando(true);
    const id = setTimeout(() => {
      api.buscarGlobal(texto)
        .then((r) => { if (!vivo) return; setDatos(r.items || []); setPregunta(!!r.parece_pregunta); })
        .catch(() => { if (vivo) { setDatos([]); setPregunta(false); } })
        .finally(() => { if (vivo) setBuscando(false); });
    }, 180);
    return () => { vivo = false; clearTimeout(id); };
  }, [q, open]);

  const resultados = useMemo(() => {
    const qn = q.trim().toLowerCase();
    return secciones
      .map((id) => ({ id, label: t(id === "panel" && vistaHerramienta ? "mnav.mi_dia" : catalogo[id].lk), icon: catalogo[id].icon }))
      .filter((r) => !qn || r.label.toLowerCase().includes(qn));
  }, [q, secciones, catalogo, vistaHerramienta, t]);

  // La fila de Ángela vive SIEMPRE al final: con o sin query, preguntarle
  // algo a Ángela es una acción válida, no un fallback de "no encontré nada".
  // SALVO cuando lo escrito tiene forma de pregunta (lo decide el backend,
  // core/buscador.parece_pregunta): ahí va primera, porque "¿cuánta plata
  // tengo parada?" no es el nombre de nada y buscarlo como nombre no da nada.
  const filaAngela = { tipo: "preguntar", id: "__preguntar__" };
  const filasDatos = datos.map((d) => ({ ...d, tipo_dato: d.tipo, tipo: "dato" }));
  const filasIr = resultados.map((r) => ({ tipo: "ir", ...r }));
  const filas = pregunta
    ? [filaAngela, ...filasDatos, ...filasIr]
    : [...filasIr, ...filasDatos, filaAngela];

  const elegir = (fila) => {
    if (!fila) return;
    if (fila.tipo === "ir") onNavegar(fila.id);
    // A data hit lands on its section with the item already focused — never
    // on row 1 of 430. `foco` speaks the same highlight vocabulary the map
    // and Prioridades already hand to onNavegar.
    else if (fila.tipo === "dato") onNavegar(fila.seccion, fila.foco || null);
    else onPreguntar(q.trim() || t("nav.buscador"));
    onClose();
  };

  // Los resultados de datos llegan DESPUÉS de escribir, así que la lista puede
  // encogerse con el cursor ya movido: sin esto, Enter caería en `undefined`
  // y la tecla no haría nada. Se acota al elegir y al pintar.
  const iActivo = Math.min(activo, filas.length - 1);

  const onKeyDown = (e) => {
    if (e.key === "Escape") { onClose(); return; }
    if (e.key === "ArrowDown") { e.preventDefault(); setActivo((i) => Math.min(i + 1, filas.length - 1)); return; }
    if (e.key === "ArrowUp") { e.preventDefault(); setActivo((i) => Math.max(i - 1, 0)); return; }
    if (e.key === "Enter") { e.preventDefault(); elegir(filas[iActivo]); }
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
                className="flex-1 bg-transparent text-base outline-none placeholder:text-tinta-suave/80"
              />
              <kbd className="rounded-md border border-linea px-1.5 py-0.5 text-xs font-semibold text-tinta-suave">Esc</kbd>
            </div>
            <div className="max-h-[22rem] overflow-y-auto p-2">
              {filas.map((fila, i) => {
                const sel = i === iActivo;
                const comun = `flex w-full items-center gap-3 rounded-xl px-2.5 py-2 text-left text-sm font-medium ${
                  sel ? "bg-violeta-suave text-violeta-hondo" : "text-tinta hover:bg-papel-hondo/60"}`;
                const encabezado =
                  (fila.tipo === "ir" && filas[i - 1]?.tipo !== "ir") ? t("palette.ir_a")
                  : (fila.tipo === "dato" && filas[i - 1]?.tipo !== "dato") ? t("palette.en_tus_datos")
                  : null;
                if (fila.tipo === "preguntar") {
                  return (
                    <button key="__preguntar__" onMouseEnter={() => setActivo(i)}
                      onClick={() => elegir(fila)}
                      className={`${comun} ${i > 0 ? "mt-1 border-t border-linea pt-3" : ""}`}>
                      <MessageCircle size={16} className={sel ? "text-violeta" : "text-tinta-suave"} />
                      <span className="min-w-0 flex-1 truncate">
                        {q.trim() ? t("palette.preguntar_con", { q: q.trim() }) : t("palette.preguntar")}
                      </span>
                      {sel && <CornerDownLeft size={13} className="text-violeta" />}
                    </button>
                  );
                }
                const Icon = fila.tipo === "ir" ? fila.icon : (ICONO_TIPO[fila.tipo_dato] || Search);
                return (
                  <div key={fila.tipo === "ir" ? `ir-${fila.id}` : `dato-${fila.tipo_dato}-${fila.id}`}>
                    {encabezado && (
                      <p className="px-2.5 pb-1 pt-1 text-xs font-semibold uppercase tracking-[0.12em] text-tinta-suave">
                        {encabezado}
                      </p>
                    )}
                    <button onMouseEnter={() => setActivo(i)} onClick={() => elegir(fila)} className={comun}>
                      <Icon size={16} className={sel ? "text-violeta" : "text-tinta-suave"} />
                      <span className="min-w-0 flex-1 truncate">
                        {fila.tipo === "ir" ? fila.label : fila.etiqueta}
                        {fila.detalle && (
                          <span className="ml-2 text-xs font-normal text-tinta-suave">{fila.detalle}</span>
                        )}
                      </span>
                      {sel && <CornerDownLeft size={13} className="text-violeta" />}
                    </button>
                  </div>
                );
              })}
              {buscando && (
                <p className="flex items-center gap-2 px-2.5 py-2 text-xs text-tinta-suave">
                  <Loader2 size={12} className="animate-spin" /> {t("palette.buscando")}
                </p>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
