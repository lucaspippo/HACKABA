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
import { useT } from "../../lib/i18n";

// --- el lenguaje visual, el mismo del cerebro -------------------------------
// EL FONDO ES PAPEL, NO NEGRO. La escena vive adentro del producto y tiene
// que hablar su mismo idioma: un lienzo oscuro acá se lee como otra
// aplicacion. `TINTA` dejo de ser el fondo y volvio a ser lo que es en el
// resto del sistema — el color del texto.
const FONDO = "#fbfbfa";          // --color-papel
const TINTA = "#21201d";          // --color-tinta, el texto
const LINEA = "#e9e7e2";          // --color-linea, las hairlines
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
      <circle cx={n.x} cy={n.y} r={r} fill="none" stroke="rgba(33,32,29,.28)" strokeWidth="1.5" />
      {/* cabeza y hombros: la silueta que se lee a cualquier tamaño */}
      <circle cx={n.x} cy={n.y - 8} r={11} fill={TINTA} opacity=".78" />
      <path d={`M ${n.x - 19} ${n.y + 22} Q ${n.x} ${n.y + 1} ${n.x + 19} ${n.y + 22} Z`}
            fill={TINTA} opacity=".78" />
      <text x={n.x} y={n.y + r + 22} textAnchor="middle"
            fill={TINTA} fontSize="17" fontWeight="600">{n.nombre}</text>
      {n.rol && (
        <text x={n.x} y={n.y + r + 39} textAnchor="middle"
              fill="rgba(33,32,29,.55)" fontSize="12">{n.rol}</text>
      )}
    </g>
  );
}

// La insignia del canal: el ÚNICO lugar del lienzo con color de marca ajeno.
// Confinada a un disco de 26 px pegado al post-it — nunca el cuerpo del nodo,
// nunca una arista, para que el azul se siga leyendo como Ángela (DESIGN.md).
// LOS LOGOS, DE VERDAD. Antes había un trazo dibujado a mano "parecido" al de
// WhatsApp, y eso no sirve: la gracia de una marca es que se reconoce sin
// mirarla. Van como imagen desde /canales/, recortadas a un disco.
//
// Es el ÚNICO lugar del lienzo con color de marca ajeno, y queda confinado al
// disco de la insignia — nunca el cuerpo del nodo, nunca una arista, para que
// el azul se siga leyendo como Ángela (DESIGN.md).
const LOGO_CANAL = {
  whatsapp: "/canales/whatsapp.png",
  email: "/canales/mail.jpg",
};

function InsigniaCanal({ x, y, canal, r = 17 }) {
  const src = LOGO_CANAL[canal];
  const cid = `recorte-${canal}-${Math.round(x)}-${Math.round(y)}`;
  return (
    <g>
      <circle cx={x} cy={y} r={r + 2.5} fill="#fff" />
      {src ? (
        <>
          <clipPath id={cid}>
            <circle cx={x} cy={y} r={r} />
          </clipPath>
          <image href={src} x={x - r} y={y - r} width={r * 2} height={r * 2}
                 clipPath={`url(#${cid})`} preserveAspectRatio="xMidYMid slice" />
        </>
      ) : (
        <circle cx={x} cy={y} r={r} fill="#e8e4dc" />
      )}
      <circle cx={x} cy={y} r={r + 2.5} fill="none" stroke={TINTA} strokeWidth="2" />
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
            fill="none" stroke="rgba(33,32,29,.28)" strokeWidth="1.6" />
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
            fill="rgba(33,32,29,.6)" fontSize="12">
        {n.autor} · {(n.fecha || "").slice(5)}
      </text>
    </g>
  );
}

function Producto({ n, encendido }) {
  const r = 58;   // el texto va adentro: el círculo tiene que darle lugar
  // tres renglones cortos entran en un disco; dos largos se desbordan por los
  // costados, que es lo que pasaba con «LECHE ENTERA CAMPO ALEGRE 1L (X12U)»
  const lineas = partirEnTres(n.nombre);
  const y0 = n.y - (lineas.length - 1) * 7 - (n.lote ? 6 : 0);
  return (
    <g opacity={encendido ? 1 : 0.22}>
      <circle cx={n.x} cy={n.y} r={r} fill={HIELO} />
      <circle cx={n.x} cy={n.y} r={r} fill="none" stroke="rgba(33,32,29,.32)" strokeWidth="1.5" />
      {lineas.map((l, i) => (
        <text key={i} x={n.x} y={y0 + i * 14} textAnchor="middle" fill="#07242a"
              fontSize="12" fontWeight="700">{l}</text>
      ))}
      {n.lote && (
        <text x={n.x} y={y0 + lineas.length * 14 + 6} textAnchor="middle"
              fill="rgba(7,36,42,.7)" fontSize="10.5">lote {n.lote}</text>
      )}
    </g>
  );
}

// EL CIERRE DEL CIRCUITO. Sin este nodo la cadena terminaba en la regla y
// parecía que el sistema entrega un informe — que es justo lo que PolPilot
// dice que no hace (PRODUCT.md, The Action Principle).
function Envio({ n, encendido }) {
  // EL ANCHO SALE DEL TEXTO, no al reves. Estaba fijo en 196 y «con foto del
  // lote y numero de remito» se salia de la caja verde: el texto arranca en
  // x+62 (despues del logo) y a 11.5px esa linea mide ~198px contra 134
  // disponibles. Ahora la linea larga se parte en dos y la caja crece lo justo.
  const izq = 62;                       // donde arranca el texto, despues del logo
  const lineas = partirEn(`con ${n.adjuntos}`, 30);
  const anchoTexto = Math.max(
    "Reclamo enviado".length * 7.6,
    ...lineas.map((l) => l.length * 5.6),
    `a ${n.destinatario}`.length * 5.4,
  );
  const w = Math.max(200, Math.round(izq + anchoTexto + 16));
  const h = 74 + lineas.length * 15;
  const x = n.x - w / 2, y = n.y - h / 2;
  const y0 = n.y - (lineas.length === 1 ? 6 : 13);
  return (
    <g opacity={encendido ? 1 : 0.22}>
      <rect x={x} y={y} width={w} height={h} rx="14" fill="#eaf6ef" />
      <rect x={x} y={y} width={w} height={h} rx="14" fill="none"
            stroke="#2e9c6a" strokeWidth="2" />
      <InsigniaCanal x={x + 34} y={n.y} canal={n.canal} r={19} />
      <text x={x + izq} y={y + 26} fill="#1d6b47" fontSize="14" fontWeight="700">
        Reclamo enviado
      </text>
      {lineas.map((l, i) => (
        <text key={i} x={x + izq} y={y0 + 14 + i * 15}
              fill="rgba(33,32,29,.72)" fontSize="11.5">{l}</text>
      ))}
      <text x={x + izq} y={y + h - 12} fill="rgba(33,32,29,.5)" fontSize="11">
        a {n.destinatario}
      </text>
    </g>
  );
}

// Parte un texto en lineas de a lo sumo `max` caracteres, sin cortar palabras.
function partirEn(txt, max) {
  const palabras = (txt || "").trim().split(/\s+/);
  const lineas = [];
  let actual = "";
  for (const p of palabras) {
    if (!actual) { actual = p; continue; }
    if ((actual + " " + p).length <= max) actual += " " + p;
    else { lineas.push(actual); actual = p; }
  }
  if (actual) lineas.push(actual);
  return lineas.length ? lineas : [""];
}

function Proveedor({ n, encendido }) {
  const r = 36;   // ⌀72
  const apag = n.apagado;
  return (
    <g opacity={encendido ? (apag ? 0.5 : 1) : 0.22}>
      <path d={`M ${n.x} ${n.y - r} L ${n.x + r} ${n.y} L ${n.x} ${n.y + r} L ${n.x - r} ${n.y} Z`}
            fill={apag ? "#8a7a63" : OCRE} />
      <path d={`M ${n.x} ${n.y - r} L ${n.x + r} ${n.y} L ${n.x} ${n.y + r} L ${n.x - r} ${n.y} Z`}
            fill="none" stroke="rgba(33,32,29,.32)" strokeWidth="1.5" />
      <text x={n.x} y={n.y + r + 21} textAnchor="middle"
            fill={apag ? "rgba(33,32,29,.5)" : TINTA}
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
            fill="none" stroke="rgba(33,32,29,.32)" strokeWidth="1.6" />
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
            fill="none" stroke="rgba(33,32,29,.32)" strokeWidth="1.5" />
      {[0, 1, 2].map((i) => (
        <line key={i} x1={x + 11} y1={y + 34 + i * 11} x2={x + w - 11} y2={y + 34 + i * 11}
              stroke="rgba(15,17,19,.28)" strokeWidth="2" strokeLinecap="round" />
      ))}
      <text x={n.x} y={y + h + 19} textAnchor="middle"
            fill={TINTA} fontSize="13" fontWeight="600">{n.numero}</text>
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

// Tres renglones cortos: un nombre de producto no entra en uno, y en dos se
// desborda por los costados del disco.
function partirEnTres(txt) {
  const palabras = (txt || "").trim().split(/\s+/);
  const lineas = [];
  let actual = "";
  for (const p of palabras) {
    if ((actual + " " + p).trim().length > 13 && actual) { lineas.push(actual); actual = p; }
    else actual = (actual + " " + p).trim();
    if (lineas.length === 3) break;
  }
  if (lineas.length < 3 && actual) lineas.push(actual);
  return lineas.slice(0, 3);
}

const FORMAS = { persona: Persona, nota: Nota, producto: Producto,
                 proveedor: Proveedor, regla: Regla, orden: Orden, envio: Envio };

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
  const color = a.apagado ? "rgba(33,32,29,.20)" : (activa ? AZUL_IA : "rgba(33,32,29,.38)");
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
          {/* dx/dy vienen del backend (core/escena.py): tres aristas llegan
              al proveedor desde abajo y sus puntos medios caen casi encima.
              El corrimiento se decide alla, con el resto de las posiciones. */}
          <EtiquetaPildora x={cx + (a.dx || 0)} y={cy + (a.dy || 0)}
                           texto={a.etiqueta} apagada={a.apagado} />
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
            fill={FONDO} stroke={apagada ? LINEA : "rgba(33,32,29,.22)"}
            strokeWidth="1" />
      <text x={x} y={y + 4.5} textAnchor="middle"
            fill={apagada ? "rgba(33,32,29,.45)" : TINTA}
            fontSize="12">{texto}</text>
    </>
  );
}

// =============================================================================
// LA EXPANSION — lo que hay detras del camino.
//
// Se toca el producto y aparecen sus OTRAS relaciones: las que no son parte de
// la respuesta. Sin animacion de recorrido, a proposito: el trazado cuenta un
// razonamiento y esto no es un razonamiento, es «ademas, hay todo esto». Sale
// de una vez, como se ve un grafo normalmente.
//
// Las formas son DELIBERADAMENTE simples —un disco y una etiqueta— contra las
// del caso, que estan dibujadas una por una (el post-it, el rombo, el remito).
// Esa diferencia hace el trabajo: lo dibujado con cuidado es la respuesta, lo
// simple es el resto del cerebro asomando. Si tuvieran la misma prolijidad,
// competirian.
const COLOR_EXP = {
  rubro: "#6f7490", local: "#a99f8c", cliente: "#2e9c6a",
  producto: "#2f8fa8", ubicacion: "#8a8378", remito: "#7a63b8",
};

function Expansion({ datos, desde, visible }) {
  const grupos = datos?.grupos || [];
  if (!grupos.length || !desde) return null;
  let orden = 0;
  return (
    <g style={{ pointerEvents: "none" }}>
      {grupos.map((gr) => {
        const alto = gr.nodos.length * 38;
        return (
          <g key={gr.rel}>
            {/* una sola linea por RACIMO, no una por nodo: once lineas
                saliendo del mismo punto son una estrella ilegible */}
            <path d={`M ${desde.x} ${desde.y} C ${desde.x + 160} ${desde.y}, `
                   + `${gr.x - 170} ${gr.y + alto / 2}, ${gr.x - 96} ${gr.y + alto / 2}`}
                  fill="none" stroke="rgba(33,32,29,.20)" strokeWidth="1.5"
                  style={{ opacity: visible ? 1 : 0, transition: "opacity 320ms" }} />
            <text x={gr.x} y={gr.y + 4} textAnchor="middle"
                  fill="rgba(33,32,29,.52)" fontSize="12"
                  style={{ opacity: visible ? 1 : 0, transition: "opacity 300ms" }}>
              {gr.rel}
            </text>
            {gr.nodos.map((n) => {
              const color = COLOR_EXP[n.tipo] || "#8b8fa8";
              const ancho = Math.max(112, n.nombre.length * 5.75 + 46);
              const izq = n.x - ancho / 2;
              const retraso = 90 + orden++ * 55;
              return (
                <g key={n.id}
                   style={{ opacity: visible ? 1 : 0,
                            transition: `opacity 300ms ease-out ${visible ? retraso : 0}ms` }}>
                  <rect x={izq} y={n.y - 15} width={ancho} height="30" rx="15"
                        fill={FONDO} stroke={color} strokeWidth="1.6" />
                  <circle cx={izq + 16} cy={n.y} r="5" fill={color} />
                  <text x={izq + 30} y={n.y + 4} fill={TINTA} fontSize="11.5">
                    {n.nombre}
                  </text>
                </g>
              );
            })}
          </g>
        );
      })}
    </g>
  );
}

export default function EscenaReclamo({ escena, trazar = true, onNodo }) {
  const [paso, setPaso] = useState(trazar ? 0 : 99);
  // QUE nodo esta abierto (null = ninguno). Son varios los que se pueden
  // tocar: el producto y el proveedor, cada uno con lo suyo.
  const [abiertoId, setAbiertoId] = useState(null);
  const t = useT();
  useEffect(() => { setAbiertoId(null); }, [escena, trazar]);

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
  const { ancho, alto } = escena.lienzo;

  // Un nodo se enciende cuando ya lo tocó alguna arista trazada (o si no hay
  // animación). La persona arranca encendida: es donde empieza la historia.
  const encendidos = new Set(["persona"]);
  (escena.aristas || []).slice(0, paso).forEach((a) => {
    encendidos.add(a.de); encendidos.add(a.a);
  });

  // EL ALEJARSE DEL LIENZO ES EL MENSAJE. Al abrir, la escena se achica y se
  // recentra para que entre todo lo que aparecio: ese movimiento dice «lo que
  // estabas mirando era un recorte» mejor que cualquier cartel.
  //
  // No se anima el viewBox (no es animable por CSS): el viewBox queda fijo y se
  // transforma el grupo de adentro, que si transiciona suave.
  const expansiones = escena.expansiones || {};
  const listo = paso >= (escena.aristas || []).length;
  const seAbre = (id) => listo && !!expansiones[id]?.grupos?.length;
  const hayAlgunaAbrible = Object.keys(expansiones).some(seAbre);
  const exp = abiertoId ? expansiones[abiertoId] : null;
  const vb = exp?.lienzo_abierto;
  let encuadre = "";
  if (abiertoId && vb) {
    const [ox, oy, ow, oh] = vb;
    const k = Math.min(ancho / ow, alto / oh);
    // EN CSS, NO EN SINTAXIS SVG. `translate(184 150)` es valido como atributo
    // `transform` de SVG pero NO como propiedad CSS: ahi van unidades y coma, y
    // sin ellas el navegador descarta la regla entera en silencio — la escena
    // no se movia y los nodos nuevos quedaban fuera del viewBox, invisibles.
    // `transformBox: view-box` + `transformOrigin: 0 0` hacen que el transform
    // CSS se comporte como el de SVG (si no, el origen es el centro de la caja
    // del elemento y la cuenta de arriba no cierra).
    encuadre = `translate(${ancho / 2 - k * (ox + ow / 2)}px, ${alto / 2 - k * (oy + oh / 2)}px) scale(${k})`;
  }
  const nodoDesde = nodos[abiertoId];

  return (
    <div className="relative h-full w-full">
    <svg viewBox={`0 0 ${ancho} ${alto}`} className="h-full w-full"
         style={{ background: FONDO }}>
      <defs>
        {[["normal", "rgba(33,32,29,.45)"], ["viva", AZUL_IA],
          ["apagada", "rgba(33,32,29,.22)"]].map(([id, c]) => (
          <marker key={id} id={`punta-${id}`} viewBox="0 0 10 10" refX="9" refY="5"
                  markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill={c} />
          </marker>
        ))}
      </defs>


      <g style={{ transform: encuadre || "none",
                  transformBox: "view-box", transformOrigin: "0 0",
                  transition: "transform 720ms cubic-bezier(.4,0,.2,1)" }}>
        {(escena.aristas || []).map((a, i) => (
          <Arista key={i} a={a} nodos={nodos} idx={i}
                  trazada={i < paso} activa={!a.apagado} />
        ))}

        {/* Lo que hay detras, DEBAJO de los nodos del caso: el camino nunca
            queda tapado por lo que se sumo — se suma, no lo reemplaza. */}
        <Expansion datos={exp} desde={nodoDesde} visible={!!abiertoId} />

        {(escena.nodos || []).map((n) => {
          const F = FORMAS[n.tipo];
          if (!F) return null;
          // se tocan los que tienen algo detras: hoy el producto y el proveedor
          const esElQueAbre = seAbre(n.id);
          return (
            <g key={n.id}
               onClick={() => (esElQueAbre
                 ? setAbiertoId((v) => (v === n.id ? null : n.id))
                 : onNodo?.(n))}
               style={{ cursor: esElQueAbre || onNodo ? "pointer" : "default" }}>
              {/* un halo que late una sola vez cuando ya se puede tocar: sin
                  esto nadie adivina que ese nodo hace algo */}
              {esElQueAbre && !abiertoId && (
                <circle cx={n.x} cy={n.y} r="66" fill="none" stroke={AZUL_IA}
                        strokeWidth="2" opacity=".55">
                  <animate attributeName="r" values="60;74;60" dur="2.2s"
                           repeatCount="indefinite" />
                  <animate attributeName="opacity" values=".55;.1;.55" dur="2.2s"
                           repeatCount="indefinite" />
                </circle>
              )}
              <F n={n} encendido={encendidos.has(n.id)} />
            </g>
          );
        })}
      </g>

    </svg>

      {/* LA PISTA, y tambien la puerta de vuelta. EN HTML, NO ADENTRO DEL SVG.
          Adentro vivia en coordenadas del lienzo, pero al abrir una expansion
          TODO el contenido se escala para entrar y la pildora no — asi que dos
          cajas separadas por 90px terminaban superpuestas en pantalla, y un
          chequeo en coordenadas del lienzo daba cero. Afuera el problema no
          existe: se posiciona contra el panel y nada la puede alcanzar. */}
      {hayAlgunaAbrible && (
        <button
          onClick={() => abiertoId && setAbiertoId(null)}
          className={`absolute bottom-4 left-4 rounded-full border px-3.5 py-1.5 text-[12.5px]
                      ${abiertoId
                        ? "border-violeta/60 bg-crema text-violeta"
                        : "cursor-default border-linea bg-crema text-tinta-suave"} sombra-papel`}>
          {abiertoId ? `← ${t("cerebro.contraer")}` : t("cerebro.expandir")}
        </button>
      )}
    </div>
  );
}
