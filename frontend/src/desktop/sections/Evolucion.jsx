import { useEffect, useState } from "react";
import { LineChart, Line, BarChart, Bar, AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, ReferenceLine, LabelList, CartesianGrid } from "recharts";
import { TrendingUp, ArrowRight, AlertTriangle, Sparkles } from "lucide-react";
import { gridProps, ejeX, ejeY, tooltipProps, STROKE_DATA, GRIS_TENUE, tealSecuencial } from "../../components/charts/tema";
import AngelaMark from "../../components/AngelaMark";
import Widget from "../../components/Widget";
import { useVista, vistaStore } from "../../lib/vistaStore";
import { api } from "../../lib/api";
import Cargando from "../../components/Cargando";
import { pesoCorto, peso, num } from "../../lib/format";
import { GRAFICO } from "../../lib/paleta";
import { useT } from "../../lib/i18n";

// Evolución: comparar peras con peras. La serie nominal miente en Argentina;
// acá todo se muestra también en pesos de hoy (deflactado por IPC INDEC).
// Sin ventas cargadas: la sección existe en modo "esperando datos" y despierta
// sola con el MISMO CSV que activa rotación/margen/quiebre.

function CardComparacion({ titulo, comp }) {
  const t = useT();
  if (!comp) return null;
  const real = comp.variacion_real_pct;
  const nominal = comp.variacion_nominal_pct;
  const positivo = real !== null && real >= 0;
  return (
    <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
      <p className="text-[0.72rem] font-semibold uppercase tracking-[0.14em] text-tinta-suave">{titulo}</p>
      {real !== null ? (
        <>
          <p className={`plata mt-1 text-3xl font-medium ${positivo ? "text-salvia" : "text-rojo"}`}>
            {real > 0 ? "+" : ""}{real}%
          </p>
          <p className="text-[0.84rem] font-medium text-tinta">{t("evolucion.en_terminos_reales")}</p>
        </>
      ) : (
        <p className="mt-1 text-[0.9rem] text-tinta-suave">{t("evolucion.sin_indice")}</p>
      )}
      <p className="mt-2 text-[0.8rem] leading-snug text-tinta-suave">
        {t("evolucion.en_pesos_corrientes")} {nominal > 0 ? "+" : ""}{nominal}% ·{" "}
        {peso(comp.nominal_actual)} vs {peso(comp.nominal_anterior)}
      </p>
    </div>
  );
}

export default function Evolucion({ data, onNavegar, onPreguntar }) {
  const t = useT();
  const vista = useVista();
  const [d, setD] = useState(null);
  const [error, setError] = useState(null);
  const [meses, setMeses] = useState(12);
  const [analisis, setAnalisis] = useState(null);
  const [verNominal, setVerNominal] = useState(true);

  // `data` cambia de identidad en cada recarga global (una lista de precios
  // aplicada/revertida, un saneo): los KPIs se re-piden y el número CAMBIA a la
  // vista, sin salir de la sección (P22·A).
  useEffect(() => {
    api.evolucion().then(setD).catch(setError);
    api.analisis().then(setAnalisis).catch(() => {});
  }, [data]);
  const picos = analisis?.estacionalidad?.proximos_picos || [];
  const kpis = analisis?.kpis || {};

  if (!d) return <div className="pt-2"><Cargando error={error} /></div>;

  // --- Modo dormido: el estado honesto que ya usa el producto ---
  if (!d.hay_datos) {
    return (
      <div className="space-y-6">
        <header className="flex items-center gap-2">
          <TrendingUp size={24} className="text-tinta-suave" />
          <div>
            <h1 className="font-display text-3xl font-bold leading-none">{t("evolucion.titulo")}</h1>
            <p className="mt-1 text-[0.95rem] text-tinta-suave">{t("evolucion.subtitulo")}</p>
          </div>
        </header>
        <div className="flex items-start gap-4 rounded-[var(--radius-card)] border border-violeta/15 bg-violeta/[0.04] p-6">
          <AngelaMark size={40} />
          <div className="flex-1">
            <p className="text-[1.02rem] leading-snug text-tinta">
              {t("evolucion.dormida_1")} <b>{t("evolucion.dormida_ventas")}</b> {t("evolucion.dormida_2")} <b>{t("evolucion.dormida_precios_hoy")}</b> {t("evolucion.dormida_3")}
            </p>
            <button
              onClick={() => (onNavegar ? onNavegar("cargar") : onPreguntar?.("¿Qué necesito cargar para ver la evolución del negocio?"))}
              className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.85rem] font-semibold text-crema transition-transform active:scale-95"
            >
              {t("evolucion.cargar_ventas")} <ArrowRight size={15} />
            </button>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {[
            ["evolucion.card_mes_titulo", "evolucion.card_mes_detalle"],
            ["evolucion.card_acumulado_titulo", "evolucion.card_acumulado_detalle"],
            ["evolucion.card_serie_titulo", "evolucion.card_serie_detalle"],
          ].map(([tk, sk]) => (
            <div key={tk} className="rounded-[var(--radius-card)] border border-dashed border-linea bg-papel-hondo/40 p-5">
              <TrendingUp size={18} className="text-tinta-suave" />
              <p className="mt-2 font-display text-[1rem] font-bold leading-tight">{t(tk)}</p>
              <p className="mt-1 text-[0.84rem] leading-snug text-tinta-suave">{t(sk)}</p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // --- Con datos (reales o demo marcada) ---
  const serie = (d.serie || []).slice(-meses);
  // Anotación honesta: el pico REAL del recorte visible, detectado del dato.
  const pico = serie.reduce((mx, p) => (p.real != null && (mx == null || p.real > mx.real) ? p : mx), null);
  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <TrendingUp size={24} className="text-tinta-suave" />
          <div>
            <h1 className="font-display text-3xl font-bold leading-none">{t("evolucion.titulo")}</h1>
            <p className="mt-1 text-[0.95rem] text-tinta-suave">{d.etiqueta_base}</p>
          </div>
        </div>
        {d.demo && (
          <span className="rounded-full border border-oro/40 bg-oro/10 px-3 py-1 text-[0.74rem] font-semibold uppercase tracking-wide text-oro-tinta">
            {t("evolucion.demo_badge")}
          </span>
        )}
      </header>

      {/* P18·A — la fila de KPIs del dueño: MISMA fuente que el chat y el PDF
          (analisis.kpis, cacheado). Cada card existe solo si su dato existe;
          flecha SOLO donde la comparación es real (crecimiento). */}
      {Object.keys(kpis).length > 0 && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 3xl:grid-cols-5">
          {kpis.crecimiento_pct != null && (
            <div className="card-hover rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
              <p className="text-[0.7rem] font-semibold uppercase tracking-wide text-tinta-suave">{t("evolucion.kpi_crec")}</p>
              <p className={`plata mt-1 text-2xl font-medium leading-none ${kpis.crecimiento_pct >= 0 ? "text-salvia" : "text-rojo"}`}>
                {kpis.crecimiento_pct >= 0 ? "↑" : "↓"} {kpis.crecimiento_pct > 0 ? "+" : ""}{kpis.crecimiento_pct}%
              </p>
              <p className="mt-1 text-[0.7rem] leading-snug text-tinta-suave">{t("evolucion.kpi_crec_sub")}</p>
              {(d.serie || []).length >= 6 && (
                <div className="mt-2 h-8">
                  <ResponsiveContainer>
                    <LineChart data={(d.serie || []).slice(-12).filter((p) => p.real != null)} margin={{ top: 2, bottom: 2, left: 2, right: 2 }}>
                      <Line type="monotone" dataKey="real" stroke={GRAFICO.hielo} strokeWidth={1.8} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          )}
          {kpis.rotacion_dias != null && (
            <div className="card-hover rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
              <p className="text-[0.7rem] font-semibold uppercase tracking-wide text-tinta-suave">{t("evolucion.kpi_rot")}</p>
              <p className="plata mt-1 text-2xl font-medium leading-none">{num(kpis.rotacion_dias)} {t("evolucion.kpi_dias")}</p>
              <p className="mt-1 text-[0.7rem] leading-snug text-tinta-suave">{t("evolucion.kpi_rot_sub")}</p>
            </div>
          )}
          {kpis.dormido && (
            <button
              onClick={() => onNavegar?.("oportunidades")}
              className="card-hover rounded-[var(--radius-card)] border border-linea bg-crema p-4 text-left sombra-papel"
            >
              <p className="text-[0.7rem] font-semibold uppercase tracking-wide text-tinta-suave">{t("evolucion.kpi_dormido")}</p>
              <p className="plata mt-1 text-2xl font-medium leading-none text-hielo">{kpis.dormido.pct}%</p>
              <p className="mt-1 text-[0.7rem] leading-snug text-tinta-suave">
                {t("evolucion.kpi_dormido_sub", { monto: pesoCorto(kpis.dormido.monto) })} →
              </p>
            </button>
          )}
          {kpis.margen_teorico && (
            <div className="card-hover rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
              <p className="text-[0.7rem] font-semibold uppercase tracking-wide text-tinta-suave">{t("evolucion.kpi_margen")}</p>
              <p className="plata mt-1 text-2xl font-medium leading-none">{kpis.margen_teorico.pct}%</p>
              <p className="mt-1 text-[0.7rem] leading-snug text-tinta-suave">
                {t("evolucion.kpi_margen_sub", { n: kpis.margen_teorico.sin_pvp })}
              </p>
            </div>
          )}
          {kpis.cobro_dias != null && (
            <div className="card-hover rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
              <p className="text-[0.7rem] font-semibold uppercase tracking-wide text-tinta-suave">{t("evolucion.kpi_cobro")}</p>
              <p className="plata mt-1 text-2xl font-medium leading-none">{num(kpis.cobro_dias)} {t("evolucion.kpi_dias")}</p>
              <p className="mt-1 text-[0.7rem] leading-snug text-tinta-suave">{t("evolucion.kpi_cobro_sub")}</p>
            </div>
          )}
        </div>
      )}

      {d.aviso_indice && (
        <p className="rounded-xl border border-oro/30 bg-oro/[0.07] px-3.5 py-2 text-[0.86rem]">{d.aviso_indice}</p>
      )}

      {(d.alertas || []).map((a) => (
        <div key={a.tipo} className="flex items-start gap-3 rounded-[var(--radius-card)] border border-rojo/25 bg-rojo/[0.05] p-4">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-rojo" />
          <div>
            <p className="font-display text-[0.98rem] font-bold">{a.titulo}</p>
            <p className="mt-0.5 text-[0.88rem] leading-snug text-tinta">{a.detalle}</p>
          </div>
        </div>
      ))}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <CardComparacion
          titulo={d.interanual ? `${d.interanual.mes} vs ${d.interanual.mes_anterior}` : t("evolucion.interanual_fallback")}
          comp={d.interanual}
        />
        <CardComparacion
          titulo={d.ytd ? t("evolucion.ytd_titulo", { anio: d.ytd.anio, meses: d.ytd.meses }) : t("evolucion.ytd_fallback")}
          comp={d.ytd}
        />
      </div>

      <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-[0.78rem] font-semibold uppercase tracking-[0.12em] text-tinta-suave">
              {t("evolucion.grafico_titulo")}
            </p>
            <p className="text-[0.82rem] text-tinta-suave">{t("evolucion.ajuste_copy")} · {d.etiqueta_base}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setVerNominal((v) => !v)}
              className={`rounded-full border px-3 py-1 text-[0.78rem] font-semibold transition-colors ${
                verNominal ? "border-linea bg-papel-hondo/60 text-tinta" : "border-linea text-tinta-suave"
              }`}
            >
              {t("evolucion.toggle_nominal")}
            </button>
            <div className="flex gap-1">
              {[6, 12, 24].map((n) => (
                <button
                  key={n}
                  onClick={() => setMeses(n)}
                  className={`rounded-full px-3 py-1 text-[0.78rem] font-semibold ${
                    meses === n ? "bg-tinta text-crema" : "text-tinta-suave hover:bg-papel-hondo/60"
                  }`}
                >
                  {t("evolucion.n_meses", { n })}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="h-72">
          <ResponsiveContainer>
            <LineChart data={serie} margin={{ left: 12, right: 12, top: 18 }}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="mes" {...ejeX({ tickFormatter: (m) => m.slice(2) })} />
              <YAxis {...ejeY({ tickFormatter: pesoCorto, width: 64 })} />
              <Tooltip {...tooltipProps} formatter={(v, name) => [peso(v), name]} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {pico && (
                <ReferenceLine
                  x={pico.mes}
                  stroke={GRAFICO.tintaSuave}
                  strokeDasharray="3 4"
                  strokeWidth={1}
                  label={{ value: t("evolucion.pico_label"), position: "top", fontSize: 10, fill: GRAFICO.tintaSuave }}
                />
              )}
              {verNominal && (
                <Line type="monotone" dataKey="nominal" name={t("evolucion.serie_nominal")} stroke={GRIS_TENUE} strokeWidth={1.5} strokeDasharray="5 4" dot={false} />
              )}
              <Line type="monotone" dataKey="real" name={t("evolucion.serie_real")} stroke={GRAFICO.hielo} strokeWidth={STROKE_DATA} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-2 text-[0.78rem] text-tinta-suave">
          {t("evolucion.grafico_nota", { base: d.etiqueta_base })}
        </p>
      </div>

      {/* P19·E — el chart YoY mismo-mes se OCULTA a propósito: los pares
          tempranos (2025-07 vs 2024-07) dan +32% real porque la inflación
          sintética del dataset le gana al IPC en ese tramo — un número
          indefendible en entrevista. El cálculo está verificado (el mismo
          motor da interanual +5.7% e YTD +7.9%, que sí quedan a la vista).
          Volver a mostrarlo cuando el dataset acompañe: restaurar el bloque
          de este commit (git log -S yoy_titulo). */}

      {/* P25·C — composición de la facturación por categoría, % mes a mes
          (el análisis vertical como serie: área apilada, últimos 24 meses) */}
      {d.composicion?.length > 0 && (() => {
        const cats = Object.keys(d.composicion[d.composicion.length - 1]).filter((k) => k !== "mes");
        return (
          <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
            <p className="text-[0.78rem] font-semibold uppercase tracking-[0.12em] text-tinta-suave">
              {t("evolucion.comp_titulo")}
            </p>
            <p className="mb-3 text-[0.82rem] text-tinta-suave">{t("evolucion.comp_nota")}</p>
            <div className="h-64">
              <ResponsiveContainer>
                <AreaChart data={d.composicion} margin={{ left: 4, right: 12, top: 6 }} stackOffset="expand">
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="mes" {...ejeX({ tickFormatter: (m) => m.slice(2), tick: { fontSize: 10 } })} />
                  <YAxis {...ejeY({ tickFormatter: (v) => `${Math.round(v * 100)}%`, width: 40, tick: { fontSize: 10 } })} />
                  <Tooltip {...tooltipProps} formatter={(v, name) => [`${v}%`, name]} />
                  {cats.map((c, i) => (
                    <Area key={c} type="monotone" dataKey={c} stackId="1"
                      stroke="none" fill={tealSecuencial(cats.length > 1 ? i / (cats.length - 1) : 0.5)} />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        );
      })()}

      {/* P25·C — la historia argentina en un gráfico: volumen vs pesos reales
          (los DOS crecimientos interanuales, ya calculados y sanos) */}
      {kpis.crecimiento_pct != null && d.interanual?.variacion_real_pct != null && (
        <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
          <p className="text-[0.78rem] font-semibold uppercase tracking-[0.12em] text-tinta-suave">
            {t("evolucion.vol_titulo")}
          </p>
          <p className="mb-3 text-[0.82rem] text-tinta-suave">{t("evolucion.vol_nota")}</p>
          <div className="grid grid-cols-2 gap-4">
            {[{ lk: "evolucion.vol_unidades", v: kpis.crecimiento_pct },
              { lk: "evolucion.vol_reales", v: d.interanual.variacion_real_pct }].map((b) => (
              <div key={b.lk} className="rounded-xl bg-papel-hondo/40 p-4 text-center">
                <p className={`plata text-3xl font-medium ${b.v >= 0 ? "text-salvia" : "text-rojo"}`}>
                  {b.v >= 0 ? "+" : ""}{b.v}%
                </p>
                <p className="mt-1 text-[0.78rem] text-tinta-suave">{t(b.lk)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Estacionalidad por default + los picos que vienen (del cache de análisis) */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Widget widget={{ id: "def-estacionalidad", tipo: "barras", datos_fuente: "estacionalidad_meses", titulo: t("evolucion.def_estacionalidad") }} />
        {picos.length > 0 && (
          <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
            <p className="flex items-center gap-1.5 text-[0.78rem] font-semibold uppercase tracking-[0.12em] text-tinta-suave">
              <Sparkles size={13} className="text-violeta" /> {t("evolucion.picos_titulo")}
            </p>
            <ul className="mt-3 space-y-2.5">
              {picos.map((p, i) => (
                <li key={i} className="flex items-start gap-2.5 text-[0.88rem] leading-snug text-tinta">
                  <span className="plata mt-0.5 shrink-0 rounded-full bg-oro/15 px-2 py-0.5 text-[0.78rem] font-semibold text-oro-tinta">{p.indice}×</span>
                  {p.aviso}
                </li>
              ))}
            </ul>
          </div>
        )}
        {/* Widgets que el dueño le pidió a Ángela para esta sección */}
        {(vista.widgets?.evolucion || []).map((w) => (
          <Widget key={w.id} widget={w} onQuitar={(id) => vistaStore.quitarWidget("evolucion", id)} />
        ))}
      </div>
    </div>
  );
}
