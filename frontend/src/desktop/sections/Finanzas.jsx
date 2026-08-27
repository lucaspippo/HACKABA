import { useEffect, useState } from "react";
import { Lock, Snowflake, TrendingUp, Banknote, CreditCard, FileText, ArrowRight } from "lucide-react";
import AngelaSays from "../../components/AngelaSays";
import { api } from "../../lib/api";
import { peso, pesoCorto, num } from "../../lib/format";
import { useT } from "../../lib/i18n";

// `datos` (de /api/fase) dice qué hay REALMENTE cargado en este tenant (B3):
// con cuentas presentes, ni el intro ni los placeholders piden ese Excel.
// P16: con pagos/cheques/tarjeta cargados (finanzas.json), la liquidez de la
// semana es REAL y su placeholder muere; sin datos, el candado honesto queda.
export default function Finanzas({ data, onPreguntar, datos, onNavegar }) {
  const t = useT();
  const { resumen, alertas } = data;
  const potencial = alertas.sin_pvp.impacto_pesos;
  const hayCuentas = !!datos?.cuentas;
  const [pagos, setPagos] = useState(null);
  useEffect(() => { api.pagos().then(setPagos).catch(() => {}); }, []);
  const liq = pagos?.resumen?.hay_datos ? pagos.resumen : null;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-3xl font-bold">{t("finanzas.titulo")}</h1>
        <p className="mt-1 text-[0.95rem] text-tinta-suave">{t("finanzas.subtitulo")}</p>
      </header>

      <AngelaSays tone="neutral">
        {t(hayCuentas ? "finanzas.angela_intro_ok" : "finanzas.angela_intro")}
      </AngelaSays>

      {/* Lo que SÍ se puede mostrar */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <button
          type="button"
          onClick={() => onNavegar?.("inventario", "plata")}
          className="card-hover rounded-[var(--radius-card)] border border-hielo/20 bg-hielo-claro p-6 text-left sombra-papel"
        >
          <div className="flex items-center gap-2 text-hielo">
            <Snowflake size={18} />
            <p className="text-[0.88rem] font-semibold uppercase tracking-[0.14em]">{t("finanzas.congelado_titulo")}</p>
          </div>
          <p className="plata mt-2 text-4xl font-medium leading-none text-hielo">{peso(resumen.inmovilizado_total)}</p>
          <p className="mt-2 text-[0.95rem] leading-snug text-tinta">
            {t("finanzas.congelado_detalle")}
          </p>
          {onNavegar && (
            <p className="mt-3 inline-flex items-center gap-1.5 text-[0.88rem] font-semibold text-hielo">
              {t("finanzas.congelado_ver_inventario")} <ArrowRight size={13} />
            </p>
          )}
        </button>

        <div className="rounded-[var(--radius-card)] border border-salvia/30 bg-salvia/[0.08] p-6 sombra-papel">
          <div className="flex items-center gap-2 text-salvia">
            <TrendingUp size={18} />
            <p className="text-[0.88rem] font-semibold uppercase tracking-[0.14em]">{t("finanzas.potencial_titulo")}</p>
          </div>
          <p className="plata mt-2 text-4xl font-medium leading-none text-salvia">{peso(potencial)}</p>
          <p className="mt-2 text-[0.95rem] leading-snug text-tinta">
            {num(alertas.sin_pvp.cantidad)} {t("finanzas.potencial_detalle")}
          </p>
        </div>
      </div>

      {/* Liquidez de la semana: REAL cuando pagos/cheques/tarjeta están cargados */}
      {liq && (
        <div>
          <h2 className="mb-3 font-display text-[1.15rem] font-bold">{t("finanzas.liquidez_titulo")}</h2>
          {liq.pagos_vencidos > 0 && (
            <p className="mb-3 rounded-xl border border-rojo/25 bg-rojo/[0.05] px-4 py-2.5 text-[0.95rem] text-tinta">
              {t("finanzas.liq_vencido", { n: num(liq.pagos_vencidos), monto: pesoCorto(liq.vencidos_total) })}
            </p>
          )}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
              <div className="flex items-center gap-2 text-oro-tinta">
                <Banknote size={16} />
                <p className="text-[0.88rem] font-semibold uppercase tracking-[0.12em]">{t("finanzas.liq_por_pagar")}</p>
              </div>
              <p className="plata mt-2 text-3xl font-medium leading-none">{pesoCorto(liq.por_pagar_total)}</p>
              <p className="mt-2 text-[0.95rem] text-tinta-suave">{t("finanzas.liq_por_pagar_sub", { monto: pesoCorto(liq.por_pagar_semana) })}</p>
            </div>
            <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
              <div className="flex items-center gap-2 text-salvia">
                <CreditCard size={16} />
                <p className="text-[0.88rem] font-semibold uppercase tracking-[0.12em]">{t("finanzas.liq_tarjeta")}</p>
              </div>
              <p className="plata mt-2 text-3xl font-medium leading-none text-salvia">{pesoCorto(liq.tarjeta_7dias)}</p>
              <p className="mt-2 text-[0.95rem] text-tinta-suave">{t("finanzas.liq_tarjeta_sub")}</p>
            </div>
            <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
              <div className="flex items-center gap-2 text-hielo">
                <FileText size={16} />
                <p className="text-[0.88rem] font-semibold uppercase tracking-[0.12em]">{t("finanzas.liq_cheques")}</p>
              </div>
              <p className="plata mt-2 text-3xl font-medium leading-none text-hielo">{pesoCorto(liq.cheques_total)}</p>
              <p className="mt-2 text-[0.95rem] text-tinta-suave">{t("finanzas.liq_cheques_sub", { n: num(liq.cheques_cartera) })}</p>
            </div>
          </div>
        </div>
      )}

      {/* P24·F1 — Flujo de caja 30/60/90: el candado murió — es TRABAJO de
          PolPilot con los datos que ya viven acá (comportamiento histórico de
          cobro por cliente − vencimientos cargados). Supuestos DECLARADOS. */}
      {pagos?.proyeccion?.disponible && (
        <div>
          <h2 className="mb-1 font-display text-[1.15rem] font-bold">{t("finanzas.proyeccion_titulo")}</h2>
          <p className="mb-3 text-[0.95rem] text-tinta-suave">{pagos.proyeccion.supuestos}</p>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            {pagos.proyeccion.ventanas.map((v) => (
              <div key={v.dias} className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
                <p className="text-[0.88rem] font-semibold uppercase tracking-[0.14em] text-tinta-suave">
                  {t("finanzas.proyeccion_ventana", { dias: v.dias })}
                </p>
                <p className={`plata mt-2 text-3xl font-medium leading-none ${v.acumulado >= 0 ? "text-salvia" : "text-rojo"}`}>
                  {v.acumulado >= 0 ? "+" : ""}{pesoCorto(v.acumulado)}
                </p>
                <p className="mt-2 text-[0.95rem] text-tinta-suave">
                  {t("finanzas.proyeccion_detalle", { cobros: pesoCorto(v.cobros), pagos: pesoCorto(v.pagos) })}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Estructura preparada (placeholders): cada candado dice la verdad de lo que falta */}
      {(!hayCuentas || !liq) && (
        <div>
          <h2 className="mb-3 font-display text-[1.15rem] font-bold">{t("finanzas.desbloquea_titulo")}</h2>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            {[
              ...(hayCuentas ? [] : [{ tk: "finanzas.bloque_cobros", fk: "finanzas.bloque_cobros_falta" }]),
              ...(liq ? [] : [{ tk: "finanzas.bloque_liquidez", fk: "finanzas.bloque_liquidez_falta" }]),
            ].map((b) => (
              <div key={b.tk} className="rounded-[var(--radius-card)] border border-dashed border-linea bg-papel-hondo/40 p-5">
                <Lock size={16} className="text-tinta-suave" />
                <p className="mt-2 font-display text-[1rem] font-bold leading-tight">{t(b.tk)}</p>
                <p className="mt-1 text-[0.95rem] text-tinta-suave">{t("finanzas.falta", { que: t(b.fk) })}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
