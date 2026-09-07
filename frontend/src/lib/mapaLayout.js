// ============================================================================
// THE OPERATION MAP'S GEOMETRY — where each node goes, and nothing else.
// ----------------------------------------------------------------------------
// RULE OF THIS FILE: no business knowledge enters here. Not a domain name,
// not a state, not a metric. Points come in, points come out. Who is a
// supplier and who is a cold room is the backend's decision
// (core/mapa_operacion.py); MapaOperacion.jsx only iterates.
//
// The layered layout — «where it comes from → where it is → where it goes» —
// makes position MEAN something: a node sits where it sits because of the
// moment of the route it occupies. The eye travels left to right and
// understands the operation without anyone explaining it.
//
// WHY THE CENTER IS A GRID AND NOT A COLUMN. Between warehouse zones there is
// traffic in both directions. In a column, the back-and-forth arrows cross
// and none reads; in a grid each pair shares its own corridor, and the gap in
// the middle is the one place where the company logo is not decoration: it is
// the answer to «whose is all this?».
// ============================================================================

/**
 * Which side of a node an edge should leave from toward another node. React
 * Flow needs to know, or it draws lines straight through the card.
 */
export function ladoHacia(a, b) {
  const dx = b.x - a.x, dy = b.y - a.y;
  if (Math.abs(dx) > Math.abs(dy)) return dx > 0 ? "r" : "l";
  return dy > 0 ? "b" : "t";
}

// Measurements come from measuring the map that already works. Each column
// has its own width and step: origin is narrow and tight because it is a list
// of names; the center is the widest because that is where the numbers that
// matter live.
export const ANCHO_NODO = { origen: 214, centro: 292, orden: 196, salida: 214 };
const PASO = { origen: 90, orden: 96, salida: 92 };

// The FOUR columns. Destination splits in two — first what is leaving right
// now, then which channel it goes to — because they are two different
// questions and mixed they read as neither. The gap between the two center
// columns is not aesthetic: it is the corridor the transfers cross, and where
// the logo goes. Tuned by measuring the render: with the ~870 px canvas the
// Ángela panel leaves, a 1,680 px graph fits at 0.5 zoom and no number
// reads. At 1,430 it fits at 0.6 and the center cards keep their weight.
export const COLUMNA = { origen: 0, centroIzq: 262, centroDer: 716,
                         orden: 1060, salida: 1300 };
const GRID_Y = [0, 236];              // top row / bottom row of the grid
const ALTO_CENTRO = 196;              // height of a center card
const ALTO_BANDA = 96;                // height of the context bands
// The logo must FIT the gap, not overlap it: the gap measures 162 px
// (centroDer − centroIzq − card width) and the logo gets air on both sides.
const LADO_LOGO = 126;


function apilar(n, paso, ejeY) {
  /** Center `n` cards in a column around the horizontal axis. */
  const y0 = ejeY - (n * paso) / 2;
  return Array.from({ length: n }, (_, i) => y0 + i * paso);
}

/**
 * Place the operation map's nodes.
 *
 * Knows no business: receives nodes with `capa` and `tipo`, returns points.
 */
export function disponerEnCapas(nodos) {
  const de = (capa, filtro) =>
    nodos.filter((n) => n.capa === capa && (!filtro || filtro(n)));

  const origen = de("origen");
  const hub = nodos.find((n) => n.es_hub);
  const zonas = de("centro", (n) => !n.es_hub);
  // What is leaving RIGHT NOW gets its own column, before the channels.
  const saliendo = de("destino", (n) => n.tipo === "pedido" || n.tipo === "camion");
  const canales = de("destino", (n) => n.tipo !== "pedido" && n.tipo !== "camion");

  const medioX = (COLUMNA.centroIzq + COLUMNA.centroDer + ANCHO_NODO.centro) / 2;
  const ejeY = GRID_Y[1] / 2 + ALTO_CENTRO / 2;

  const posiciones = {};
  // The grid fills by rows: the fullest zone — which comes first — lands top
  // left, which is where the eye starts.
  zonas.forEach((n, i) => {
    posiciones[n.id] = {
      x: i % 2 ? COLUMNA.centroDer : COLUMNA.centroIzq,
      y: GRID_Y[i > 1 ? 1 : 0],
    };
  });

  // THE HUB IS THE BRAND: the grid IS the warehouse, so no separate card. The
  // brand takes the middle gap and opens the warehouse detail.
  const logo = { x: medioX - LADO_LOGO / 2, y: ejeY - LADO_LOGO / 2, lado: LADO_LOGO };
  if (hub) posiciones[hub.id] = { x: logo.x, y: logo.y };

  // Each column returns WHERE IT ENDS, and the context hangs from there.
  // Fixed offsets were what produced the overlaps: one extra card and the
  // block below crawled inside the column's last card.
  const columna = (lista, x, paso) => {
    const ys = apilar(lista.length, paso, ejeY);
    ys.forEach((y, i) => (posiciones[lista[i].id] = { x, y }));
    return ys.length ? ys[ys.length - 1] + paso : ejeY;
  };
  const finOrigen = columna(origen, COLUMNA.origen, PASO.origen);
  const finSaliendo = columna(saliendo, COLUMNA.orden, PASO.orden);
  const finCanales = columna(canales, COLUMNA.salida, PASO.salida);

  // --- the context layer ---------------------------------------------------
  // Two wide, low bands above and below the grid, and two blocks that start
  // BELOW where their column ends. Weight 3: it reads as context without
  // having to be read.
  const anchoCuadro = COLUMNA.centroDer + ANCHO_NODO.centro - COLUMNA.centroIzq;
  const AIRE_CTX = 56;
  const altoCuadro = GRID_Y[1] + ALTO_CENTRO;
  const abajo = Math.max(altoCuadro, finOrigen, finSaliendo, finCanales) + AIRE_CTX;
  const ctx = {
    canales: { x: COLUMNA.centroIzq, y: GRID_Y[0] - ALTO_BANDA - AIRE_CTX,
               ancho: anchoCuadro },
    devuelve: { x: COLUMNA.centroIzq, y: abajo, ancho: anchoCuadro },
    equipo: { x: COLUMNA.origen, y: finOrigen + AIRE_CTX,
              ancho: ANCHO_NODO.origen + 26 },
    reglas: { x: COLUMNA.orden, y: abajo, ancho: 300 },
  };
  nodos.filter((n) => n.capa === "contexto").forEach((n) => {
    if (ctx[n.id]) posiciones[n.id] = { x: ctx[n.id].x, y: ctx[n.id].y };
  });

  return { posiciones, logo, ejeY, ctx };
}

/**
 * Handles and edge shape between two cells of the center grid. Inside the
 * grid, lines go STRAIGHT: horizontal between cells of the same row,
 * vertical within a column, and the diagonals go around the logo instead of
 * running over the company name.
 */
export function ladosDelCuadro(a, b) {
  const filaA = a > 1, filaB = b > 1;
  const colA = a % 2, colB = b % 2;
  if (filaA === filaB) return colA < colB ? ["s-r", "t-l", "straight"] : ["s-l", "t-r", "straight"];
  if (colA === colB) return filaA < filaB ? ["s-b", "t-t", "straight"] : ["s-t", "t-b", "straight"];
  const arriba = Math.min(a, b) === 0;
  return arriba ? ["s-t", "t-t", "smoothstep"] : ["s-b", "t-b", "smoothstep"];
}
