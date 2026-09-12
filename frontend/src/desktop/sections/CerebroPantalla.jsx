// EL CEREBRO, A PANTALLA COMPLETA, CON LA ÁNGELA DEL PRODUCTO ADENTRO.
//
// EL ORDEN IMPORTA Y ES TODO EL EFECTO:
//
//     grafo completo  →  pregunta  →  zoom  →  el camino se arma
//
// Nunca el camino ya armado esperando: el que mira vería el resultado ANTES
// que la causa, y eso delata que está preparado.
//
// TRES DECISIONES QUE COSTARON Y NO HAY QUE DESHACER:
//
// 1. EL CHAT ES EL DEL PRODUCTO, NO UNO DE ESTA PANTALLA.
//    Acá adentro va `ChatPanel`, el mismo componente que el dock y el
//    fullscreen, con el cerebrito y las tarjetas de herramienta de
//    `ToolCallCard`. Antes había un panel propio con burbujas parecidas, y
//    "parecidas" es justo lo que no puede ser: la respuesta del demo se veía
//    distinta de una respuesta real.
//
// 2. LA RESPUESTA DEL DEMO VIENE DEL BACKEND, POR EL MISMO PROTOCOLO.
//    `core/guion.py` emite los mismos eventos NDJSON que el modelo —mismas
//    tool calls, corriendo de verdad— así que el chat la pinta con el mismo
//    componente. Acá no hay ni una respuesta escrita. Lo único que esta
//    pantalla sabe de la pregunta del demo es CUÁNDO mover la cámara.
//
// 3. EL FONDO ES CLARO.
//    Un lienzo negro adentro de un producto claro entra de golpe y se lee
//    como otra aplicación. El cerebro usa el mismo papel, las mismas
//    hairlines y la misma tipografía que el resto.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { forceCollide } from "d3-force-3d";
import { X, Maximize2, Mic, Square } from "lucide-react";
import { api } from "../../lib/api";
import { cerebroBus } from "../../lib/cerebroBus";
import { useT } from "../../lib/i18n";
import ChatPanel from "../../views/ChatPanel";
import EscenaReclamo from "./EscenaReclamo";

// Los tokens del producto, leídos del CSS: una sola definición de color.
const PAPEL = "#fbfbfa";
const TINTA = "#21201d";
const VIOLETA = "#2a5cdf";

// Los tipos, en la paleta de la casa. Legibles sobre papel, no sobre negro.
const COLOR_TIPO = {
  producto: "#2f8fa8", cliente: "#2e9c6a", proveedor: "#b5721f",
  rubro: "#6f7490", local: "#a99f8c", remito: "#7a63b8", cuenta: "#2a9c86",
  nota: "#c79a1e", persona: "#d2a52c", ubicacion: "#8a8378",
  conocimiento: "#c79a1e",
};
const GRIS = "#8b8fa8";

// Cuánto dura el viaje de cámara desde el cerebro entero hasta el caso.
const MS_ZOOM = 1500;

// LA PREGUNTA DEL DEMO — SÓLO PARA LA CÁMARA.
// La respuesta la decide el backend (core/guion.py, con la misma comparación).
// Acá se usa únicamente para saber si hay que viajar a la zona del caso y
// mostrar la escena: es una decisión de puesta en escena, no de contenido.
const normalizar = (t) => (t || "")
  .toLowerCase().normalize("NFD").replace(/\p{M}/gu, "")
  .replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim();

const PREGUNTA_DEMO = [
  "Llegaron ocho cajas rotas de Campo Alegre, ¿qué hago?",
  "Eight broken boxes arrived from Campo Alegre, what do I do?",
].map(normalizar);

const esLaDelDemo = (t) => PREGUNTA_DEMO.includes(normalizar(t));

// Los tipos de nodo que tocaron estas herramientas, según el mapa que sirve el
// backend. Una herramienta que no está en el mapa no enciende nada.
const tiposDe = (tools, mapa) => {
  if (!mapa) return null;
  const vistos = new Set();
  for (const n of tools || []) for (const tipo of mapa[n] || []) vistos.add(tipo);
  return vistos.size ? vistos : null;
};

// =============================================================================
// LAS POSICIONES, CALCULADAS UNA VEZ Y GUARDADAS.
//
// La simulación de fuerzas sobre 605 nodos tarda lo suyo, y un segundo de
// nodos acomodándose al entrar arruina la entrada. Se guardan en memoria para
// las reaperturas de la sesión y en localStorage para las recargas: la segunda
// vez que alguien abre el cerebro —o sea SIEMPRE en el escenario del demo,
// porque se prueba antes— pinta ya quieto.
// =============================================================================
const LLAVE_POS = "polpilot.cerebro.posiciones.v1";
let _posiciones = null;

function leerGuardadas(n) {
  if (_posiciones) return _posiciones;
  try {
    const crudo = window.localStorage.getItem(LLAVE_POS);
    if (!crudo) return null;
    const g = JSON.parse(crudo);
    // si el grafo cambió de tamaño, las posiciones viejas no sirven
    if (!g || g.n !== n || !g.p) return null;
    _posiciones = g.p;
    return _posiciones;
  } catch { return null; }
}

function guardar(nodos, n) {
  const p = {};
  for (const nodo of nodos) {
    if (Number.isFinite(nodo.x)) p[nodo.id] = [Math.round(nodo.x), Math.round(nodo.y)];
  }
  _posiciones = p;
  try { window.localStorage.setItem(LLAVE_POS, JSON.stringify({ n, p })); }
  catch { /* storage lleno: se recalcula la próxima, no es grave */ }
}

// =============================================================================
// El grafo completo: el estado de reposo. Tiene que LEERSE COMO UNA RED.
//
// Antes era puntitos sueltos sobre negro con las líneas a 7% de opacidad, o
// sea invisibles. Decir «605 entidades · 2062 relaciones» encima de una
// pantalla donde no se ve ninguna relación es peor que no decir nada: el
// número queda desmentido por lo que se ve.
// =============================================================================
function GrafoCompleto({ datos, w, h, apagado, refGrafo, encendidos }) {
  const gd = useMemo(() => {
    if (!datos?.nodos?.length) return null;
    const maxPeso = Math.max(1, ...datos.nodos.map((n) => n.peso || 0));
    const guardadas = leerGuardadas(datos.nodos.length);
    const nodes = datos.nodos.map((n) => {
      const p = guardadas?.[n.id];
      return {
        ...n,
        _r: 2.4 + 5.2 * Math.sqrt((n.peso || 0) / maxPeso),
        ...(p ? { x: p[0], y: p[1] } : {}),
      };
    });
    return { nodes, links: datos.aristas.map((a, i) => ({ ...a, _i: i })), _pre: !!guardadas };
  }, [datos]);

  useEffect(() => {
    const fg = refGrafo.current;
    if (!fg || !gd) return;
    fg.d3Force("charge")?.strength(-70).distanceMax(320);
    fg.d3Force("collide", forceCollide((n) => n._r + 1.2));
  }, [gd, refGrafo]);

  const alParar = useCallback(() => {
    if (!gd) return;
    guardar(gd.nodes, gd.nodes.length);
    refGrafo.current?.zoomToFit(0, 40);
  }, [gd, refGrafo]);

  if (!gd || !w) return null;
  return (
    <div className="absolute inset-0 transition-opacity duration-700"
         style={{ opacity: apagado ? 0.12 : 1 }}>
      <ForceGraph2D
        ref={refGrafo}
        width={w} height={h}
        graphData={gd}
        backgroundColor={PAPEL}
        warmupTicks={gd._pre ? 0 : 90}
        cooldownTicks={gd._pre ? 0 : 140}
        onEngineStop={alParar}
        enableNodeDrag={false}
        enableZoomInteraction={false}
        enablePanInteraction={false}
        // LAS RELACIONES SE VEN. Tinta al 13% sobre papel: suficiente para que
        // el tejido se lea de lejos y no tanto como para tapar los nodos.
        linkColor={() => (encendidos ? "rgba(33,32,29,.05)" : "rgba(33,32,29,.13)")}
        linkWidth={0.7}
        nodeCanvasObject={(n, ctx) => {
          if (!Number.isFinite(n.x)) return;
          // Con una respuesta en curso, lo que Ángela consultó se enciende y
          // el resto se apaga: de todo el cerebro, esto.
          const vivo = !encendidos || encendidos.has(n.tipo);
          const base = COLOR_TIPO[n.tipo] || GRIS;
          if (vivo && encendidos) {
            ctx.beginPath();
            ctx.arc(n.x, n.y, n._r * 2.6, 0, 2 * Math.PI);
            ctx.fillStyle = base;
            ctx.globalAlpha = 0.18;
            ctx.fill();
            ctx.globalAlpha = 1;
          }
          ctx.beginPath();
          ctx.arc(n.x, n.y, vivo && encendidos ? n._r * 1.45 : n._r, 0, 2 * Math.PI);
          ctx.fillStyle = vivo ? base : "rgba(33,32,29,.10)";
          ctx.fill();
        }}
      />
    </div>
  );
}

// =============================================================================
// EL MICRÓFONO. En el demo no se tipea: alguien del depósito le habla a la app,
// que es como pasaría en la vida real.
//
// Tres estados, y cada uno se ve distinto a propósito:
//   escuchando  la pelotita late y hay ondas — está tomando audio
//   transcripto aparece la frase, un segundo, para que se lea que entendió
//   procesando  otra animación, más apretada — está pensando, no escuchando
//
// No transcribe de verdad: el navegador no tiene con qué garantizarlo en una
// sala con ruido y un pitch no se juega a eso. El texto que aparece es el
// mismo que manda el chip, así que entra por la misma puerta que cualquier
// pregunta escrita.
// =============================================================================
function Microfono({ onPregunta, texto }) {
  const t = useT();
  const [estado, setEstado] = useState(null);
  const timers = useRef([]);

  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  const arrancar = () => { timers.current.forEach(clearTimeout); setEstado("escuchando"); };

  const cortar = () => {
    setEstado("transcripto");
    timers.current.push(setTimeout(() => setEstado("procesando"), 1100));
    timers.current.push(setTimeout(() => { setEstado(null); onPregunta(texto); }, 2100));
  };

  if (!estado) {
    return (
      <button onClick={arrancar}
              className="flex items-center gap-2.5 rounded-full border border-linea bg-crema
                         px-4 py-2.5 text-sm font-medium text-tinta sombra-papel
                         transition-colors hover:border-violeta/50">
        <Mic className="size-4 text-violeta" />
        {t("cerebro.hablar")}
      </button>
    );
  }

  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-linea
                    bg-crema px-6 py-5 sombra-papel">
      <div className="relative flex size-16 items-center justify-center">
        {estado === "escuchando" && (
          <>
            <span className="absolute inline-flex size-16 animate-ping rounded-full
                             opacity-40" style={{ background: VIOLETA }} />
            <span className="absolute inline-flex size-[52px] animate-pulse rounded-full
                             opacity-30" style={{ background: VIOLETA }} />
          </>
        )}
        {estado === "procesando" && (
          <span className="absolute inline-flex size-[58px] animate-spin rounded-full border-[3px]
                           border-transparent"
                style={{ borderTopColor: VIOLETA, borderRightColor: VIOLETA }} />
        )}
        {/* LA PELOTITA. La misma de siempre: es Ángela, no un ícono de audio. */}
        <span className="relative size-9 rounded-full shadow-inner"
              style={{
                background: `radial-gradient(circle at 32% 28%, #86a8ff 0%, ${VIOLETA} 62%, #1c3f9e 100%)`,
                transform: estado === "escuchando" ? "scale(1.06)" : "scale(1)",
                transition: "transform .35s",
              }} />
      </div>

      {estado === "escuchando" && (
        <>
          <p className="text-sm text-tinta-suave">{t("cerebro.escuchando")}</p>
          <button onClick={cortar}
                  className="flex items-center gap-1.5 rounded-full bg-violeta px-3.5 py-1.5
                             text-xs font-semibold text-white">
            <Square className="size-3 fill-current" /> {t("cerebro.listo")}
          </button>
        </>
      )}
      {estado === "transcripto" && (
        <p className="max-w-[280px] text-center text-sm font-medium leading-snug text-tinta">
          «{texto}»
        </p>
      )}
      {estado === "procesando" && (
        <p className="text-sm text-tinta-suave">{t("cerebro.pensando")}</p>
      )}
    </div>
  );
}

// =============================================================================
export default function CerebroPantalla({ onCerrar }) {
  const t = useT();
  const [escena, setEscena] = useState(null);
  const [grafo, setGrafo] = useState(null);
  const [mapaTools, setMapaTools] = useState(null);
  // null = reposo (el cerebro entero) · "zoom" = viajando · "escena" = el caso
  const [fase, setFase] = useState(null);
  const [encendidos, setEncendidos] = useState(null);
  const [pregunta, setPregunta] = useState(null);   // lo que se manda al chat
  const refGrafo = useRef(null);
  const lienzoRef = useRef(null);
  const [caja, setCaja] = useState({ w: 0, h: 0 });
  const usadas = useRef([]);

  useEffect(() => {
    api.escenaReclamo().then(setEscena).catch(() => {});
    api.grafo().then(setGrafo).catch(() => {});
    api.cerebroToolsNodos()
      .then((r) => setMapaTools(r?.nodos_por_tool || null))
      .catch(() => {});
  }, []);

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

  // --- EL GRAFO SIGUE AL CHAT -------------------------------------------
  // Todo lo que pasa acá lo dispara el chat real: no hay una copia del
  // stream ni una segunda fuente de verdad. El adapter avisa por el bus.
  useEffect(() => {
    return cerebroBus.subscribe((ev) => {
      if (ev.tipo === "empieza") {
        usadas.current = [];
        setEncendidos(null);
        if (esLaDelDemo(ev.pregunta) && escena?.disponible) {
          // EL VIAJE DE CÁMARA: se ve que de seiscientas cosas el sistema fue
          // a buscar estas ocho. Recién cuando llegó aparece la escena.
          setFase("zoom");
          const fg = refGrafo.current;
          if (fg && grafo) {
            const delCaso = new Set(["nota:wa08", "persona:nahuel",
                                     "prov:lacteos_campo_alegre"]);
            fg.zoomToFit(MS_ZOOM, 120, (n) => delCaso.has(n.id));
          }
          setTimeout(() => setFase("escena"), MS_ZOOM - 150);
        } else {
          setFase(null);
        }
      } else if (ev.tipo === "herramienta") {
        usadas.current = [...usadas.current, ev.nombre];
        // en la escena guionada el camino ya lo cuenta la escena; encender
        // además el grafo de atrás sería decir lo mismo dos veces
        if (fase === null) setEncendidos(tiposDe(usadas.current, mapaTools));
      } else if (ev.tipo === "termina") {
        if (fase === null && ev.tools?.length) {
          setEncendidos(tiposDe(ev.tools, mapaTools));
        }
      }
    });
  }, [escena, grafo, mapaTools, fase]);

  const enEscena = fase === "escena";
  const enReposo = fase === null && !encendidos;

  return (
    <div className="fixed inset-0 z-[140] flex flex-col bg-papel">
      <header className="flex items-center gap-3 border-b border-linea bg-crema px-5 py-3">
        <h2 className="min-w-0 flex-1 truncate font-display text-xl font-semibold text-tinta">
          {enEscena ? escena?.titulo : t("cerebro.titulo")}
          {!enEscena && grafo?.meta && (
            <span className="ml-2 text-base font-normal text-tinta-suave">
              {grafo.meta.nodos} entidades · {grafo.meta.aristas} relaciones
            </span>
          )}
        </h2>
        {enEscena && (
          <button onClick={() => { setFase(null); setEncendidos(null); }}
                  className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-base
                             text-tinta-suave hover:bg-papel hover:text-tinta">
            <Maximize2 className="size-4" /> {t("cerebro.ver_todo")}
          </button>
        )}
        {/* cerrar vuelve al mapa de tu negocio, que es de donde se vino */}
        <button onClick={onCerrar}
                className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-base
                           text-tinta-suave hover:bg-papel hover:text-tinta">
          <X className="size-4" /> {t("cerebro.cerrar_escena")}
        </button>
      </header>

      <div className="flex min-h-0 flex-1">
        <main ref={lienzoRef} className="relative min-w-0 flex-1 overflow-hidden bg-papel">
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

          {/* EL MICRÓFONO, sobre el lienzo y sólo en reposo: es lo que hay que
              hacer cuando todavía no se preguntó nada. */}
          {enReposo && escena?.disponible && (
            <div className="pointer-events-auto absolute bottom-8 left-1/2 -translate-x-1/2">
              <Microfono texto={t("cerebro.pregunta_demo")}
                         onPregunta={(q) => setPregunta(q)} />
            </div>
          )}
        </main>

        {/* ÁNGELA, LA DEL PRODUCTO. El mismo componente del dock: el cerebrito,
            las tarjetas de herramienta, el mismo tratamiento. Nada propio. */}
        <aside className="flex h-full w-[420px] shrink-0 flex-col border-l border-linea bg-papel">
          <ChatPanel variant="dock" inputInicial={pregunta} />
        </aside>
      </div>
    </div>
  );
}
