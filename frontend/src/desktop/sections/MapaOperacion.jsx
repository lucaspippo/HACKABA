import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ReactFlow, ReactFlowProvider, Background, Handle, Position, MarkerType,
  useNodesState, useEdgesState, useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  Snowflake, Warehouse, Truck, Store, Users, Building2, FileText, PackageCheck,
  ChevronDown, ChevronRight, X, Package,
  Mic, MessageSquare, ClipboardList, Camera, Database, BookOpen, Eye, Check,
  Mail, Sparkles,
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
function IconoWhatsApp({ size = 12 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="#25D366" aria-hidden>
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
      <div className="mt-2 flex flex-wrap gap-1.5">
        {(data.chips || []).map((c) => {
          const I = ICONO_CANAL[c.id] || ClipboardList;
          const marca = c.id === "whatsapp";
          return (
            <span key={c.id}
                  className={`flex cursor-pointer items-center gap-1.5 rounded-full border
                              bg-crema px-2.5 py-1 text-[0.72rem] transition
                              hover:border-oro ${c.de_afuera
                      ? "border-oro/45 font-medium text-tinta" : "border-linea text-tinta-suave"}`}
                  data-chip={c.id}>
              {/* The brand glyph keeps its color; generic ones go amber. */}
              <I size={12} className="shrink-0"
                 style={marca ? undefined : { color: c.de_afuera ? AMBAR : "#8d887f" }}
                 data-chip={c.id} />
              <span data-chip={c.id}>{c.nombre}</span>
              <strong className="tabular-nums" data-chip={c.id}>{c.total}</strong>
            </span>
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

const TIPOS_NODO = {
  operacion: NodoOperacion, marca: NodoMarca, canales: NodoCanales,
  equipo: NodoEquipo, reglas: NodoReglas, devuelve: NodoDevuelve,
};

const PESO_DE_CAPA = { centro: 1, origen: 2, destino: 2, contexto: 3 };

// React Flow frames ONCE, on mount. When the Ángela aside opens, the canvas
// loses 380 px and the right column hides. This re-frames whenever the
// container resizes — the map moves over instead of hiding.
function Reencuadre({ contenedor }) {
  const rf = useReactFlow();
  useEffect(() => {
    const el = contenedor.current;
    if (!el || typeof ResizeObserver === "undefined") return undefined;
    let t = null;
    const ro = new ResizeObserver(() => {
      clearTimeout(t);
      t = setTimeout(() => rf.fitView({ padding: 0.06, duration: 220 }), 80);
    });
    ro.observe(el);
    return () => { ro.disconnect(); clearTimeout(t); };
  }, [contenedor, rf]);
  return null;
}

// ---------------------------------------------------------------------------
export default function MapaOperacion({ onPreguntar, focoInicial = null }) {
  const t = useT();
  const [d, setD] = useState(null);
  const [foco, setFoco] = useState(null);
  const [abierto, setAbierto] = useState(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const lienzo = useRef(null);

  useEffect(() => {
    let vivo = true;
    api.mapaOperacion().then((r) => vivo && setD(r)).catch(() => vivo && setD(false));
    return () => { vivo = false; };
  }, []);

  // Arriving from a Home card: the finding is pre-chosen. Its path lights and
  // its panel opens as soon as data lands, so the first second on the map is
  // the answer, not a search.
  useEffect(() => {
    if (!d || d === false || !focoInicial) return;
    const h = (d.hallazgos || []).find((x) => x.id === focoInicial);
    if (h) { setFoco(h.id); setAbierto({ hallazgo: h }); }
  }, [d, focoInicial]);

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
      return {
        id: a.id, source: a.origen, target: a.destino, type: forma,
        sourceHandle: sh, targetHandle: th,
        label: (enCam || !camino) && rotulable ? a.etiqueta : undefined,
        labelStyle: { fontSize: 10, fontWeight: 500,
                      fill: a.alerta ? GRAFICO.rojo : GRAFICO.tintaSuave },
        labelBgStyle: { fill: "#fbfbfa", fillOpacity: 0.92 },
        labelBgPadding: [4, 2], labelBgBorderRadius: 4,
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
  }, [d, camino, setNodes, setEdges, t]);

  const abrir = useCallback((id, etiqueta) => {
    setAbierto({ id, etiqueta, cargando: true });
    api.mapaOperacionNodo(id)
      .then((r) => setAbierto({ id, etiqueta, ...r }))
      .catch(() => setAbierto({ id, etiqueta, filas: [] }));
  }, []);

  if (d === null) return <Esqueleto />;
  if (d === false) return <Aviso>{t("mapaop.error_carga")}</Aviso>;
  if (!d.hay_datos) return <Aviso>{t("mapaop.sin_datos")}</Aviso>;

  return (
    <div className="space-y-4">
      {/* Title and numbers on the SAME line: four cards under the title made
          you scroll before reaching the map. */}
      <header className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div>
          <h1 className="font-display text-[1.7rem] font-bold leading-tight">
            {t("mapaop.titulo")}
          </h1>
          <p className="mt-1 text-[0.86rem] text-tinta-suave">
            {t("mapaop.sub")}
          </p>
        </div>
        {/* THE FOUR NUMBERS IMPLY AN ACTION. «380 lots in the warehouse» is
            inventory: it lives on the brand at the center, where it belongs. */}
        <div className="flex flex-wrap items-start gap-x-9 gap-y-3">
          {(d.resumen?.titulares || []).map((x) => (
            <div key={x.label} className="min-w-[104px]">
              <p className="text-[0.58rem] font-semibold uppercase tracking-[0.14em]
                            text-tinta-suave">{x.label}</p>
              <p className={`font-display text-[1.6rem] font-bold leading-none tabular-nums ${
                x.estado === "error" ? "text-rojo"
                : x.estado === "dudoso" ? "text-oro-tinta" : "text-tinta"}`}>
                {x.valor}
              </p>
              {x.pie && (
                <p className="mt-0.5 text-[0.62rem] leading-tight text-tinta-suave/80">
                  {x.pie}
                </p>
              )}
            </div>
          ))}
        </div>
      </header>

      {/* Findings as chips: six fit in two lines and each one is a door. */}
      <div className="flex flex-wrap gap-2">
        {(d.hallazgos || []).map((h) => {
          const on = foco === h.id;
          const rojo = h.gravedad === "alta";
          return (
            <button
              key={h.id}
              onClick={() => { setFoco(on ? null : h.id); setAbierto(on ? null : { hallazgo: h }); }}
              className={`flex min-h-[34px] items-center gap-1.5 rounded-full border
                          px-3 text-[0.78rem] transition ${on
                  ? "border-violeta bg-violeta-suave font-semibold text-violeta"
                  : rojo ? "border-rojo/30 bg-rojo/[0.04] text-tinta hover:border-rojo/60"
                         : "border-linea bg-crema text-tinta-suave hover:border-oro/50"}`}
            >
              <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                on ? "bg-violeta" : rojo ? "bg-rojo" : "bg-oro"}`} />
              {h.chip || h.titulo}
            </button>
          );
        })}
      </div>

      <Leyenda />

      {/* With the panel open the canvas CEDES the 420 px instead of getting
          covered: the padding shrinks the content-box, Reencuadre's observer
          sees it and re-frames. The padding snaps with NO transition: with
          one, the observer fired mid-way and fitView framed an intermediate
          width. What animates is the re-frame (220 ms). */}
      <div ref={lienzo}
           style={{ paddingRight: abierto ? ANCHO_PANEL : 0, transition: "none" }}
           className="relative h-[700px] overflow-hidden rounded-2xl border border-linea
                      bg-papel">
        <RotulosDeCapa capas={d.capas} />
        <ReactFlowProvider>
        <ReactFlow
          nodes={nodes} edges={edges}
          onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
          nodeTypes={TIPOS_NODO}
          fitView fitViewOptions={{ padding: 0.06 }}
          minZoom={0.25} maxZoom={1.5}
          nodesConnectable={false} edgesFocusable={false} zoomOnDoubleClick={false}
          proOptions={{ hideAttribution: true }}
          onNodeClick={(e, n) => {
            // A channel chip opens ITS detail, not the whole block's.
            const chip = e.target?.closest?.("[data-chip]")?.dataset?.chip;
            abrir(chip ? `${n.id}:${chip}` : n.id, n.data.etiqueta);
          }}
        >
          <Background gap={24} size={1} color="#eceae5" />
          <Reencuadre contenedor={lienzo} />
        </ReactFlow>
        </ReactFlowProvider>

        {abierto && (
          <Panel p={abierto} onCerrar={() => setAbierto(null)} onPreguntar={onPreguntar} />
        )}
      </div>
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

function Panel({ p, onCerrar, onPreguntar }) {
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
                  {queHacer.propuesta ? (
                    <p className="text-[0.88rem] leading-snug text-tinta">{queHacer.propuesta}</p>
                  ) : (
                    <p className="text-[0.84rem] leading-snug text-tinta-suave">
                      {t("mapaop.nada_frenado")}
                    </p>
                  )}
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
