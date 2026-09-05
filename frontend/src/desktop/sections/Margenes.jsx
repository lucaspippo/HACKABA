import { Fragment, useEffect, useState } from "react";
import { ChevronDown, ChevronRight, Sparkles, Store, Truck } from "lucide-react";
import AngelaMark from "../../components/AngelaMark";
import { api } from "../../lib/api";
import { peso, pesoCorto, num } from "../../lib/format";
import { useT } from "../../lib/i18n";
import { GmroiBars } from "./InventarioViz";

// P38·C — el número que el dueño más pide: cuánto gana POR GRUPO.
//
// Dos canales, porque la distribuidora vende de dos maneras muy distintas y
// promediarlas no responde nada:
//   · MAYORISTA — precio de lista contra costo, ponderado por lo que realmente
//     vendió en 12 meses. Márgenes de distribución (15-21%).
//   · MOSTRADOR — las bocas propias, con los márgenes del rubro. Ahí una horma
//     feteada deja 80% sobre el costo y la misma horma entera, 30%.
//
// Se muestran las DOS definiciones de margen porque el rubro habla las dos:
// margen sobre la venta (el del P&L) y recargo sobre el costo ("le pongo 45%").

function Barra({ pct, max, tono }) {
  const w = max > 0 ? Math.max(3, (pct / max) * 100) : 0;
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-papel-hondo">
      <div className={`h-full rounded-full ${tono}`} style={{ width: `${w}%` }} />
    </div>
  );
}

function TablaCanal({ titulo, sub, icon: Icon, grupos, total, tono, onGrupo, abierto, detalle }) {
  const t = useT();
  const max = Math.max(...grupos.map((g) => g.margen_pct || 0), 1);
  return (
    <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
      <div className="flex items-center gap-2.5 border-b border-linea px-5 py-4">
        <Icon size={18} className="text-tinta-suave" />
        <div className="min-w-0">
          <h3 className="font-display text-lg font-bold leading-tight">{titulo}</h3>
          <p className="text-sm text-tinta-suave">{sub}</p>
        </div>
        {total && (
          <div className="ml-auto shrink-0 text-right">
            <p className={`plata text-xl font-medium ${tono.txt}`}>{total.margen_pct}%</p>
            <p className="text-xs text-tinta-suave">{t("margenes.total_margen")}</p>
          </div>
        )}
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-linea text-xs uppercase tracking-wide text-tinta-suave">
            <th className="px-5 py-2.5 text-left font-semibold">{t("margenes.col_grupo")}</th>
            <th className="px-3 py-2.5 text-right font-semibold">{t("margenes.col_ventas")}</th>
            <th className="w-40 px-3 py-2.5 text-right font-semibold">{t("margenes.col_margen")}</th>
            <th className="px-5 py-2.5 text-right font-semibold">{t("margenes.col_recargo")}</th>
          </tr>
        </thead>
        <tbody>
          {grupos.map((g) => {
            const esAbierto = abierto === g.id;
            return (
              <Fragment key={g.id}>
                <tr onClick={() => onGrupo?.(g)}
                  className={`border-b border-linea/60 last:border-0 ${onGrupo ? "cursor-pointer hover:bg-papel-hondo/40" : ""} ${esAbierto ? "bg-papel-hondo/50" : ""}`}>
                  <td className="px-5 py-2.5">
                    <span className="flex items-center gap-1.5 font-medium">
                      {onGrupo && (esAbierto ? <ChevronDown size={14} className="text-tinta-suave" /> : <ChevronRight size={14} className="text-tinta-suave" />)}
                      {g.label}
                    </span>
                    {g.productos != null && (
                      <span className="text-xs text-tinta-suave">{t("margenes.n_productos", { n: num(g.productos) })}</span>
                    )}
                  </td>
                  <td className="plata px-3 py-2.5 text-right text-tinta-suave">{pesoCorto(g.ventas_12m)}</td>
                  <td className="px-3 py-2.5">
                    <div className="flex items-center justify-end gap-2">
                      <Barra pct={g.margen_pct} max={max} tono={tono.barra} />
                      <span className={`plata w-12 shrink-0 text-right font-semibold ${tono.txt}`}>{g.margen_pct}%</span>
                    </div>
                  </td>
                  <td className="plata px-5 py-2.5 text-right text-tinta-suave">{g.recargo_pct}%</td>
                </tr>
                {esAbierto && (
                  <tr className="border-b border-linea/60">
                    <td colSpan={4} className="bg-papel-hondo/30 px-5 py-3">
                      <Detalle detalle={detalle} grupo={g} />
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Detalle({ detalle, grupo }) {
  const t = useT();
  if (!detalle) return <p className="text-sm text-tinta-suave">{t("margenes.cargando")}</p>;
  if (!detalle.items?.length) return <p className="text-sm text-tinta-suave">{t("margenes.sin_detalle")}</p>;
  return (
    <div>
      <p className="text-sm text-tinta-suave">
        {t("margenes.detalle_nota", { grupo: grupo.label, prom: detalle.promedio_pct })}
      </p>
      <div className="mt-2 overflow-hidden rounded-xl border border-linea bg-crema">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-linea text-2xs uppercase tracking-wide text-tinta-suave">
              <th className="px-3 py-2 text-left font-semibold">{t("inventario.col_producto")}</th>
              <th className="px-3 py-2 text-right font-semibold">{t("margenes.col_unidades")}</th>
              <th className="px-3 py-2 text-right font-semibold">{t("margenes.col_ventas")}</th>
              <th className="px-3 py-2 text-right font-semibold">{t("margenes.col_margen")}</th>
              <th className="px-3 py-2 text-right font-semibold">{t("margenes.col_vs_grupo")}</th>
            </tr>
          </thead>
          <tbody>
            {detalle.items.map((p) => (
              <tr key={p.codigo} className={`border-b border-linea/50 last:border-0 ${p.bajo_su_grupo ? "bg-oro/[0.07]" : ""}`}>
                <td className="px-3 py-1.5">
                  {p.producto}
                  {p.bajo_su_grupo && (
                    <span className="ml-2 rounded-full bg-oro/20 px-1.5 py-0.5 text-2xs font-semibold text-oro-tinta align-middle">
                      {t("margenes.bajo_grupo")}
                    </span>
                  )}
                </td>
                <td className="plata px-3 py-1.5 text-right text-tinta-suave">{num(Math.round(p.unidades_12m))}{p.por_peso ? " kg" : ""}</td>
                <td className="plata px-3 py-1.5 text-right text-tinta-suave">{pesoCorto(p.ventas_12m)}</td>
                <td className={`plata px-3 py-1.5 text-right font-semibold ${p.bajo_su_grupo ? "text-oro-tinta" : ""}`}>{p.margen_unitario_pct}%</td>
                <td className={`plata px-3 py-1.5 text-right ${p.diferencia_pp < 0 ? "text-rojo" : "text-salvia"}`}>
                  {p.diferencia_pp > 0 ? "+" : ""}{p.diferencia_pp} pp
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function Margenes({ onPreguntar, onNavegar, viz }) {
  const t = useT();
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  const [abierto, setAbierto] = useState(null);
  const [detalle, setDetalle] = useState(null);

  useEffect(() => { api.margenes().then(setData).catch(() => setError(true)); }, []);

  const abrirGrupo = async (g) => {
    if (abierto === g.id) { setAbierto(null); return; }
    setAbierto(g.id);
    setDetalle(null);
    try {
      setDetalle(await api.margenes_detalle(g.id));
    } catch { setDetalle({ items: [] }); }
  };

  if (error) return <p className="py-10 text-center text-sm text-tinta-suave">{t("margenes.error")}</p>;
  if (!data) return <div className="skeleton h-72 w-full rounded-[var(--radius-card)]" />;
  if (!data.disponible) {
    return (
      <div className="flex items-start gap-3 rounded-[var(--radius-card)] border border-linea bg-papel-hondo/40 p-6">
        <AngelaMark size={32} />
        <p className="text-base leading-snug text-tinta-suave">{data.motivo || t("margenes.sin_ventas")}</p>
      </div>
    );
  }

  const may = data.mayorista;
  const min = data.minorista?.disponible ? data.minorista : null;
  const peorMay = may.grupos[may.grupos.length - 1];
  const mejorMay = may.grupos[0];

  return (
    <div className="space-y-5">
      <div className="flex items-start gap-3 rounded-[var(--radius-card)] border border-violeta/15 bg-violeta/[0.04] p-5">
        <AngelaMark size={38} />
        <div className="flex-1">
          <p className="text-base leading-snug text-tinta">
            {t("margenes.intro_1")} <b>{mejorMay.label}</b> {t("margenes.intro_2", { alto: mejorMay.margen_pct })}{" "}
            <b>{peorMay.label}</b> {t("margenes.intro_3", { bajo: peorMay.margen_pct })}
            {min && <> {t("margenes.intro_mostrador", { top: min.grupos[0].recargo_pct })}</>}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button onClick={() => onPreguntar?.(t("margenes.preguntar"))}
              className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-sm font-semibold text-crema">
              <Sparkles size={14} /> {t("margenes.preguntar_cta")}
            </button>
            {onNavegar && (
              <button
                type="button"
                onClick={() => onNavegar("productos")}
                className="inline-flex items-center gap-1.5 rounded-full border border-linea px-4 py-2 text-sm font-semibold text-tinta"
              >
                {t("margenes.ir_catalogo")}
              </button>
            )}
          </div>
        </div>
      </div>

      <GmroiBars data={viz?.gmroi} />

      <TablaCanal
        titulo={t("margenes.canal_mayorista")} sub={t("margenes.canal_mayorista_sub")}
        icon={Truck} grupos={may.grupos} total={may.total}
        tono={{ txt: "text-hielo", barra: "bg-hielo" }}
        onGrupo={abrirGrupo} abierto={abierto} detalle={detalle}
      />
      <p className="-mt-3 px-1 text-xs leading-snug text-tinta-suave">{t("margenes.supuesto_mayorista")}</p>

      {min && (
        <>
          <TablaCanal
            titulo={t("margenes.canal_mostrador")}
            sub={t("margenes.canal_mostrador_sub", { locales: min.locales.join(" · ") })}
            icon={Store} grupos={min.grupos} total={min.total}
            tono={{ txt: "text-salvia", barra: "bg-salvia" }}
          />
          <p className="-mt-3 px-1 text-xs leading-snug text-tinta-suave">{t("margenes.supuesto_mostrador")}</p>
        </>
      )}
    </div>
  );
}
