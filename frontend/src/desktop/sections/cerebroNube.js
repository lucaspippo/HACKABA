// =============================================================================
// LA NUBE DEL REPOSO: el cerebro entero, antes de que nadie pregunte nada.
//
// QUÉ ES Y QUÉ NO ES.
//
// Esto es una IMAGEN, y eso está decidido a propósito. Durante los segundos
// previos al audio la pantalla tiene que decir «esto es grande y tiene forma»;
// después la cámara entra hacia el caso y a partir de ahí TODO es real —las
// ocho fuentes, los cruces, las reglas, la respuesta—. Nadie consulta esta
// nube, nadie la filtra, nadie la toca.
//
// Antes se dibujaba el grafo real: 605 nodos de los cuales 427 son productos.
// Una población así no tiene estructura visible — sale una maraña azul sin
// forma, y eso es lo primero que ve un jurado de algo que se llama «el cerebro
// del negocio». Se intentó separarla con fuerzas (isla 0.11 y 0.42, carga -58
// y -130, colisión +1.4 y +5, resortes 0.035 y 0.02) y no separó nada: cuando
// el 70% de la población es de un tipo, no hay fuerza que haga islas. Eso ya
// estaba documentado en CerebroPantalla.jsx y sigue siendo cierto.
//
// Así que la nube se COMPONE. Las posiciones se calculan acá, con una semilla
// fija, y se congelan (fx/fy): sale idéntica en cada carga, no hay simulación
// enfriándose ni espera, y lo que se ve es exactamente lo que se diseñó.
//
// LO QUE SÍ TIENE QUE SEGUIR SIENDO VERDAD: los tres nodos a los que vuela la
// cámara (IDS_CASO) existen en la nube, juntos y con su nombre. El zoom los
// sigue buscando por id, igual que antes, y desde ahí arranca la escena real.
//
// EL DISEÑO, y por qué cada cosa:
//
//   · TAMAÑO POR IMPORTANCIA. Un hub grande, unos pocos medianos y muchas
//     hojas chicas en cada comunidad. Todos los nodos iguales es ruido; una
//     jerarquía visible se lee como estructura de un vistazo.
//   · COMUNIDADES SEPARADAS, cada una con su color y su campo de fondo. La
//     separación tiene que verse en el espacio vacío, no sólo en el color.
//   · SUB-ESTRUCTURA ADENTRO. Las hojas no se esparcen parejo alrededor del
//     centro —eso da una pelota borrosa—: se agrupan alrededor de sub-hubs,
//     con caída gaussiana. Eso es lo que hace que la densidad se lea como
//     organización y no como niebla.
//   · PROFUNDIDAD. Cada nodo lleva una `z`: los del fondo son más chicos y más
//     transparentes, los de adelante nítidos. Da capas, y hace que el zoom se
//     sienta como entrar y no como agrandar.
//   · CURVAS, NO RECTAS. Y los PUENTES entre comunidades, más curvos y en el
//     azul de Ángela: son la tesis del producto —los mundos se cruzan— y
//     tienen que leerse por encima del tejido interno.
// =============================================================================

// Los tres que la cámara va a buscar. Tienen que coincidir con los de
// CerebroPantalla: si acá no existen, el zoom no tiene a dónde ir.
export const IDS_CASO = ["nota:wa08", "persona:nahuel", "prov:lacteos_campo_alegre"];

/** PRNG con semilla: la misma nube en cada carga y en cada máquina. */
function azar(semilla) {
  let a = semilla >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Normal(0,1) por Box-Muller: la caída natural de una nube. */
function normal(rnd) {
  const u = Math.max(1e-9, rnd());
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rnd());
}

// Las comunidades: `tipo` decide el color y el encendido por herramienta (el
// resto de la pantalla ya habla ese vocabulario), cuántos nodos, y dónde cae
// su centro sobre la elipse.
//
// Los tamaños son DESPAREJOS a propósito: ocho comunidades iguales se leen
// como un diagrama; desparejas se leen como un negocio.
// El catálogo va al CENTRO y el resto en anillo alrededor, repartidos cada
// ~51 grados. La separación está verificada: ningún par de campos queda a
// menos del 78% de la suma de sus radios (scripts de prueba en el commit).
const COMUNIDADES = [
  { tipo: "producto",     n: 116, ang: -102, r: 0.10 },
  { tipo: "cliente",      n:  86, ang:   20, r: 0.95 },
  { tipo: "local",        n:  34, ang:   71, r: 0.88 },
  { tipo: "remito",       n:  70, ang:  122, r: 1.00 },
  { tipo: "proveedor",    n:  56, ang:  173, r: 0.95 },
  { tipo: "nota",         n:  44, ang:  224, r: 0.90 },
  { tipo: "persona",      n:  20, ang:  275, r: 0.74 },
  { tipo: "conocimiento", n:  26, ang:  326, r: 0.82 },
];

// Un rótulo por comunidad. Un grafo sin una sola palabra es abstracto; ocho
// palabras lo vuelven el mapa de un negocio. No son consultables: son el
// nombre del barrio, no el de una fila.
const ROTULOS = {
  producto: "Catálogo", cliente: "Clientes", remito: "Comprobantes",
  proveedor: "Proveedores", nota: "Lo que avisa el equipo",
  local: "Sucursales", conocimiento: "Reglas de la casa", persona: "El equipo",
};

const RX = 640, RY = 430;

/**
 * Devuelve { nodes, links, campos } listo para ForceGraph2D.
 * `campos` son los discos de color del fondo, uno por comunidad.
 */
export function construirNube(semilla = 20260912) {
  const rnd = azar(semilla);
  const nodes = [];
  const links = [];
  const campos = [];
  let k = 0;

  COMUNIDADES.forEach((c, ic) => {
    const rad = (c.ang * Math.PI) / 180;
    const cx = Math.cos(rad) * RX * c.r;
    const cy = Math.sin(rad) * RY * c.r;
    // el radio crece con la RAÍZ de la población: así una comunidad del doble
    // de nodos no ocupa el doble de pantalla, que es justo lo que las hacía
    // chocar entre sí
    const R = 32 + 9.2 * Math.sqrt(c.n);
    campos.push({ x: cx, y: cy, r: R * 1.5, tipo: c.tipo });

    const nSub = Math.max(2, Math.round(Math.sqrt(c.n) / 1.5));
    const hub = {
      id: `c${ic}:hub`, tipo: c.tipo, x: cx, y: cy,
      _r: 6.0 + 3.6 * (c.n / 116), _z: 1, _rotulo: ROTULOS[c.tipo],
    };
    nodes.push(hub);

    const subs = [];
    for (let i = 0; i < nSub; i++) {
      const a = (i / nSub) * 2 * Math.PI + rnd() * 0.7;
      const d = R * (0.42 + rnd() * 0.28);
      const s = {
        id: `c${ic}:s${i}`, tipo: c.tipo,
        x: cx + Math.cos(a) * d, y: cy + Math.sin(a) * d,
        _r: 3.0 + rnd() * 2.0, _z: 0.62 + rnd() * 0.38,
      };
      subs.push(s);
      nodes.push(s);
      links.push({ source: hub.id, target: s.id, _puente: false });
    }

    // las hojas, alrededor de SU sub-hub y no del centro de la comunidad: eso
    // es lo que hace que adentro se vea organización y no niebla
    const hojas = Math.max(0, c.n - 1 - nSub);
    for (let i = 0; i < hojas; i++) {
      const s = subs[Math.floor(rnd() * subs.length)];
      const sg = R * 0.23;
      const n = {
        id: `n${k++}`, tipo: c.tipo,
        x: s.x + normal(rnd) * sg, y: s.y + normal(rnd) * sg,
        _r: 1.3 + rnd() * 1.55, _z: 0.16 + rnd() * 0.62,
      };
      nodes.push(n);
      links.push({ source: s.id, target: n.id, _puente: false });
      // un poco de tejido lateral: sin esto se ve un árbol, no una red
      if (rnd() < 0.16) {
        const o = nodes[nodes.length - 2 - Math.floor(rnd() * 4)];
        if (o && o.tipo === c.tipo && o.id !== n.id) {
          links.push({ source: n.id, target: o.id, _puente: false });
        }
      }
    }
  });

  // LOS PUENTES. Pocos, largos y visibles: son la tesis —los mundos se
  // cruzan—. Si fueran muchos volverían a ser maraña, que es de donde venimos.
  const cabezas = nodes.filter((n) => /:hub$|:s\d+$/.test(n.id));
  for (let i = 0; i < 26; i++) {
    const a = cabezas[Math.floor(rnd() * cabezas.length)];
    const b = cabezas[Math.floor(rnd() * cabezas.length)];
    if (a && b && a.tipo !== b.tipo) {
      links.push({ source: a.id, target: b.id, _puente: true });
    }
  }

  // EL CASO, ADENTRO DE LA NUBE. Tres nodos con su nombre, juntos: es a donde
  // vuela la cámara, y tiene que sentirse que estaban ahí adentro desde el
  // principio. Van entre el catálogo y el equipo, no en un rincón vacío.
  const caso = [
    { id: "prov:lacteos_campo_alegre", tipo: "proveedor",
      nombre: "Lácteos Campo Alegre", dx: 0, dy: 0 },
    { id: "persona:nahuel", tipo: "persona", nombre: "Nahuel", dx: -66, dy: 36 },
    { id: "nota:wa08", tipo: "nota", nombre: "«llegaron rotas»", dx: 58, dy: 42 },
  ];
  // en un hueco visible entre el catálogo, las sucursales y los clientes: la
  // cámara tiene que volar a un lugar propio, no a un punto dentro del bollo
  const bx = 258, by = 62;
  const nodosCaso = caso.map((c) => ({
    id: c.id, tipo: c.tipo, x: bx + c.dx, y: by + c.dy,
    _r: 5.6, _z: 1, _rotulo: c.nombre, _caso: true,
  }));
  nodes.push(...nodosCaso);
  links.push({ source: nodosCaso[1].id, target: nodosCaso[0].id, _puente: true });
  links.push({ source: nodosCaso[2].id, target: nodosCaso[0].id, _puente: true });
  // y enganchados al resto, para que no floten sueltos
  for (const c of nodosCaso) {
    const cab = cabezas[Math.floor(rnd() * cabezas.length)];
    if (cab) links.push({ source: c.id, target: cab.id, _puente: true });
  }

  // POSICIONES CONGELADAS. La composición es la que se diseñó, no la que
  // decida una simulación que además tarda en enfriarse y sale distinta cada
  // vez. Con fx/fy el dibujo aparece ya armado.
  for (const n of nodes) { n.fx = n.x; n.fy = n.y; }
  return { nodes, links, campos };
}
