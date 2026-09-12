import { useEffect, useMemo, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Treemap, Tooltip } from "recharts";
import { Search, Sparkles, Lock, X } from "lucide-react";
import AngelaMark from "../../components/AngelaMark";
import AngelaSays from "../../components/AngelaSays";
import { useCountUp } from "../../lib/useCountUp";
import { useVista, vistaStore } from "../../lib/vistaStore";
import { useFoco, focoStore } from "../../lib/focoStore";
import Widget from "../../components/Widget";
import Margenes from "./Margenes";
import Reponer from "./Reponer";
import { peso, pesoCorto, num } from "../../lib/format";
import { api } from "../../lib/api";
import { ALERTA_DEFS } from "../../lib/alertas";
import { GRAFICO } from "../../lib/paleta";
import { tealSecuencial, textoSobre } from "../../components/charts/tema";
import { resaltarPorId } from "../../lib/navGuiada";
import { useT } from "../../lib/i18n";

// P16: el subtab "balanzas" murió — un producto de balanza es un producto más
// (se pricea distinto): vive como filtro "Por kg" de la tabla completa.
const SUBTABS = [
  { id: "panorama", lk: "inventario.tab_panorama" },
  // P38·C — el margen por grupo: LA pregunta del dueño, con sus dos canales.
  { id: "margenes", lk: "inventario.tab_margenes" },
  // Bloque D — la card de quiebre muestra UN producto; acá está el orden
  // completo de qué reponer primero, con la plata que cuesta no hacerlo.
  { id: "reponer", lk: "inventario.tab_reponer" },
  { id: "problemas", lk: "inventario.tab_problemas" },
];
const GRUPOS = ["fantasmas", "negativos", "sin_pvp", "balanza"];

// P38·A — la barra de filtros del stock quedó en CUATRO entradas:
// Todos · Activos · Balanza · Datos a corregir.
//   · "Balanza" absorbió a "Por kg": son lo mismo (lo que se vende por peso).
//     El viejo filtro "Balanza" (peso teórico fuera de rango) NO era una forma
//     de vender: era un error de calibración → se fue con los demás errores.
//   · Fantasma / Negativo / Sin precio / Peso mal calibrado / Costo viejo son
//     errores de DATOS: viven agrupados bajo "Datos a corregir" con su conteo.
//     NO se esconden del stock — siguen en "Todos", en rojo y con su etiqueta.
const ERRORES_DATO = ["fantasma", "negativo", "sin_precio", "balanza", "costo_viejo"];

// Estado de calidad → etiqueta (lk del diccionario) + color (para badges de la tabla).
const ESTADO_CAL = {
  ok: { lk: "inventario.estado_ok", cls: "bg-salvia/15 text-salvia" },
  fantasma: { lk: "inventario.estado_fantasma", cls: "bg-rojo/12 text-rojo" },
  negativo: { lk: "inventario.estado_negativo", cls: "bg-rojo/12 text-rojo" },
  sin_precio: { lk: "inventario.estado_sin_precio", cls: "bg-oro/20 text-oro-tinta" },
  balanza: { lk: "inventario.estado_balanza", cls: "bg-oro/20 text-oro-tinta" },
  costo_viejo: { lk: "inventario.estado_costo_viejo", cls: "bg-oro/20 text-oro-tinta" },
};

export default function Inventario({ data, highlight, onPreguntar, onNavegar }) {
  const t = useT();
  const [sub, setSub] = useState("panorama");
  const [grupoSel, setGrupoSel] = useState("fantasmas");
  const [detalle, setDetalle] = useState(null); // producto seleccionado (modal)
  const [tablaFiltro, setTablaFiltro] = useState(null); // filtro pedido desde afuera
  const vista = useVista();
  const foco = useFoco();

  const tabs = [...SUBTABS, ...(vista.pestanas || []).map((p) => ({ id: p.id, label: p.nombre, custom: p }))];
  const irABalanzas = () => {
    setSub("panorama");
    setTablaFiltro("balanza");
    resaltarPorId("tabla-completa");
  };

  useEffect(() => {
    if (!highlight) return;
    if (highlight === "foco") setSub("foco");
    else if (highlight === "margenes") setSub("margenes");
    else if (highlight === "plata") setSub("panorama");
    else if (highlight === "balanzas") irABalanzas();
    else if (GRUPOS.includes(highlight)) {
      setSub("problemas");
      setGrupoSel(highlight);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [highlight]);

  const pestActiva = (vista.pestanas || []).find((p) => p.id === sub);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-3xl font-bold">{t("inventario.titulo")}</h1>
        <p className="mt-1 text-[0.95rem] text-tinta-suave">
          {t("inventario.subtitulo")}
        </p>
      </header>

      {/* Ángela propone separar las balanzas la primera vez */}
      {!vista.balanzaEsquemaOk && <BalanzaPropuesta onVer={irABalanzas} />}

      <div className="flex flex-wrap gap-2 border-b border-linea">
        {tabs.map((tb) => (
          <button
            key={tb.id}
            onClick={() => setSub(tb.id)}
            className={`-mb-px flex items-center gap-1.5 border-b-2 px-1 py-2.5 text-[0.92rem] font-semibold transition-colors ${
              sub === tb.id ? "border-tinta text-tinta" : "border-transparent text-tinta-suave hover:text-tinta"
            }`}
          >
            {tb.lk ? t(tb.lk) : tb.label}
            {tb.custom && (
              <X size={13} onClick={(e) => { e.stopPropagation(); vistaStore.quitarPestana(tb.id); if (sub === tb.id) setSub("panorama"); }}
                 className="opacity-50 hover:opacity-100" />
            )}
          </button>
        ))}
      </div>

      {sub === "foco" && <FocoView foco={foco} onSelect={setDetalle} onPreguntar={onPreguntar} onSalir={() => { focoStore.clear(); setSub("panorama"); }} />}
      {sub === "panorama" && <Panorama data={data} onSelect={setDetalle} onNavegar={onNavegar} tablaFiltro={tablaFiltro} />}
      {sub === "margenes" && <Margenes onPreguntar={onPreguntar} />}
      {sub === "reponer" && <Reponer onPreguntar={onPreguntar} />}
      {sub === "problemas" && (
        <Problemas data={data} grupoSel={grupoSel} setGrupoSel={setGrupoSel} highlight={highlight} />
      )}
      {pestActiva && <PestanaCustom pestana={pestActiva} onSelect={setDetalle} />}

      {detalle && <ProductoDetalle p={detalle} onClose={() => setDetalle(null)} onPreguntar={onPreguntar} />}
    </div>
  );
}

// Primera vez en inventario: Ángela detecta los productos de balanza y propone el esquema.
function BalanzaPropuesta({ onVer }) {
  const t = useT();
  const [n, setN] = useState(null);
  useEffect(() => { api.balanzas().then((d) => setN(d.total)).catch(() => {}); }, []);
  if (!n) return null;
  return (
    <div className="flex items-start gap-3 rounded-[var(--radius-card)] border border-oro/30 bg-oro/[0.06] p-5">
      <AngelaMark size={34} />
      <div className="flex-1">
        <p className="text-[0.98rem] leading-snug text-tinta">
          {t("inventario.balanza_prop_1")} <b>{t("inventario.balanza_prop_n", { n: num(n) })}</b>{t("inventario.balanza_prop_2")}
        </p>
        <div className="mt-3 flex gap-2">
          <button onClick={() => { vistaStore.aplicar({ balanzaEsquemaOk: true }); onVer(); }}
            className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.88rem] font-semibold text-crema">
            {t("inventario.balanza_prop_si")}
          </button>
          <button onClick={() => vistaStore.aplicar({ balanzaEsquemaOk: true })}
            className="rounded-full border border-linea px-4 py-2 text-[0.88rem] font-semibold text-tinta-suave">
            {t("inventario.balanza_prop_no")}
          </button>
        </div>
      </div>
    </div>
  );
}

// Vista de foco: SOLO los productos que Ángela señaló (de una anomalía), resaltados.
function FocoView({ foco, onSelect, onPreguntar, onSalir }) {
  const t = useT();
  const [items, setItems] = useState(null);
  useEffect(() => { api.articulos().then((d) => setItems(d.items)).catch(() => {}); }, []);
  if (!foco?.codigos?.length) {
    return <p className="text-[0.9rem] text-tinta-suave">{t("inventario.foco_vacio")} <button onClick={onSalir} className="font-semibold text-tinta">{t("inventario.foco_volver")}</button>.</p>;
  }
  if (!items) return <p className="text-[0.9rem] text-tinta-suave">{t("inventario.cargando")}</p>;
  const set = new Set(foco.codigos);
  const filt = items.filter((p) => set.has(p.codigo));
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3 rounded-[var(--radius-card)] border border-rojo/25 bg-rojo/[0.04] p-4">
        <AngelaMark size={28} />
        <p className="flex-1 text-[0.92rem] text-tinta"><b>{num(filt.length)}</b> {t("inventario.foco_senalados")} {foco.titulo}</p>
        <button onClick={() => onPreguntar?.(`¿cómo corrijo ${foco.titulo.toLowerCase()}?`)} className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-3.5 py-1.5 text-[0.88rem] font-semibold text-crema">
          <Sparkles size={14} /> {t("inventario.arreglar_angela")}
        </button>
        <button onClick={onSalir} className="rounded-full border border-linea px-3.5 py-1.5 text-[0.88rem] font-semibold text-tinta-suave hover:text-tinta">{t("inventario.salir")}</button>
      </div>
      <div className="overflow-x-auto rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
        <table className="w-full text-[0.88rem]">
          <thead>
            <tr className="border-b border-linea text-left text-tinta-suave">
              <th className="px-4 py-2.5 font-semibold">{t("inventario.col_producto")}</th>
              <th className="px-4 py-2.5 text-right font-semibold">{t("inventario.col_stock")}</th>
              <th className="px-4 py-2.5 text-right font-semibold">{t("inventario.col_costo")}</th>
              <th className="px-4 py-2.5 text-right font-semibold">{t("inventario.col_pvp")}</th>
              <th className="px-4 py-2.5 text-right font-semibold">{t("inventario.plata_parada")}</th>
            </tr>
          </thead>
          <tbody>
            {filt.map((p) => (
              <tr key={p.codigo} onClick={() => onSelect(p)} className="cursor-pointer border-b border-linea/60 bg-rojo/[0.025] last:border-0 hover:bg-rojo/[0.05]">
                <td className="px-4 py-2 text-tinta">{p.descripcion}</td>
                <td className="plata px-4 py-2 text-right">{num(Math.round(p.stock || 0))}</td>
                <td className="plata px-4 py-2 text-right text-tinta-suave">{p.costo_iva ? peso(p.costo_iva) : "—"}</td>
                <td className="plata px-4 py-2 text-right text-tinta-suave">{p.pvp ? peso(p.pvp) : "—"}</td>
                <td className="plata px-4 py-2 text-right font-medium text-hielo">{p.inmovilizado ? peso(p.inmovilizado) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Pestaña creada por Ángela a pedido: filtra la tabla por estado de calidad.
function PestanaCustom({ pestana, onSelect }) {
  const t = useT();
  const [items, setItems] = useState(null);
  useEffect(() => { api.articulos().then((d) => setItems(d.items)).catch(() => {}); }, []);
  if (!items) return <p className="text-[0.9rem] text-tinta-suave">{t("inventario.cargando")}</p>;
  const filt = pestana.filtro === "balanza"
    ? items.filter((p) => p.estado_calidad === "balanza")
    : items.filter((p) => p.estado_calidad === pestana.filtro);
  return (
    <div className="space-y-3">
      <p className="text-[0.9rem] text-tinta-suave">
        {t("inventario.pestana_custom_1")} <b>{num(filt.length)}</b> {t("inventario.pestana_custom_2")}
      </p>
      <div className="overflow-x-auto rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
        <table className="w-full text-[0.88rem]">
          <thead>
            <tr className="border-b border-linea text-left text-tinta-suave">
              <th className="px-4 py-2.5 font-semibold">{t("inventario.col_producto")}</th>
              <th className="px-4 py-2.5 text-right font-semibold">{t("inventario.col_stock")}</th>
              <th className="px-4 py-2.5 text-right font-semibold">{t("inventario.plata_parada")}</th>
            </tr>
          </thead>
          <tbody>
            {filt.slice(0, 100).map((p) => (
              <tr key={p.codigo} onClick={() => onSelect(p)} className="cursor-pointer border-b border-linea/60 last:border-0 hover:bg-papel-hondo/40">
                <td className="px-4 py-2 text-tinta">{p.descripcion}</td>
                <td className="plata px-4 py-2 text-right">{num(Math.round(p.stock || 0))}</td>
                <td className="plata px-4 py-2 text-right font-medium text-hielo">{p.inmovilizado ? peso(p.inmovilizado) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Tarjeta({ label, valor, acento }) {
  return (
    <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
      <p className={`plata text-2xl font-medium ${acento ? "text-hielo" : "text-tinta"}`}>{valor}</p>
      <p className="text-[0.8rem] text-tinta-suave">{label}</p>
    </div>
  );
}

/* ---------------- PANORAMA ---------------- */
function Panorama({ data, onSelect, onNavegar, tablaFiltro }) {
  const t = useT();
  const { resumen, alertas, top_inmovilizado } = data;
  const contado = useCountUp(resumen.inmovilizado_total);
  const vista = useVista();
  const widgets = vista.widgets?.inventario || [];
  // P25·D — murió el donut "activos 427 / anulados 3" (no aportaba nada):
  // en su lugar, LA pregunta que el dueño de verdad se hace — dónde está la
  // plata por categoría (misma capa auditada de consultas del P21).
  const [plataCat, setPlataCat] = useState([]);
  useEffect(() => {
    api.consultaSerie({ fuente: "inventario", metrica: "inmovilizado", agrupar: "categoria" })
      .then((r) => r.ok && setPlataCat(r.series[0].puntos.slice(0, 8)))
      .catch(() => {});
  }, []);
  const indicadores = [
    { tipo: "fantasmas", valor: alertas.fantasmas.cantidad, sub: t("inventario.ind_fantasmas", { u: num(Math.abs(alertas.fantasmas.unidades)) }), urgente: true },
    { tipo: "negativos", valor: alertas.negativos.cantidad, sub: t("inventario.ind_negativos", { u: num(Math.abs(alertas.negativos.unidades)) }), urgente: true },
    { tipo: "sin_pvp", valor: alertas.sin_pvp.cantidad, sub: t("inventario.ind_sin_pvp"), urgente: false },
    { tipo: "balanza", valor: alertas.balanza.cantidad, sub: t("inventario.ind_balanza"), urgente: false },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="relative overflow-hidden rounded-[var(--radius-card)] border border-hielo/20 bg-hielo-claro p-6 sombra-alta lg:col-span-2">
          <div className="relative">
            <p className="text-[0.88rem] font-semibold uppercase tracking-[0.16em] text-hielo">{t("inventario.plata_parada_mercaderia")}</p>
            <p className="plata mt-2 text-5xl font-medium leading-none text-hielo">{peso(contado)}</p>
            <p className="mt-3 max-w-md text-[0.92rem] leading-snug text-tinta">
              {t("inventario.plata_parada_detalle")}
            </p>
          </div>
        </div>
        <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-6 sombra-papel">
          <p className="text-[0.88rem] font-semibold uppercase tracking-[0.14em] text-tinta-suave">{t("inventario.plata_por_cat")}</p>
          <div className="mt-3 space-y-1.5">
            {plataCat.length === 0 && <div className="skeleton h-36 w-full" />}
            {plataCat.map((p) => {
              const max = plataCat[0]?.y || 1;
              return (
                <div key={p.x} className="relative rounded-lg px-2.5 py-1">
                  <div className="absolute inset-y-0 left-0 rounded-lg bg-hielo/15" style={{ width: `${Math.max(6, (p.y / max) * 100)}%` }} />
                  <div className="relative flex items-center justify-between gap-2 text-[0.8rem]">
                    <span className="truncate">{p.x}</span>
                    <span className="plata shrink-0 font-medium text-hielo">{pesoCorto(p.y)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {indicadores.map((ind) => {
          const def = ALERTA_DEFS[ind.tipo];
          return (
            <div key={ind.tipo} className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
              <div className={`mb-2 h-1.5 w-8 rounded-full ${ind.urgente ? "bg-rojo" : "bg-oro"}`} />
              <p className="plata text-3xl font-medium leading-none">{num(ind.valor)}</p>
              <p className="mt-1.5 font-display text-[0.92rem] font-bold leading-tight">{t(def.titulo)}</p>
              <p className="mt-0.5 text-[0.88rem] text-tinta-suave">{ind.sub}</p>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <TreemapPlata data={data} onSelect={onSelect} />
        <div className="space-y-5">
          <SaludCatalogo data={data} />
          <ConcentracionTop10 data={data} />
        </div>
      </div>

      {/* Widgets que el dueño le pidió a Ángela */}
      {widgets.length > 0 && (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          {widgets.map((w) => (
            <Widget key={w.id} widget={w} data={data} onQuitar={(id) => vistaStore.quitarWidget("inventario", id)} />
          ))}
        </div>
      )}

      {/* Ver TODO el stock, producto por producto */}
      <TablaCompleta onSelect={onSelect} onNavegar={onNavegar} filtroInicial={tablaFiltro} />

      <RotacionPlaceholder data={data} />
    </div>
  );
}

/* Treemap interactivo: tooltip + click → detalle */
function TreemapPlata({ data, onSelect }) {
  const t = useT();
  // El mapa muestra los productos con MÁS plata parada. Antes graficaba 10 SKUs
  // contra el total del catálogo entero y el nodo "resto del catálogo" se comía
  // el gráfico (parecía un error). Ahora el mapa es de los top reales y la
  // relación con el total se dice en texto, honesta.
  const [top, setTop] = useState(() => data.top_inmovilizado.slice(0, 12));
  useEffect(() => {
    api.inventarioTop(50).then((r) => { if (r.items?.length) setTop(r.items); }).catch(() => {});
  }, []);
  const sumaTop = top.reduce((a, p) => a + p.inmovilizado, 0);
  const total = data.resumen.inmovilizado_total || 0;
  const pct = total > 0 ? Math.round((sumaTop / total) * 100) : 0;
  // P17·E3: muere el arcoíris — escala secuencial de UN hue (teal):
  // más oscuro = más plata inmovilizada. El color ES el dato.
  const maxV = top[0]?.inmovilizado || 1;
  const minV = top[top.length - 1]?.inmovilizado || 0;
  const nodos = top.map((p) => ({
    name: p.descripcion, size: p.inmovilizado,
    fill: tealSecuencial(maxV > minV ? (p.inmovilizado - minV) / (maxV - minV) * 0.85 + 0.15 : 0.5),
    codigo: p.codigo, stock: p.stock, costo_iva: p.costo_iva, inmovilizado: p.inmovilizado, estado: p.estado,
  }));

  return (
    <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
      <p className="text-[0.88rem] font-semibold uppercase tracking-[0.14em] text-tinta-suave">{t("inventario.donde_plata")}</p>
      <p className="mt-0.5 text-[0.88rem] text-tinta-suave">{t("inventario.donde_plata_detalle")}</p>
      {total > 0 && sumaTop > 0 && (
        <p className="mt-0.5 text-[0.8rem] text-tinta-suave">
          {t("inventario.donde_plata_top", { n: num(top.length), pct, monto: pesoCorto(sumaTop), total: pesoCorto(total) })}
        </p>
      )}
      <div className="mt-3 h-64">
        <ResponsiveContainer>
          <Treemap
            data={nodos} dataKey="size" stroke={GRAFICO.fondo} content={<CeldaTreemap />} isAnimationActive={false}
            onClick={(n) => { if (n && !n.resto && n.codigo != null) onSelect(n); }}
          >
            <Tooltip content={<TreemapTooltip />} />
          </Treemap>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function TreemapTooltip({ active, payload }) {
  const t = useT();
  if (!active || !payload?.length) return null;
  const n = payload[0].payload;
  return (
    <div className="rounded-xl border border-linea bg-crema p-3 text-[0.88rem] sombra-alta">
      <p className="font-semibold text-tinta">{n.name}</p>
      {!n.resto && (
        <div className="mt-1 space-y-0.5 text-tinta-suave">
          <p>{t("inventario.tt_stock")} <span className="plata">{num(n.stock)}</span></p>
          <p>{t("inventario.tt_costo_iva")} <span className="plata">{n.costo_iva ? peso(n.costo_iva) : "—"}</span></p>
          <p>{t("inventario.tt_plata_parada")} <span className="plata font-semibold text-hielo">{peso(n.inmovilizado)}</span></p>
        </div>
      )}
    </div>
  );
}

function CeldaTreemap({ x, y, width, height, name, fill, inmovilizado }) {
  if (width == null || height == null || width < 1 || height < 1) return null;
  const safeName = name || "";
  // Labels (SKU + $) solo en rectángulos grandes; los chicos hablan por tooltip.
  const mostrar = safeName && width > 84 && height > 40;
  const maxChars = Math.floor(width / 7);
  const texto = textoSobre(fill || "rgb(215,231,235)");
  return (
    <g style={{ cursor: "pointer" }}>
      <rect x={x} y={y} width={width} height={height} style={{ fill: fill || GRAFICO.linea, stroke: GRAFICO.fondo, strokeWidth: 2 }} />
      {mostrar && (
        <>
          <text x={x + 7} y={y + 16} fill={texto} fontSize={10.5} fontWeight={600} style={{ pointerEvents: "none" }}>
            {safeName.length > maxChars ? safeName.slice(0, maxChars) + "…" : safeName}
          </text>
          <text x={x + 7} y={y + 30} fill={texto} fontSize={10} opacity={0.85}
            style={{ pointerEvents: "none", fontVariantNumeric: "tabular-nums" }}>
            {pesoCorto(inmovilizado)}
          </text>
        </>
      )}
    </g>
  );
}

function SaludCatalogo({ data }) {
  const t = useT();
  const { resumen, alertas } = data;
  const sinPrecio = alertas.sin_pvp.cantidad;
  const activosConPrecio = Math.max(0, resumen.activos - sinPrecio);
  const total = resumen.total_articulos;
  const segs = [
    { label: t("inventario.salud_activos_precio"), value: activosConPrecio, color: GRAFICO.salvia },
    { label: t("inventario.salud_activos_sin_precio"), value: sinPrecio, color: GRAFICO.oro },
    { label: t("inventario.anulados"), value: resumen.anulados, color: GRAFICO.linea },
  ];
  return (
    <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
      <p className="text-[0.88rem] font-semibold uppercase tracking-[0.14em] text-tinta-suave">{t("inventario.salud_titulo")}</p>
      <div className="mt-3 flex h-4 overflow-hidden rounded-full">
        {segs.map((s) => <div key={s.label} style={{ width: `${(s.value / total) * 100}%`, background: s.color }} title={`${s.label}: ${s.value}`} />)}
      </div>
      <div className="mt-3 space-y-1">
        {segs.map((s) => (
          <div key={s.label} className="flex items-center justify-between text-[0.88rem]">
            <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: s.color }} />{s.label}</span>
            <span className="plata font-medium">{num(s.value)}</span>
          </div>
        ))}
      </div>
      <p className="mt-2 text-[0.88rem] text-tinta-suave">{t("inventario.salud_ademas", { n: num(alertas.negativos.cantidad), m: num(alertas.balanza.cantidad) })}</p>
    </div>
  );
}

function ConcentracionTop10({ data }) {
  const t = useT();
  const top = data.top_inmovilizado.slice(0, 10);
  const sumaTop = top.reduce((a, p) => a + p.inmovilizado, 0);
  const total = data.resumen.inmovilizado_total;
  const pct = Math.round((sumaTop / total) * 100);
  // P15·E4: el copy sigue al dato. Concentración alta (≥25%) = hay palanca;
  // baja = la verdad útil es la contraria: está repartida, se trabaja en lista.
  const concentrada = pct >= 25;
  return (
    <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
      <p className="text-[0.88rem] font-semibold uppercase tracking-[0.14em] text-tinta-suave">{t("inventario.conc_titulo")}</p>
      <p className="mt-2 text-[0.9rem] text-tinta">
        {concentrada ? (
          <>
            {t("inventario.conc_1")} <b className="plata text-hielo">{pct}%</b> {t("inventario.conc_2")} <b>{t("inventario.conc_3")}</b>{t("inventario.conc_4")}
          </>
        ) : (
          <>
            {t("inventario.conc_baja_1")} <b className="plata text-hielo">{pct}%</b> {t("inventario.conc_baja_2")}
          </>
        )}
      </p>
      <div className="mt-3 flex h-3 overflow-hidden rounded-full bg-papel-hondo">
        <div style={{ width: `${pct}%` }} className="bg-hielo" />
      </div>
      <div className="mt-1.5 flex justify-between text-[0.88rem] text-tinta-suave">
        <span>{t("inventario.conc_top", { monto: pesoCorto(sumaTop) })}</span><span>{t("inventario.conc_resto", { monto: pesoCorto(total - sumaTop) })}</span>
      </div>
    </div>
  );
}

/* Tabla completa: TODOS los productos, con búsqueda y CUATRO filtros (P38·A):
   Todos · Activos · Balanza · Datos a corregir. "Balanza" es el mundo de lo
   que se vende por peso (absorbió a "Por kg"); los errores de dato viven
   juntos en "Datos a corregir" sin desaparecer del listado general. */
function TablaCompleta({ onSelect, onNavegar, filtroInicial }) {
  const t = useT();
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [filtro, setFiltro] = useState("todos");
  const [errSel, setErrSel] = useState("todos"); // sub-filtro dentro de "Datos a corregir"
  const vista = useVista();
  const margen = (p) => (p.pvp && p.costo_iva ? Math.round(((p.pvp - p.costo_iva) / p.pvp) * 100) : null);

  useEffect(() => { api.articulos().then((r) => setItems(r.items)).catch(() => {}); }, []);
  // Navegación guiada ("mostrame las balanzas"): activa el filtro desde afuera.
  useEffect(() => { if (filtroInicial) setFiltro(filtroInicial); }, [filtroInicial]);

  // P19·A — preferencia recordada: margen teórico < umbral fijado ARRIBA.
  // Solo reordena y destaca datos que ya están calculados; la columna de
  // margen se muestra sola mientras la preferencia viva.
  const pinUmbral = vista.margenPinUmbral;
  const conMargen = vista.invMostrarMargen || pinUmbral != null;
  const pineado = (p) => {
    const m = margen(p);
    return pinUmbral != null && m != null && m < pinUmbral;
  };

  const filtrados = useMemo(() => {
    const qn = q.trim().toLowerCase();
    const base = items.filter((p) => {
      if (filtro === "balanza") {
        // el mundo de lo que se vende por peso (antes "Por kg")
        if (p.unidad_pricing !== "kg") return false;
      } else if (filtro === "ok") {
        if (p.estado_calidad !== "ok") return false;
      } else if (filtro === "a_corregir") {
        if (p.estado_calidad === "ok") return false;
        if (errSel !== "todos" && p.estado_calidad !== errSel) return false;
      }
      if (qn && !`${p.descripcion} ${p.codigo}`.toLowerCase().includes(qn)) return false;
      return true;
    });
    if (pinUmbral == null) return base;
    const arriba = base.filter(pineado).sort((a, b) => (margen(a) ?? 100) - (margen(b) ?? 100));
    return [...arriba, ...base.filter((p) => !pineado(p))];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, q, filtro, errSel, pinUmbral]);
  const nPineados = pinUmbral != null ? filtrados.filter(pineado).length : 0;

  // El conteo de la entrada "Datos a corregir": TODO lo que no está sano.
  // Es el mismo universo que se ve en rojo dentro de "Todos" — una sola verdad.
  const porError = useMemo(() => {
    const c = {};
    for (const p of items) {
      if (p.estado_calidad && p.estado_calidad !== "ok") c[p.estado_calidad] = (c[p.estado_calidad] || 0) + 1;
    }
    return c;
  }, [items]);
  const nACorregir = Object.values(porError).reduce((a, b) => a + b, 0);

  const FILTROS = [
    { id: "todos", label: t("inventario.filtro_todos") },
    { id: "ok", label: t("inventario.filtro_activos") },
    { id: "balanza", label: `⚖️ ${t("inventario.filtro_balanza")}` },
    { id: "a_corregir", label: t("inventario.filtro_a_corregir", { n: num(nACorregir) }) },
  ];

  // Resumen del mundo por peso (los tiles del viejo subtab, junto al filtro)
  const esKg = filtro === "balanza";
  const kgStats = useMemo(() => {
    if (!esKg) return null;
    const totalKg = filtrados.reduce((a, p) => a + Math.max(0, p.stock || 0), 0);
    const plata = filtrados.reduce((a, p) => a + (p.inmovilizado || 0), 0);
    const negativos = filtrados.filter((p) => (p.stock || 0) < 0).length;
    // P38·G — los mismos kilos, contados como los cuenta el depósito
    const piezas = filtrados.reduce((a, p) => a + Math.max(0, p.unidades || 0), 0);
    return { totalKg, plata, negativos, piezas };
  }, [esKg, filtrados]);

  return (
    <div data-nav-id="tabla-completa" className="rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
      <div className="flex flex-wrap items-center gap-3 border-b border-linea p-4">
        <h2 className="font-display text-[1.1rem] font-bold">{t("inventario.tabla_titulo")}</h2>
        <span className="text-[0.8rem] text-tinta-suave">{t("inventario.tabla_conteo", { a: num(filtrados.length), b: num(items.length) })}</span>
        <div className="relative ml-auto">
          <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-tinta-suave" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("inventario.tabla_buscar")}
            className="w-64 rounded-full border border-linea bg-papel py-2 pl-9 pr-3 text-[0.88rem] outline-none focus:border-tinta/40" />
        </div>
      </div>
      <div className="flex flex-wrap gap-2 border-b border-linea px-4 py-2.5">
        {FILTROS.map((f) => (
          <button key={f.id} onClick={() => { setFiltro(f.id); setErrSel("todos"); }}
            className={`rounded-full px-3 py-1 text-[0.88rem] font-semibold ${
              filtro === f.id
                ? f.id === "a_corregir" ? "bg-rojo text-crema" : "bg-tinta text-crema"
                : f.id === "a_corregir" && nACorregir > 0
                  ? "border border-rojo/35 text-rojo" : "border border-linea text-tinta-suave"}`}>
            {f.label}
          </button>
        ))}
        {pinUmbral != null && (
          <span className="ml-auto inline-flex items-center gap-1.5 rounded-full bg-oro/15 px-3 py-1 text-[0.88rem] font-semibold text-oro-tinta">
            {t("inventario.pin_margen", { umbral: pinUmbral, n: num(nPineados) })}
          </span>
        )}
      </div>
      {/* P38·A — dentro de "Datos a corregir": los tipos de error juntos.
          Siguen apareciendo en "Todos" en rojo: acá se concentran para resolverlos. */}
      {filtro === "a_corregir" && (
        <div className="border-b border-linea bg-rojo/[0.03] px-4 py-3">
          <p className="text-[0.88rem] leading-snug text-tinta">{t("inventario.corregir_intro")}</p>
          <div className="mt-2.5 flex flex-wrap items-center gap-2">
            <button onClick={() => setErrSel("todos")}
              className={`rounded-full px-3 py-1 text-[0.88rem] font-semibold ${errSel === "todos" ? "bg-rojo text-crema" : "border border-rojo/30 text-rojo"}`}>
              {t("inventario.corregir_todos", { n: num(nACorregir) })}
            </button>
            {ERRORES_DATO.filter((e) => porError[e]).map((e) => (
              <button key={e} onClick={() => setErrSel(e)}
                className={`rounded-full px-3 py-1 text-[0.88rem] font-semibold ${errSel === e ? "bg-rojo text-crema" : "border border-rojo/30 text-rojo"}`}>
                {t(ESTADO_CAL[e].lk)} · {num(porError[e])}
              </button>
            ))}
            {onNavegar && (
              <button onClick={() => onNavegar("saneamiento", errSel === "todos" ? undefined : errSel)}
                className="ml-auto inline-flex items-center gap-1.5 rounded-full bg-violeta px-3.5 py-1.5 text-[0.88rem] font-semibold text-crema">
                <AngelaMark size={14} /> {t("inventario.corregir_resolver")}
              </button>
            )}
          </div>
        </div>
      )}
      {kgStats && (
        <div className="border-b border-linea px-4 py-3">
          <div className="grid grid-cols-4 gap-3">
            <div><p className="text-[0.7rem] font-semibold uppercase text-tinta-suave">{t("inventario.bal_productos_kilo")}</p>
              <p className="plata text-xl font-medium">{num(filtrados.length)}</p></div>
            <div><p className="text-[0.7rem] font-semibold uppercase text-tinta-suave">{t("inventario.bal_stock_total")}</p>
              <p className="plata text-xl font-medium">{num(Math.round(kgStats.totalKg))} kg</p></div>
            <div><p className="text-[0.7rem] font-semibold uppercase text-tinta-suave">{t("inventario.bal_piezas")}</p>
              <p className="plata text-xl font-medium">{num(Math.round(kgStats.piezas))}</p></div>
            <div><p className="text-[0.7rem] font-semibold uppercase text-tinta-suave">{t("inventario.plata_parada")}</p>
              <p className="plata text-xl font-medium text-hielo">{pesoCorto(kgStats.plata)}</p></div>
          </div>
          <p className="mt-2.5 text-[0.8rem] leading-snug text-tinta-suave">{t("inventario.bal_tres_cosas")}</p>
          {kgStats.negativos > 0 && (
            <p className="mt-2.5 rounded-xl border border-rojo/20 bg-rojo/[0.04] px-3 py-2 text-[0.88rem] text-tinta">
              ⚠️ {num(kgStats.negativos)} {t("inventario.bal_neg_1")} <b>{t("inventario.bal_neg_2")}</b> {t("inventario.bal_neg_3")} <b>{t("inventario.bal_neg_4")}</b>.
            </p>
          )}
        </div>
      )}
      <div className="max-h-[26rem] overflow-y-auto">
        <table className="w-full text-left text-[0.88rem]">
          <thead className="sticky top-0 bg-crema">
            <tr className="border-b border-linea text-[0.88rem] uppercase tracking-wide text-tinta-suave">
              <th className="px-4 py-2.5 font-semibold">{t("inventario.col_producto")}</th>
              <th className="px-4 py-2.5 text-right font-semibold">{t("inventario.col_stock")}</th>
              {!vista.invOcultarCosto && <th className="px-4 py-2.5 text-right font-semibold">{t("inventario.col_costo_iva")}</th>}
              {esKg && <th className="px-4 py-2.5 text-right font-semibold">$/kg</th>}
              {/* P38·G — el pesable son TRES cosas: kilos, piezas y el precio de
                  una pieza. El chofer y el local piden piezas, no kilos. */}
              {esKg && <th className="px-4 py-2.5 text-right font-semibold">{t("inventario.col_precio_pieza")}</th>}
              {conMargen && <th className="px-4 py-2.5 text-right font-semibold">{t("inventario.col_margen")}</th>}
              <th className="px-4 py-2.5 text-right font-semibold">{t("inventario.plata_parada")}</th>
              <th className="px-4 py-2.5 font-semibold">{t("inventario.col_estado")}</th>
            </tr>
          </thead>
          <tbody>
            {filtrados.map((p, i) => {
              const e = ESTADO_CAL[p.estado_calidad] || ESTADO_CAL.ok;
              const problema = p.estado_calidad !== "ok";
              // Producto problemático → va directo a "Datos a corregir" filtrado. Sano → detalle.
              const click = () => (problema && onNavegar ? onNavegar("saneamiento", p.estado_calidad) : onSelect({ ...p, name: p.descripcion }));
              return (
                <tr key={`${p.codigo}-${i}`} onClick={click}
                  className={`cursor-pointer border-b border-linea/70 last:border-0 ${problema ? "bg-rojo/[0.045] hover:bg-rojo/[0.08]" : "hover:bg-papel-hondo/40"}`}>
                  <td className="px-4 py-2">
                    <p className={`font-medium ${problema ? "text-rojo-hondo" : ""}`}>
                      {p.descripcion}
                      {p.unidad_pricing === "kg" && (
                        <span className="ml-2 rounded-full bg-hielo/15 px-1.5 py-0.5 text-[0.88rem] font-semibold text-hielo align-middle">{t("inventario.por_kg")}</span>
                      )}
                    </p>
                    <p className="text-[0.88rem] text-tinta-suave">{problema ? t("inventario.cod_toca", { codigo: p.codigo }) : t("inventario.cod", { codigo: p.codigo })}</p>
                  </td>
                  <td className={`plata px-4 py-2 text-right ${p.stock < 0 ? "font-semibold text-rojo" : ""}`}>
                    {num(p.stock)}{p.unidad_pricing === "kg" ? " kg" : ""}
                    {p.unidades != null && (
                      <span className="block text-[0.88rem] font-normal text-tinta-suave">
                        {t("inventario.n_piezas", { n: num(p.unidades) })}
                      </span>
                    )}
                  </td>
                  {!vista.invOcultarCosto && <td className="plata px-4 py-2 text-right text-tinta-suave">{p.costo_iva ? `${peso(p.costo_iva)}${p.unidad_pricing === "kg" ? "/kg" : ""}` : "—"}</td>}
                  {esKg && <td className="plata px-4 py-2 text-right text-tinta-suave">{p.pvp ? `${peso(p.pvp)}/kg` : "—"}</td>}
                  {esKg && (
                    <td className="plata px-4 py-2 text-right text-tinta-suave">
                      {p.precio_por_unidad ? peso(p.precio_por_unidad) : "—"}
                      {p.peso_por_unidad != null && (
                        <span className="block text-[0.88rem] font-normal text-tinta-suave/80">
                          {t("inventario.pieza_de", { kg: num(p.peso_por_unidad) })}
                        </span>
                      )}
                    </td>
                  )}
                  {conMargen && <td className={`plata px-4 py-2 text-right ${pineado(p) ? "font-semibold text-oro-tinta" : "text-tinta-suave"}`}>{margen(p) != null ? `${margen(p)}%` : "—"}</td>}
                  <td className="plata px-4 py-2 text-right font-medium text-hielo">{p.inmovilizado ? peso(p.inmovilizado) : "—"}</td>
                  <td className="px-4 py-2"><span className={`rounded-full px-2 py-0.5 text-[0.88rem] font-semibold ${e.cls}`}>{t(e.lk)}</span></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RotacionPlaceholder({ data }) {
  // Cableado al apartado ventas: cuando el CSV entre Y el dueño confirme el
  // validador de montos, esta card despierta sola con los números reales.
  const t = useT();
  const [v, setV] = useState(null);
  useEffect(() => { api.ventas().then(setV).catch(() => {}); }, []);

  if (v?.disponible) {
    const rot = v.rotacion;
    return (
      <div className="rounded-[var(--radius-card)] border border-salvia/30 bg-salvia/[0.05] p-6">
        <p className="font-display text-[1.05rem] font-bold">{t("inventario.rot_titulo")}</p>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div><p className="text-[0.88rem] font-semibold uppercase text-tinta-suave">{t("inventario.rot_parado_total")}</p>
            <p className="plata text-2xl font-medium text-hielo">{pesoCorto(rot.inmovilizado_total)}</p></div>
          <div><p className="text-[0.88rem] font-semibold uppercase text-tinta-suave">{t("inventario.rot_excedente")}</p>
            <p className="plata text-2xl font-medium text-salvia">{pesoCorto(rot.plata_excedente)}</p></div>
          <div><p className="text-[0.88rem] font-semibold uppercase text-tinta-suave">{t("inventario.rot_necesario")}</p>
            <p className="plata text-2xl font-medium">{pesoCorto(rot.plata_necesaria)}</p></div>
        </div>
        {v.quiebre?.cantidad > 0 && (
          <p className="mt-3 text-[0.88rem] text-rojo">
            {t("inventario.rot_quiebre", { n: v.quiebre.cantidad })}
          </p>
        )}
      </div>
    );
  }

  const validando = v?.validacion?.estado === "pendiente" || v?.validacion?.estado === "sospechoso";
  return (
    <div className="rounded-[var(--radius-card)] border border-dashed border-linea bg-papel-hondo/40 p-6">
      <div className="flex items-start gap-3">
        <Lock size={18} className="mt-0.5 shrink-0 text-tinta-suave" />
        <div>
          <p className="font-display text-[1.05rem] font-bold">{t("inventario.rot_titulo")}</p>
          <p className="mt-1.5 max-w-2xl text-[0.9rem] leading-snug text-tinta-suave">
            {validando
              ? (v.validacion.estado === "sospechoso"
                  ? t("inventario.rot_sospechoso")
                  : t("inventario.rot_pendiente"))
              : <>{t("inventario.rot_1")} <b className="plata">{pesoCorto(data?.resumen?.inmovilizado_total || 0)}</b> {t("inventario.rot_2")} <b>{t("inventario.rot_3")}</b>{t("inventario.rot_4")} <b>{t("inventario.rot_5")}</b> {t("inventario.rot_6")} <b>{t("inventario.rot_7")}</b> {t("inventario.rot_8")}</>}
          </p>
        </div>
      </div>
    </div>
  );
}

function Leyenda({ color, label, value }) {
  return (
    <div className="flex items-center justify-between text-[0.88rem]">
      <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: color }} />{label}</span>
      <span className="plata font-medium">{num(value)}</span>
    </div>
  );
}

/* Modal de detalle de un producto */
function ProductoDetalle({ p, onClose, onPreguntar }) {
  const t = useT();
  const e = ESTADO_CAL[p.estado_calidad] || ESTADO_CAL.ok;
  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-tinta/40 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-[var(--radius-card)] border border-linea bg-crema p-6 sombra-alta" onClick={(ev) => ev.stopPropagation()}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="font-display text-[1.2rem] font-bold leading-tight">{p.descripcion || p.name}</p>
            <p className="text-[0.88rem] text-tinta-suave">{t("inventario.det_codigo", { codigo: p.codigo })}</p>
          </div>
          <button onClick={onClose} className="text-tinta-suave hover:text-tinta"><X size={20} /></button>
        </div>
        {p.estado_calidad && (
          <span className={`mt-2 inline-block rounded-full px-2.5 py-0.5 text-[0.88rem] font-semibold ${e.cls}`}>{t(e.lk)}</span>
        )}
        <div className="mt-4 grid grid-cols-2 gap-3">
          <Dato label={t("inventario.col_stock")} valor={`${num(p.stock)}${p.unidad_pricing === "kg" ? " kg" : ""}`} alerta={p.stock < 0} />
          <Dato label={t("inventario.col_costo_iva")} valor={p.costo_iva ? peso(p.costo_iva) : "—"} />
          <Dato label={t("inventario.det_precio_venta")} valor={p.pvp ? peso(p.pvp) : t("inventario.det_sin_cargar")} alerta={!p.pvp} />
          <Dato label={t("inventario.plata_parada")} valor={p.inmovilizado ? peso(p.inmovilizado) : "—"} />
          {/* P38·G — el pesable, completo: piezas, peso de una pieza y lo que
              sale una pieza. Sin esto, "522 kg" no le sirve a nadie del piso. */}
          {p.unidades != null && (
            <>
              <Dato label={t("inventario.det_piezas")} valor={num(p.unidades)} />
              <Dato label={t("inventario.det_peso_pieza")} valor={`${num(p.peso_por_unidad)} kg`} />
              {p.precio_por_unidad != null && (
                <Dato label={t("inventario.det_precio_pieza")} valor={peso(p.precio_por_unidad)} />
              )}
            </>
          )}
        </div>
        <button
          onClick={() => { onClose(); onPreguntar?.(`Contame sobre el producto ${p.descripcion || p.name} (código ${p.codigo})`); }}
          className="mt-5 inline-flex items-center gap-2 rounded-full bg-violeta px-4 py-2 text-[0.88rem] font-semibold text-crema"
        >
          <AngelaMark size={18} /> {t("inventario.det_preguntar")}
        </button>
      </div>
    </div>
  );
}

function Dato({ label, valor, alerta }) {
  return (
    <div className="rounded-xl border border-linea bg-papel p-3">
      <p className="text-[0.88rem] font-semibold uppercase tracking-wide text-tinta-suave">{label}</p>
      <p className={`plata mt-0.5 text-[1.05rem] font-medium ${alerta ? "text-rojo" : "text-tinta"}`}>{valor}</p>
    </div>
  );
}

/* ---------------- PROBLEMAS DETECTADOS ---------------- */
function Problemas({ data, grupoSel, setGrupoSel, highlight }) {
  const t = useT();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.grupo(grupoSel, 100).then((r) => { setItems(r.items); setLoading(false); }).catch(() => setLoading(false));
  }, [grupoSel]);

  const def = ALERTA_DEFS[grupoSel];
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {GRUPOS.map((g) => {
          const d = ALERTA_DEFS[g];
          const activo = grupoSel === g;
          const pulse = highlight === g;
          return (
            <button key={g} onClick={() => setGrupoSel(g)}
              className={`rounded-full px-4 py-2 text-[0.88rem] font-semibold transition-all ${activo ? "bg-tinta text-crema" : "border border-linea bg-crema text-tinta-suave hover:text-tinta"} ${pulse && !activo ? "ring-2 ring-violeta ring-offset-2 ring-offset-papel" : ""}`}>
              {t(d.titulo)} · {num(data.alertas[g].cantidad)}
            </button>
          );
        })}
      </div>
      <AngelaSays tone={def.tono}>{t(def.detalle)} <span className="font-semibold">{t("inventario.accion_label")} {t(def.accion)}.</span></AngelaSays>
      <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
        {loading ? (
          <p className="py-10 text-center text-sm text-tinta-suave">{t("inventario.cargando")}</p>
        ) : (
          <table className="w-full text-left text-[0.88rem]">
            <thead>
              <tr className="border-b border-linea text-[0.88rem] uppercase tracking-wide text-tinta-suave">
                <th className="px-4 py-3 font-semibold">{t("inventario.col_producto")}</th>
                <th className="px-4 py-3 text-right font-semibold">{grupoSel === "negativos" || grupoSel === "fantasmas" ? t("inventario.col_stock") : grupoSel === "balanza" ? t("inventario.col_peso_teorico") : t("inventario.plata_parada")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p, i) => (
                <tr key={`${p.codigo}-${i}`} className="border-b border-linea/70 last:border-0 hover:bg-papel-hondo/30">
                  <td className="px-4 py-2.5"><p className="font-medium">{p.descripcion}</p><p className="text-[0.88rem] text-tinta-suave">{t("inventario.cod", { codigo: p.codigo })}</p></td>
                  <td className={`plata px-4 py-2.5 text-right font-medium ${grupoSel === "negativos" ? "text-rojo" : "text-tinta"}`}>
                    {grupoSel === "balanza" ? p.valor_peso : grupoSel === "sin_pvp" ? pesoCorto(p.inmovilizado) : num(p.stock)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
