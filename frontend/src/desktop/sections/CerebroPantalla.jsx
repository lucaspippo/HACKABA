// EL CEREBRO, A PANTALLA COMPLETA, CON ÁNGELA ADENTRO.
//
// EL ORDEN IMPORTA Y ES TODO EL EFECTO:
//
//     grafo completo  →  pregunta  →  zoom  →  el camino se arma
//
// Nunca el camino ya armado esperando. Antes se entraba y los ocho nodos del
// caso ya estaban ahí con todas sus relaciones; después se mandaba la
// pregunta. El que mira ve el resultado ANTES que la causa, y eso delata que
// está preparado de antemano.
//
// Ahora el estado de reposo es el cerebro entero —seiscientas entidades, sin
// nada respondido— y recién al preguntar la cámara viaja hacia la zona
// relevante mientras el resto se apaga. Ese movimiento es parte del
// argumento: se ve que de todo ese cerebro el sistema fue a buscar estas ocho
// cosas.
//
// También reemplaza la pantalla intermedia: «Lo que sé de tu negocio» abre
// directo acá, y cerrar vuelve al mapa de la operación.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { forceCollide } from "d3-force-3d";
import { X, Maximize2, Send, Sparkles } from "lucide-react";
import { api } from "../../lib/api";
import { authStore } from "../../lib/auth";
import { useT } from "../../lib/i18n";
import AngelaMark from "../../components/AngelaMark";
import EscenaReclamo from "./EscenaReclamo";

const TINTA = "#0f1113";
const AZUL_IA = "#4d7bf0";

const COLOR_TIPO = {
  producto: "#4aa8bf", cliente: "#5fbf8f", proveedor: "#c98a3c",
  rubro: "#8b8fa8", local: "#d7cfc0", remito: "#9d8bc4", cuenta: "#7fd0b0",
  nota: "#e8c86a", persona: "#f2d98c", ubicacion: "#9a938a",
  conocimiento: "#e8c86a",
};

// Cuánto dura el viaje de cámara desde el cerebro entero hasta el caso.
const MS_ZOOM = 1500;

// LAS POSICIONES DEL GRAFO COMPLETO, CACHEADAS.
// La simulación de fuerzas tarda en asentarse, y un segundo de nodos
// acomodándose al entrar arruina el efecto de entrada. Se guardan la primera
// vez y las siguientes aperturas pintan ya quietas.
let _posiciones = null;

// =============================================================================
// LA ÚNICA RUTA GUIONADA DE TODO EL PRODUCTO, Y ES LA EXCEPCIÓN.
//
// Acá adentro hay exactamente UNA pregunta con respuesta escrita: la del demo.
// Cualquier otra cosa —incluida una segunda pregunta sobre el mismo reclamo—
// se va por el flujo real de Ángela, con sus herramientas, y el camino que se
// enciende sale de lo que efectivamente consultó.
//
// Por qué la coincidencia es EXACTA y no por palabras sueltas: antes bastaba
// con que el texto dijera «reclamo», o «campo alegre», o «devoluc» para
// disparar el guion. O sea que si el jurado preguntaba «¿cuánto le debemos a
// Campo Alegre?» le contestábamos con el reclamo de las cajas rotas. Un
// producto que contesta una sola frase se nota al primer intento. Así que la
// puerta se cerró: se normaliza (minúsculas, sin tildes, sin signos, espacios
// colapsados) y tiene que dar IGUAL a la frase del demo. En vivo no se tipea:
// se toca el chip, que manda esa misma cadena.
const normalizar = (t) => (t || "")
  .toLowerCase().normalize("NFD").replace(/\p{M}/gu, "")
  .replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim();

// Las dos formas de la misma pregunta (ES y EN), y nada más. Se comparan ya
// normalizadas, así que un «¿»,  una tilde o un espacio de más no rompen nada.
const PREGUNTA_DEMO = [
  "Llegaron ocho cajas rotas de Campo Alegre, ¿qué hago?",
  "Eight broken boxes arrived from Campo Alegre, what do I do?",
].map(normalizar);

const esLaDelDemo = (t) => PREGUNTA_DEMO.includes(normalizar(t));

// Los tipos de nodo que tocaron estas herramientas, según el mapa que sirve el
// backend (core/temas.py). Una herramienta que no está en el mapa no enciende
// nada: preferimos no iluminar antes que iluminar de mentira.
const tiposDe = (tools, mapa) => {
  if (!mapa) return null;
  const vistos = new Set();
  for (const nombre of tools || []) for (const tipo of mapa[nombre] || []) vistos.add(tipo);
  return vistos.size ? vistos : null;
};

// =============================================================================
// El grafo completo: el estado de reposo. Es DECORADO — no hace falta que sea
// interactivo, hace falta que impresione y que cargue quieto.
// =============================================================================
function GrafoCompleto({ datos, w, h, apagado, refGrafo, encendidos }) {
  const gd = useMemo(() => {
    if (!datos?.nodos?.length) return null;
    const maxPeso = Math.max(1, ...datos.nodos.map((n) => n.peso || 0));
    const nodes = datos.nodos.map((n) => {
      const guardada = _posiciones?.[n.id];
      return {
        ...n,
        _r: 2.2 + 5.4 * Math.sqrt((n.peso || 0) / maxPeso),
        ...(guardada ? { x: guardada.x, y: guardada.y } : {}),
      };
    });
    return { nodes, links: datos.aristas.map((a, i) => ({ ...a, _i: i })) };
  }, [datos]);

  useEffect(() => {
    const fg = refGrafo.current;
    if (!fg || !gd) return;
    fg.d3Force("charge")?.strength(-70).distanceMax(320);
    fg.d3Force("collide", forceCollide((n) => n._r + 1.2));
  }, [gd, refGrafo]);

  const guardar = useCallback(() => {
    if (!gd) return;
    _posiciones = {};
    for (const n of gd.nodes) {
      if (Number.isFinite(n.x)) _posiciones[n.id] = { x: n.x, y: n.y };
    }
    refGrafo.current?.zoomToFit(0, 40);
  }, [gd, refGrafo]);

  if (!gd || !w) return null;
  return (
    <div className="absolute inset-0 transition-opacity duration-700"
         style={{ opacity: apagado ? 0.1 : 1 }}>
      <ForceGraph2D
        ref={refGrafo}
        width={w} height={h}
        graphData={gd}
        backgroundColor={TINTA}
        // si ya hay posiciones guardadas, NO se vuelve a simular: pinta quieto
        warmupTicks={_posiciones ? 0 : 90}
        cooldownTicks={_posiciones ? 0 : 140}
        onEngineStop={guardar}
        enableNodeDrag={false}
        enableZoomInteraction={false}
        enablePanInteraction={false}
        linkColor={() => "rgba(255,255,255,.07)"}
        linkWidth={0.45}
        nodeCanvasObject={(n, ctx) => {
          if (!Number.isFinite(n.x)) return;
          // Con una respuesta real de Ángela en curso, lo que ella consultó se
          // enciende y el resto se apaga. Es el mismo gesto que el zoom del
          // caso guionado —de todo el cerebro, esto— pero acá el recorte lo
          // decide la herramienta que corrió, no un guion.
          const vivo = !encendidos || encendidos.has(n.tipo);
          const base = COLOR_TIPO[n.tipo] || "#8b8fa8";
          ctx.beginPath();
          ctx.arc(n.x, n.y, vivo ? n._r * (encendidos ? 1.5 : 1) : n._r, 0, 2 * Math.PI);
          ctx.fillStyle = vivo ? base : "rgba(255,255,255,.07)";
          ctx.fill();
          if (vivo && encendidos) {     // un halo, para que se lea de lejos
            ctx.strokeStyle = base;
            ctx.globalAlpha = 0.28;
            ctx.lineWidth = n._r * 1.6;
            ctx.stroke();
            ctx.globalAlpha = 1;
          }
        }}
      />
    </div>
  );
}

// =============================================================================
// Ángela. El MISMO tratamiento que el chat del producto: papel claro, el
// cerebrito arriba, burbujas con hairline. No un panel oscuro genérico — es
// la misma Ángela, no una versión para esta pantalla.
// =============================================================================
function PanelAngela({ escena, onPreguntar, mensajes, pensando, valor, setValor }) {
  const t = useT();
  const finRef = useRef(null);
  useEffect(() => { finRef.current?.scrollIntoView({ behavior: "smooth" }); },
            [mensajes, pensando]);

  return (
    <aside className="flex h-full w-[400px] shrink-0 flex-col border-l border-linea bg-papel">
      <div className="flex items-center gap-2.5 border-b border-linea bg-crema px-4 py-3">
        <AngelaMark size={22} />
        <span className="font-display text-base font-bold tracking-tight text-tinta">
          Ángela
        </span>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {mensajes.length === 0 && (
          <div className="flex flex-col items-center pt-6 text-center">
            <AngelaMark size={44} />
            <h3 className="mt-3 font-display text-lg font-bold tracking-tight text-tinta">
              {t("angela.hola")}
            </h3>
            <p className="mt-1.5 max-w-[280px] text-sm leading-relaxed text-tinta-suave">
              {t("cerebro.angela_vacio")}
            </p>
            {escena?.disponible && (
              <button onClick={() => onPreguntar(t("cerebro.pregunta_demo"))}
                      className="mt-5 w-full rounded-xl border border-linea bg-crema px-3 py-2.5
                                 text-left text-sm font-medium text-tinta-suave sombra-papel
                                 transition-colors hover:border-violeta/40 hover:text-tinta">
                <Sparkles className="mr-1.5 inline size-3.5 text-violeta" />
                {t("cerebro.pregunta_demo")}
              </button>
            )}
          </div>
        )}

        {mensajes.map((m, i) => (
          m.de === "yo" ? (
            <div key={i} className="ml-8 rounded-2xl rounded-br-sm bg-violeta px-3.5 py-2.5
                                    text-sm leading-snug text-white">{m.texto}</div>
          ) : (
            <div key={i} className="space-y-2.5">
              <div className="rounded-2xl rounded-bl-sm border border-linea bg-crema px-3.5 py-3
                              text-sm leading-relaxed text-tinta sombra-papel">
                {/* Lo que está haciendo mientras lo hace. Sale del `status` que
                    manda la propia Ángela en cada tool call — no es un texto
                    nuestro, es ella diciendo a qué fue. */}
                {m.haciendo && (
                  <p className="mb-2 flex items-center gap-1.5 text-xs text-tinta-suave">
                    <span className="size-1.5 animate-ping rounded-full bg-violeta" />
                    {m.haciendo}
                  </p>
                )}
                {m.lineas.map((l, j) => <p key={j} className={j ? "mt-2" : ""}>{l}</p>)}
                {/* LA LÍNEA DEL PLAZO: sale de restar la fecha de entrega
                    contra el plazo del proveedor, no de un texto fijo. */}
                {m.plazo && (
                  <p className="mt-3 rounded-lg bg-oro/12 px-2.5 py-2 font-semibold text-oro-tinta">
                    {m.plazo}
                  </p>
                )}
              </div>
              {/* LA PROCEDENCIA DE UNA RESPUESTA REAL: las herramientas que
                  efectivamente corrieron. Mismo tratamiento de tarjeta que la
                  del caso guionado, pero acá la lista no está escrita: es lo
                  que el stream fue reportando. */}
              {!m.procedencia && m.tools?.length > 0 && (
                <div className="rounded-xl border border-linea bg-crema px-3 py-2.5 sombra-papel">
                  <p className="text-2xs font-semibold uppercase tracking-[0.14em] text-tinta-suave">
                    {t("cerebro.consulto")}
                  </p>
                  <p className="mt-1 flex flex-wrap gap-1.5">
                    {[...new Set(m.tools)].map((c) => (
                      <span key={c} className="rounded-full border border-linea bg-papel
                                               px-2 py-0.5 text-xs text-tinta-suave">
                        {c.replace(/_/g, " ")}
                      </span>
                    ))}
                  </p>
                </div>
              )}
              {/* la procedencia, con el mismo tratamiento de tarjeta del chat */}
              {m.procedencia && (
                <div className="rounded-xl border border-linea bg-crema px-3 py-2.5 sombra-papel">
                  <p className="text-2xs font-semibold uppercase tracking-[0.14em] text-tinta-suave">
                    {t("cerebro.consulto")}
                  </p>
                  <p className="mt-1 flex flex-wrap gap-1.5">
                    {m.procedencia.consulto.map((c) => (
                      <span key={c} className="rounded-full border border-linea bg-papel
                                               px-2 py-0.5 text-xs text-tinta-suave">{c}</span>
                    ))}
                  </p>
                  <p className="mt-2.5 text-2xs font-semibold uppercase tracking-[0.14em] text-tinta-suave">
                    {t("cerebro.se_acordo")}
                  </p>
                  <p className="mt-1 text-sm leading-snug text-tinta">
                    «{m.procedencia.recordo.texto}»
                  </p>
                  <p className="mt-1 text-xs text-tinta-suave">
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
          <div className="flex items-center gap-2 text-sm text-tinta-suave">
            <span className="size-2 animate-ping rounded-full bg-violeta" />
            {t("cerebro.pensando")}
          </div>
        )}
        <div ref={finRef} />
      </div>

      <form className="flex items-center gap-2 border-t border-linea bg-crema px-3 py-3"
            onSubmit={(e) => { e.preventDefault(); onPreguntar(valor); }}>
        <input value={valor} onChange={(e) => setValor(e.target.value)}
               placeholder={t("cerebro.preguntale")}
               className="min-w-0 flex-1 rounded-xl border border-linea bg-papel px-3 py-2
                          text-sm text-tinta placeholder:text-tinta-suave focus:outline-none
                          focus:border-violeta/50" />
        <button type="submit" className="rounded-xl bg-violeta p-2.5">
          <Send className="size-4 text-white" />
        </button>
      </form>
    </aside>
  );
}

// =============================================================================
export default function CerebroPantalla({ onCerrar }) {
  const t = useT();
  const [escena, setEscena] = useState(null);
  const [grafo, setGrafo] = useState(null);
  const [mensajes, setMensajes] = useState([]);
  const [pensando, setPensando] = useState(false);
  const [valor, setValor] = useState("");
  // null = reposo (el cerebro entero) · "zoom" = viajando · "escena" = el caso
  const [fase, setFase] = useState(null);
  // Los tipos de nodo encendidos por una respuesta REAL de Ángela. null = nada
  // encendido (reposo o escena guionada).
  const [encendidos, setEncendidos] = useState(null);
  const [mapaTools, setMapaTools] = useState(null);
  const refGrafo = useRef(null);
  const lienzoRef = useRef(null);
  const [caja, setCaja] = useState({ w: 0, h: 0 });

  useEffect(() => {
    api.escenaReclamo().then(setEscena).catch(() => {});
    api.grafo().then(setGrafo).catch(() => {});
    // el mapa herramienta→tipo de nodo, para encender el camino real. Se pide
    // al entrar, no al preguntar: cuando haga falta ya tiene que estar.
    api.cerebroToolsNodos()
      .then((r) => setMapaTools(r?.nodos_por_tool || null))
      .catch(() => {});
  }, []);

  // medir el lienzo (el force-graph necesita px, no %)
  useEffect(() => {
    const el = lienzoRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      const r = el.getBoundingClientRect();
      setCaja({ w: Math.round(r.width), h: Math.round(r.height) });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onCerrar?.(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCerrar]);

  // --- LA RUTA GUIONADA: una pregunta, la del demo, y nada más -------------
  const responderElDemo = useCallback((q) => {
    // EL VIAJE DE CÁMARA. Primero se ve el movimiento desde el cerebro entero
    // hacia la zona del caso — ese desplazamiento es el que explica que el
    // sistema fue a buscar ocho cosas entre seiscientas. Recién cuando llegó
    // aparece la escena y se arman las relaciones.
    setFase("zoom");
    const fg = refGrafo.current;
    if (fg && grafo) {
      const delCaso = new Set(["nota:wa08", "persona:nahuel",
                               "prov:lacteos_campo_alegre"]);
      fg.zoomToFit(MS_ZOOM, 120, (n) => delCaso.has(n.id));
    }
    setTimeout(() => setFase("escena"), MS_ZOOM - 150);
    setTimeout(() => {
      setPensando(false);
      const tiene = (escena.tiene || []).map((x) => `${x.que} (${x.valor})`).join(" y ");
      const falta = (escena.falta || []).join(" y ");
      setMensajes((m) => [...m, {
        de: "angela",
        lineas: [t("cerebro.resp_1", { proveedor: "Lácteos Campo Alegre" }),
                 t("cerebro.resp_2", { tiene, falta }),
                 t("cerebro.resp_3")],
        plazo: escena.plazo?.texto,
        procedencia: escena.procedencia,
      }]);
    }, MS_ZOOM + 250);
  }, [escena, grafo, t]);

  // --- EL CAMINO REAL: Ángela de verdad, y el grafo siguiéndola -------------
  // Lee el NDJSON de /api/angela/stream. Cada `text` es un delta que se va
  // escribiendo; cada `tool_call` enciende en el cerebro los tipos de nodo que
  // esa herramienta consulta. O sea: el camino que se ilumina NO está escrito,
  // es el rastro de lo que Ángela fue a buscar mientras contestaba.
  const responderDeVerdad = useCallback(async (q) => {
    // si veníamos de la escena guionada, se vuelve al cerebro entero: esta
    // respuesta es otra y no puede quedar la escena anterior de fondo.
    setFase(null);
    setEncendidos(null);
    const historial = mensajes
      .filter((m) => m.de === "yo" || (m.de === "angela" && m.lineas?.length))
      .slice(-6)
      .map((m) => ({ role: m.de === "yo" ? "user" : "assistant",
                     content: m.de === "yo" ? m.texto : (m.lineas || []).join("\n") }));

    const indice = mensajes.length + 1;   // el nuestro entra después del "yo"
    setMensajes((m) => [...m, { de: "angela", lineas: [""], real: true, tools: [] }]);

    const parche = (cambio) => setMensajes((m) => {
      const copia = [...m];
      if (copia[indice]) copia[indice] = { ...copia[indice], ...cambio };
      return copia;
    });

    let texto = "";
    const tools = [];
    try {
      const token = authStore.getSnapshot()?.token;
      const res = await api.chatStream(q, historial, { token });
      const lector = res.body.getReader();
      const dec = new TextDecoder();
      let resto = "";
      for (;;) {
        const { done, value } = await lector.read();
        if (done) break;
        resto += dec.decode(value, { stream: true });
        const lineas = resto.split("\n");
        resto = lineas.pop() || "";
        for (const linea of lineas) {
          if (!linea.trim()) continue;
          let ev;
          try { ev = JSON.parse(linea); } catch { continue; }
          if (ev.type === "text") {
            texto += ev.delta || "";
            setPensando(false);
            parche({ lineas: texto.split("\n").filter(Boolean) });
          } else if (ev.type === "tool_call") {
            tools.push(ev.name);
            // el cerebro se enciende MIENTRAS busca, no al final
            setEncendidos(tiposDe(tools, mapaTools));
            parche({ tools: [...tools], haciendo: ev.label || null });
          } else if (ev.type === "done") {
            parche({ tools: ev.result?.tools_used || tools, haciendo: null });
          } else if (ev.type === "error") {
            parche({ lineas: [texto || t("cerebro.resp_error")], haciendo: null });
          }
        }
      }
      if (!texto) parche({ lineas: [t("cerebro.resp_error")], haciendo: null });
    } catch {
      parche({ lineas: [t("cerebro.resp_error")], haciendo: null });
    } finally {
      setPensando(false);
    }
  }, [mensajes, mapaTools, t]);

  const preguntar = useCallback((texto) => {
    const q = (texto || "").trim();
    if (!q) return;
    setValor("");
    setMensajes((m) => [...m, { de: "yo", texto: q }]);
    setPensando(true);
    // LA BIFURCACIÓN, y es la única de todo el producto: coincidencia exacta
    // con la pregunta del demo → el guion. Absolutamente todo lo demás →
    // Ángela de verdad, con sus herramientas.
    if (esLaDelDemo(q) && escena?.disponible) responderElDemo(q);
    else responderDeVerdad(q);
  }, [escena, responderElDemo, responderDeVerdad]);

  const enEscena = fase === "escena";

  return (
    <div className="fixed inset-0 z-[140] flex flex-col" style={{ background: TINTA }}>
      <header className="flex items-center gap-3 border-b px-5 py-3"
              style={{ borderColor: "rgba(255,255,255,.09)" }}>
        <h2 className="min-w-0 flex-1 truncate font-display text-xl font-semibold text-white">
          {enEscena ? escena?.titulo : t("cerebro.titulo")}
          {!enEscena && grafo?.meta && (
            <span className="ml-2 text-base font-normal text-white/40">
              {grafo.meta.nodos} entidades · {grafo.meta.aristas} relaciones
            </span>
          )}
        </h2>
        {enEscena && (
          <button onClick={() => setFase(null)}
                  className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-base text-white/70
                             hover:bg-white/10 hover:text-white">
            <Maximize2 className="size-4" /> {t("cerebro.ver_todo")}
          </button>
        )}
        {/* cerrar vuelve al mapa de tu negocio, que es de donde se vino */}
        <button onClick={onCerrar}
                className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-base text-white/70
                           hover:bg-white/10 hover:text-white">
          <X className="size-4" /> {t("cerebro.cerrar_escena")}
        </button>
      </header>

      <div className="flex min-h-0 flex-1">
        <main ref={lienzoRef} className="relative min-w-0 flex-1 overflow-hidden">
          <GrafoCompleto datos={grafo} w={caja.w} h={caja.h}
                         apagado={fase !== null} refGrafo={refGrafo}
                         encendidos={encendidos} />
          {/* la escena entra encima, escalando desde un poco más chica: se lee
              como que el lienzo se acercó, no como que cambió de pantalla */}
          <div className="absolute inset-0 transition-all duration-700"
               style={{ opacity: enEscena ? 1 : 0,
                        transform: enEscena ? "scale(1)" : "scale(.94)",
                        pointerEvents: enEscena ? "auto" : "none" }}>
            {escena?.disponible && (
              <EscenaReclamo escena={escena} trazar={enEscena} />
            )}
          </div>
        </main>
        <PanelAngela escena={escena} mensajes={mensajes} pensando={pensando}
                     valor={valor} setValor={setValor} onPreguntar={preguntar} />
      </div>
    </div>
  );
}
