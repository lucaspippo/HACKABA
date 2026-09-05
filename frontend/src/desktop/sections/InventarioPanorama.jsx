import { useEffect, useMemo, useState } from "react";
import { ResponsiveContainer, Treemap, Tooltip } from "recharts";
import {
  ArrowRight, ClipboardList, Hourglass, Package, PackagePlus, ShoppingCart,
  Sparkles, Truck, Warehouse, TrendingUp,
} from "lucide-react";
import AngelaMark from "../../components/AngelaMark";
import Widget from "../../components/Widget";
import { useCountUp } from "../../lib/useCountUp";
import { useVista, vistaStore } from "../../lib/vistaStore";
import { ALERTA_DEFS, ORDEN_ALERTAS, contarACorregir } from "../../lib/alertas";
import { peso, pesoCorto, num } from "../../lib/format";
import { api } from "../../lib/api";
import { GRAFICO } from "../../lib/paleta";
import { tealSecuencial, textoSobre } from "../../components/charts/tema";
import { authStore } from "../../lib/auth";
import { useT, useLang, tCat } from "../../lib/i18n";
import { ExcessByCat, ExpiryHorizon, SeasonalityCover } from "./InventarioViz";

// Inventario inteligente is the briefing, not the workbench.
// Reading order: the stake (one sentence) → Ángela's ranked actions →
// one money map (category filter drives the treemap) → the rest of the floor.
// Concentration, catalog-health bars and the rotation lock used to repeat the
// same three facts; they now live inside the stake, the briefing, and the map.

const FILTROS = [
  { id: "todas", lk: "inventario.filtro_brief_todas" },
  { id: "urgente", lk: "inventario.filtro_brief_urgente" },
  { id: "datos", lk: "inventario.filtro_brief_datos" },
  { id: "plata", lk: "inventario.filtro_brief_plata" },
  { id: "reponer", lk: "inventario.filtro_brief_reponer" },
];

const TONO = {
  urgente: { chip: "bg-rojo/10 text-rojo", cifra: "text-rojo", ring: "hover:border-rojo/35" },
  atencion: { chip: "bg-oro/15 text-oro-tinta", cifra: "text-oro-tinta", ring: "hover:border-oro/40" },
  oportunidad: { chip: "bg-salvia/12 text-salvia", cifra: "text-salvia", ring: "hover:border-salvia/35" },
  insight: { chip: "bg-hielo/12 text-hielo", cifra: "text-hielo", ring: "hover:border-hielo/35" },
};

const HIGHLIGHT_ERR = {
  fantasmas: "fantasma", negativos: "negativo", sin_pvp: "sin_precio",
  balanza: "balanza", costo_viejo: "costo_viejo",
};

export default function Panorama({ data, onSelect, onNavegar, onTab, onPreguntar, viz }) {
  const t = useT();
  const lang = useLang();
  const { resumen } = data;
  const nCorregir = contarACorregir(data);
  const [reponer, setReponer] = useState(null);
  const [ventas, setVentas] = useState(null);
  const [venc, setVenc] = useState(null);
  const [plataCat, setPlataCat] = useState([]);
  const [top, setTop] = useState(() => data.top_inmovilizado.slice(0, 12));
  const [filtro, setFiltro] = useState("todas");
  const [catSel, setCatSel] = useState(null);

  useEffect(() => {
    api.reponer().then(setReponer).catch(() => setReponer({ disponible: false }));
    api.ventas().then(setVentas).catch(() => setVentas({ disponible: false }));
    api.vencimientos().then(setVenc).catch(() => setVenc(null));
    api.consultaSerie({ fuente: "inventario", metrica: "inmovilizado", agrupar: "categoria" })
      .then((r) => { if (r.ok && r.series?.[0]?.puntos) setPlataCat(r.series[0].puntos.slice(0, 8)); })
      .catch(() => {});
    api.inventarioTop(50).then((r) => { if (r.items?.length) setTop(r.items); }).catch(() => {});
  }, []);

  const acciones = useMemo(
    () => armarAcciones({ data, reponer, ventas, venc, t }),
    [data, reponer, ventas, venc, lang],
  );
  const visibles = filtro === "todas"
    ? acciones
    : acciones.filter((a) => a.lanes.includes(filtro) || a.kind === filtro);

  return (
    <div className="space-y-8">
      <Stake
        t={t}
        resumen={resumen}
        ventas={ventas}
        reponer={reponer}
        onTab={onTab}
        onNavegar={onNavegar}
        onPreguntar={onPreguntar}
      />

      {viz && <ExcessByCat data={viz.excess_by_category} />}

      <section data-nav-id="briefing" className="space-y-3">
        <div>
          <h2 className="font-display text-lg font-bold">{t("inventario.brief_titulo")}</h2>
          <p className="mt-1 max-w-2xl text-sm leading-snug text-tinta-suave">
            {t("inventario.brief_sub")}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {FILTROS.map((f) => {
            const n = f.id === "todas"
              ? acciones.length
              : acciones.filter((a) => a.lanes.includes(f.id) || a.kind === f.id).length;
            if (f.id !== "todas" && n === 0) return null;
            const on = filtro === f.id;
            return (
              <button
                key={f.id}
                type="button"
                aria-pressed={on}
                onClick={() => setFiltro(f.id)}
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors ${
                  on ? "border-violeta bg-violeta/[0.06] text-violeta"
                     : "border-linea text-tinta-suave hover:text-tinta"
                }`}
              >
                {t(f.lk)}
                <span className={on ? "text-violeta/70" : "text-tinta-suave/70"}>{num(n)}</span>
              </button>
            );
          })}
        </div>
        {visibles.length === 0 ? (
          <p className="rounded-[var(--radius-card)] border border-linea bg-crema px-4 py-5 text-sm text-tinta-suave">
            {t("inventario.brief_vacio")}
          </p>
        ) : (
          <ul className="divide-y divide-linea overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
            {visibles.map((a) => (
              <AccionFila
                key={a.id}
                a={a}
                t={t}
                onNavegar={onNavegar}
                onTab={onTab}
                onPreguntar={onPreguntar}
              />
            ))}
          </ul>
        )}
      </section>

      {viz && <ExpiryHorizon data={viz.expiry_horizon} />}
      {viz && <SeasonalityCover data={viz.seasonality} />}

      <MapaPlata
        t={t}
        data={data}
        top={top}
        plataCat={plataCat}
        catSel={catSel}
        onCat={setCatSel}
        onSelect={onSelect}
        onNavegar={onNavegar}
      />

      <PisoDestinos
        t={t}
        data={data}
        nCorregir={nCorregir}
        reponer={reponer}
        ventas={ventas}
        onNavegar={onNavegar}
        onTab={onTab}
      />

      <WidgetsLive data={data} />
    </div>
  );
}

function WidgetsLive({ data }) {
  const vista = useVista();
  const widgets = vista.widgets?.inventario || [];
  if (!widgets.length) return null;
  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
      {widgets.map((w) => (
        <Widget key={w.id} widget={w} data={data} onQuitar={(id) => vistaStore.quitarWidget("inventario", id)} />
      ))}
    </div>
  );
}

/* ---------------- STAKE ---------------- */

function Stake({ t, resumen, ventas, reponer, onTab, onNavegar, onPreguntar }) {
  const contado = useCountUp(resumen.inmovilizado_total);
  const rot = ventas?.disponible ? ventas.rotacion : null;
  const riesgo = reponer?.disponible && reponer.plata_total > 0 ? reponer.plata_total : null;
  const validando = ventas?.validacion?.estado === "pendiente" || ventas?.validacion?.estado === "sospechoso";

  return (
    <section data-nav-id="plata" className="space-y-3">
      <p className="font-display text-2xl font-bold leading-snug text-tinta sm:text-3xl">
        {t("inventario.stake_hay_antes")}{" "}
        <span className="plata text-hielo">{peso(contado)}</span>
        {t("inventario.stake_hay_despues")}
      </p>
      <p className="text-sm text-tinta-suave">
        {t("inventario.stake_articulos", { n: num(resumen.activos) })}
      </p>
      {rot ? (
        <div className="flex flex-wrap gap-x-4 gap-y-2 text-base leading-snug">
          {rot.plata_excedente > 0 && (
            <button
              type="button"
              onClick={() => onPreguntar?.(t("inventario.acc_excedente_angela", { monto: pesoCorto(rot.plata_excedente) }))}
              className="text-left font-medium text-salvia hover:underline"
            >
              {t("inventario.stake_excedente", { monto: pesoCorto(rot.plata_excedente) })}
            </button>
          )}
          <span className="text-tinta">
            {t("inventario.stake_necesario", { monto: pesoCorto(rot.plata_necesaria) })}
          </span>
          {riesgo != null && (
            <button
              type="button"
              onClick={() => onTab?.("reponer")}
              className="text-left font-medium text-rojo hover:underline"
            >
              {t("inventario.stake_riesgo", { monto: pesoCorto(riesgo) })}
            </button>
          )}
        </div>
      ) : ventas && !ventas.disponible ? (
        <div className="flex items-start gap-3 rounded-[var(--radius-card)] border border-linea bg-crema p-4">
          <AngelaMark size={30} />
          <div className="min-w-0 flex-1">
            <p className="text-sm leading-snug text-tinta">
              {validando
                ? (ventas.validacion?.estado === "sospechoso"
                    ? t("inventario.rot_sospechoso")
                    : t("inventario.rot_pendiente"))
                : t("inventario.stake_sin_ventas")}
            </p>
            {!validando && onNavegar && (
              <button
                type="button"
                onClick={() => onNavegar("cargar")}
                className="mt-2 inline-flex items-center gap-1.5 text-sm font-semibold text-violeta hover:underline"
              >
                {t("inventario.acc_ver_cargar")} <ArrowRight size={13} />
              </button>
            )}
          </div>
        </div>
      ) : null}
    </section>
  );
}

/* ---------------- BRIEFING ROWS ---------------- */

function AccionFila({ a, t, onNavegar, onTab, onPreguntar }) {
  const tono = TONO[a.kind] || TONO.insight;
  const go = (dest) => {
    if (!dest) return;
    if (dest.tab) onTab?.(dest.tab);
    else if (dest.seccion) onNavegar?.(dest.seccion, dest.highlight);
  };
  return (
    <li data-nav-id={a.navId || a.id} className={`px-4 py-3.5 sm:px-5 ${tono.ring}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${tono.chip}`}>
            {t(a.chipLk)}
          </span>
          <p className="mt-1.5 font-display text-lg font-bold leading-tight">{a.titulo}</p>
          <p className="mt-0.5 text-sm leading-snug text-tinta-suave">{a.dato}</p>
        </div>
        <div className="shrink-0 text-right">
          {a.monto != null && a.monto > 0 ? (
            <p className={`plata text-xl font-medium ${tono.cifra}`}>{pesoCorto(a.monto)}</p>
          ) : a.cifra != null ? (
            <p className={`plata text-xl font-medium ${tono.cifra}`}>{num(a.cifra)}</p>
          ) : null}
          {a.cifraLabel && (
            <p className="text-xs text-tinta-suave">{a.cifraLabel}</p>
          )}
        </div>
      </div>
      <div className="mt-2.5 flex flex-wrap items-center gap-2">
        {a.ir && (
          <button
            type="button"
            onClick={() => go(a.ir)}
            className="inline-flex items-center gap-1 rounded-full border border-linea px-3 py-1.5 text-sm font-semibold text-tinta hover:bg-papel-hondo/50"
          >
            {a.ir.label} <ArrowRight size={12} />
          </button>
        )}
        {a.ir2 && (
          <button
            type="button"
            onClick={() => go(a.ir2)}
            className="inline-flex items-center gap-1 rounded-full border border-linea px-3 py-1.5 text-sm font-semibold text-tinta-suave hover:text-tinta"
          >
            {a.ir2.label} <ArrowRight size={12} />
          </button>
        )}
        {a.angela && (
          <button
            type="button"
            onClick={() => onPreguntar?.(a.angela)}
            className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-3 py-1.5 text-sm font-semibold text-crema"
          >
            <Sparkles size={12} /> {t("inventario.acc_preguntar")}
          </button>
        )}
      </div>
    </li>
  );
}

function armarAcciones({ data, reponer, ventas, venc, t }) {
  const { resumen, alertas, top_inmovilizado } = data;
  const items = [];

  for (const g of ORDEN_ALERTAS) {
    const stat = alertas[g];
    if (!stat?.cantidad) continue;
    const def = ALERTA_DEFS[g];
    const urgente = def.tono === "urgente";
    items.push({
      id: g,
      navId: g,
      kind: urgente ? "urgente" : "atencion",
      lanes: urgente ? ["urgente", "datos"] : ["datos"],
      chipLk: urgente ? "inventario.chip_urgente" : "inventario.chip_datos",
      titulo: t(def.titulo),
      dato: t(def.resumen),
      cifra: stat.cantidad,
      cifraLabel: t("inventario.acc_productos"),
      monto: stat.impacto_pesos > 0 ? stat.impacto_pesos : null,
      ir: {
        seccion: "productos",
        highlight: `err:${HIGHLIGHT_ERR[g] || g}`,
        label: t("inventario.acc_ver_catalogo"),
      },
      ir2: authStore.tiene("saneamiento") ? {
        seccion: "saneamiento",
        highlight: HIGHLIGHT_ERR[g] || g,
        label: t("inventario.acc_ver_saneamiento"),
      } : null,
      angela: t(`inventario.acc_${g}_angela`),
    });
  }

  if (reponer?.disponible && reponer.ya_tarde > 0) {
    items.push({
      id: "reponer-tarde",
      navId: "reponer",
      kind: "urgente",
      lanes: ["urgente", "reponer"],
      chipLk: "inventario.chip_reponer",
      titulo: t("inventario.acc_reponer_titulo", { n: num(reponer.ya_tarde) }),
      dato: t("inventario.acc_reponer_dato", {
        zona: num(reponer.total_en_zona),
        stockout: reponer.stockout_mes ? t("inventario.acc_reponer_stockout", { n: num(reponer.stockout_mes) }) : "",
      }),
      monto: reponer.plata_total,
      cifraLabel: t("inventario.acc_dejas_facturar"),
      ir: { tab: "reponer", label: t("inventario.acc_ver_reponer") },
      ir2: { seccion: "ordenes_compra", label: t("inventario.acc_ver_ordenes") },
      angela: t("reponer.angela_preguntar"),
    });
  } else if (reponer?.disponible && reponer.con_tiempo > 0) {
    items.push({
      id: "reponer-tiempo",
      kind: "atencion",
      lanes: ["reponer"],
      chipLk: "inventario.chip_reponer",
      titulo: t("inventario.acc_reponer_tiempo_titulo", { n: num(reponer.con_tiempo) }),
      dato: t("inventario.acc_reponer_tiempo_dato"),
      cifra: reponer.con_tiempo,
      cifraLabel: t("inventario.acc_productos"),
      ir: { tab: "reponer", label: t("inventario.acc_ver_reponer") },
      angela: t("reponer.angela_preguntar"),
    });
  }

  if (venc?.disponible && (venc.total_en_riesgo > 0 || venc.items?.length > 0)) {
    const n = venc.lotes_en_riesgo || venc.items?.length || 0;
    const monto = venc.total_en_riesgo || 0;
    if (n > 0) {
      items.push({
        id: "vencimientos",
        kind: "urgente",
        lanes: ["urgente", "reponer"],
        chipLk: "inventario.chip_urgente",
        titulo: t("inventario.acc_venc_titulo", { n: num(n) }),
        dato: t("inventario.acc_venc_dato"),
        monto: monto > 0 ? monto : null,
        cifra: monto > 0 ? null : n,
        cifraLabel: monto > 0 ? t("inventario.acc_se_tira") : t("inventario.acc_lotes"),
        ir: authStore.tiene("deposito")
          ? { seccion: "deposito", label: t("inventario.acc_ver_deposito") }
          : null,
        angela: t("inventario.acc_venc_angela"),
      });
    }
  }

  const rot = ventas?.disponible ? ventas.rotacion : null;
  if (rot?.plata_excedente > 0) {
    items.push({
      id: "excedente",
      kind: "oportunidad",
      lanes: ["plata"],
      chipLk: "inventario.chip_oportunidad",
      titulo: t("inventario.acc_excedente_titulo"),
      dato: t("inventario.acc_excedente_dato"),
      monto: rot.plata_excedente,
      ir: { tab: "rotacion", label: t("inventario.acc_ver_rotacion") },
      angela: t("inventario.acc_excedente_angela", { monto: pesoCorto(rot.plata_excedente) }),
    });
  }

  const top = (top_inmovilizado || []).slice(0, 10);
  const sumaTop = top.reduce((a, p) => a + (p.inmovilizado || 0), 0);
  const total = resumen.inmovilizado_total || 0;
  const pct = total > 0 ? Math.round((sumaTop / total) * 100) : 0;
  if (pct >= 25) {
    items.push({
      id: "concentracion",
      kind: "insight",
      lanes: ["plata"],
      chipLk: "inventario.chip_insight",
      titulo: t("inventario.acc_conc_titulo", { pct }),
      dato: t("inventario.acc_conc_dato"),
      cifra: 10,
      cifraLabel: t("inventario.acc_productos"),
      monto: sumaTop,
      ir: { seccion: "productos", label: t("inventario.acc_ver_catalogo") },
      angela: t("inventario.acc_conc_angela", { pct }),
    });
  }

  if (!items.length && resumen.a_corregir === 0) {
    items.push({
      id: "en-orden",
      kind: "oportunidad",
      lanes: ["datos"],
      chipLk: "inventario.chip_ok",
      titulo: t("inventario.acc_ok_titulo"),
      dato: t("inventario.acc_ok_dato", { n: num(resumen.activos) }),
      ir: { seccion: "productos", label: t("inventario.acc_ver_catalogo") },
    });
  }

  return items;
}

/* ---------------- MONEY MAP ---------------- */

function MapaPlata({ t, data, top, plataCat, catSel, onCat, onSelect, onNavegar }) {
  const filtrados = catSel
    ? top.filter((p) => (p.tipo || "?") === catSel)
    : top;
  const sumaTop = (catSel ? filtrados : top).reduce((a, p) => a + (p.inmovilizado || 0), 0);
  const total = data.resumen.inmovilizado_total || 0;
  const top10 = data.top_inmovilizado.slice(0, 10);
  const suma10 = top10.reduce((a, p) => a + (p.inmovilizado || 0), 0);
  const pct = total > 0 ? Math.round((suma10 / total) * 100) : 0;
  const concentrada = pct >= 25;

  return (
    <section data-nav-id="mapa" className="space-y-3">
      <div>
        <h2 className="font-display text-lg font-bold">{t("inventario.mapa_titulo")}</h2>
        <p className="mt-1 max-w-2xl text-sm leading-snug text-tinta-suave">
          {concentrada
            ? t("inventario.mapa_conc_alta", { pct, monto: pesoCorto(suma10) })
            : t("inventario.mapa_conc_baja", { pct })}
          {" "}{t("inventario.mapa_hint")}
        </p>
      </div>
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-5">
        <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel lg:col-span-2">
          <p className="text-sm font-semibold text-tinta-suave">{t("inventario.plata_por_cat")}</p>
          <div className="mt-2 space-y-1">
            {plataCat.length === 0 && <div className="skeleton h-40 w-full" />}
            <button
              type="button"
              onClick={() => onCat(null)}
              className={`flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-left text-sm ${
                !catSel ? "bg-hielo/15 font-semibold text-hielo" : "text-tinta-suave hover:bg-papel-hondo/50"
              }`}
            >
              <span>{t("inventario.mapa_todas")}</span>
              <span className="plata">{pesoCorto(total)}</span>
            </button>
            {plataCat.map((p) => {
              const max = plataCat[0]?.y || 1;
              const on = catSel === p.x;
              return (
                <button
                  key={p.x}
                  type="button"
                  onClick={() => onCat(on ? null : p.x)}
                  className="relative w-full rounded-lg px-2.5 py-1.5 text-left"
                >
                  <div
                    className={`absolute inset-y-0 left-0 rounded-lg ${on ? "bg-hielo/25" : "bg-hielo/12"}`}
                    style={{ width: `${Math.max(6, (p.y / max) * 100)}%` }}
                  />
                  <div className="relative flex items-center justify-between gap-2 text-sm">
                    <span className={`truncate ${on ? "font-semibold text-hielo" : "text-tinta"}`}>
                      {tCat(p.x)}
                    </span>
                    <span className="plata shrink-0 font-medium text-hielo">{pesoCorto(p.y)}</span>
                  </div>
                </button>
              );
            })}
          </div>
          {catSel && (
            <button
              type="button"
              onClick={() => onNavegar?.("productos", `q:${catSel}`)}
              className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-hielo hover:underline"
            >
              {t("inventario.mapa_ver_cat", { cat: tCat(catSel) })} <ArrowRight size={12} />
            </button>
          )}
        </div>
        <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel lg:col-span-3">
          <p className="text-sm text-tinta-suave">
            {catSel
              ? t("inventario.mapa_n_cat", { n: num(filtrados.length), cat: tCat(catSel), monto: pesoCorto(sumaTop) })
              : t("inventario.donde_plata_top", {
                  n: num(top.length),
                  pct: total > 0 ? Math.round((sumaTop / total) * 100) : 0,
                  monto: pesoCorto(sumaTop),
                  total: pesoCorto(total),
                })}
          </p>
          <TreemapPlata nodos={filtrados} onSelect={onSelect} />
        </div>
      </div>
    </section>
  );
}

function TreemapPlata({ nodos, onSelect }) {
  const t = useT();
  if (!nodos.length) {
    return (
      <p className="mt-6 text-sm text-tinta-suave">{t("inventario.mapa_vacio")}</p>
    );
  }
  const maxV = nodos[0]?.inmovilizado || 1;
  const minV = nodos[nodos.length - 1]?.inmovilizado || 0;
  const data = nodos.map((p) => ({
    name: p.descripcion,
    size: p.inmovilizado,
    fill: tealSecuencial(maxV > minV ? (p.inmovilizado - minV) / (maxV - minV) * 0.85 + 0.15 : 0.5),
    codigo: p.codigo,
    stock: p.stock,
    costo_iva: p.costo_iva,
    inmovilizado: p.inmovilizado,
    estado: p.estado,
  }));
  return (
    <div className="mt-3 h-64">
      <ResponsiveContainer>
        <Treemap
          data={data}
          dataKey="size"
          stroke={GRAFICO.fondo}
          content={<CeldaTreemap />}
          isAnimationActive={false}
          onClick={(n) => { if (n && n.codigo != null) onSelect(n); }}
        >
          <Tooltip content={<TreemapTooltip />} />
        </Treemap>
      </ResponsiveContainer>
    </div>
  );
}

function TreemapTooltip({ active, payload }) {
  const t = useT();
  if (!active || !payload?.length) return null;
  const n = payload[0].payload;
  return (
    <div className="rounded-xl border border-linea bg-crema p-3 text-sm sombra-alta">
      <p className="font-semibold text-tinta">{n.name}</p>
      <div className="mt-1 space-y-0.5 text-tinta-suave">
        <p>{t("inventario.tt_stock")} <span className="plata">{num(n.stock)}</span></p>
        <p>{t("inventario.tt_costo_iva")} <span className="plata">{n.costo_iva ? peso(n.costo_iva) : "—"}</span></p>
        <p>{t("inventario.tt_plata_parada")} <span className="plata font-semibold text-hielo">{peso(n.inmovilizado)}</span></p>
      </div>
    </div>
  );
}

function CeldaTreemap({ x, y, width, height, name, fill, inmovilizado }) {
  if (width == null || height == null || width < 1 || height < 1) return null;
  const safeName = name || "";
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

/* ---------------- FLOOR DESTINATIONS ---------------- */

function PisoDestinos({ t, data, nCorregir, reponer, ventas, onNavegar, onTab }) {
  const { resumen } = data;
  const lanes = [
    {
      id: "productos",
      icon: Package,
      titulo: t("nav.productos"),
      dato: t("inventario.lane_catalogo_d", {
        activos: num(resumen.activos),
        anulados: num(resumen.anulados),
      }),
      go: () => onNavegar?.("productos"),
    },
    authStore.tiene("saneamiento") && nCorregir > 0 && {
      id: "saneamiento",
      icon: ClipboardList,
      titulo: t("nav.saneamiento"),
      dato: t("inventario.lane_saneamiento_d", { n: num(nCorregir) }),
      cifra: nCorregir,
      go: () => onNavegar?.("saneamiento"),
    },
    {
      id: "reponer",
      icon: PackagePlus,
      titulo: t("inventario.tab_reponer"),
      dato: reponer?.disponible
        ? t("inventario.lane_reponer_d", {
            n: num(reponer.ya_tarde),
            monto: pesoCorto(reponer.plata_total),
          })
        : t("inventario.lane_reponer_lock"),
      go: () => onTab?.("reponer"),
    },
    {
      id: "rotacion",
      icon: Hourglass,
      titulo: t("inventario.tab_rotacion"),
      dato: ventas?.disponible
        ? t("inventario.lane_rotacion_d")
        : t("inventario.lane_rotacion_lock"),
      go: () => onTab?.("rotacion"),
    },
    {
      id: "margenes",
      icon: TrendingUp,
      titulo: t("inventario.tab_margenes"),
      dato: ventas?.disponible
        ? t("inventario.lane_margenes_d")
        : t("inventario.lane_margenes_lock"),
      go: () => onTab?.("margenes"),
    },
    authStore.tiene("deposito") && {
      id: "deposito",
      icon: Warehouse,
      titulo: t("nav.deposito"),
      dato: t("inventario.lane_deposito_d"),
      go: () => onNavegar?.("deposito"),
      extra: [
        { label: t("nav.conciliacion"), go: () => onNavegar?.("conciliacion") },
        { label: t("nav.ubicaciones"), go: () => onNavegar?.("ubicaciones") },
      ],
    },
    {
      id: "recepciones",
      icon: Truck,
      titulo: t("nav.recepciones"),
      dato: t("inventario.lane_recepciones_d"),
      go: () => onNavegar?.("recepciones"),
      extra: [
        { label: t("nav.movimientos"), go: () => onNavegar?.("movimientos") },
        { label: t("nav.ubicaciones"), go: () => onNavegar?.("ubicaciones") },
      ],
    },
    {
      id: "compras",
      icon: ShoppingCart,
      titulo: t("nav.ordenes_compra"),
      dato: t("inventario.lane_compras_d"),
      go: () => onNavegar?.("ordenes_compra"),
      extra: [
        { label: t("nav.proveedores"), go: () => onNavegar?.("proveedores") },
      ],
    },
  ].filter(Boolean);

  return (
    <section data-nav-id="piso" className="space-y-3">
      <div>
        <h2 className="font-display text-lg font-bold">{t("inventario.piso_titulo")}</h2>
        <p className="mt-1 max-w-2xl text-sm leading-snug text-tinta-suave">
          {t("inventario.piso_sub")}
        </p>
      </div>
      <ul className="divide-y divide-linea overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
        {lanes.map((l) => {
          const Icon = l.icon;
          return (
            <li key={l.id}>
              <button
                type="button"
                onClick={l.go}
                className="flex w-full items-start gap-3 px-4 py-3.5 text-left hover:bg-papel-hondo/40 sm:px-5"
              >
                <Icon size={18} className="mt-0.5 shrink-0 text-tinta-suave" />
                <span className="min-w-0 flex-1">
                  <span className="flex items-baseline justify-between gap-3">
                    <span className="font-display text-lg font-bold">{l.titulo}</span>
                    {l.cifra != null && (
                      <span className="plata text-base font-medium text-oro-tinta">{num(l.cifra)}</span>
                    )}
                  </span>
                  <span className="mt-0.5 block text-sm leading-snug text-tinta-suave">{l.dato}</span>
                </span>
                <ArrowRight size={16} className="mt-1 shrink-0 text-tinta-suave" />
              </button>
              {l.extra && (
                <div className="flex flex-wrap gap-2 px-4 pb-3 pl-11 sm:px-5 sm:pl-12">
                  {l.extra.map((e) => (
                    <button
                      key={e.label}
                      type="button"
                      onClick={e.go}
                      className="rounded-full border border-linea px-2.5 py-1 text-xs font-semibold text-tinta-suave hover:text-tinta"
                    >
                      {e.label}
                    </button>
                  ))}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
