import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  ReactFlow, ReactFlowProvider, Background, Handle, Position, MarkerType,
  useNodesState, useEdgesState, useReactFlow, useNodesInitialized,
  BaseEdge, EdgeLabelRenderer,
  getBezierPath, getStraightPath, getSmoothStepPath,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  Snowflake, Warehouse, Truck, Store, Users, Building2, FileText, PackageCheck,
  ChevronDown, ChevronRight, X, Package, ArrowRight,
  Mic, MessageSquare, ClipboardList, Camera, Database, BookOpen, Eye, Check,
  Mail, Sparkles,
  Maximize2, Minimize2, Maximize, Plus, Minus, PanelLeftClose, PanelLeftOpen,
} from "lucide-react";
import { api } from "../../lib/api";
import AngelaMark from "../../components/AngelaMark";
import { GRAFICO } from "../../lib/paleta";
import { useT } from "../../lib/i18n";
import {
  disponerEnCapas, ANCHO_NODO, ladoHacia, ladosDelCuadro,
} from "../../lib/mapaLayout";

// ============================================================================
// THE OPERATION MAP
// ----------------------------------------------------------------------------
// Two layers, deliberately weighted apart:
//
//   THE ROUTE (weight 1 and 2) — where goods come from, where they are and
//   where they go. It is physical: a node's position means the moment of the
//   circuit it occupies, not an algorithm's output.
//
//   THE CONTEXT (weight 3) — what NO ERP captures, and the reason the route
//   makes sense: the team's heads-ups, who they are, the house criterion
//   nobody wrote down, and what returns to the system. It goes around, in
//   grey, with dashed amber strokes toward what it touched.
//
// THREE DECISIONS THAT HOLD THE SCREEN
//
//   1. COLOR IS STATE, NEVER DECORATION. Red = money being lost or something
//      stuck. Amber = needs attention, there is still time. Neutral = nothing
//      to do here today.
//   2. EVERY LINE CARRIES ITS NUMBER. An empty line is a diagram; one with
//      «154 packages unconfirmed» on top is a board.
//   3. GRID LINES GO STRAIGHT, and the diagonals go around the logo.
//
// The component COMPUTES NOTHING: every node ships `metricas: [{label,
// valor}]` and `badges` with the text already written — per language, by the
// backend. Here it iterates. That is what lets this same screen serve another
// industry (or another language) without touching a line.
// ============================================================================

const ICONO = {
  proveedor: Building2, orden_compra: FileText, deposito: Warehouse,
  zona: Snowflake, pedido: PackageCheck, camion: Truck, boca: Store,
  cliente: Users, cobranza: Store,
};

// The WhatsApp glyph, monochrome in its own green. Drawn here because no icon
// library ships brand marks, and the visitor recognizes it before reading the
// word — which is exactly what it is there for.
// Monochrome and `currentColor`: the recognisable SHAPE is what makes the
// channel readable at a glance — the official brand green would break the
// palette and drag a branding question into a data screen for no gain.
function IconoWhatsApp({ size = 12 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.46 1.32 4.96L2 22l5.25-1.38a9.9 9.9 0 0 0 4.79 1.22h.01c5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01A9.82 9.82 0 0 0 12.04 2Zm0 18.12h-.01a8.2 8.2 0 0 1-4.19-1.15l-.3-.18-3.12.82.83-3.04-.2-.31a8.2 8.2 0 0 1-1.26-4.35c0-4.54 3.7-8.24 8.25-8.24 2.2 0 4.27.86 5.83 2.42a8.19 8.19 0 0 1 2.41 5.83c0 4.54-3.7 8.2-8.24 8.2Zm4.52-6.16c-.25-.12-1.47-.72-1.69-.81-.23-.08-.39-.12-.56.13-.16.24-.64.8-.78.97-.14.16-.29.19-.54.06-.25-.12-1.05-.39-1.99-1.23-.74-.66-1.23-1.47-1.38-1.72-.14-.25-.01-.38.11-.5.11-.11.25-.29.37-.43.12-.15.16-.25.25-.41.08-.17.04-.31-.02-.43-.06-.12-.56-1.34-.76-1.84-.2-.48-.4-.42-.56-.43h-.47c-.17 0-.43.06-.66.31-.23.25-.86.85-.86 2.06s.89 2.39 1.01 2.56c.12.16 1.75 2.67 4.23 3.74.59.26 1.05.41 1.41.52.59.19 1.13.16 1.56.1.47-.07 1.47-.6 1.68-1.18.21-.58.21-1.08.14-1.18-.06-.11-.22-.17-.47-.29Z" />
    </svg>
  );
}

// One icon per channel, all the same weight. The three that come in FROM
// OUTSIDE — the ones no ERP captures — go first.
const ICONO_CANAL = {
  whatsapp: IconoWhatsApp, email: Mail, foto: Camera,
  voz: Mic, chat: MessageSquare, reporte: FileText,
};

const TONO = {
  verde: { borde: GRAFICO.salvia, fondo: "#f4f9f6", texto: GRAFICO.salvia },
  amarillo: { borde: GRAFICO.oro, fondo: "#fdf8f1", texto: "#96560a" },
  rojo: { borde: GRAFICO.rojo, fondo: "#fdf4f3", texto: GRAFICO.rojo },
  neutro: { borde: "#e3dfd8", fondo: "#ffffff", texto: "#6e6a63" },
};

const AMBAR = GRAFICO.oro;
const AZUL_IA = "#2a5cdf";
const COLOR_ARISTA = {
  recepcion: GRAFICO.hielo, orden: GRAFICO.oro, contiene: "#ddd9d2",
  carga: GRAFICO.hielo, reparto: GRAFICO.salvia, reposicion: GRAFICO.salvia,
  mostrador: "#ddd9d2", transito: GRAFICO.rojo, corredor: GRAFICO.hielo,
  cobranza: GRAFICO.oro,
  informacion: AMBAR, criterio: AMBAR, devolucion: GRAFICO.salvia,
};

const LADOS = ["t", "r", "b", "l"];
const POS_HANDLE = { t: Position.Top, r: Position.Right, b: Position.Bottom, l: Position.Left };

// Four handles per node. React Flow needs them to EXIST before an edge names
// them: an edge into an unmounted handle simply does not draw, silently.
function Handles() {
  return LADOS.map((l) => (
    <span key={l}>
      <Handle type="source" id={`s-${l}`} position={POS_HANDLE[l]} style={{ opacity: 0 }} />
      <Handle type="target" id={`t-${l}`} position={POS_HANDLE[l]} style={{ opacity: 0 }} />
    </span>
  ));
}

const sombra = {
  1: "0 8px 28px rgba(33,32,29,.10), 0 1px 2px rgba(33,32,29,.06)",
  2: "0 2px 8px rgba(33,32,29,.06)",
  3: "0 1px 3px rgba(33,32,29,.04)",
};

// --- the route card ---------------------------------------------------------
function NodoOperacion({ data }) {
  const Icono = ICONO[data.tipo] || Package;
  const t = TONO[data.estado] || TONO.neutro;
  const [principal, ...resto] = data.metricas || [];
  const grande = data.peso === 1;

  return (
    <div
      className={`rounded-2xl border transition-all duration-200
                  ${data.apagado ? "opacity-[0.18]" : ""}`}
      style={{
        width: data.ancho,
        padding: grande ? "16px 18px" : "11px 13px",
        borderColor: data.enCamino ? AZUL_IA : t.borde,
        borderWidth: grande || data.enCamino ? 1.5 : 1,
        background: t.fondo,
        boxShadow: data.enCamino
          ? `0 0 0 4px rgba(42,92,223,.14), ${sombra[1]}`
          : sombra[data.peso] || sombra[2],
      }}
    >
      <Handles />
      <div className="flex items-start gap-2">
        <Icono size={grande ? 18 : 15} className="mt-px shrink-0"
               style={{ color: t.texto }} />
        <div className="min-w-0 flex-1">
          <p className={`truncate font-semibold leading-tight text-tinta
                         ${grande ? "text-[1.02rem]" : "text-[0.86rem]"}`}>
            {data.etiqueta}
          </p>
          {data.subtitulo && (
            <p className="truncate text-[0.7rem] leading-tight text-tinta-suave">
              {data.subtitulo}
            </p>
          )}
        </div>
        {data.expandible && (
          <span className="shrink-0 rounded-full bg-tinta/[0.06] px-1.5 py-0.5
                           text-[0.62rem] font-semibold text-tinta-suave">
            {data.hijos?.length}
          </span>
        )}
      </div>

      {/* ONE big number, its unit beside it. Three same-size numbers are none. */}
      {principal && (
        <p className={`font-display font-bold leading-none tabular-nums text-tinta
                       ${grande ? "mt-3 text-[2.3rem]" : "mt-1.5 text-[1.3rem]"}`}>
          {principal.valor}
          <span className="ml-1.5 text-[0.66rem] font-medium uppercase
                           tracking-[0.08em] text-tinta-suave">
            {principal.label}
          </span>
        </p>
      )}

      {/* The bar: it reads before any number does. */}
      {data.ocupacion_pct != null && (
        <div className="mt-2.5 h-[7px] overflow-hidden rounded-full bg-tinta/[0.07]">
          <div className="h-full rounded-full transition-all duration-500"
               style={{ width: `${Math.min(100, data.ocupacion_pct)}%`,
                        background: t.borde }} />
        </div>
      )}

      {/* Sub-labels: the number says how much, these say in what state. */}
      {data.badges?.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-1">
          {data.badges.map((b) => (
            <span key={b.texto}
                  className="rounded-md px-1.5 py-[3px] text-[0.63rem] font-medium leading-none"
                  style={{ color: (TONO[b.tono] || TONO.neutro).texto,
                           background: (TONO[b.tono] || TONO.neutro).borde + "1a" }}>
              {b.texto}
            </span>
          ))}
        </div>
      )}

      {resto.length > 0 && !grande && (
        <div className="mt-1.5 flex flex-wrap gap-x-2.5 gap-y-0.5">
          {resto.map((m) => (
            <span key={m.label} className="text-[0.68rem] leading-tight">
              <span className="text-tinta-suave">{m.label} </span>
              <span className={`font-semibold tabular-nums ${
                m.estado === "error" ? "text-rojo"
                : m.estado === "dudoso" ? "text-oro-tinta" : "text-tinta"}`}>
                {m.valor}
              </span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// The hub at the center IS the brand. It says whose all of this is and opens
// the warehouse detail on tap: one node doing both jobs, in the only place on
// the map where the logo is not decoration.
function NodoMarca({ data }) {
  return (
    <div className="grid cursor-pointer place-items-center gap-1.5 rounded-2xl
                    border border-linea bg-crema px-3 transition hover:border-violeta/40"
         style={{ width: data.lado, height: data.lado, boxShadow: sombra[1] }}>
      <Handles />
      {data.logo
        ? <img src={data.logo} alt={data.empresa}
               className="max-h-[46px] max-w-[118px] object-contain" />
        : <span className="text-center font-display text-[0.9rem] font-bold leading-tight">
            {data.empresa}
          </span>}
      <span className="font-display text-[1.15rem] font-bold leading-none tabular-nums">
        {data.total}
      </span>
      <span className="text-center text-[0.6rem] leading-tight text-tinta-suave">
        {data.pie}
      </span>
    </div>
  );
}

// --- the context layer (weight 3) -------------------------------------------
// Slightly different ground and dashed border: at a glance it reads as not
// part of the route — it is what explains it.
function envoltura(extra = "") {
  return `rounded-2xl border border-dashed bg-papel-hondo/60 px-4 py-3 ` +
         `transition-all duration-200 ${extra}`;
}

function NodoCanales({ data }) {
  return (
    <div className={envoltura()} style={{ width: data.ancho, borderColor: "#ddd9d2",
                                          boxShadow: sombra[3] }}>
      <Handles />
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-[0.7rem] font-semibold uppercase tracking-[0.12em] text-tinta-suave">
          {data.etiqueta}
        </p>
        <p className="text-[0.66rem] italic text-tinta-suave/80">{data.subtitulo}</p>
      </div>
      {/* GROUPED, not tagged one by one. The per-chip "← de afuera" label had
          to be read to be understood; two labelled groups separated by a rule
          are understood before being read — which is the whole job of this
          band. Outside first: the reading order carries the thesis. */}
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2">
        {[true, false].map((deAfuera) => {
          const grupo = (data.chips || []).filter((c) => !!c.de_afuera === deAfuera);
          if (!grupo.length) return null;
          return (
            <div key={String(deAfuera)} className="flex items-center gap-1.5">
              <span className={`shrink-0 text-[0.56rem] font-semibold uppercase
                                tracking-[0.1em] ${deAfuera ? "text-oro-tinta" : "text-tinta-suave/70"}`}>
                {deAfuera ? data.rotulo_afuera : data.rotulo_adentro}
              </span>
              {grupo.map((c) => {
                const I = ICONO_CANAL[c.id] || ClipboardList;
                return (
                  <span key={c.id}
                        className={`flex cursor-pointer items-center gap-1.5 rounded-full border
                                    px-2.5 py-1 text-[0.72rem] transition ${deAfuera
                            ? "border-oro/50 bg-oro/[0.07] font-medium text-tinta hover:border-oro"
                            : "border-linea bg-crema text-tinta-suave hover:border-tinta-suave/40"}`}
                        data-chip={c.id}>
                    <I size={12} className="shrink-0"
                       style={{ color: deAfuera ? AMBAR : "#8d887f" }}
                       data-chip={c.id} />
                    <span data-chip={c.id}>{c.nombre}</span>
                    <strong className="tabular-nums" data-chip={c.id}>{c.total}</strong>
                  </span>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function NodoEquipo({ data }) {
  return (
    <div className={envoltura()} style={{ width: data.ancho, borderColor: "#ddd9d2",
                                          boxShadow: sombra[3] }}>
      <Handles />
      <div className="flex items-center gap-2">
        <Users size={15} className="shrink-0 text-tinta-suave" />
        <p className="text-[0.86rem] font-semibold text-tinta">{data.etiqueta}</p>
      </div>
      <p className="mt-0.5 text-[0.7rem] text-tinta-suave">{data.subtitulo}</p>
      {/* Overlapping avatars: the Linear/Notion pattern. Up front go the ones
          who flagged the MOST, not the first of the alphabet. */}
      <div className="mt-2.5 flex items-center">
        {(data.avatares || []).map((a, i) => (
          <span key={a.username}
                title={`${a.nombre} · ${a.rol}`}
                className="grid h-8 w-8 place-items-center rounded-full border-2
                           border-crema text-[0.68rem] font-bold text-crema"
                style={{ background: a.color, marginLeft: i ? -10 : 0, zIndex: 10 - i }}>
            {a.inicial}
          </span>
        ))}
        {data.resto > 0 && (
          <span className="grid h-8 w-8 place-items-center rounded-full border-2
                           border-crema bg-tinta/10 text-[0.64rem] font-bold text-tinta-suave"
                style={{ marginLeft: -10 }}>
            +{data.resto}
          </span>
        )}
      </div>
      <p className="mt-2 text-[0.68rem] text-tinta-suave">{data.pie}</p>
    </div>
  );
}

function NodoReglas({ data }) {
  return (
    <div className={envoltura()} style={{ width: data.ancho, borderColor: AMBAR + "88",
                                          background: "#fdfaf5", boxShadow: sombra[3] }}>
      <Handles />
      <div className="flex items-center gap-2">
        <BookOpen size={15} className="shrink-0" style={{ color: AMBAR }} />
        <p className="text-[0.86rem] font-semibold text-tinta">{data.etiqueta}</p>
      </div>
      <p className="mt-0.5 text-[0.7rem] text-tinta-suave">{data.subtitulo}</p>
      <ul className="mt-2 space-y-1">
        {(data.ejemplos || []).map((e) => (
          <li key={e} className="text-[0.68rem] italic leading-snug text-tinta-suave">
            «{e}»
          </li>
        ))}
      </ul>
    </div>
  );
}

function NodoDevuelve({ data }) {
  return (
    <div className={envoltura()} style={{ width: data.ancho, borderColor: "#ddd9d2",
                                          boxShadow: sombra[3] }}>
      <Handles />
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <span className="flex items-center gap-2">
          <Database size={14} className="shrink-0 text-tinta-suave" />
          <span className="text-[0.7rem] font-semibold uppercase tracking-[0.12em]
                           text-tinta-suave">{data.etiqueta}</span>
          {/* WHICH system, not "a system". It comes from the backend: tenant
              identity, phase-1 CSV connector rail (core/conectores.py). */}
          {data.sistema && (
            <span className="rounded border border-linea bg-crema px-1.5 py-0.5
                             font-display text-[0.7rem] font-bold tracking-tight text-tinta">
              {data.sistema}
            </span>
          )}
          {data.via && (
            <span className="text-[0.62rem] text-tinta-suave/80">{data.via}</span>
          )}
        </span>
        {/* Chips say what HAPPENED, not a fixed check mark. If nothing went
            back, it says so: a decorative ✓ cannot be defended when asked. */}
        {data.vacio
          ? <span className="text-[0.72rem] text-tinta-suave">{data.subtitulo}</span>
          : (data.chips || []).map((c) => (
              <span key={c.id}
                    className="flex items-center gap-1 rounded-full bg-salvia/10 px-2.5
                               py-1 text-[0.72rem] font-medium text-salvia">
                <Check size={11} className="shrink-0" />
                {c.texto}
                <strong className="tabular-nums">{c.n}</strong>
              </span>
            ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// LA ARISTA CON RÓTULO — el número va donde SE LEE, no donde cae el medio.
// ---------------------------------------------------------------------------
// El problema, medido: una arista que va del cuadro central a las columnas de
// la derecha tiene su punto medio geométrico ADENTRO de una tarjeta
// intermedia, y React Flow dibuja las aristas por debajo de los nodos — así
// que el rótulo quedaba cortado («…tos sin confirmar»).
//
// Subir el z-index lo dejaría flotando encima de las tarjetas: se leería, pero
// ensuciaría el cuadro. En vez de eso, el rótulo se corre al primer punto
// LIBRE de su propio recorrido (ver `posicionLibre`), medido contra los
// rectángulos reales de los nodos. Ningún nodo se mueve y ningún rótulo se
// pierde.
function AristaRotulada(props) {
  const {
    id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition,
    markerEnd, style, label, data,
  } = props;
  const forma = data?.forma;
  const [path] =
    forma === "straight"
      ? getStraightPath({ sourceX, sourceY, targetX, targetY })
      : forma === "smoothstep"
        ? getSmoothStepPath({ sourceX, sourceY, targetX, targetY,
                              sourcePosition, targetPosition })
        : getBezierPath({ sourceX, sourceY, targetX, targetY,
                          sourcePosition, targetPosition });
  const pos = posicionLibre(id, { x: sourceX, y: sourceY },
                            { x: targetX, y: targetY },
                            label, data?.rects || []);
  return (
    <>
      <BaseEdge id={id} path={path} markerEnd={markerEnd} style={style} />
      {label && (
        <EdgeLabelRenderer>
          <div
            className="pointer-events-none absolute rounded"
            style={{
              transform: `translate(-50%, -50%) translate(${pos.x}px, ${pos.y}px)`,
              fontSize: 10,
              fontWeight: 500,
              lineHeight: 1.4,
              padding: "1px 5px",
              whiteSpace: "nowrap",
              color: data.alerta ? GRAFICO.rojo : GRAFICO.tintaSuave,
              // Opaque, not translucent: where a stroke passes underneath, a
              // 92%-alpha pill still shows the line through the digits.
              background: "#fbfbfa",
              opacity: data.opacidad,
              transition: "opacity .2s ease",
            }}
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

const TIPOS_ARISTA = { rotulada: AristaRotulada };

/**
 * Cuánto mide de ancho un rótulo, en píxeles, de verdad.
 *
 * Estimarlo por cantidad de caracteres se pasaba largo — «69 bultos sin
 * confirmar» da 141 px estimados contra 113 reales — y con 28 px de más el
 * test de colisión descartaba huecos donde el rótulo entraba holgado. Se mide
 * con el mismo tipo con el que se va a dibujar y se cachea: es una medición
 * por texto distinto, no por render.
 */
const _anchos = new Map();
let _pincel = null;
function anchoDeTexto(texto) {
  const s = String(texto || "");
  const ya = _anchos.get(s);
  if (ya != null) return ya;
  if (!_pincel && typeof document !== "undefined") {
    _pincel = document.createElement("canvas").getContext("2d");
    const familia = getComputedStyle(document.body).fontFamily || "sans-serif";
    _pincel.font = `500 10px ${familia}`;   // el mismo del rótulo
  }
  // +14 = los 10 px de padding lateral del chip y 4 de margen de seguridad.
  const w = _pincel ? Math.ceil(_pincel.measureText(s).width) + 14 : s.length * 6;
  _anchos.set(s, w);
  return w;
}

const ALTO_ROTULO = 16;
const PADDING_ROTULO = 7;   // lo que sobra a cada lado del texto dentro del chip
                            // (5 px de padding + 2 de margen, ver anchoDeTexto)

// Puntos a probar a lo largo del trayecto, del medio hacia las puntas, y en
// cada uno un corrimiento PERPENDICULAR, de menor a mayor: mover el número dos
// líneas arriba de su propia arista no lo despega de ella. El paso es chico a
// propósito: con saltos de 18 px el mejor lugar para «76 bultos sin confirmar»
// se comía la «r» final, y con 9 px entra entero.
const _TES = Array.from({ length: 25 },
  (_, i) => 0.5 + (i % 2 ? 1 : -1) * Math.ceil(i / 2) * 0.035);
const _OFFS = Array.from({ length: 27 },
  (_, i) => (i % 2 ? 1 : -1) * Math.ceil(i / 2) * 9);

// Dónde quedó cada rótulo de esta pasada, para que el siguiente lo esquive.
const _colocados = new Map();
let _rectsDeLaPasada = null;

/**
 * Dónde poner el rótulo de una arista para que se lea entero.
 *
 * Devuelve el primer punto que no pisa ningún nodo. Si no hay ninguno —y hay
 * cuatro que no lo tienen: el pasillo entre columnas mide 44 px y «10 pedidos»
 * mide 59, así que el hueco no existe y no lo va a crear un barrido más
 * ancho— devuelve el que menos TEXTO tapa, penalizando la distancia a la línea
 * para que no se vaya lejos a cambio de dos píxeles: un rótulo a 106 px de un
 * trayecto de 46 ya no se lee como suyo. Eso reemplaza al viejo «si no hay
 * lugar, al punto medio», que mandaba el número justo adentro de una tarjeta.
 *
 * Los rótulos ya colocados en esta misma pasada cuentan como obstáculo: sin
 * eso, correrlos para esquivar las tarjetas los hacía chocar entre ellos —
 * medido, cuatro pares encimados hasta un 78 %. React Flow dibuja las aristas
 * en un solo barrido y en orden, así que alcanza con ir anotándolos; el
 * registro se vacía cuando cambian las medidas de los nodos, que es lo único
 * que puede mover a todos de lugar.
 *
 * Nunca devuelve null: toda línea lleva su número, es regla del mapa.
 */
function posicionLibre(id, a, b, texto, rects) {
  if (rects !== _rectsDeLaPasada) { _colocados.clear(); _rectsDeLaPasada = rects; }
  const ancho = anchoDeTexto(texto);
  const medioAlto = ALTO_ROTULO / 2;
  const dx = b.x - a.x, dy = b.y - a.y;
  const largo = Math.hypot(dx, dy) || 1;
  const px = -dy / largo, py = dx / largo;    // normal unitaria al trayecto
  const estorban = [...rects];
  _colocados.forEach((r, k) => { if (k !== id) estorban.push(r); });

  const anotar = (x, y) => {
    _colocados.set(id, { x: x - ancho / 2, y: y - medioAlto,
                         w: ancho, h: ALTO_ROTULO });
    return { x, y };
  };

  // Cuando no queda ningún lugar limpio —y hay tres que no lo tienen: el
  // pasillo entre columnas mide 44 px y «10 pedidos» mide 59, así que el hueco
  // no existe y no lo va a crear un barrido más ancho— gana el que tape menos
  // LETRA. El chip se puede solapar por el padding sin que se pierda nada; que
  // se coma una «r» no. De ahí el peso de 100 a 1 entre una cosa y la otra.
  const anchoTexto = ancho - PADDING_ROTULO * 2;
  const medioAltoTexto = medioAlto - 2;
  let mejor = null;
  for (const t of _TES) {
    for (const off of _OFFS) {
      const x = a.x + dx * t + px * off;
      const y = a.y + dy * t + py * off;
      let chip = 0, letra = 0;
      for (const n of estorban) {
        const ix = Math.max(0, Math.min(x + ancho / 2, n.x + n.w) - Math.max(x - ancho / 2, n.x));
        if (ix <= 0) continue;
        const alto = Math.max(0, Math.min(y + medioAlto, n.y + n.h) - Math.max(y - medioAlto, n.y));
        if (alto <= 0) continue;
        chip += ix * alto;
        const jx = Math.max(0, Math.min(x + anchoTexto / 2, n.x + n.w)
                               - Math.max(x - anchoTexto / 2, n.x));
        if (jx <= 0) continue;
        letra += jx * Math.max(0, Math.min(y + medioAltoTexto, n.y + n.h)
                                  - Math.max(y - medioAltoTexto, n.y));
      }
      // Un lugar limpio gana siempre, por lejos que esté: el barrido ya va del
      // centro hacia afuera, así que el primero que aparece es el más cercano.
      if (!chip) return anotar(x, y);
      const puntaje = letra * 100 + chip + Math.abs(off) * 4;
      if (!mejor || puntaje < mejor.puntaje) mejor = { x, y, puntaje };
    }
  }
  return anotar(mejor.x, mejor.y);
}

const TIPOS_NODO = {
  operacion: NodoOperacion, marca: NodoMarca, canales: NodoCanales,
  equipo: NodoEquipo, reglas: NodoReglas, devuelve: NodoDevuelve,
};

const PESO_DE_CAPA = { centro: 1, origen: 2, destino: 2, contexto: 3 };

// React Flow frames ONCE, on mount. When the Ángela aside opens, the canvas
// loses 380 px and the right column hides. This re-frames whenever the
// container resizes — the map moves over instead of hiding.
// Los rectángulos REALES de los nodos, para que el rótulo sepa qué esquivar.
// Se miden en vez de estimarse: una zona mide ~145 px de alto, no los ~196 que
// sugiere la constante del layout, y con la estimación de más el test de
// colisión rechazaba todos los candidatos y mandaba cada rótulo al medio —
// justo lo que había que arreglar. React Flow ya los midió; acá se leen.
function MedidorDeNodos({ onCambio }) {
  const inicializados = useNodesInitialized();
  const { getNodes } = useReactFlow();
  useEffect(() => {
    if (!inicializados) return;
    // Redondeadas a propósito: `measured` trae fracciones que cambian de un
    // render a otro, y con eso la firma de abajo nunca coincidía consigo
    // misma — el lienzo entraba en un bucle de re-render y la pestaña se
    // quedaba sin responder. Al píxel alcanza y de sobra para esquivar una
    // tarjeta.
    onCambio(getNodes()
      .filter((n) => n.measured?.width)
      .map((n) => ({ x: Math.round(n.position.x), y: Math.round(n.position.y),
                     w: Math.round(n.measured.width),
                     h: Math.round(n.measured.height) })));
  }, [inicializados, getNodes, onCambio]);
  return null;
}

// =============================================================================
// LA CÁMARA DEL MAPA. Una sola, y ese es el punto.
//
// Hay TRES cosas que quieren mover el encuadre y si cada una lo hace por su
// cuenta se pelean:
//
//   · el contenedor cambia de tamaño (abrir el panel lateral le come 420 px,
//     plegar el riel se los devuelve, entrar a pantalla completa lo cambia
//     todo);
//   · alguien toca una tarjeta y hay que acercarse a ella;
//   · alguien toca «centrar» o el fondo y hay que volver a ver todo.
//
// El caso que lo hacía obvio: al tocar una tarjeta se abre el panel, el panel
// achica el lienzo, el ResizeObserver ve el cambio y hacía `fitView` de TODO —
// o sea que deshacía el acercamiento 80 ms después de hacerlo. Por eso el
// observer no reencuadra "todo": llama a `encuadrar()`, que sabe si hay una
// tarjeta enfocada y en ese caso vuelve a encuadrar ESA.
//
// `foco` es el id de la tarjeta enfocada, o null para el mapa entero.
// LOS CONTROLES, ARRIBA A LA DERECHA.
//
// Estaban abajo a la derecha porque arriba corre la barra de rótulos de capa
// (RotulosDeCapa) y se pisaban. Pero abajo nadie los busca: el lugar donde uno
// va a buscar «ver completo» y el zoom es la esquina de arriba. Así que se
// ponen arriba y DEBAJO de esa barra, que mide ~52 px — la esquina de arriba
// del lienzo propiamente dicho, sin pisar nada.
//
// Van adentro del bloque del lienzo, así que aparecen igual en pantalla
// completa: expandido es justamente donde más falta hace poder volver a ver
// todo.
function Controles({ completo, onCompleto, onCentrar, onAcercar, onAlejar, t }) {
  const boton = "grid h-8 w-8 place-items-center text-tinta-suave transition-colors hover:text-tinta";
  return (
    <div className="absolute right-3 top-[60px] z-20 flex items-center gap-1
                    rounded-full border border-linea bg-crema/95 px-1 py-1
                    shadow-sm backdrop-blur">
      <button onClick={() => onCompleto(!completo)}
              aria-label={completo ? t("mapaop.salir_completo") : t("mapaop.ver_completo")}
              className="flex h-8 items-center gap-1.5 rounded-full px-2.5 text-[0.76rem]
                         font-semibold text-tinta-suave transition-colors hover:text-tinta">
        {completo ? <Minimize2 className="size-3.5" /> : <Maximize2 className="size-3.5" />}
        {completo ? t("mapaop.salir_completo") : t("mapaop.ver_completo")}
      </button>
      <span className="h-5 w-px bg-linea" />
      <button onClick={onAlejar}
              aria-label={t("mapaop.alejar")} className={boton}>
        <Minus className="size-4" />
      </button>
      <button onClick={onAcercar}
              aria-label={t("mapaop.acercar")} className={boton}>
        <Plus className="size-4" />
      </button>
      {/* CENTRAR vuelve a ver todo DESDE DONDE SEA: suelta la tarjeta enfocada
          (por eso avisa al padre) y encuadra el mapa entero. Si sólo limpiara
          el foco, con el foco ya en null —alguien que hizo zoom a mano— no
          pasaría nada. */}
      <button onClick={onCentrar}
              aria-label={t("mapaop.centrar")} className={boton}>
        <Maximize className="size-4" />
      </button>
    </div>
  );
}

export default function MapaOperacion({ onPreguntar, onNavegar, focoInicial = null }) {
  const t = useT();
  const [d, setD] = useState(null);
  const [foco, setFoco] = useState(null);
  const [abierto, setAbierto] = useState(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [rects, setRects] = useState([]);
  // PANTALLA COMPLETA. El mapa vivia en 700px con el titulo, cuatro numeros y
  // seis chips encima: la mitad de la pantalla gastada antes de ver nada. Acá
  // el lienzo se come la ventana entera.
  const [completo, setCompleto] = useState(false);
  // El riel de hallazgos se puede plegar: con el mapa lleno, a veces lo que se
  // quiere es el mapa y nada mas.
  const [riel, setRiel] = useState(true);
  // QUE TARJETA ESTA ENFOCADA (null = el mapa entero). Tocar una tarjeta abria
  // el panel y dejaba la tarjeta donde estaba: habia que buscarla con la vista
  // para entender de que hablaba el panel. Ahora el lienzo se acerca a ella.
  // Es la unica fuente de verdad del encuadre: lo mira `encuadrar` y el
  // observer de tamanio no puede deshacer un acercamiento.
  const [nodoFoco, setNodoFoco] = useState(null);
  // LA INSTANCIA DE REACT FLOW, POR `onInit` Y NO POR `useReactFlow()`.
  //
  // Medido en el navegador contra el deploy: con el hook, `zoomIn`, `zoomOut`
  // y `fitView` no hacen absolutamente NADA —sin un solo error en consola—
  // mientras la rueda del mouse sigue zoomeando y las lecturas del store
  // (getNodes) siguen funcionando. O sea que el `panZoom` que esas tres
  // necesitan no esta en el store que ve el hook. Probado con el componente
  // como hermano de <ReactFlow> y como hijo: los dos igual de mudos, y el
  // segundo es donde vivia el `Reencuadre` anterior.
  //
  // `onInit` entrega la instancia YA inicializada, sin depender de donde este
  // montado quien la pide. Es la forma documentada y no tiene ese modo de
  // falla. De paso, la camara puede vivir acá, en el padre, que es donde ya
  // estan `nodoFoco`, `edges` y el ref del contenedor.
  const rfRef = useRef(null);
  const lienzo = useRef(null);
  // Sólo re-dibuja las aristas si las MEDIDAS cambiaron de verdad: el medidor
  // corre en cada render del lienzo y un array nuevo cada vez sería un bucle.
  const firmaRects = useRef("");
  const recibirRects = useCallback((rs) => {
    const firma = rs.map((r) => `${r.x},${r.y},${r.w},${r.h}`).join("|");
    if (firma === firmaRects.current) return;
    firmaRects.current = firma;
    setRects(rs);
  }, []);

  useEffect(() => {
    let vivo = true;
    api.mapaOperacion().then((r) => vivo && setD(r)).catch(() => vivo && setD(false));
    return () => { vivo = false; };
  }, []);

  // Escape sale de pantalla completa. Una vista que ocupa todo y no se cierra
  // con Escape es una trampa: es el primer reflejo de cualquiera.
  useEffect(() => {
    if (!completo) return;
    const salir = (e) => { if (e.key === "Escape") setCompleto(false); };
    window.addEventListener("keydown", salir);
    // el fondo no scrollea detras de la vista llena
    const antes = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", salir);
      document.body.style.overflow = antes;
    };
  }, [completo]);

  const camino = useMemo(() => {
    const h = (d?.hallazgos || []).find((x) => x.id === foco);
    return h ? { nodos: new Set(h.camino), aristas: new Set(h.aristas || []) } : null;
  }, [d, foco]);

  useEffect(() => {
    if (!d || d === false || !d.hay_datos) return;
    const todos = [...d.nodos, ...(d.nodos_contexto || [])];
    const { posiciones, logo, ctx } = disponerEnCapas(todos);

    const anchoDe = (n) => {
      if (n.capa === "contexto") return ctx[n.id]?.ancho || 300;
      if (n.capa === "origen") return ANCHO_NODO.origen;
      if (n.capa === "centro") return ANCHO_NODO.centro;
      return n.tipo === "pedido" || n.tipo === "camion"
        ? ANCHO_NODO.orden : ANCHO_NODO.salida;
    };
    const celda = {};
    todos.forEach((n) => { if (n.celda != null) celda[n.id] = n.celda; });


    const ns = todos
      .filter((n) => posiciones[n.id] && !n.es_hub)
      .map((n) => ({
        id: n.id,
        type: n.capa === "contexto" ? n.tipo : "operacion",
        position: posiciones[n.id], draggable: false,
        data: {
          ...n, ancho: anchoDe(n), peso: PESO_DE_CAPA[n.capa] || 2,
          enCamino: !!camino?.nodos.has(n.id),
          apagado: !!camino && !camino.nodos.has(n.id),
        },
      }));

    const hub = todos.find((n) => n.es_hub);
    ns.push({
      id: hub ? hub.id : "__marca", type: "marca",
      position: { x: logo.x, y: logo.y }, draggable: false,
      data: {
        lado: logo.lado, empresa: d.empresa,
        logo: d.logo,
        total: hub?.metricas?.[0]?.valor, pie: t("mapaop.marca_pie"),
      },
    });

    // RULE AGAINST PILE-UPS: several same-type edges into the same node put
    // their labels in the same corridor and stack until none reads. The
    // heaviest gets the label; the rest read on tap, where the detail lives.
    const todasAristas = [...d.aristas, ...(d.aristas_contexto || [])];
    const manda = new Set();
    const porDestino = {};
    todasAristas.forEach((a) => {
      const k = `${a.tipo}->${a.destino}`;
      const peso = a.peso ?? parseFloat(String(a.etiqueta || "").replace(/\D/g, "")) ?? 0;
      if (!porDestino[k] || peso > porDestino[k].peso) porDestino[k] = { id: a.id, peso };
    });
    Object.values(porDestino).forEach((x) => manda.add(x.id));

    const es = todasAristas.map((a) => {
      const pa = posiciones[a.origen], pb = posiciones[a.destino];
      const color = COLOR_ARISTA[a.tipo] || "#ddd9d2";
      const enCam = camino
        && (camino.aristas.has(a.id)
            || (camino.nodos.has(a.origen) && camino.nodos.has(a.destino)));
      const flojo = a.tipo === "contiene" || a.tipo === "mostrador";
      // With six corridors in the grid, six labels on top overlap. The
      // heaviest gets the label; the rest read on tap.
      const rotulable = !flojo && manda.has(a.id)
        && !(a.tipo === "corredor" && (a.peso || 0) < 12);
      // Inside the grid, lines go STRAIGHT; between columns, a soft curve.
      const [sh, th, forma] = (celda[a.origen] != null && celda[a.destino] != null)
        ? ladosDelCuadro(celda[a.origen], celda[a.destino])
        : [pa && pb ? `s-${ladoHacia(pa, pb)}` : undefined,
           pa && pb ? `t-${ladoHacia(pb, pa)}` : undefined,
           "default"];
      const muestraRotulo = (enCam || !camino) && rotulable;
      const opacidad = camino ? (enCam ? 1 : 0.06)
        : flojo ? 0.35 : a.alerta ? 0.9 : 0.55;
      return {
        id: a.id, source: a.origen, target: a.destino, type: "rotulada",
        sourceHandle: sh, targetHandle: th,
        // Sin hueco libre no hay rótulo: el número se lee tocando el nodo.
        label: muestraRotulo ? a.etiqueta : undefined,
        data: { forma, rects, alerta: !!a.alerta, opacidad },
        animated: !!a.punteada && (!camino || enCam),
        markerEnd: { type: MarkerType.ArrowClosed, color: enCam ? AZUL_IA : color,
                     width: 13, height: 13 },
        style: {
          stroke: enCam ? AZUL_IA : color,
          strokeWidth: enCam ? 2.6 : a.alerta ? 2 : flojo ? 1 : 1.4,
          strokeDasharray: a.punteada ? "5 4" : undefined,
          opacity: camino ? (enCam ? 1 : 0.06) : flojo ? 0.35 : a.alerta ? 0.9 : 0.55,
          transition: "opacity .2s ease",
        },
      };
    });
    setNodes(ns);
    setEdges(es);
  }, [d, camino, rects, setNodes, setEdges, t]);

  const abrir = useCallback((id, etiqueta) => {
    setAbierto({ id, etiqueta, cargando: true });
    api.mapaOperacionNodo(id)
      .then((r) => setAbierto({ id, etiqueta, ...r }))
      .catch(() => setAbierto({ id, etiqueta, filas: [] }));
  }, []);

  // --- LA CÁMARA -------------------------------------------------------
  //
  // POR QUÉ EL ENCUADRE SE CALCULA Y SE ANIMA ACÁ, Y NO CON `fitView`.
  //
  // Primero, una corrección sobre cómo llegué acá, porque importa para el que
  // venga después: pasé un buen rato creyendo que `fitView` y todo lo que
  // lleva `duration` estaban rotos en esta app, porque medidos contra el
  // deploy no movían un pixel. No era eso. Las animaciones de React Flow van
  // por d3-transition, que corre sobre requestAnimationFrame, y el panel del
  // navegador donde yo probaba estaba oculto a nivel compositor: rAF daba CERO
  // frames en 400 ms con `document.visibilityState === "visible"`. O sea que
  // no animaba NADA —ni la librería ni nada mío— y todo lo directo
  // (`setViewport` sin duración, la rueda del mouse) sí andaba. `fitView`
  // funciona perfectamente en una ventana de verdad.
  //
  // Dicho eso, el encuadre se queda escrito a mano por dos razones que siguen
  // valiendo:
  //
  //   · CONTROL DE LA CURVA. easeInOutCubic arranca y frena suave, que es como
  //     se mueve una cámara. Lo que hace entender que te acercaste a una parte
  //     de algo más grande es el MOVIMIENTO, no el destino.
  //   · SIEMPRE LLEGA. Si rAF no corre —una pestaña en segundo plano, una
  //     máquina que ahoga el navegador, un `prefers-reduced-motion` agresivo—
  //     igual se aplica el destino. Vale más llegar sin animación que quedarse
  //     donde estabas: eso último se lee como que el clic no hizo nada.
  const refFoco = useRef(null);
  refFoco.current = nodoFoco;
  const refAristas = useRef(edges);
  refAristas.current = edges;
  const refAnim = useRef(0);
  const refZoomPrevio = useRef(0);
  const refRed = useRef(0);
  const pane = useRef(null);

  const animarA = useCallback((destino, duracion) => {
    const rf = rfRef.current;
    if (!rf) return;
    cancelAnimationFrame(refAnim.current);
    const desde = rf.getViewport();
    if (duracion <= 0) { rf.setViewport(destino); return; }
    const t0 = performance.now();
    let vivos = 0;
    const paso = (ahora) => {
      vivos++;
      const p = Math.min(1, (ahora - t0) / duracion);
      // easeInOutCubic: arranca y frena suave, que es como se mueve una cámara
      const e = p < 0.5 ? 4 * p * p * p : 1 - ((-2 * p + 2) ** 3) / 2;
      rf.setViewport({
        x: desde.x + (destino.x - desde.x) * e,
        y: desde.y + (destino.y - desde.y) * e,
        zoom: desde.zoom + (destino.zoom - desde.zoom) * e,
      });
      if (p < 1) refAnim.current = requestAnimationFrame(paso);
    };
    refAnim.current = requestAnimationFrame(paso);
    // LA RED: si a los 120 ms no corrió un solo frame, rAF no está corriendo
    // (pestaña en segundo plano, compositor detenido) y la animación no va a
    // pasar nunca. Se salta al destino. Quedarse donde estabas se lee como que
    // el clic no hizo nada, que es peor que no tener animación.
    clearTimeout(refRed.current);
    refRed.current = setTimeout(() => {
      if (vivos === 0) { cancelAnimationFrame(refAnim.current); rf.setViewport(destino); }
    }, 120);
  }, []);

  /** El viewport que encuadra `caja` dejando `relleno` de aire alrededor. */
  const vistaDe = useCallback((caja, relleno, zoomMax) => {
    const el = pane.current;
    if (!el || !caja || caja.width <= 0) return null;
    const w = el.clientWidth, h = el.clientHeight;
    const z = Math.min(
      w / (caja.width * (1 + relleno * 2)),
      h / (caja.height * (1 + relleno * 2)),
      zoomMax,
    );
    const zz = Math.min(Math.max(z, 0.25), 1.5);   // los mismos topes del flow
    return {
      x: w / 2 - (caja.x + caja.width / 2) * zz,
      y: h / 2 - (caja.y + caja.height / 2) * zz,
      zoom: zz,
    };
  }, []);

  const encuadrar = useCallback((duracion = 620) => {
    const rf = rfRef.current;
    const el = pane.current;
    if (!rf || !el) return;
    const todos = rf.getNodes();
    if (!todos.length) return;

    // El encuadre del mapa entero sirve para dos cosas: es el destino cuando
    // no hay nada enfocado, y es el PISO de zoom cuando sí lo hay — acercarse
    // a una tarjeta nunca puede terminar alejando más que ver todo.
    const vistaTodo = vistaDe(rf.getNodesBounds(todos), 0.06, 1.5);
    const id = refFoco.current;
    if (!id || !vistaTodo) { if (vistaTodo) animarA(vistaTodo, duracion); return; }

    const nodo = todos.find((n) => n.id === id);
    if (!nodo) { animarA(vistaTodo, duracion); return; }
    const medida = (n) => [n.measured?.width || 0, n.measured?.height || 0];
    const [nw, nh] = medida(nodo);
    const cx = nodo.position.x + nw / 2;
    const cy = nodo.position.y + nh / 2;

    // LA CAJA ES SIMÉTRICA ALREDEDOR DE LA TARJETA, y eso es lo que hace que
    // la tarjeta quede EN EL CENTRO y no apenas dentro del cuadro. Encuadrar
    // el grupo «tarjeta + vecinas» tal cual la dejaba corrida hasta 183 px del
    // medio —medido—, porque el grupo casi nunca es simétrico. Acá el radio se
    // toma desde la tarjeta hacia la vecina más lejana, en cada eje.
    const vecinas = new Set([id]);
    for (const e of refAristas.current || []) {
      if (e.source === id) vecinas.add(e.target);
      else if (e.target === id) vecinas.add(e.source);
    }
    let rx = nw / 2, ry = nh / 2;
    for (const n of todos) {
      if (!vecinas.has(n.id)) continue;
      const [w, h] = medida(n);
      rx = Math.max(rx, Math.abs(n.position.x + w / 2 - cx) + w / 2);
      ry = Math.max(ry, Math.abs(n.position.y + h / 2 - cy) + h / 2);
    }
    const conVecinas = vistaDe(
      { x: cx - rx, y: cy - ry, width: rx * 2, height: ry * 2 },
      vecinas.size > 1 ? 0.1 : 0.42,
      1.3,   // el techo evita que una tarjeta chica se agrande hasta pixelarse
    );
    // EL PISO ES EL ZOOM QUE HABÍA AL TOCAR, y eso es lo que hace que tocar
    // una tarjeta SIEMPRE acerque.
    //
    // Con el piso puesto en «el mapa entero» no alcanzaba: al tocar se abre el
    // panel, el panel le come 420 px al lienzo, y el encuadre completo de ese
    // lienzo más angosto es 0,305 contra los 0,585 que se estaban viendo. O
    // sea que las tarjetas con muchas vecinas desparramadas —Cámara de frío 2,
    // Reglas de tu casa, Casa Central— terminaban MÁS CHICAS que antes del
    // clic. Medido en once tarjetas: ocho de once achicaban.
    //
    // Si las vecinas están muy repartidas para entrar a ese zoom, gana ver la
    // tarjeta grande y centrada: las de al lado se leen igual, y las lejanas
    // se siguen por la línea.
    const piso = Math.max(vistaTodo.zoom, refZoomPrevio.current || 0);
    // Y SIEMPRE AGRANDA, no sólo centra. Una tarjeta con muchas vecinas
    // desparramadas —Cámara de frío 2, Casa Central— pedía un zoom más chico
    // que el piso, así que terminaba centrada pero del mismo tamaño: el clic
    // se sentía a medias. Con el 45% de aumento mínimo siempre se ve que te
    // acercaste; las vecinas que no entren se siguen por la línea, que para
    // eso está.
    const z = Math.min(Math.max(conVecinas ? conVecinas.zoom : 0, piso * 1.45), 1.3);
    animarA({ x: el.clientWidth / 2 - cx * z, y: el.clientHeight / 2 - cy * z, zoom: z },
            duracion);
  }, [animarA, vistaDe]);

  // CENTRAR vuelve a ver todo DESDE DONDE SEA. No alcanza con soltar la
  // tarjeta enfocada: si el foco ya era null —alguien que hizo zoom con la
  // rueda— el estado no cambia, el efecto no se dispara y no pasaría nada.
  const encuadrarTodo = useCallback(() => {
    refFoco.current = null;
    refZoomPrevio.current = 0;
    encuadrar(520);
  }, [encuadrar]);

  const zoomPor = useCallback((factor) => {
    const rf = rfRef.current;
    const el = pane.current;
    if (!rf || !el) return;
    const v = rf.getViewport();
    const z = Math.min(Math.max(v.zoom * factor, 0.25), 1.5);
    // se acerca al CENTRO de lo que se está viendo, no al origen del lienzo
    const cx = el.clientWidth / 2, cy = el.clientHeight / 2;
    animarA({ x: cx - ((cx - v.x) / v.zoom) * z, y: cy - ((cy - v.y) / v.zoom) * z, zoom: z }, 200);
  }, [animarA]);

  // Hay TRES cosas que quieren mover el encuadre —el contenedor que cambia de
  // tamaño, el acercamiento a una tarjeta, y el volver a todo— y si cada una
  // lo hace por su cuenta se pelean. El caso que lo hacía obvio: tocar una
  // tarjeta abre el panel, el panel achica el lienzo, el observer ve el cambio
  // y encuadraba TODO, o sea que deshacía el acercamiento 90 ms después de
  // hacerlo. Por eso el observer no encuadra «todo»: llama a `encuadrar`, que
  // mira si hay una tarjeta enfocada y en ese caso vuelve a encuadrar ESA.
  useEffect(() => {
    const el = lienzo.current;
    if (!el || typeof ResizeObserver === "undefined") return undefined;
    let t = null;
    const ro = new ResizeObserver(() => {
      clearTimeout(t);
      t = setTimeout(() => encuadrar(260), 90);
    });
    ro.observe(el);
    return () => { ro.disconnect(); clearTimeout(t); };
  }, [encuadrar]);

  // Pantalla completa y plegar el riel cambian el ancho ÚTIL sin que el
  // contenedor observado cambie de tamaño en el mismo tick: el riel se anima
  // 200 ms, así que el observer ve el paso intermedio o no ve nada.
  useEffect(() => {
    const t = setTimeout(() => encuadrar(260), 280);
    return () => clearTimeout(t);
  }, [completo, riel, encuadrar]);

  // Y el acercamiento propiamente dicho. La PRIMERA vez no: al montar,
  // `nodoFoco` ya es null y encuadrar acá sería pelearse con el `fitView`
  // inicial de <ReactFlow>, que es lo único de esa familia que sí corre.
  const primerEncuadre = useRef(true);
  useEffect(() => {
    if (primerEncuadre.current) { primerEncuadre.current = false; return; }
    encuadrar(620);
  }, [nodoFoco, encuadrar]);

  useEffect(() => () => {
    cancelAnimationFrame(refAnim.current);
    clearTimeout(refRed.current);
  }, []);

  // Arriving from a Home card: the finding is pre-chosen. Its path lights and
  // its panel opens as soon as data lands, so the first second on the map is
  // the answer, not a search.
  useEffect(() => {
    if (!d || d === false || !focoInicial) return;
    const h = (d.hallazgos || []).find((x) => x.id === focoInicial);
    if (h) { setFoco(h.id); setAbierto({ hallazgo: h }); return; }
    // A global-search hit is a NODE id, not a finding: open its panel. The
    // logistics order is the one entity with no list screen of its own, and
    // the map is where it actually reads.
    const n = [...(d.nodos || []), ...(d.nodos_contexto || [])]
      .find((x) => x.id === focoInicial);
    if (n) abrir(n.id, n.etiqueta);
  }, [d, focoInicial, abrir]);


  if (d === null) return <Esqueleto />;
  if (d === false) return <Aviso>{t("mapaop.error_carga")}</Aviso>;
  if (!d.hay_datos) return <Aviso>{t("mapaop.sin_datos")}</Aviso>;

  // EL RIEL DE HALLAZGOS. Antes eran chips en una franja arriba del lienzo, y
  // decian LO MISMO que los cuatro numeros del encabezado: «290 bultos · nadie
  // confirmo» estaba en los dos lados, «20 pedidos sin salir» tambien, «Doña
  // Elsa 66 dias» tambien. O sea: media pantalla gastada en repetirse antes de
  // que se viera el mapa. Ahora van al costado, en columna, y funcionan como lo
  // que siempre fueron: filtros que encienden un camino del mapa.
  const hallazgos = d?.hallazgos || [];
  const rielJsx = (
    <div className={`relative z-10 flex shrink-0 flex-col border-r border-linea
                     bg-crema/70 backdrop-blur-[2px] transition-[width] duration-200
                     ${riel ? "w-[236px]" : "w-[42px]"}`}>
      <button onClick={() => setRiel((v) => !v)}
              aria-label={riel ? t("mapaop.riel_plegar") : t("mapaop.riel_abrir")}
              className="flex min-h-[40px] items-center gap-2 border-b border-linea
                         px-3 text-left text-[0.66rem] font-semibold uppercase
                         tracking-[0.12em] text-tinta-suave hover:text-tinta">
        {riel ? <PanelLeftClose className="size-3.5 shrink-0" />
              : <PanelLeftOpen className="size-3.5 shrink-0" />}
        {riel && <span className="truncate">{t("mapaop.riel_titulo")}</span>}
      </button>
      {riel && (
        <div className="flex-1 space-y-1.5 overflow-y-auto p-2.5">
          {hallazgos.map((h) => {
            const on = foco === h.id;
            const rojo = h.gravedad === "alta";
            return (
              <button
                key={h.id}
                onClick={() => { setFoco(on ? null : h.id); setAbierto(on ? null : { hallazgo: h }); }}
                className={`flex w-full items-start gap-2 rounded-xl border px-2.5 py-2
                            text-left text-[0.76rem] leading-snug transition ${on
                    ? "border-violeta bg-violeta-suave font-semibold text-violeta"
                    : rojo ? "border-rojo/30 bg-rojo/[0.04] text-tinta hover:border-rojo/60"
                           : "border-linea bg-papel text-tinta-suave hover:border-oro/50"}`}
              >
                <span className={`mt-[5px] h-1.5 w-1.5 shrink-0 rounded-full ${
                  on ? "bg-violeta" : rojo ? "bg-rojo" : "bg-oro"}`} />
                <span className="min-w-0">{h.chip || h.titulo}</span>
              </button>
            );
          })}
          {!hallazgos.length && (
            <p className="px-1 py-2 text-[0.74rem] leading-snug text-tinta-suave">
              {t("mapaop.riel_vacio")}
            </p>
          )}
        </div>
      )}
      {riel && <div className="border-t border-linea p-2.5"><Leyenda /></div>}
    </div>
  );

  const encabezado = (
    <header className="flex flex-wrap items-end justify-between gap-x-8 gap-y-3">
      <div>
        <h1 className="font-display text-[1.7rem] font-bold leading-tight">
          {t("mapaop.titulo")}
        </h1>
        <p className="mt-1 text-[0.86rem] text-tinta-suave">{t("mapaop.sub")}</p>
      </div>
      {/* LOS NUMEROS, SIN EL PIE. El pie («4 pedidos salieron y nadie avisó»)
          era palabra por palabra el chip del riel. Un numero y que dice: el
          detalle esta a un clic, al costado. */}
      <div className="flex flex-wrap items-start gap-x-8 gap-y-3">
        {(d.resumen?.titulares || []).map((x) => (
          <div key={x.label} className="min-w-[96px]">
            <p className="text-[0.58rem] font-semibold uppercase tracking-[0.14em]
                          text-tinta-suave">{x.label}</p>
            <p className={`font-display text-[1.5rem] font-bold leading-none tabular-nums ${
              x.estado === "error" ? "text-rojo"
              : x.estado === "dudoso" ? "text-oro-tinta" : "text-tinta"}`}>
              {x.valor}
            </p>
          </div>
        ))}
      </div>
    </header>
  );

  const lienzoBloque = (
    <div ref={lienzo}
         style={{ paddingRight: abierto ? ANCHO_PANEL : 0, transition: "none" }}
         className={`relative flex overflow-hidden border border-linea bg-papel
                     ${completo ? "min-h-0 flex-1 rounded-xl" : "h-[700px] rounded-2xl"}`}>
      {rielJsx}
      <div ref={pane} className="relative min-w-0 flex-1">
        <RotulosDeCapa capas={d.capas} />
        <ReactFlowProvider>
        <ReactFlow
          nodes={nodes} edges={edges}
          onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
          nodeTypes={TIPOS_NODO} edgeTypes={TIPOS_ARISTA}
          fitView fitViewOptions={{ padding: 0.06 }}
          minZoom={0.25} maxZoom={1.5}
          nodesConnectable={false} edgesFocusable={false} zoomOnDoubleClick={false}
          proOptions={{ hideAttribution: true }}
          onInit={(inst) => { rfRef.current = inst; }}
          onNodeClick={(e, n) => {
            // A channel chip opens ITS detail, not the whole block's.
            const chip = e.target?.closest?.("[data-chip]")?.dataset?.chip;
            abrir(chip ? `${n.id}:${chip}` : n.id, n.data.etiqueta);
            // y el lienzo se acerca a ella. El panel dice QUE pasa; el
            // acercamiento dice DONDE, que es la mitad de la respuesta en un
            // mapa. Se enfoca la tarjeta, no el chip: el chip es un detalle
            // adentro de la misma tarjeta.
            // el zoom de ANTES del clic, que es el piso del acercamiento
            refZoomPrevio.current = rfRef.current?.getViewport?.().zoom || 0;
            setNodoFoco(n.id);
          }}
          // TOCAR EL FONDO ES VOLVER. Cierra el panel y suelta la tarjeta, y
          // al soltarla la Camara encuadra el mapa entero.
          onPaneClick={() => { setAbierto(null); setNodoFoco(null); refZoomPrevio.current = 0; }}
        >
          <Background gap={24} size={1} color="#eceae5" />
          <MedidorDeNodos onCambio={recibirRects} />
        </ReactFlow>
        <Controles completo={completo} onCompleto={setCompleto}
                   onAcercar={() => zoomPor(1.25)}
                   onAlejar={() => zoomPor(1 / 1.25)}
                   onCentrar={() => { setAbierto(null); setNodoFoco(null); encuadrarTodo(); }}
                   t={t} />
        </ReactFlowProvider>
      </div>

      {abierto && (
        <Panel p={abierto} onCerrar={() => { setAbierto(null); setNodoFoco(null); }}
               onPreguntar={onPreguntar} onNavegar={onNavegar} />
      )}
    </div>
  );

  if (completo) {
    // en un portal al body: cualquier `overflow` o `transform` de un ancestro
    // recorta un `fixed`, y esta pantalla se abre desde adentro de la seccion.
    return createPortal(
      <div className="fixed inset-0 z-[60] flex flex-col gap-2 bg-crema p-3">
        {lienzoBloque}
      </div>,
      document.body,
    );
  }

  return (
    <div className="space-y-3">
      {encabezado}
      {lienzoBloque}
    </div>
  );
}

// --- column labels, anchored to the canvas's real x positions ---------------
function RotulosDeCapa({ capas }) {
  const anclas = [
    { id: "origen", izq: 0, ancho: 22 },
    { id: "centro", izq: 26, ancho: 40 },
    { id: "destino", izq: 70, ancho: 30 },
  ];
  return (
    <div className="pointer-events-none absolute inset-x-0 top-0 z-10 border-b
                    border-linea bg-papel/90 px-6 py-2.5 backdrop-blur-sm">
      <div className="relative h-8">
        {anclas.map((a) => {
          const c = capas.find((x) => x.id === a.id);
          return (
            <div key={a.id} className="absolute top-0"
                 style={{ left: `${a.izq}%`, width: `${a.ancho}%` }}>
              <p className="truncate text-[0.6rem] font-semibold uppercase
                            tracking-[0.16em] text-tinta-suave">{c?.titulo || a.id}</p>
              <p className="truncate text-[0.66rem] text-tinta-suave/70">{c?.detalle}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Leyenda() {
  const t = useT();
  const items = [
    { c: GRAFICO.hielo, k: "mapaop.ley_traslados" },
    { c: GRAFICO.rojo, k: "mapaop.ley_transito", p: true },
    { c: AMBAR, k: "mapaop.ley_info", p: true },
    { c: GRAFICO.salvia, k: "mapaop.ley_vuelve" },
    { c: AZUL_IA, k: "mapaop.ley_camino" },
  ];
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[0.66rem] text-tinta-suave">
      {items.map((i) => (
        <span key={i.k} className="flex items-center gap-1.5">
          <svg width="18" height="4" aria-hidden>
            <line x1="0" y1="2" x2="18" y2="2" stroke={i.c} strokeWidth="2"
                  strokeDasharray={i.p ? "5 3" : undefined} />
          </svg>
          {t(i.k)}
        </span>
      ))}
      <span className="flex items-center gap-1.5 text-tinta-suave/80">
        <Eye size={12} /> {t("mapaop.ley_toca")}
      </span>
    </div>
  );
}

const ANCHO_PANEL = 420;

function Panel({ p, onCerrar, onPreguntar, onNavegar }) {
  const t = useT();
  // Whoever taps the card already knows how many lots there are: it is
  // written on it. They want WHY it is red and WHAT TO DO. Hence the order:
  // what is going on → where it came from → what can be done → and only at
  // the bottom, folded, the listing. The listing is the last resort.
  const h = p.hallazgo;
  // For a finding, the short chip is the title and the long sentence is the
  // «what is going on»: same reading order as a node's panel.
  const titulo = h ? (h.chip || h.titulo) : (p.titulo || p.etiqueta);
  const quePasa = h ? [h.titulo].filter(Boolean) : (p.que_pasa || []);
  const deDonde = h
    ? (h.detalle || []).map((x) => ({ tipo: "hecho", texto: x }))
    : (p.de_donde || []);
  // Same verbs the backend composes in `_que_hacer`: a finding's panel
  // (which arrives pre-built from the chip, without /nodo) must say the same
  // as a node's. Copy of a string, not a computation.
  const verbo = h
    ? (t(`mapaop.verbo_${h.accion.tipo}`) !== `mapaop.verbo_${h.accion.tipo}`
        ? t(`mapaop.verbo_${h.accion.tipo}`)
        : h.accion.tipo.replace(/_/g, " "))
    : null;
  const queHacer = h
    ? { propuesta: h.alternativa, accion: h.accion,
        boton: t("mapaop.boton_preparar", { verbo, numero: h.accion.numero }),
        pregunta: t("mapaop.pregunta_preparar", { verbo, numero: h.accion.numero }) }
    : p.que_hacer;
  const listado = p.listado;
  const fuente = h ? h.fuentes?.[0] : p.fuente;
  const pregunta = h
    ? t("mapaop.pregunta_hallazgo", { nombre: h.chip || h.titulo })
    : p.pregunta;
  const [verListado, setVerListado] = useState(false);
  const tono = TONO[p.estado] || TONO.neutro;

  // How each data section is called for a person. The source is cited, but
  // at the foot and in the user's language — not «41 rows of deposito» above
  // the title.
  const apartado = (id) => {
    const key = `mapaop.apartado_${id}`;
    const v = t(key);
    return v === key ? String(id).replace(/_/g, " ") : v;
  };

  return (
    <aside className="absolute inset-y-0 right-0 z-20 flex w-[420px] max-w-full flex-col
                      border-l border-linea bg-crema shadow-2xl">
      <header className="flex items-start justify-between gap-2 border-b border-linea px-5 py-3.5">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            {p.estado && p.estado !== "neutro" && (
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: tono.borde }} />
            )}
            <p className="font-display text-[1.02rem] font-semibold leading-snug">{titulo}</p>
          </div>
        </div>
        <button onClick={onCerrar} aria-label={t("mapaop.cerrar")}
                className="grid h-9 w-9 shrink-0 place-items-center rounded-lg
                           text-tinta-suave transition hover:bg-papel-hondo">
          <X size={16} />
        </button>
      </header>

      <div className="min-h-0 flex-1 overflow-auto px-5 py-4">
        {p.cargando && <p className="text-sm text-tinta-suave">{t("mapaop.buscando")}</p>}

        {/* 1 · WHAT IS GOING ON — two or three sentences, numbers inside. */}
        {quePasa.length > 0 && (
          <section>
            <Rotulo>{t("mapaop.rot_que_pasa")}</Rotulo>
            <div className="space-y-1.5">
              {quePasa.map((q, i) => (
                <p key={i} className={`leading-snug ${i === 0
                  ? "text-[0.98rem] font-semibold text-tinta" : "text-[0.88rem] text-tinta"}`}>
                  {q}
                </p>
              ))}
            </div>
          </section>
        )}

        {/* 2 · WHERE IT CAME FROM — the heads-ups with who and when, the
            order, the rule. */}
        {deDonde.length > 0 && (
          <section className="mt-5">
            <Rotulo>{t("mapaop.rot_de_donde")}</Rotulo>
            <ul className="space-y-2">
              {deDonde.map((x, i) => (
                <li key={i} className={`rounded-lg border-l-2 px-3 py-2 text-[0.82rem] ${
                  x.tipo === "aviso" ? "border-oro bg-oro/[0.06]"
                  : x.tipo === "regla" ? "border-oro bg-oro/[0.06] italic"
                  : x.tipo === "orden" ? "border-hielo bg-hielo-claro/60"
                  : "border-linea bg-papel-hondo/50"}`}>
                  {x.titulo && (
                    <p className="text-[0.7rem] font-semibold uppercase tracking-wide text-tinta-suave">
                      {x.titulo}
                    </p>
                  )}
                  <p className="leading-snug text-tinta">{x.tipo === "regla" ? `«${x.texto}»` : x.texto}</p>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* 3 · WHAT CAN BE DONE — the proposal, and the button. Nothing is
            applied here: it is asked of Ángela through the usual rail,
            propose → approve → write back. A button that touched an order on
            its own would be exactly what the product promises not to do. */}
        {queHacer && (queHacer.propuesta || queHacer.pregunta) && (
          <section className="mt-5">
            <Rotulo>{t("mapaop.rot_que_hacer")}</Rotulo>
            <div className="rounded-xl border border-violeta/25 bg-violeta-suave/60 p-3.5">
              <div className="flex items-start gap-2.5">
                <AngelaMark size={22} />
                <div className="min-w-0 flex-1">
                  {/* Design rule #1: a panel that ends in "nothing to do here"
                      is a report, and a report is an unfinished process. The
                      healthy state is stated as a FACT, and the exit — go see
                      the data where it lives — sits right underneath. */}
                  <p className={`leading-snug ${queHacer.propuesta
                      ? "text-[0.88rem] text-tinta" : "text-[0.84rem] text-tinta-suave"}`}>
                    {queHacer.propuesta || t("mapaop.sin_frenos")}
                  </p>
                </div>
              </div>
              {queHacer.accion && onPreguntar && (
                <button onClick={() => onPreguntar(queHacer.pregunta)}
                        className="mt-3 flex min-h-[44px] w-full items-center justify-center
                                   gap-2 rounded-lg bg-violeta px-3 text-[0.84rem] font-semibold
                                   text-crema transition hover:brightness-110">
                  <Check size={15} /> {queHacer.boton}
                </button>
              )}
              {p.ver && onNavegar && (
                <button onClick={() => onNavegar(p.ver.seccion, p.ver.foco || null)}
                        className={`flex min-h-[44px] w-full items-center justify-center gap-2
                                    rounded-lg border border-violeta/35 px-3 text-[0.84rem]
                                    font-semibold text-violeta transition hover:bg-violeta-suave
                                    ${queHacer.accion && onPreguntar ? "mt-2" : "mt-3"}`}>
                  {p.ver.label} <ArrowRight size={15} />
                </button>
              )}
            </div>
          </section>
        )}

        {/* 4 · AND ONLY DOWN HERE, FOLDED, THE LISTING. */}
        {listado && listado.filas?.length > 0 && (
          <section className="mt-5">
            <button onClick={() => setVerListado((v) => !v)}
                    className="flex min-h-[40px] w-full items-center justify-between rounded-lg
                               border border-linea px-3 text-[0.82rem] font-medium text-tinta-suave
                               transition hover:text-tinta">
              <span>
                {verListado ? t("mapaop.ocultar") : t("mapaop.ver")}{" "}
                {listado.titulo.toLowerCase()} · {listado.filas.length}
              </span>
              {verListado ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
            </button>
            {verListado && <Listado filas={listado.filas} />}
          </section>
        )}
        {!h && !quePasa.length && !p.cargando && (!listado || !listado.filas?.length) && (
          <p className="text-sm text-tinta-suave">{t("mapaop.sin_detalle")}</p>
        )}

        {/* The source citation, at the foot: it can be opened, but it is not
            the first thing read. */}
        {fuente && !p.cargando && (
          <p className="mt-5 text-[0.68rem] text-tinta-suave/80">
            {t("mapaop.fuente")} {apartado(fuente.apartado)}
            {fuente.filas != null && ` · ${fuente.filas} ${t("mapaop.filas")}`}
          </p>
        )}
      </div>

      {/* Ángela lives in the panel: the mark, and the question about THIS node. */}
      {onPreguntar && pregunta && (
        <footer className="border-t border-linea p-3">
          <button onClick={() => onPreguntar(pregunta)}
                  className="flex min-h-[44px] w-full items-center gap-2.5 rounded-lg border
                             border-violeta/30 px-3 text-left text-[0.84rem] text-violeta
                             transition hover:bg-violeta-suave">
            <AngelaMark size={20} />
            <span className="min-w-0 flex-1 truncate">{pregunta}</span>
            <Sparkles size={14} className="shrink-0" />
          </button>
        </footer>
      )}
    </aside>
  );
}

function Rotulo({ children }) {
  return (
    <p className="mb-2 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-tinta-suave">
      {children}
    </p>
  );
}

function Listado({ filas }) {
  const cols = filas.length ? Object.keys(filas[0]).filter((k) => k !== "items") : [];
  return (
    <div className="mt-2">
      {filas.map((f, i) => (
        <div key={i} className="border-b border-linea/60 py-2 last:border-0">
          <div className="flex flex-wrap items-baseline justify-between gap-x-3 text-[0.8rem]">
            {cols.map((c) => (
              <span key={c} className={c === cols[0] ? "font-semibold" : "text-tinta-suave"}>
                {String(f[c] ?? "—")}
              </span>
            ))}
          </div>
          {f.items?.length > 0 && (
            <ul className="mt-1 space-y-0.5 pl-3 text-[0.74rem] text-tinta-suave">
              {f.items.map((it, j) => (
                <li key={j} className="flex justify-between gap-2">
                  <span className="truncate">{it.bultos} × {it.producto}</span>
                  <span className="shrink-0">{it.zona}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}

function Aviso({ children }) {
  return <p className="rounded-xl border border-linea bg-crema p-5 text-tinta-suave">{children}</p>;
}

function Esqueleto() {
  return (
    <div className="space-y-5">
      <div className="h-10 w-80 animate-pulse rounded bg-papel-hondo" />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-[76px] animate-pulse rounded-xl bg-papel-hondo" />
        ))}
      </div>
      <div className="h-[700px] animate-pulse rounded-2xl bg-papel-hondo" />
    </div>
  );
}
