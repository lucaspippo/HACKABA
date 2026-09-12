// EL CEREBRO, A PANTALLA COMPLETA, CON ÁNGELA ADENTRO.
//
// Reemplaza la pantalla intermedia. Antes, «Lo que sé de tu negocio» llevaba a
// una vista con siete bloques compitiendo —título con contador, punto ciego,
// once píldoras de hallazgos, el texto del camino, el contrafáctico, los chips
// de dominios y «lo que disparó esto»— y recién abajo el lienzo, que encima
// arrancaba debajo del fold. Alguien que entraba por primera vez no sabía
// dónde tocar.
//
// Esa pantalla deja de existir. El botón abre DIRECTO acá: el lienzo ocupa
// todo, Ángela entra por la derecha, se pregunta y el camino se traza al lado.
// Cerrar vuelve al mapa de la operación. No hay escala intermedia.
//
// Arriba, lo mínimo: qué se está viendo y tres controles. Todo lo demás —el
// punto ciego, los evals, los otros hallazgos, el contrafáctico— vive detrás
// del botón «⋯», fuera de la vista principal.
import { useCallback, useEffect, useRef, useState } from "react";
import { X, Maximize2, MoreHorizontal, Send, Sparkles } from "lucide-react";
import { api } from "../../lib/api";
import { useT } from "../../lib/i18n";
import AngelaMark from "../../components/AngelaMark";
import EscenaReclamo from "./EscenaReclamo";

const TINTA = "#0f1113";
const AZUL_IA = "#4d7bf0";

// La pregunta del demo. Se reconoce por palabras sueltas y no por la frase
// exacta: en vivo uno tipea rápido y se come una tilde, y que el show dependa
// de escribir catorce palabras idénticas es una forma tonta de que falle.
const PISTAS_RECLAMO = [
  ["caja", "rota"], ["cajas", "rotas"], ["reclam", "campo alegre"],
  ["reclamo"], ["devoluc"], ["campo alegre"],
];

function coincide(texto) {
  const q = (texto || "").toLowerCase()
    .normalize("NFD").replace(/\p{M}/gu, "");
  return PISTAS_RECLAMO.some((grupo) => grupo.every((p) => q.includes(p)));
}

// --- el panel de Ángela ------------------------------------------------------
function PanelAngela({ escena, onPreguntar, mensajes, pensando, valor, setValor }) {
  const t = useT();
  const finRef = useRef(null);
  useEffect(() => { finRef.current?.scrollIntoView({ behavior: "smooth" }); },
            [mensajes, pensando]);

  return (
    <aside className="flex h-full w-[390px] shrink-0 flex-col border-l"
           style={{ background: "#141719", borderColor: "rgba(255,255,255,.09)" }}>
      <div className="flex items-center gap-2 border-b px-4 py-3"
           style={{ borderColor: "rgba(255,255,255,.09)" }}>
        <AngelaMark size={16} />
        <span className="text-base font-semibold text-white/90">Ángela</span>
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {mensajes.length === 0 && (
          <p className="text-base leading-snug text-white/45">
            {t("cerebro.angela_vacio")}
          </p>
        )}
        {mensajes.map((m, i) => (
          m.de === "yo" ? (
            <div key={i} className="ml-6 rounded-2xl rounded-br-sm px-3.5 py-2.5 text-base text-white"
                 style={{ background: AZUL_IA }}>{m.texto}</div>
          ) : (
            <div key={i} className="space-y-3">
              <div className="rounded-2xl rounded-bl-sm px-3.5 py-3 text-base leading-snug text-white/90"
                   style={{ background: "rgba(255,255,255,.06)" }}>
                {m.lineas.map((l, j) => (
                  <p key={j} className={j ? "mt-2" : ""}>{l}</p>
                ))}
                {/* LA LÍNEA DEL PLAZO. Sale de restar la fecha de entrega
                    contra el plazo del proveedor — no es un texto fijo. */}
                {m.plazo && (
                  <p className="mt-2.5 rounded-lg px-2.5 py-1.5 font-semibold"
                     style={{ background: "rgba(240,160,75,.16)", color: "#f0a04b" }}>
                    {m.plazo}
                  </p>
                )}
              </div>
              {/* LA PROCEDENCIA, adentro de la respuesta: qué consultó y qué
                  recordó, con quién lo enseñó y cuándo. Es la contestación
                  preparada a «¿cómo sé que no lo inventó?». */}
              {m.procedencia && (
                <div className="rounded-xl border px-3 py-2.5 text-sm"
                     style={{ borderColor: "rgba(255,255,255,.1)" }}>
                  <p className="text-white/40">{t("cerebro.consulto")}</p>
                  <p className="mt-0.5 flex flex-wrap gap-1.5">
                    {m.procedencia.consulto.map((c) => (
                      <span key={c} className="rounded-full px-2 py-0.5 text-white/70"
                            style={{ background: "rgba(255,255,255,.07)" }}>{c}</span>
                    ))}
                  </p>
                  <p className="mt-2 text-white/40">{t("cerebro.se_acordo")}</p>
                  <p className="mt-0.5 leading-snug text-white/80">
                    «{m.procedencia.recordo.texto}»
                  </p>
                  <p className="mt-1 text-white/45">
                    {t("cerebro.enseñada", {
                      quien: m.procedencia.recordo.quien,
                      cuando: (m.procedencia.recordo.cuando || "").split("-").reverse().join("/"),
                      veces: m.procedencia.recordo.veces,
                    })}
                  </p>
                </div>
              )}
            </div>
          )
        ))}
        {pensando && (
          <div className="flex items-center gap-2 text-base text-white/45">
            <span className="size-2 animate-ping rounded-full" style={{ background: AZUL_IA }} />
            {t("cerebro.pensando")}
          </div>
        )}
        <div ref={finRef} />
      </div>

      {/* sugerencia: la pregunta del caso, a un toque */}
      {mensajes.length === 0 && escena?.disponible && (
        <div className="px-4 pb-2">
          <button onClick={() => onPreguntar(t("cerebro.pregunta_demo"))}
                  className="w-full rounded-xl border px-3 py-2 text-left text-base text-white/75
                             hover:text-white"
                  style={{ borderColor: "rgba(255,255,255,.14)" }}>
            <Sparkles className="mr-1.5 inline size-3.5" style={{ color: AZUL_IA }} />
            {t("cerebro.pregunta_demo")}
          </button>
        </div>
      )}

      <form className="flex items-center gap-2 border-t px-3 py-3"
            style={{ borderColor: "rgba(255,255,255,.09)" }}
            onSubmit={(e) => { e.preventDefault(); onPreguntar(valor); }}>
        <input value={valor} onChange={(e) => setValor(e.target.value)}
               placeholder={t("cerebro.preguntale")}
               className="min-w-0 flex-1 rounded-xl px-3 py-2 text-base text-white
                          placeholder:text-white/35 focus:outline-none"
               style={{ background: "rgba(255,255,255,.06)" }} />
        <button type="submit" className="rounded-xl p-2" style={{ background: AZUL_IA }}>
          <Send className="size-4 text-white" />
        </button>
      </form>
    </aside>
  );
}

// =============================================================================
export default function CerebroPantalla({ onCerrar, onVerTodo, onMas }) {
  const t = useT();
  const [escena, setEscena] = useState(null);
  const [mensajes, setMensajes] = useState([]);
  const [pensando, setPensando] = useState(false);
  const [valor, setValor] = useState("");
  const [trazando, setTrazando] = useState(false);

  useEffect(() => { api.escenaReclamo().then(setEscena).catch(() => {}); }, []);

  // Esc cierra: es el gesto que todo el mundo prueba en una pantalla completa.
  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onCerrar?.(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCerrar]);

  const preguntar = useCallback((texto) => {
    const q = (texto || "").trim();
    if (!q) return;
    setValor("");
    setMensajes((m) => [...m, { de: "yo", texto: q }]);
    setPensando(true);

    // La respuesta del caso se arma con los datos de la escena — el plazo sale
    // de una resta de fechas y la procedencia del conocimiento real. No es un
    // texto escrito a mano: si mañana cambia la regla, cambia la respuesta.
    const esDelCaso = coincide(q) && escena?.disponible;
    setTimeout(() => {
      setPensando(false);
      if (esDelCaso) {
        const tiene = (escena.tiene || []).map((x) => `${x.que} (${x.valor})`).join(" y ");
        const falta = (escena.falta || []).join(" y ");
        setMensajes((m) => [...m, {
          de: "angela",
          lineas: [
            t("cerebro.resp_1", { proveedor: "Lácteos Campo Alegre" }),
            t("cerebro.resp_2", { tiene, falta }),
            t("cerebro.resp_3"),
          ],
          plazo: escena.plazo?.texto,
          procedencia: escena.procedencia,
        }]);
        setTrazando(false);
        // un tick para reiniciar la animación desde cero
        requestAnimationFrame(() => setTrazando(true));
      } else {
        setMensajes((m) => [...m, {
          de: "angela",
          lineas: [t("cerebro.resp_otra")],
        }]);
      }
    }, 420);
  }, [escena, t]);

  return (
    <div className="fixed inset-0 z-[140] flex flex-col" style={{ background: TINTA }}>
      {/* ------------------------------------------ arriba: lo mínimo */}
      <header className="flex items-center gap-3 border-b px-5 py-3"
              style={{ borderColor: "rgba(255,255,255,.09)" }}>
        <h2 className="min-w-0 flex-1 truncate font-display text-xl font-semibold text-white">
          {escena?.titulo || t("cerebro.titulo")}
        </h2>
        <button onClick={onMas} title={t("cerebro.mas")}
                className="rounded-lg p-2 text-white/55 hover:bg-white/10 hover:text-white">
          <MoreHorizontal className="size-4" />
        </button>
        <button onClick={onVerTodo}
                className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-base text-white/70
                           hover:bg-white/10 hover:text-white">
          <Maximize2 className="size-4" /> {t("cerebro.ver_todo")}
        </button>
        <button onClick={onCerrar}
                className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-base text-white/70
                           hover:bg-white/10 hover:text-white">
          <X className="size-4" /> {t("cerebro.cerrar_escena")}
        </button>
      </header>

      <div className="flex min-h-0 flex-1">
        <main className="min-w-0 flex-1">
          {escena?.disponible
            ? <EscenaReclamo escena={escena} trazar={trazando} />
            : <div className="flex h-full items-center justify-center text-base text-white/40">
                {t("cerebro.cargando")}
              </div>}
        </main>
        <PanelAngela escena={escena} mensajes={mensajes} pensando={pensando}
                     valor={valor} setValor={setValor} onPreguntar={preguntar} />
      </div>
    </div>
  );
}
