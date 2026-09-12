// LA ESCENA DEL RECLAMO — ocho nodos, colocados, en SVG.
//
// POR QUÉ SVG Y NO EL LIENZO DE FUERZAS.
//
// El cerebro (CerebroNegocio.jsx) dibuja 605 entidades en canvas con un layout
// de fuerzas, y para eso está bien. Esta escena son OCHO nodos con posiciones
// decididas, texto adentro de las formas, curvas con flecha y etiquetas que no
// se pueden pisar. Todo eso en canvas es pelearse con el motor; en SVG es lo
// que el formato hace de fábrica:
//
//   · el texto es texto — nítido a cualquier zoom, y en un proyector eso se ve
//   · las etiquetas se posicionan y se quedan quietas
//   · el trazo que CRECE de origen a destino es `stroke-dashoffset`, dos líneas
//   · escala sola con viewBox: igual en un monitor que en una pantalla grande
//
// El backend manda las coordenadas ya resueltas (core/escena.py) porque la
// posición es una decisión de producto —se lee como una frase de izquierda a
// derecha— y no algo que deba recalcular el navegador.
import { useEffect, useMemo, useState } from "react";

// --- el lenguaje visual, el mismo del cerebro -------------------------------
const TINTA = "#0f1113";          // el fondo
const AZUL_IA = "#4d7bf0";        // Ángela, y sólo Ángela
const AMARILLO = "#e8c86a";       // lo que dijo una persona
const AMARILLO_CLARO = "#f2d98c"; // la persona
const HIELO = "#4aa8bf";          // el producto
const OCRE = "#c98a3c";           // el proveedor
const PAPEL = "#d7cfc0";          // el documento
const VERDE_WA = "#25D366";       // SÓLO en la insignia del canal

// Cuánto dura cada tramo del trazado, en ms. Seis aristas ≈ 3,6 s.
const MS_POR_ARISTA = 600;

// =============================================================================
// Las formas. Cada tipo tiene la suya y se reconoce sin leer.
// =============================================================================

function Persona({ n, encendido }) {
  const r = 38;   // ⌀76
  return (
    <g opacity={encendido ? 1 : 0.22}>
      <circle cx={n.x} cy={n.y} r={r} fill={AMARILLO_CLARO} />
      <circle cx={n.x} cy={n.y} r={r} fill="none" stroke="rgba(15,17,19,.35)" strokeWidth="1.5" />
      {/* cabeza y hombros: la silueta que se lee a cualquier tamaño */}
      <circle cx={n.x} cy={n.y - 8} r={11} fill={TINTA} opacity=".78" />
      <path d={`M ${n.x - 19} ${n.y + 22} Q ${n.x} ${n.y + 1} ${n.x + 19} ${n.y + 22} Z`}
            fill={TINTA} opacity=".78" />
      <text x={n.x} y={n.y + r + 22} textAnchor="middle"
            fill="#f5f5f4" fontSize="17" fontWeight="600">{n.nombre}</text>
      {n.rol && (
        <text x={n.x} y={n.y + r + 39} textAnchor="middle"
              fill="rgba(245,245,244,.55)" fontSize="12">{n.rol}</text>
      )}
    </g>
  );
}

// La insignia del canal: el ÚNICO lugar del lienzo con color de marca ajeno.
// Confinada a un disco de 26 px pegado al post-it — nunca el cuerpo del nodo,
// nunca una arista, para que el azul se siga leyendo como Ángela (DESIGN.md).
function InsigniaCanal({ x, y, canal }) {
  const fondo = canal === "whatsapp" ? VERDE_WA : "#f4f1ea";
  return (
    <g>
      <circle cx={x} cy={y} r={15} fill={fondo} stroke={TINTA} strokeWidth="2" />
      <g stroke={canal === "whatsapp" ? "#fff" : TINTA} strokeWidth="1.7"
         fill="none" strokeLinecap="round" strokeLinejoin="round">
        {canal === "whatsapp" ? (
          <>
            {/* la burbuja con su cola, y el tubo adentro */}
            <path d={`M ${x + 7} ${y - 1} a 7.5 7.5 0 1 0 -3.2 5.9 L ${x - 8} ${y + 7.5} l 1.6 -4.6`}
                  fill="none" />
            <path d={`M ${x - 2.6} ${y - 2.8} q 1.8 1.8 2.6 2.7 q 1 1 2.8 2.5`} />
          </>
        ) : (
          <>
            {/* el sobre, con la solapa en V */}
            <rect x={x - 8} y={y - 5.5} width="16" height="11" rx="1.4" />
            <path d={`M ${x - 8} ${y - 5.5} L ${x} ${y + 1.4} L ${x + 8} ${y - 5.5}`} />
          </>
        )}
      </g>
    </g>
  );
}

function Nota({ n, encendido }) {
  const w = 172, h = 118, dobl = 22;
  const x = n.x - w / 2, y = n.y - h / 2;
  return (
    <g opacity={encendido ? 1 : 0.22}>
      {/* post-it con la esquina doblada. El borde DISCONTINUO dice que entró
          de afuera del sistema: es la lectura de un vistazo. */}
      <path d={`M ${x} ${y} H ${x + w} V ${y + h - dobl} L ${x + w - dobl} ${y + h} H ${x} Z`}
            fill={AMARILLO} />
      <path d={`M ${x} ${y} H ${x + w} V ${y + h - dobl} L ${x + w - dobl} ${y + h} H ${x} Z`}
            fill="none" stroke={TINTA} strokeWidth="2.4" strokeDasharray="7 5" />
      <path d={`M ${x + w} ${y + h - dobl} L ${x + w - dobl} ${y + h - dobl} L ${x + w - dobl} ${y + h}`}
            fill="none" stroke="rgba(15,17,19,.35)" strokeWidth="1.6" />
      {/* el texto ADENTRO: con ocho nodos hay lugar, y leerlo en el nodo es
          mucho mejor que una etiqueta flotando al lado */}
      <foreignObject x={x + 11} y={y + 13} width={w - 36} height={h - 26}>
        <div xmlns="http://www.w3.org/1999/xhtml"
             style={{ font: "600 13px/1.3 'Hanken Grotesk',system-ui,sans-serif",
                      color: "#1a1a18" }}>
          «{n.texto}»
        </div>
      </foreignObject>
      <InsigniaCanal x={x + w - 6} y={y + 6} canal={n.canal} />
      <text x={n.x} y={y + h + 19} textAnchor="middle"
            fill="rgba(245,245,244,.6)" fontSize="12">
        {n.autor} · {(n.fecha || "").slice(5)}
      </text>
    </g>
  );
}

function Producto({ n, encendido }) {
  const r = 32;   // ⌀64
  return (
    <g opacity={encendido ? 1 : 0.22}>
      <circle cx={n.x} cy={n.y} r={r} fill={HIELO} />
      <circle cx={n.x} cy={n.y} r={r} fill="none" stroke="rgba(15,17,19,.4)" strokeWidth="1.5" />
      {/* dos renglones: el nombre completo de un producto no entra en uno, y
          cortarlo a tres palabras dejaba «LECHE ENTERA CAMPO» */}
      {partirEnDos(n.nombre).map((linea, i) => (
        <text key={i} x={n.x} y={n.y + r + 20 + i * 17} textAnchor="middle"
              fill="#f5f5f4" fontSize="14" fontWeight="600">{linea}</text>
      ))}
      {n.lote && (
        <text x={n.x} y={n.y + r + 56} textAnchor="middle"
              fill="rgba(245,245,244,.5)" fontSize="11.5">lote {n.lote}</text>
      )}
    </g>
  );
}

function Proveedor({ n, encendido }) {
  const r = 36;   // ⌀72
  const apag = n.apagado;
  return (
    <g opacity={encendido ? (apag ? 0.5 : 1) : 0.22}>
      <path d={`M ${n.x} ${n.y - r} L ${n.x + r} ${n.y} L ${n.x} ${n.y + r} L ${n.x - r} ${n.y} Z`}
            fill={apag ? "#8a7a63" : OCRE} />
      <path d={`M ${n.x} ${n.y - r} L ${n.x + r} ${n.y} L ${n.x} ${n.y + r} L ${n.x - r} ${n.y} Z`}
            fill="none" stroke="rgba(15,17,19,.4)" strokeWidth="1.5" />
      <text x={n.x} y={n.y + r + 21} textAnchor="middle"
            fill={apag ? "rgba(245,245,244,.6)" : "#f5f5f4"}
            fontSize="15" fontWeight="600">{n.nombre}</text>
    </g>
  );
}

function Regla({ n, encendido }) {
  const w = 170, h = 80, pl = 18;
  const x = n.x - w / 2, y = n.y - h / 2;
  const apag = n.apagado;
  return (
    <g opacity={encendido ? (apag ? 0.5 : 1) : 0.22}>
      {/* tarjeta con la esquina superior izquierda plegada: es una hoja que
          alguien escribió, no un registro del sistema */}
      <path d={`M ${x + pl} ${y} H ${x + w} V ${y + h} H ${x} V ${y + pl} Z`}
            fill={apag ? "#b8a878" : AMARILLO} />
      <path d={`M ${x + pl} ${y} L ${x} ${y + pl} L ${x + pl} ${y + pl} Z`}
            fill="rgba(15,17,19,.3)" />
      <path d={`M ${x + pl} ${y} H ${x + w} V ${y + h} H ${x} V ${y + pl} Z`}
            fill="none" stroke="rgba(15,17,19,.4)" strokeWidth="1.6" />
      <foreignObject x={x + 11} y={y + 10} width={w - 22} height={h - 30}>
        <div xmlns="http://www.w3.org/1999/xhtml"
             style={{ font: "600 12px/1.24 'Hanken Grotesk',system-ui,sans-serif",
                      color: "#1a1a18" }}>
          {n.requisitos} · por {n.canal} · {n.plazo_dias} días
        </div>
      </foreignObject>
      {/* quién la enseñó y cuándo: es lo que la vuelve memoria y no config */}
      <text x={x + 11} y={y + h - 9} fill="rgba(26,26,24,.72)" fontSize="11">
        se lo enseñó {n.quien} · {(n.cuando || "").slice(8, 10)}/{(n.cuando || "").slice(5, 7)}
      </text>
    </g>
  );
}

function Orden({ n, encendido }) {
  const w = 60, h = 80;
  const x = n.x - w / 2, y = n.y - h / 2;
  return (
    <g opacity={encendido ? 1 : 0.22}>
      {/* hoja con el borde superior ondulado: se lee como "papel arrancado" */}
      <path d={`M ${x} ${y + 8} q 7.5 -8 15 0 t 15 0 t 15 0 t 15 0 V ${y + h} H ${x} Z`}
            fill={PAPEL} />
      <path d={`M ${x} ${y + 8} q 7.5 -8 15 0 t 15 0 t 15 0 t 15 0 V ${y + h} H ${x} Z`}
            fill="none" stroke="rgba(15,17,19,.4)" strokeWidth="1.5" />
      {[0, 1, 2].map((i) => (
        <line key={i} x1={x + 11} y1={y + 34 + i * 11} x2={x + w - 11} y2={y + 34 + i * 11}
              stroke="rgba(15,17,19,.28)" strokeWidth="2" strokeLinecap="round" />
      ))}
      <text x={n.x} y={y + h + 19} textAnchor="middle"
            fill="#f5f5f4" fontSize="13" fontWeight="600">{n.numero}</text>
    </g>
  );
}

// Parte un nombre largo en dos renglones por el espacio más cercano al medio:
// «LECHE ENTERA CAMPO ALEGRE 1L (X12U)» entra entero en vez de quedar cortado.
function partirEnDos(txt) {
  const t = (txt || "").trim();
  if (t.length <= 20) return [t];
  const medio = Math.floor(t.length / 2);
  let corte = -1;
  for (let i = 0; i < t.length; i++) {
    if (t[i] === " " && (corte < 0 || Math.abs(i - medio) < Math.abs(corte - medio))) corte = i;
  }
  return corte < 0 ? [t] : [t.slice(0, corte), t.slice(corte + 1)];
}

const FORMAS = { persona: Persona, nota: Nota, producto: Producto,
                 proveedor: Proveedor, regla: Regla, orden: Orden };

// =============================================================================
// Las líneas
// =============================================================================

// Curva, no recta: una recta entre dos cajas parece un cable, una curva parece
// un recorrido. El desvío es perpendicular al segmento, así que el mismo
// número sirve para cualquier par sin calcular nada a mano.
function curva(a, b, k) {
  const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
  const dx = b.x - a.x, dy = b.y - a.y;
  return { d: `M ${a.x} ${a.y} Q ${mx - dy * k} ${my + dx * k} ${b.x} ${b.y}`,
           cx: mx - dy * k * 0.5, cy: my + dx * k * 0.5 };
}

function Arista({ a, nodos, trazada, activa, idx }) {
  const de = nodos[a.de], hacia = nodos[a.a];
  if (!de || !hacia) return null;
  const { d, cx, cy } = curva(de, hacia, a.curva || 0);
  const color = a.apagado ? "rgba(245,245,244,.28)" : (activa ? AZUL_IA : "rgba(245,245,244,.45)");
  const ancho = a.fuerte ? 3.4 : 2.6;
  return (
    <g opacity={trazada ? 1 : 0}>
      <path d={d} fill="none" stroke={color} strokeWidth={ancho}
            markerEnd={`url(#punta-${a.apagado ? "apagada" : activa ? "viva" : "normal"})`}
            strokeLinecap="round"
            // EL TRAZO CRECE de origen a destino. Es `stroke-dasharray` del
            // largo total con el offset animándose a cero: la línea no aparece,
            // avanza — que es lo que hace que se lea como un recorrido.
            style={{ strokeDasharray: 1200, strokeDashoffset: trazada ? 0 : 1200,
                     transition: `stroke-dashoffset ${MS_POR_ARISTA}ms ease-out` }} />
      {/* la partícula que la recorre, sólo mientras se traza */}
      {trazada && !a.apagado && (
        <circle r="4.5" fill={AZUL_IA}>
          <animateMotion dur="1.5s" repeatCount="indefinite" path={d} />
        </circle>
      )}
      {a.etiqueta && (
        <g opacity={trazada ? 1 : 0} style={{ transition: "opacity 320ms ease-out 260ms" }}>
          {/* la etiqueta en píldora con el fondo del lienzo: así nunca se lee
              encima de una línea ni de un nodo */}
          <EtiquetaPildora x={cx} y={cy} texto={a.etiqueta} apagada={a.apagado} />
        </g>
      )}
    </g>
  );
}

function EtiquetaPildora({ x, y, texto, apagada }) {
  const ancho = texto.length * 6.4 + 18;
  return (
    <>
      <rect x={x - ancho / 2} y={y - 11} width={ancho} height="22" rx="11"
            fill={TINTA} stroke={apagada ? "rgba(245,245,244,.18)" : "rgba(245,245,244,.3)"}
            strokeWidth="1" />
      <text x={x} y={y + 4.5} textAnchor="middle"
            fill={apagada ? "rgba(245,245,244,.55)" : "rgba(245,245,244,.9)"}
            fontSize="12">{texto}</text>
    </>
  );
}

// =============================================================================
export default function EscenaReclamo({ escena, trazar = true, onNodo }) {
  const [paso, setPaso] = useState(trazar ? 0 : 99);

  const nodos = useMemo(() => {
    const m = {};
    for (const n of escena?.nodos || []) m[n.id] = n;
    return m;
  }, [escena]);

  // El trazado, una arista por vez. El orden es el del backend, que es el
  // orden en que se cuenta: quién lo dijo, qué pasó, a quién, qué exige.
  useEffect(() => {
    if (!trazar || !escena) return;
    setPaso(0);
    const total = (escena.aristas || []).length;
    const t = setInterval(() => {
      setPaso((p) => {
        if (p >= total) { clearInterval(t); return p; }
        return p + 1;
      });
    }, MS_POR_ARISTA);
    return () => clearInterval(t);
  }, [escena, trazar]);

  if (!escena?.disponible) return null;
  const { ancho, alto, separador } = escena.lienzo;

  // Un nodo se enciende cuando ya lo tocó alguna arista trazada (o si no hay
  // animación). La persona arranca encendida: es donde empieza la historia.
  const encendidos = new Set(["persona"]);
  (escena.aristas || []).slice(0, paso).forEach((a) => {
    encendidos.add(a.de); encendidos.add(a.a);
  });

  return (
    <svg viewBox={`0 0 ${ancho} ${alto}`} className="h-full w-full"
         style={{ background: TINTA }}>
      <defs>
        {[["normal", "rgba(245,245,244,.45)"], ["viva", AZUL_IA],
          ["apagada", "rgba(245,245,244,.28)"]].map(([id, c]) => (
          <marker key={id} id={`punta-${id}`} viewBox="0 0 10 10" refX="9" refY="5"
                  markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill={c} />
          </marker>
        ))}
      </defs>

      {/* la línea que separa el caso del contraste */}
      <line x1="60" y1={separador} x2={ancho - 60} y2={separador}
            stroke="rgba(245,245,244,.16)" strokeWidth="1" strokeDasharray="3 6" />
      <text x={ancho - 60} y={separador - 10} textAnchor="end"
            fill="rgba(245,245,244,.42)" fontSize="12.5" fontStyle="italic">
        {escena.separador_texto}
      </text>

      {(escena.aristas || []).map((a, i) => (
        <Arista key={i} a={a} nodos={nodos} idx={i}
                trazada={i < paso} activa={!a.apagado} />
      ))}

      {(escena.nodos || []).map((n) => {
        const F = FORMAS[n.tipo];
        if (!F) return null;
        return (
          <g key={n.id} onClick={() => onNodo?.(n)} style={{ cursor: onNodo ? "pointer" : "default" }}>
            <F n={n} encendido={encendidos.has(n.id)} />
          </g>
        );
      })}
    </svg>
  );
}
