// EL CEREBRO — la segunda forma de mirar el negocio.
//
// El mapa de árbol (MapaNegocio.jsx) muestra las FUENTES: ocho dominios y sus
// cortes. Esta vista muestra la capa de abajo: las ENTIDADES individuales
// —cada producto, cada cliente, cada proveedor, cada remito— y las relaciones
// reales que las cruzan. Nada de acá toca el mapa: son archivos, endpoints y
// estados separados. Si el cerebro se rompe, el mapa sigue intacto.
//
// Por qué force-directed y no un layout fijo: la posición NO se decide, se gana.
// Atracción por arista + repulsión + una gravedad proporcional al grado hacen
// que las entidades más conectadas migren solas al centro. El núcleo denso no
// está dibujado: emerge. Eso es lo que lo vuelve una demostración y no un
// adorno — mirás el centro y ahí están el proveedor clave y el rubro que sostiene
// la facturación, porque tienen más cruces que nadie.
//
// Lienzo oscuro adentro de un producto claro, a propósito: es "la vista honda".
// Los colores siguen la regla de la casa (rojo SOLO problema real, azul SOLO
// Ángela), corridos en luminosidad para leerse sobre negro.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { forceCollide, forceX, forceY } from "d3-force-3d";
import { Search, Crosshair, Maximize2, X, ArrowRight, Sparkles } from "lucide-react";
import AngelaMark from "../../components/AngelaMark";
import { api } from "../../lib/api";
import { pesoCorto, num, fecha as fmtFecha } from "../../lib/format";
import { useT, useLang } from "../../lib/i18n";
import { useSession } from "../../lib/auth";

// --- el lenguaje visual sobre negro ------------------------------------------
const TINTA_OSCURA = "#0f1113";   // el fondo del lienzo
const AZUL_IA = "#4d7bf0";        // Ángela pensando (el #2a5cdf de marca, subido para el negro)
const ROJO = "#f0564a";
const ORO = "#f0a04b";

// un color por TIPO de entidad; la forma acompaña (ver dibujarForma)
const COLOR_TIPO = {
  producto: "#4aa8bf",   // hielo: el dato duro del negocio
  cliente: "#5fbf8f",    // salvia: la plata que entra
  proveedor: "#c98a3c",  // ocre: de donde viene la mercadería
  rubro: "#8b8fa8",      // neutro: es una agrupación, no una entidad viva
  local: "#d7cfc0",      // papel: la casa
  remito: "#9d8bc4",     // el papel que circula
  cuenta: "#7fd0b0",     // salvia clara: la plata que TODAVÍA no entró
  // lo NO estructurado: lo que el equipo le contó a Ángela. Va en el amarillo
  // del post-it a propósito — es lo único acá que no salió de una tabla.
  nota: "#e8c86a",
};
const TIPOS_ORDEN = ["producto", "cliente", "proveedor", "rubro", "local", "remito", "cuenta", "nota"];

const COLOR_REL = {
  coventa: "rgba(74,168,191,0.34)",
  pertenece: "rgba(139,143,168,0.20)",
  provee: "rgba(201,138,60,0.30)",
  vende: "rgba(215,207,192,0.18)",
  debe: "rgba(95,191,143,0.42)",
  entrega: "rgba(157,139,196,0.34)",
  ordena: "rgba(201,138,60,0.38)",
  pide: "rgba(157,139,196,0.28)",
  traslado: "rgba(215,207,192,0.16)",
  // qué se lleva cada cliente: dato real (antes era la hipótesis punteada)
  compra: "rgba(95,191,143,0.40)",
  // la nota del equipo, colgada de lo que nombra
  menciona: "rgba(232,200,106,0.40)",
  // la inferida sobrevive sólo de respaldo: se dibuja punteada, como siempre
  afinidad: "rgba(95,191,143,0.26)",
};

const SECCION_LK = {
  inventario: "nav.inventario", cuentas: "nav.cuentas", finanzas: "nav.finanzas",
  caja: "nav.caja", evolucion: "nav.evolucion", documentos: "nav.documentos",
  logistica: "nav.deposito", deposito: "nav.deposito",
};

// --- formas: cada tipo se reconoce de un vistazo, sin leer -------------------
function dibujarForma(ctx, tipo, x, y, r) {
  ctx.beginPath();
  switch (tipo) {
    case "cliente": { // cuadrado redondeado
      const k = r * 0.9;
      ctx.roundRect(x - k, y - k, 2 * k, 2 * k, k * 0.32);
      return;
    }
    case "proveedor": // rombo
      ctx.moveTo(x, y - r * 1.2); ctx.lineTo(x + r * 1.2, y);
      ctx.lineTo(x, y + r * 1.2); ctx.lineTo(x - r * 1.2, y); ctx.closePath();
      return;
    case "local": // triángulo (el techo de la casa)
      ctx.moveTo(x, y - r * 1.25); ctx.lineTo(x + r * 1.15, y + r * 0.85);
      ctx.lineTo(x - r * 1.15, y + r * 0.85); ctx.closePath();
      return;
    case "rubro": { // hexágono
      for (let i = 0; i < 6; i++) {
        const a = (Math.PI / 3) * i - Math.PI / 6;
        const px = x + r * 1.1 * Math.cos(a), py = y + r * 1.1 * Math.sin(a);
        i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
      }
      ctx.closePath();
      return;
    }
    case "remito": { // hoja de papel vertical
      const w = r * 0.82, h = r * 1.15;
      ctx.roundRect(x - w, y - h, 2 * w, 2 * h, r * 0.22);
      return;
    }
    case "nota": { // post-it: cuadrado con la esquina doblada
      const k = r * 1.05;
      ctx.moveTo(x - k, y - k); ctx.lineTo(x + k, y - k);
      ctx.lineTo(x + k, y + k * 0.35); ctx.lineTo(x + k * 0.35, y + k);
      ctx.lineTo(x - k, y + k); ctx.closePath();
      return;
    }
    default: // producto y cuenta: círculo (la cuenta se dibuja hueca aparte)
      ctx.arc(x, y, r, 0, 2 * Math.PI);
  }
}

// el mismo glifo en HTML, para la leyenda y el panel
function Glifo({ tipo, size = 11 }) {
  const c = COLOR_TIPO[tipo] || "#8b8fa8";
  const s = size;
  if (tipo === "cliente") return <svg width={s} height={s} viewBox="0 0 10 10"><rect x="1" y="1" width="8" height="8" rx="2" fill={c} /></svg>;
  if (tipo === "proveedor") return <svg width={s} height={s} viewBox="0 0 10 10"><path d="M5 0.4 9.6 5 5 9.6 0.4 5Z" fill={c} /></svg>;
  if (tipo === "local") return <svg width={s} height={s} viewBox="0 0 10 10"><path d="M5 0.8 9.5 8.9H0.5Z" fill={c} /></svg>;
  if (tipo === "rubro") return <svg width={s} height={s} viewBox="0 0 10 10"><path d="M5 0.6 9.2 3v4L5 9.4 0.8 7V3Z" fill={c} /></svg>;
  if (tipo === "remito") return <svg width={s} height={s} viewBox="0 0 10 10"><rect x="2.2" y="0.8" width="5.6" height="8.4" rx="1.2" fill={c} /></svg>;
  if (tipo === "cuenta") return <svg width={s} height={s} viewBox="0 0 10 10"><circle cx="5" cy="5" r="3.6" fill="none" stroke={c} strokeWidth="1.8" /></svg>;
  return <svg width={s} height={s} viewBox="0 0 10 10"><circle cx="5" cy="5" r="4" fill={c} /></svg>;
}

// --- medir el contenedor (el lienzo necesita px, no % ) ----------------------
// Callback ref y no useRef+useEffect: mientras el grafo carga, el div medido
// NO está montado. Un efecto con deps [] observaría null y el ancho se quedaría
// en 0 para siempre — el lienzo nunca llegaría a dibujarse.
//
// Devuelve además el nodo DOM (`el`): los atajos de abajo del lienzo (el núcleo)
// tienen que poder traer la vista al grafo. Sale de acá y no de un ref inline
// porque un `ref={(x)=>{...}}` se vuelve a llamar en cada render y tiraría abajo
// el ResizeObserver una vez por frame.
function useMedida() {
  const [caja, setCaja] = useState({ w: 0, h: 0 });
  const obs = useRef(null);
  const el = useRef(null);
  const ref = useCallback((nodo) => {
    obs.current?.disconnect();
    el.current = nodo;
    if (!nodo || typeof ResizeObserver === "undefined") return;
    const medir = () => setCaja({ w: Math.round(nodo.clientWidth), h: Math.round(nodo.clientHeight) });
    medir();
    obs.current = new ResizeObserver(medir);
    obs.current.observe(nodo);
  }, []);
  useEffect(() => () => obs.current?.disconnect(), []);
  return { ref, el, ...caja };
}

// --- el buscador: normalizar y rankear ---------------------------------------
// Sin quitar tildes, "almacen" no encuentra "Almacén" y "fiambreria" no encuentra
// "Fiambrería". En un catálogo en castellano eso no es un detalle: es la mitad de
// las búsquedas que fallan y el usuario concluyendo que la entidad no está.
const normalizar = (s) =>
  (s || "").normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();

// Rango del match, de mejor a peor. Ordenar sólo por grado hace que tipear el
// nombre exacto de algo poco conectado te devuelva primero otra cosa — el
// buscador tiene que llevarte a lo que escribiste, no a lo más popular.
//   0 · el nombre EMPIEZA con lo tipeado
//   1 · empieza una palabra del nombre
//   2 · aparece en el medio
function rangoMatch(nombreNorm, q) {
  const i = nombreNorm.indexOf(q);
  if (i < 0) return -1;
  if (i === 0) return 0;
  return /[\s\-/(.,]/.test(nombreNorm[i - 1]) ? 1 : 2;
}

const MAX_RESULTADOS = 8;

// --- carga (mismo patrón P32: cache de sesión por idioma) --------------------
let _cacheGrafo = { lang: null, datos: null };
function useGrafo(langKey) {
  const [d, setD] = useState(_cacheGrafo.lang === langKey ? _cacheGrafo.datos : null);
  const [error, setError] = useState(null);
  useEffect(() => {
    let vivo = true;
    if (_cacheGrafo.lang !== langKey) setD(null);
    api.grafo()
      .then((r) => {
        if (!vivo) return;
        _cacheGrafo = { lang: langKey, datos: r };
        setD(r);
      })
      .catch((e) => vivo && setError(e));
    return () => { vivo = false; };
  }, [langKey]);
  return { datos: d, error };
}

const fmtValor = (m, t) => {
  if (m.v === null || m.v === undefined || m.v === "") return "—";
  if (m.fmt === "pesos") return pesoCorto(m.v);
  if (m.fmt === "num") return num(m.v);
  if (m.fmt === "dias") return `${num(m.v)} d`;
  if (m.fmt === "pct") return `${num(m.v)}%`;
  if (m.fmt === "fecha") return fmtFecha(m.v);
  return String(m.v);
};

// =============================================================================
export default function CerebroNegocio({ onNavegar, onPreguntar }) {
  const t = useT();
  const lang = useLang();
  const langKey = useSession()?.usuario?.idioma || lang;
  const { datos, error } = useGrafo(langKey);
  const { ref: caja, el: lienzoEl, w, h } = useMedida();
  const grafoRef = useRef(null);
  const inputRef = useRef(null);

  const [foco, setFoco] = useState(null);        // id del nodo seleccionado
  const [camino, setCamino] = useState(null);    // hallazgo encendido
  const [busqueda, setBusqueda] = useState("");
  const [leyenda, setLeyenda] = useState(false);  // el detalle de la leyenda, a pedido
  const [listo, setListo] = useState(false);     // la simulación ya se asentó

  // graphData ESTABLE: force-graph muta los objetos (les escribe x/y). Si se
  // recrea en cada render, la simulación se reinicia y el grafo tiembla.
  const gd = useMemo(() => {
    if (!datos?.nodos?.length) return null;
    const maxPeso = Math.max(1, ...datos.nodos.map((n) => n.peso || 0));
    const nodes = datos.nodos.map((n) => ({
      ...n,
      // radio: raíz del volumen (para que el grande no aplaste al chico) con
      // un piso por grado — una entidad muy cruzada se ve aunque mueva poco
      _r: 3.4 + 7.6 * Math.sqrt((n.peso || 0) / maxPeso) + Math.min(3.6, (n.grado || 0) * 0.085),
    }));
    const links = datos.aristas.map((a, i) => ({ ...a, _i: i }));
    return { nodes, links };
  }, [datos]);

  const indice = useMemo(() => {
    const m = new Map();
    (gd?.nodes || []).forEach((n) => m.set(n.id, n));
    return m;
  }, [gd]);

  // vecinos del foco: qué se ilumina al tocar un nodo
  const { vecinos, aristasFoco } = useMemo(() => {
    const v = new Set(), af = new Set();
    if (!foco || !gd) return { vecinos: v, aristasFoco: af };
    v.add(foco);
    for (const l of gd.links) {
      const s = idDe(l.source), tg = idDe(l.target);
      if (s === foco || tg === foco) { v.add(s); v.add(tg); af.add(l._i); }
    }
    return { vecinos: v, aristasFoco: af };
  }, [foco, gd]);

  // el camino de un hallazgo, ya resuelto por el backend a nodos y aristas
  const { nodosCamino, aristasCamino, caminoActual } = useMemo(() => {
    const c = (datos?.caminos || []).find((x) => x.id === camino);
    return {
      caminoActual: c || null,
      nodosCamino: new Set(c?.nodos || []),
      aristasCamino: new Set(c?.aristas || []),
    };
  }, [camino, datos]);

  const hayResalte = !!foco || !!camino;
  const enfocado = (id) => (camino ? nodosCamino.has(id) : vecinos.has(id));
  const enfocadoLink = (l) => (camino ? aristasCamino.has(l._i) : aristasFoco.has(l._i));

  // --- las fuerzas: acá nace el núcleo denso --------------------------------
  useEffect(() => {
    const fg = grafoRef.current;
    if (!fg || !gd) return;
    setListo(false);
    // distanceMax acotado: sin tope, cada nodo empuja a los 524 restantes y la
    // nube no para nunca de crecer — el encuadre queda siempre corto.
    fg.d3Force("charge")?.strength(-80).distanceMax(340);
    fg.d3Force("link")?.distance((l) => {
      // la co-venta ata corto (hace los grumos del núcleo); pertenecer a un
      // rubro ata flojo (si no, los 8 rubros se comen la pantalla)
      if (l.rel === "coventa") return 26;
      if (l.rel === "pertenece") return 82;
      if (l.rel === "vende" || l.rel === "traslado") return 110;
      return 54;
    })?.strength((l) => (l.rel === "coventa" ? 0.55 : l.rel === "pertenece" ? 0.12 : 0.3));
    fg.d3Force("collide", forceCollide((n) => n._r + 1.6).iterations(2));
    // gravedad proporcional al grado: cuanto más cruzada la entidad, más fuerte
    // la tira el centro. Esto NO decide quién va al medio — lo decide el dato.
    // El piso de 0.038 no es decorativo: sin él la periferia se escapa tan lejos
    // que el zoomToFit tiene que abrir el encuadre y el núcleo queda del tamaño
    // de una moneda en un lienzo negro.
    const g = (n) => 0.055 + Math.min(0.10, (n.grado || 0) * 0.0026);
    fg.d3Force("x", forceX(0).strength(g));
    fg.d3Force("y", forceY(0).strength(g));
    fg.d3ReheatSimulation?.();
  }, [gd]);

  // encuadre inicial. onEngineStop es la señal buena, pero con ~540 nodos y ~1850
  // aristas la simulación puede no llegar a frenar sola: sin un plan B el grafo
  // se queda chiquito en el medio del lienzo y sin etiquetas (listo=false).
  const alQuedarQuieto = useCallback(() => {
    setListo(true);
    grafoRef.current?.zoomToFit(700, 34);
  }, []);

  // si el usuario ya eligió algo, el plan B no le mueve la cámara por debajo
  const tocado = useRef(false);
  tocado.current = !!foco || !!camino;
  useEffect(() => {
    if (!gd || !w) return;
    const encuadrar = () => { if (!tocado.current) grafoRef.current?.zoomToFit(700, 34); };
    // tres pasadas: la nube sigue creciendo un rato después del primer encuadre
    const t1 = setTimeout(() => { setListo(true); encuadrar(); }, 2600);
    const t2 = setTimeout(encuadrar, 5200);
    const t3 = setTimeout(encuadrar, 9000);
    const t4 = setTimeout(encuadrar, 14000);
    return () => [t1, t2, t3, t4].forEach(clearTimeout);
  }, [gd, w]);

  // IR A UNA ENTIDAD — el gesto central del cerebro. Lo usan el buscador, los
  // chips del núcleo, el panel y el clic en el lienzo: una sola forma de llegar.
  //
  // Dos cosas que no son obvias:
  //  · el nodo puede no tener x/y todavía (la simulación recién arrancó, o el
  //    grafo se acaba de rearmar por cambio de idioma). Antes eso significaba
  //    que el buscador "no hacía nada"; ahora reintenta un par de frames.
  //  · los atajos del núcleo viven DEBAJO del lienzo: si no se trae la vista al
  //    grafo, el usuario toca un chip y no ve moverse nada.
  const irAlNodo = useCallback((id) => {
    setFoco(id);
    lienzoEl.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    let intentos = 0;
    const apuntar = () => {
      const n = indice.get(id);
      if (n && Number.isFinite(n.x) && Number.isFinite(n.y)) {
        grafoRef.current?.centerAt(n.x, n.y, 800);
        grafoRef.current?.zoom(2.6, 800);
        return;
      }
      if (++intentos < 12) setTimeout(apuntar, 120);
    };
    apuntar();
  }, [indice, lienzoEl]);

  // al encender un camino, encuadrar SOLO ese camino: el hallazgo se ve entero
  useEffect(() => {
    if (!camino || !grafoRef.current) return;
    const tmr = setTimeout(() => {
      grafoRef.current?.zoomToFit(900, 90, (n) => nodosCamino.has(n.id));
    }, 80);
    return () => clearTimeout(tmr);
  }, [camino, nodosCamino]);

  // El índice de nombres normalizados se arma UNA vez por grafo: normalizar ~540
  // nombres en cada tecla se nota al tipear, y el buscador tiene que ir liso.
  const nombresNorm = useMemo(() => {
    const m = new Map();
    (gd?.nodes || []).forEach((n) => m.set(n.id, normalizar(n.nombre)));
    return m;
  }, [gd]);

  const { resultados, totalMatches } = useMemo(() => {
    const q = normalizar(busqueda.trim());
    if (q.length < 2) return { resultados: [], totalMatches: 0 };
    const hits = [];
    for (const n of gd?.nodes || []) {
      const rango = rangoMatch(nombresNorm.get(n.id) || "", q);
      if (rango >= 0) hits.push({ n, rango });
    }
    hits.sort((a, b) => a.rango - b.rango || (b.n.grado || 0) - (a.n.grado || 0));
    return {
      resultados: hits.slice(0, MAX_RESULTADOS).map((h) => h.n),
      totalMatches: hits.length,
    };
  }, [busqueda, gd, nombresNorm]);

  // el resultado marcado con el teclado; vuelve al primero en cada tecleo
  const [sel, setSel] = useState(0);
  useEffect(() => { setSel(0); }, [busqueda]);

  const elegirResultado = useCallback((n) => {
    if (!n) return;
    setBusqueda("");
    setCamino(null);
    irAlNodo(n.id);
    inputRef.current?.blur();
  }, [irAlNodo]);

  // Tipear y que te lleve: ↓/↑ recorren, Enter entra, Esc suelta. Sin esto hay
  // que soltar el teclado y buscar el ítem con el mouse, que es justamente la
  // fricción que este buscador viene a sacar.
  const teclaBusqueda = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setSel((i) => Math.min(i + 1, resultados.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setSel((i) => Math.max(i - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); elegirResultado(resultados[sel]); }
    else if (e.key === "Escape") { e.preventDefault(); setBusqueda(""); inputRef.current?.blur(); }
  };

  // "/" desde cualquier parte de la sección enfoca el buscador: es el acceso
  // principal al cerebro, no una caja más de la pantalla.
  useEffect(() => {
    const onKey = (e) => {
      if (e.key !== "/" || e.metaKey || e.ctrlKey || e.altKey) return;
      const tag = (e.target?.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || e.target?.isContentEditable) return;
      e.preventDefault();
      inputRef.current?.focus();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const nodoFoco = foco ? indice.get(foco) : null;
  const relacionesFoco = useMemo(() => {
    if (!foco || !gd) return [];
    return gd.links
      .filter((l) => idDe(l.source) === foco || idDe(l.target) === foco)
      .map((l) => {
        const otroId = idDe(l.source) === foco ? idDe(l.target) : idDe(l.source);
        return { rel: l.rel, otro: indice.get(otroId), lift: l.lift, monto: l.monto };
      })
      .filter((r) => r.otro)
      .sort((a, b) => (b.otro.peso || 0) - (a.otro.peso || 0));
  }, [foco, gd, indice]);

  // ---------------------------------------------------------------- estados
  if (error) {
    return <div className="rounded-card border border-linea bg-crema p-6 text-sm text-tinta-suave">
      {error.criollo || String(error.message)}
    </div>;
  }
  if (!datos) {
    return <div className="flex h-[70vh] items-center justify-center rounded-card border border-linea bg-crema">
      <div className="flex items-center gap-3 text-sm text-tinta-suave">
        <span className="size-2 animate-ping rounded-full bg-violeta" />
        {t("cerebro.cargando")}
      </div>
    </div>;
  }
  if (!datos.disponible || !gd) {
    return <div className="rounded-card border border-linea bg-crema p-8 text-center text-sm text-tinta-suave">
      {t("cerebro.vacio")}
    </div>;
  }

  const meta = datos.meta || {};

  return (
    <div className="space-y-4">
      {/* ------------------------------------------------------ encabezado */}
      <div>
        <h2 className="font-display text-[22px] font-semibold tracking-tight text-tinta">
          {t("cerebro.titulo")}
        </h2>
        <p className="mt-1 max-w-5xl text-[13px] leading-snug text-tinta-suave">
          {t("cerebro.bajada", { nodos: num(meta.nodos), aristas: num(meta.aristas) })}
        </p>
      </div>

      {/* ------------------------------------- los hallazgos con su camino
          LA PUERTA DE ENTRADA. El cerebro no se explora a ciegas: se entra por
          un hallazgo y se mira de dónde salió. Por eso esto va ARRIBA del
          lienzo, con el borde de Ángela — y por eso, con el camino encendido,
          las entidades de ese camino quedan acá abajo para recorrerlas una por
          una sin perder la iluminación. */}
      {!!datos.caminos?.length && (
        <div className="rounded-card border bg-crema p-4" style={{ borderColor: `${AZUL_IA}3d` }}>
          <div className="flex items-baseline gap-2">
            <AngelaMark size={14} />
            <span className="text-[13px] font-semibold text-tinta">{t("cerebro.hallazgos")}</span>
            <span className="text-[12px] text-tinta-suave">· {t("cerebro.hallazgos_ay")}</span>
          </div>
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {datos.caminos.map((c) => {
              const on = camino === c.id;
              return (
                <button key={c.id}
                  onClick={() => {
                    setCamino(on ? null : c.id);
                    setFoco(null);
                    if (!on) lienzoEl.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
                  }}
                  aria-pressed={on}
                  className={`rounded-full border px-3 py-1.5 text-left text-[12px] transition-colors ${
                    on ? "border-violeta bg-violeta text-white"
                       : "border-linea bg-papel text-tinta hover:border-violeta/50 hover:bg-violeta-suave"}`}>
                  {c.titulo}
                  {/* cuántos DOMINIOS distintos tuvo que juntar para verlo: es
                      la diferencia entre un cruce y una alerta de una fuente */}
                  {c.dominios?.length > 1 && (
                    <span className={`ml-1.5 tabular-nums ${on ? "text-white/70" : "text-violeta"}`}>
                      {c.dominios.length}⨯
                    </span>
                  )}
                  <span className={`ml-1 tabular-nums ${on ? "text-white/70" : "text-tinta-suave"}`}>
                    {c.nodos.length}
                  </span>
                </button>
              );
            })}
            {camino && (
              <button onClick={() => { setCamino(null); setFoco(null); }}
                className="rounded-full px-3 py-1.5 text-[12px] text-tinta-suave underline underline-offset-2 hover:text-tinta">
                {t("cerebro.camino_off")}
              </button>
            )}
          </div>

          {/* el camino, RECORRIBLE: cada entidad que participó del cruce, en
              orden, sin tener que cazarla con el mouse en el lienzo. Al tocarla
              se abre su ficha y el camino sigue encendido. */}
          {caminoActual && (
            <div className="mt-3 border-t border-linea pt-2.5">
              {/* QUÉ CRUZÓ y POR QUÉ. Sin esto el camino es un dibujo lindo:
                  acá se lee la cadena de razonamiento con los números que la
                  sostienen (los calcula el backend, no el modelo). */}
              {caminoActual.resumen && (
                <p className="mb-2 text-[12.5px] leading-snug text-tinta">{caminoActual.resumen}</p>
              )}
              {caminoActual.dominios?.length > 0 && (
                <div className="mb-2 flex flex-wrap items-center gap-1.5">
                  <span className="text-[11px] text-tinta-suave">{t("cerebro.cruzo")}</span>
                  {caminoActual.dominios.map((d) => (
                    <span key={d} className="rounded-full border border-violeta/30 bg-violeta-suave
                                             px-2 py-0.5 text-[10.5px] font-semibold text-violeta-hondo">
                      {t(`cerebro.dom_${d}`)}
                    </span>
                  ))}
                  {caminoActual.no_estructurado && (
                    <span className="rounded-full px-2 py-0.5 text-[10.5px] font-semibold"
                      style={{ background: "rgba(232,200,106,0.18)", color: "#8a6d1f" }}
                      title={t("cerebro.no_estructurado_ay")}>
                      {t("cerebro.no_estructurado")}
                    </span>
                  )}
                </div>
              )}
              {caminoActual.porque?.length > 0 && (
                <ul className="mb-2.5 space-y-0.5">
                  {caminoActual.porque.map((p, i) => (
                    <li key={i} className="flex gap-1.5 text-[11.5px] leading-snug text-tinta-suave">
                      <span className="mt-[7px] size-1 shrink-0 rounded-full bg-violeta/60" />
                      <span>{p}</span>
                    </li>
                  ))}
                </ul>
              )}
              <div className="text-[11px] text-tinta-suave">
                {t("cerebro.camino_recorrer", { n: nodosCamino.size })}
              </div>
              <div className="mt-1.5 flex flex-wrap gap-1">
                {[...nodosCamino].map((id) => {
                  const n = indice.get(id);
                  if (!n) return null;
                  const esSemilla = (caminoActual.semillas || []).includes(id);
                  return (
                    <button key={id} onClick={() => irAlNodo(id)}
                      className={`flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11.5px]
                                  transition-colors hover:border-violeta/50 hover:bg-violeta-suave ${
                        foco === id ? "border-violeta bg-violeta-suave text-tinta"
                                    : "border-linea bg-papel text-tinta"}`}>
                      <Glifo tipo={n.tipo} size={9} />
                      <span className="max-w-[168px] truncate">{n.nombre}</span>
                      {esSemilla && (
                        <span className="size-1.5 shrink-0 rounded-full" style={{ background: AZUL_IA }}
                          title={t("cerebro.camino_semilla")} />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ------------------------------------------------------- el lienzo */}
      {/* la altura se calcula contra lo que hay ARRIBA (encabezado + chips de
          hallazgos): con 68vh fijo el lienzo entraba pero quedaba cortado por el
          borde de la pantalla, y el cerebro es lo que hay que ver sin scrollear */}
      <div ref={caja}
        className="relative h-[clamp(440px,calc(100vh-395px),820px)] overflow-hidden
                   rounded-card border border-linea"
        style={{ background: TINTA_OSCURA }}>

        {/* BUSCADOR — el acceso principal al cerebro.
            Con ~540 entidades, buscar con el ojo en la maraña no es navegar: es
            suerte. Acá se tipea y te lleva — sin tildes, rankeado por lo que
            escribiste (no por lo más popular), y todo con el teclado. */}
        <div className="absolute left-4 top-4 z-20 w-[286px]">
          <div className="flex items-center gap-2 rounded-full border border-white/12 bg-black/45 px-3 py-1.5 backdrop-blur
                          focus-within:border-white/35">
            <Search className="size-3.5 shrink-0 text-white/45" />
            <input ref={inputRef} value={busqueda} onChange={(e) => setBusqueda(e.target.value)}
              onKeyDown={teclaBusqueda}
              placeholder={t("cerebro.buscar")}
              aria-label={t("cerebro.buscar")} autoComplete="off"
              className="w-full bg-transparent text-[12.5px] text-white placeholder:text-white/35 focus:outline-none" />
            {busqueda
              ? <button onClick={() => { setBusqueda(""); inputRef.current?.focus(); }}
                  aria-label={t("cerebro.limpiar_busqueda")} className="text-white/45 hover:text-white">
                  <X className="size-3.5" /></button>
              // la pista de la barra "/" sólo mientras está vacío: después estorba
              : <kbd className="shrink-0 rounded border border-white/15 px-1 text-[9.5px] leading-4 text-white/35">/</kbd>}
          </div>
          {busqueda.trim().length >= 2 && (
            <div className="mt-1.5 overflow-hidden rounded-xl border border-white/12 bg-black/85 backdrop-blur">
              {resultados.length === 0
                ? <div className="px-3 py-2 text-[12px] text-white/45">{t("cerebro.sin_resultados")}</div>
                : resultados.map((n, i) => (
                  <button key={n.id} onClick={() => elegirResultado(n)}
                    onMouseEnter={() => setSel(i)}
                    className={`flex w-full items-center gap-2 px-3 py-1.5 text-left transition-colors ${
                      i === sel ? "bg-white/12" : "hover:bg-white/8"}`}>
                    <span className="shrink-0"><Glifo tipo={n.tipo} /></span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[12px] leading-tight text-white/90">{n.nombre}</span>
                      {/* qué es y cuánto se cruza: dos nombres parecidos se
                          distinguen acá, no después de haber navegado */}
                      <span className="block truncate text-[10px] leading-tight text-white/40">
                        {t(`cerebro.t_${n.tipo}`)} · {t(n.grado === 1 ? "cerebro.conexiones_1" : "cerebro.conexiones", { n: n.grado })}
                      </span>
                    </span>
                  </button>
                ))}
              {totalMatches > resultados.length && (
                <div className="border-t border-white/10 px-3 py-1 text-[10px] text-white/35">
                  {t("cerebro.mas_coincidencias", { n: totalMatches - resultados.length })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* cámara — se corre a la izquierda cuando el panel de la entidad ocupa
            la derecha, si no queda debajo y no se puede soltar el foco */}
        <div className={`absolute top-4 z-20 flex gap-1.5 ${nodoFoco ? "right-[334px]" : "right-4"}`}>
          {(foco || camino) && (
            <BotonLienzo onClick={() => { setFoco(null); setCamino(null); }}>
              <X className="size-3.5" /> {t("cerebro.limpiar")}
            </BotonLienzo>
          )}
          {foco && (
            <BotonLienzo onClick={() => irAlNodo(foco)}>
              <Crosshair className="size-3.5" /> {t("cerebro.centrar")}
            </BotonLienzo>
          )}
          <BotonLienzo onClick={() => grafoRef.current?.zoomToFit(800, 70)}>
            <Maximize2 className="size-3.5" /> {t("cerebro.toda_la_red")}
          </BotonLienzo>
        </div>

        {/* leyenda: lo imprescindible siempre visible, el resto a pedido — si no,
            tapa el propio grafo que viene a explicar */}
        <div className="absolute bottom-4 left-4 z-20 max-w-[430px] rounded-xl border border-white/10
                        bg-black/60 p-2.5 backdrop-blur">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            {TIPOS_ORDEN.filter((tp) => meta.por_tipo?.[tp]).map((tp) => (
              <span key={tp} className="flex items-center gap-1.5 text-[10.5px] text-white/70">
                <Glifo tipo={tp} /> {t(`cerebro.t_${tp}_p`)}
                <span className="tabular-nums text-white/35">{meta.por_tipo[tp]}</span>
              </span>
            ))}
            <button onClick={() => setLeyenda((v) => !v)}
              className="ml-auto flex size-4 items-center justify-center rounded-full border
                         border-white/25 text-[9px] text-white/60 hover:border-white/60 hover:text-white"
              aria-label={t("cerebro.leyenda")} aria-expanded={leyenda}>
              {leyenda ? "×" : "?"}
            </button>
          </div>
          {leyenda && (
            <div className="mt-2 space-y-1.5 border-t border-white/10 pt-2">
              <div className="flex items-start gap-1.5 text-[10.5px] text-white/55">
                <span className="mt-0.5 inline-block size-2.5 shrink-0 rounded-full border-[1.5px]"
                  style={{ borderColor: ROJO }} />
                {t("cerebro.leyenda_riesgo")}
              </div>
              <div className="text-[10.5px] text-white/45">{t("cerebro.leyenda_nucleo")}</div>
              {!!meta.por_tipo?.nota && (
                <div className="flex gap-1.5 text-[10.5px] text-white/45">
                  <span className="mt-0.5 shrink-0"><Glifo tipo="nota" /></span>
                  <span>{t("cerebro.nota_equipo")}</span>
                </div>
              )}
              {!!meta.derivados?.afinidad?.aristas && (
                <div className="flex gap-1.5 text-[10.5px] text-white/45">
                  <svg width="16" height="8" className="mt-1 shrink-0" aria-hidden>
                    <line x1="0" y1="4" x2="16" y2="4" stroke="rgba(95,191,143,.7)"
                      strokeWidth="1.2" strokeDasharray="2 3" />
                  </svg>
                  <span>{t("cerebro.nota_inferida")}</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* estado del camino encendido — con el TÍTULO del hallazgo: sin él, la
            franja dice "camino encendido" y hay que acordarse cuál se tocó */}
        {caminoActual && (
          <div className="pointer-events-none absolute left-1/2 top-4 z-20 max-w-[52%] -translate-x-1/2
                          rounded-full border px-4 py-1.5 backdrop-blur"
            style={{ borderColor: `${AZUL_IA}66`, background: "rgba(15,17,19,.8)" }}>
            <span className="flex items-center gap-2 text-[12px] text-white/85">
              <Sparkles className="size-3.5 shrink-0" style={{ color: AZUL_IA }} />
              <span className="truncate">{caminoActual.titulo}</span>
              <span className="shrink-0 text-white/50">
                · {t("cerebro.camino_on", { n: nodosCamino.size })}
              </span>
            </span>
          </div>
        )}

        {/* --------------------------------------------------- el grafo */}
        {w > 0 && (
          <ForceGraph2D
            ref={grafoRef}
            width={w} height={h}
            graphData={gd}
            backgroundColor={TINTA_OSCURA}
            cooldownTicks={220}
            onEngineStop={alQuedarQuieto}
            minZoom={0.12} maxZoom={9}
            // caminar DENTRO del camino no lo apaga: si el nodo que se toca es
            // parte del cruce, la iluminación se queda (se está recorriendo el
            // hallazgo). Salirse del camino sí lo suelta.
            onNodeClick={(n) => { if (!nodosCamino.has(n.id)) setCamino(null); irAlNodo(n.id); }}
            onBackgroundClick={() => { setFoco(null); setCamino(null); }}
            nodeLabel={(n) => `${n.nombre} · ${t(`cerebro.t_${n.tipo}`)}`}
            linkColor={(l) => (hayResalte
              ? (enfocadoLink(l) ? (camino ? AZUL_IA : "rgba(255,255,255,0.55)") : "rgba(255,255,255,0.035)")
              : (COLOR_REL[l.rel] || "rgba(255,255,255,0.10)"))}
            linkWidth={(l) => (enfocadoLink(l) ? 1.7 : 0.55)}
            // punteada = hipótesis, no dato (ver meta.derivados.afinidad)
            linkLineDash={(l) => (l.inferida ? [2, 3] : null)}
            // las partículas recorren el camino: se VE por dónde pensó Ángela
            linkDirectionalParticles={(l) => (camino && enfocadoLink(l) ? 3 : 0)}
            linkDirectionalParticleWidth={2.2}
            linkDirectionalParticleSpeed={0.006}
            linkDirectionalParticleColor={() => AZUL_IA}
            nodePointerAreaPaint={(n, color, ctx) => {
              if (!Number.isFinite(n.x) || !Number.isFinite(n.y)) return;
              ctx.fillStyle = color;
              ctx.beginPath();
              ctx.arc(n.x, n.y, n._r + 3.5, 0, 2 * Math.PI);
              ctx.fill();
            }}
            nodeCanvasObject={(n, ctx, escala) => {
              // al cambiar de idioma el grafo se rearma y hay un frame donde los
              // nodos todavía no tienen x/y: createRadialGradient con NaN lanza y
              // se lleva puesto el componente entero. Ese frame se saltea.
              if (!Number.isFinite(n.x) || !Number.isFinite(n.y)) return;
              const r = n._r;
              const esFoco = n.id === foco;
              const dentro = hayResalte ? enfocado(n.id) : true;
              const semilla = camino && (datos.caminos.find((c) => c.id === camino)?.semillas || []).includes(n.id);

              ctx.save();
              if (!dentro) ctx.globalAlpha = 0.13;

              // halo: el foco elegido, o la semilla del hallazgo (en azul-Ángela)
              if (esFoco || semilla) {
                const grad = ctx.createRadialGradient(n.x, n.y, r, n.x, n.y, r + 11);
                const base = semilla ? AZUL_IA : "#ffffff";
                grad.addColorStop(0, `${base}55`);
                grad.addColorStop(1, `${base}00`);
                ctx.beginPath(); ctx.arc(n.x, n.y, r + 11, 0, 2 * Math.PI);
                ctx.fillStyle = grad; ctx.fill();
              }

              // cuerpo: forma + color por TIPO
              const color = COLOR_TIPO[n.tipo] || "#8b8fa8";
              dibujarForma(ctx, n.tipo, n.x, n.y, r);
              if (n.tipo === "cuenta") {           // la cuenta va hueca: es un saldo, no una cosa
                ctx.lineWidth = Math.max(0.7, r * 0.36);
                ctx.strokeStyle = color; ctx.stroke();
              } else {
                ctx.fillStyle = color; ctx.fill();
                ctx.lineWidth = Math.max(0.35, r * 0.1);
                ctx.strokeStyle = "rgba(0,0,0,0.5)"; ctx.stroke();
              }

              // anillo = señal. Rojo SOLO problema real, ámbar = para mirar.
              if (n.riesgo === "riesgo" || n.riesgo === "atencion") {
                ctx.beginPath(); ctx.arc(n.x, n.y, r + 2.3, 0, 2 * Math.PI);
                ctx.strokeStyle = n.riesgo === "riesgo" ? ROJO : ORO;
                ctx.lineWidth = n.riesgo === "riesgo" ? 1.25 : 0.9;
                ctx.stroke();
              }

              // etiquetas: el foco y su círculo siempre; el resto al acercarse,
              // y priorizando lo grande (si no, el núcleo es una sopa de texto)
              const grande = r > 5.2;
              const muestra = esFoco || semilla || (dentro && hayResalte && escala > 0.6)
                || (!hayResalte && (escala > 2.2 || (grande && escala > 0.7)));
              if (muestra && listo) {
                const fs = Math.max(2.6, (esFoco ? 5.2 : 4.1) / Math.sqrt(escala));
                ctx.font = `${esFoco || semilla ? 600 : 400} ${fs}px "Hanken Grotesk", sans-serif`;
                ctx.textAlign = "center"; ctx.textBaseline = "top";
                const txt = n.nombre.length > 34 ? `${n.nombre.slice(0, 33)}…` : n.nombre;
                const ancho = ctx.measureText(txt).width;
                const ty = n.y + r + 2.4;
                ctx.fillStyle = "rgba(15,17,19,0.74)";
                ctx.beginPath();
                ctx.roundRect(n.x - ancho / 2 - 2, ty - 1, ancho + 4, fs + 2.2, 2);
                ctx.fill();
                ctx.fillStyle = esFoco ? "#ffffff" : semilla ? AZUL_IA : "rgba(245,245,244,0.82)";
                ctx.fillText(txt, n.x, ty);
              }
              ctx.restore();
            }}
          />
        )}

        {/* ------------------------------------------ panel de la entidad */}
        {nodoFoco && (
          <PanelEntidad nodo={nodoFoco} relaciones={relacionesFoco} t={t}
            onIr={(id) => irAlNodo(id)} onCerrar={() => setFoco(null)}
            onNavegar={onNavegar} onPreguntar={onPreguntar} />
        )}
      </div>

      {/* ------------------------------------ el núcleo, dicho con palabras */}
      <div className="grid gap-3 lg:grid-cols-[1fr_auto]">
        <div className="rounded-card border border-linea bg-crema p-4">
          <div className="text-[13px] font-semibold text-tinta">{t("cerebro.nucleo_titulo")}</div>
          <div className="text-[12px] text-tinta-suave">{t("cerebro.nucleo_ay")}</div>
          {/* ATAJOS a lo más conectado. Viven abajo del lienzo, así que tocar
              uno trae la vista al grafo además de centrar el nodo (ver irAlNodo);
              si no, se toca un chip y aparentemente no pasa nada. */}
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {(meta.nucleo || []).map((n) => (
              <button key={n.id} onClick={() => { setCamino(null); irAlNodo(n.id); }}
                aria-pressed={foco === n.id}
                className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[12px] text-tinta
                            transition-colors hover:border-violeta/50 hover:bg-violeta-suave ${
                  foco === n.id ? "border-violeta bg-violeta-suave" : "border-linea bg-papel"}`}>
                <Glifo tipo={n.tipo} />
                <span className="max-w-[190px] truncate">{n.nombre}</span>
                <span className="tabular-nums text-tinta-suave">{t(n.grado === 1 ? "cerebro.conexiones_1" : "cerebro.conexiones", { n: n.grado })}</span>
              </button>
            ))}
          </div>
        </div>
        {!!meta.derivados?.coventa?.pares && (
          <div className="rounded-card border border-linea bg-papel-hondo p-4 lg:max-w-[300px]">
            <div className="text-[11px] uppercase tracking-wide text-tinta-suave">
              {t("cerebro.leyenda_formas")}
            </div>
            <p className="mt-1.5 text-[12px] leading-relaxed text-tinta-suave">
              {t("cerebro.nota_derivado", { pares: num(meta.derivados.coventa.pares) })}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// force-graph reemplaza source/target por el objeto del nodo después del primer tick
const idDe = (x) => (typeof x === "object" && x !== null ? x.id : x);

function BotonLienzo({ onClick, children }) {
  return (
    <button onClick={onClick}
      className="flex items-center gap-1.5 rounded-full border border-white/12 bg-black/45 px-3 py-1.5
                 text-[12px] text-white/80 backdrop-blur transition-colors hover:border-white/30 hover:text-white">
      {children}
    </button>
  );
}

function PanelEntidad({ nodo, relaciones, t, onIr, onCerrar, onNavegar, onPreguntar }) {
  const lang = useLang();     // la nota del equipo se lee en el idioma del que mira
  const seccion = nodo.seccion;
  const lkSeccion = SECCION_LK[seccion];
  const porRel = relaciones.reduce((acc, r) => {
    (acc[r.rel] = acc[r.rel] || []).push(r); return acc;
  }, {});
  // el dato primero, la hipótesis al final: la afinidad es lo único inferido y
  // no puede encabezar la ficha de una entidad
  const grupos = Object.entries(porRel)
    .sort(([a], [b]) => (a === "afinidad") - (b === "afinidad"));

  return (
    <div className="absolute right-0 top-0 z-30 flex h-full w-[318px] flex-col border-l border-white/10
                    bg-[#141719]/95 backdrop-blur">
      <div className="flex items-start gap-2.5 border-b border-white/10 p-4">
        <span className="mt-1 shrink-0"><Glifo tipo={nodo.tipo} size={13} /></span>
        <div className="min-w-0 flex-1">
          <div className="text-[10.5px] uppercase tracking-wide text-white/40">
            {t(`cerebro.t_${nodo.tipo}`)}
          </div>
          <h3 className="text-[15.5px] font-semibold leading-snug text-white">{nodo.nombre}</h3>
          {(nodo.riesgo === "riesgo" || nodo.riesgo === "atencion") && (
            <span className="mt-1.5 inline-block rounded-full px-2 py-0.5 text-[10.5px]"
              style={{
                color: nodo.riesgo === "riesgo" ? ROJO : ORO,
                background: nodo.riesgo === "riesgo" ? `${ROJO}1f` : `${ORO}1f`,
              }}>
              ● {t(nodo.riesgo === "riesgo" ? "cerebro.riesgo_alto" : "cerebro.riesgo_medio")}
            </span>
          )}
        </div>
        <button onClick={onCerrar} className="shrink-0 text-white/40 hover:text-white">
          <X className="size-4" />
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {/* Una nota no tiene números: tiene TEXTO. Es lo único del grafo que
            escribió una persona, y se lee tal cual lo dijo. */}
        {nodo.tipo === "nota" && (nodo.texto || nodo.texto_en) && (
          <p className="mb-3 rounded-lg border border-white/10 bg-white/[0.04] p-2.5
                        text-[12.5px] italic leading-snug text-white/80">
            “{lang === "en" && nodo.texto_en ? nodo.texto_en : nodo.texto}”
          </p>
        )}
        {/* números de la entidad */}
        <div className="grid grid-cols-2 gap-x-3 gap-y-2.5">
          {(nodo.metricas || []).filter((m) => m.v !== null && m.v !== undefined && m.v !== "").map((m) => (
            <div key={m.k}>
              <div className="text-[10px] uppercase tracking-wide text-white/40">{t(`cerebro.m_${m.k}`)}</div>
              <div className="mt-0.5 text-[13.5px] font-semibold tabular-nums text-white/90">
                {fmtValor(m, t)}
              </div>
            </div>
          ))}
          {nodo.vence && (
            <div>
              <div className="text-[10px] uppercase tracking-wide text-white/40">{t("cerebro.m_vence")}</div>
              <div className="mt-0.5 text-[13.5px] font-semibold tabular-nums" style={{ color: ORO }}>
                {fmtFecha(nodo.vence)}
              </div>
            </div>
          )}
          <div>
            <div className="text-[10px] uppercase tracking-wide text-white/40">{t("cerebro.m_grado")}</div>
            <div className="mt-0.5 text-[13.5px] font-semibold tabular-nums text-white/90">{nodo.grado}</div>
          </div>
        </div>

        {/* con quién se cruza */}
        <div className="mt-5">
          <div className="text-[11px] font-semibold text-white/70">
            {t("cerebro.relaciones", { n: relaciones.length })}
          </div>
          {relaciones.length === 0 && (
            <div className="mt-1 text-[12px] text-white/40">{t("cerebro.sin_relaciones")}</div>
          )}
          {grupos.map(([rel, items]) => (
            <div key={rel} className="mt-3">
              <div className="text-[10.5px] uppercase tracking-wide text-white/35">{t(`cerebro.r_${rel}`)}</div>
              <div className="mt-1 space-y-0.5">
                {items.slice(0, 12).map((r, i) => (
                  <button key={`${r.otro.id}-${i}`} onClick={() => onIr(r.otro.id)}
                    className="flex w-full items-center gap-2 rounded-lg px-1.5 py-1 text-left hover:bg-white/6">
                    <Glifo tipo={r.otro.tipo} />
                    <span className="min-w-0 flex-1 truncate text-[12px] text-white/80">{r.otro.nombre}</span>
                    {r.lift && <span className="shrink-0 text-[10.5px] tabular-nums text-white/35">×{r.lift}</span>}
                    {!r.lift && !!r.monto && <span className="shrink-0 text-[10.5px] tabular-nums text-white/35">{pesoCorto(r.monto)}</span>}
                  </button>
                ))}
                {items.length > 12 && (
                  <div className="px-1.5 text-[10.5px] text-white/30">+{items.length - 12}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* acciones: el cerebro devuelve al producto, no es un callejón */}
      <div className="flex gap-2 border-t border-white/10 p-3">
        {lkSeccion && onNavegar && (
          <button onClick={() => onNavegar(seccion, null)}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-full bg-white/8 px-3 py-2
                       text-[12px] text-white/85 transition-colors hover:bg-white/14">
            {t("cerebro.ir_a", { seccion: t(lkSeccion) })} <ArrowRight className="size-3.5" />
          </button>
        )}
        {onPreguntar && (
          <button onClick={() => onPreguntar(`contame todo sobre ${nodo.nombre}`)}
            className="flex items-center justify-center gap-1.5 rounded-full px-3 py-2 text-[12px] font-medium
                       transition-opacity hover:opacity-85"
            style={{ background: `${AZUL_IA}26`, color: AZUL_IA }}>
            <AngelaMark size={13} /> {t("cerebro.preguntar")}
          </button>
        )}
      </div>
    </div>
  );
}
