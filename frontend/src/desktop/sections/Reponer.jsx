// QUÉ REPONER PRIMERO — el ranking, no un dato.
//
// La diferencia entre un dashboard y esto: un dashboard dice "cobertura: 7
// días". Acá dice "el camión de este proveedor tarda 21, así que vas a estar
// 14 días sin venderlo, y eso son $1.521.061 que no vas a facturar. Empezá
// por acá."
//
// La plata es una cuenta de una línea (días sin stock × venta diaria) y la
// calcula el core, no el modelo. Ver core/reponer.py.
import { useEffect, useState } from "react";
import { TrendingDown, Truck, ArrowRight, Clock } from "lucide-react";
import AngelaMark from "../../components/AngelaMark";
import Cargando from "../../components/Cargando";
import { api } from "../../lib/api";
import { peso, pesoCorto, num } from "../../lib/format";
import { useT } from "../../lib/i18n";

export default function Reponer({ onPreguntar, onNavegar }) {
  const t = useT();
  const [d, setD] = useState(null);

  useEffect(() => { api.reponer().then(setD).catch(() => setD(false)); }, []);

  if (d === null) return <Cargando />;
  if (!d || !d.disponible) {
    return (
      <p className="rounded-[var(--radius-card)] border border-linea bg-crema p-8 text-center
                    text-[0.9rem] text-tinta-suave">
        {d?.motivo || t("reponer.sin_datos")}
      </p>
    );
  }

  return (
    <div className="space-y-5">
      {/* el titular: la plata que cuesta no reponer */}
      <div className="rounded-[var(--radius-card)] border border-rojo/25 bg-crema sombra-papel">
        <div className="flex flex-wrap items-center gap-3 border-b border-linea bg-rojo/[0.04] px-4 py-3">
          <TrendingDown size={18} className="text-rojo" />
          <div className="min-w-0 flex-1">
            <p className="font-display text-[1.05rem] font-bold leading-tight">
              {t("reponer.titulo", { n: num(d.ya_tarde) })}
            </p>
            <p className="text-[0.82rem] text-tinta-suave">
              {t("reponer.sub", { zona: num(d.total_en_zona), tiempo: num(d.con_tiempo) })}
              {d.stockout_mes > 0 ? ` ${t("reponer.stockout_n", { n: num(d.stockout_mes) })}` : ""}
            </p>
          </div>
          <div className="shrink-0 text-right">
            <p className="plata text-xl font-medium text-rojo">{pesoCorto(d.plata_total)}</p>
            <p className="text-[0.7rem] text-tinta-suave">{t("reponer.plata")}</p>
          </div>
        </div>

        <table className="w-full text-[0.85rem]">
          <thead>
            <tr className="border-b border-linea text-[0.68rem] uppercase tracking-wide text-tinta-suave">
              <th className="px-4 py-2 text-left font-semibold">{t("inventario.col_producto")}</th>
              <th className="px-3 py-2 text-right font-semibold">{t("reponer.col_cobertura")}</th>
              <th className="px-3 py-2 text-right font-semibold">{t("reponer.col_lead")}</th>
              <th className="px-3 py-2 text-right font-semibold">{t("reponer.col_ventana")}</th>
              <th className="px-3 py-2 text-right font-semibold">{t("reponer.col_pedir")}</th>
              <th className="px-4 py-2 text-right font-semibold">{t("reponer.col_plata")}</th>
            </tr>
          </thead>
          <tbody>
            {d.items.map((i) => (
              <tr key={i.codigo} className="border-b border-linea/60 last:border-0">
                <td className="px-4 py-2">
                  <p className="font-medium">
                    {onNavegar ? (
                      <button
                        type="button"
                        onClick={() => onNavegar("productos", `q:${i.codigo}`)}
                        className="text-left hover:underline"
                      >
                        {i.producto}
                      </button>
                    ) : i.producto}
                    {i.stockout_risk && (
                      <span className="ml-2 rounded-full bg-rojo/12 px-1.5 py-0.5 text-[0.68rem] font-semibold text-rojo align-middle">
                        {t("reponer.stockout")}
                      </span>
                    )}
                  </p>
                  <p className="text-[0.72rem] text-tinta-suave">
                    {onNavegar ? (
                      <button type="button" onClick={() => onNavegar("proveedores")} className="hover:underline">
                        {i.proveedor}
                      </button>
                    ) : i.proveedor}
                  </p>
                  {(i.incoming_qty || i.outgoing_qty) ? (
                    <p className="text-[0.72rem] text-tinta-suave">
                      {t("reponer.pipeline", {
                        mano: num(i.stock),
                        inc: i.incoming_qty ? t("reponer.pipeline_inc", { n: num(i.incoming_qty) }) : "",
                        out: i.outgoing_qty ? t("reponer.pipeline_out", { n: num(i.outgoing_qty) }) : "",
                      })}
                    </p>
                  ) : null}
                </td>
                <td className="plata px-3 py-2 text-right">{i.cobertura_dias} d</td>
                <td className="plata px-3 py-2 text-right text-tinta-suave">
                  {i.lead_dias} d
                  {/* si el plazo es un supuesto y no un dato del proveedor, se dice */}
                  {!i.lead_propio && <span title={t("reponer.lead_supuesto")}> *</span>}
                </td>
                <td className={`plata px-3 py-2 text-right font-semibold ${
                  i.dias_para_negociar < 0 ? "text-rojo" : "text-oro-tinta"}`}>
                  {i.dias_para_negociar < 0
                    ? t("reponer.tarde", { n: num(-i.dias_para_negociar) })
                    : t("reponer.quedan", { n: num(i.dias_para_negociar) })}
                </td>
                <td className="plata px-3 py-2 text-right">
                  {num(i.sugerido)}{i.por_peso ? " kg" : ""}
                </td>
                <td className="plata px-4 py-2 text-right font-medium text-rojo">
                  {i.plata_en_riesgo > 0 ? peso(i.plata_en_riesgo) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="border-t border-linea px-4 py-2.5 text-[0.76rem] leading-snug text-tinta-suave">
          {t("reponer.nota_cuenta")}
        </p>
      </div>

      {/* así se compra de verdad: una orden por proveedor, no una por producto */}
      <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
        <div className="flex items-center gap-2">
          <Truck size={16} className="text-hielo" />
          <p className="font-display text-[1rem] font-bold">{t("reponer.prov_titulo")}</p>
        </div>
        <p className="mt-0.5 text-[0.84rem] text-tinta-suave">{t("reponer.prov_sub")}</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {d.proveedores.slice(0, 6).map((g) => (
            <button key={g.proveedor} onClick={() => onPreguntar?.(
              t("reponer.prov_preguntar", { proveedor: g.proveedor }))}
              className="rounded-xl border border-linea bg-papel px-3.5 py-2.5 text-left
                         transition-colors hover:border-violeta/50 hover:bg-violeta-suave">
              <div className="flex items-baseline justify-between gap-2">
                <span className="min-w-0 truncate text-[0.9rem] font-semibold">{g.proveedor}</span>
                <span className="plata shrink-0 text-[0.9rem] font-medium text-rojo">
                  {pesoCorto(g.plata_en_riesgo)}
                </span>
              </div>
              <p className="mt-0.5 flex items-center gap-1.5 text-[0.78rem] text-tinta-suave">
                <Clock size={12} />
                {t("reponer.prov_detalle", { n: num(g.items), lead: num(g.lead_dias) })}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* la acción espera el OK: Ángela prepara, el dueño manda */}
      <div className="flex items-start gap-3 rounded-[var(--radius-card)] border border-violeta/25
                      bg-violeta/[0.04] p-4">
        <AngelaMark size={30} />
        <div className="min-w-0 flex-1">
          <p className="text-[0.92rem] leading-snug text-tinta">{t("reponer.angela")}</p>
          <div className="mt-2.5 flex flex-wrap gap-2">
            <button onClick={() => onPreguntar?.(t("reponer.angela_preguntar"))}
              className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2
                         text-[0.86rem] font-semibold text-crema">
              {t("reponer.angela_cta")} <ArrowRight size={14} />
            </button>
            {onNavegar && (
              <>
                <button
                  type="button"
                  onClick={() => onNavegar("ordenes_compra")}
                  className="inline-flex items-center gap-1.5 rounded-full border border-linea px-4 py-2 text-[0.86rem] font-semibold text-tinta"
                >
                  {t("reponer.ir_ordenes")} <ArrowRight size={14} />
                </button>
                <button
                  type="button"
                  onClick={() => onNavegar("proveedores")}
                  className="inline-flex items-center gap-1.5 rounded-full border border-linea px-4 py-2 text-[0.86rem] font-semibold text-tinta-suave"
                >
                  {t("reponer.ir_proveedores")}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
