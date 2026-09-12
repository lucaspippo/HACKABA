import { useEffect, useState } from "react";
import { BarChart, Bar, PieChart, Pie, Cell, LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip, Legend, ReferenceLine, LabelList, CartesianGrid } from "recharts";
import { X, Sparkles } from "lucide-react";
import { gridProps, ejeX, ejeY, tooltipProps, STROKE_DATA, GRIS_TENUE } from "./charts/tema";
import { api } from "../lib/api";
import { peso, pesoCorto, num } from "../lib/format";
import { useT, useLang } from "../lib/i18n";
import { GRAFICO, SERIES } from "../lib/paleta";

// Widget dinámico creado por Ángela. Las fuentes de inventario se calculan del
// payload que pasa la sección; las de evolución/estacionalidad se buscan solas
// (autofetch) para poder vivir en cualquier sección que renderice widgets.
const COLORS = SERIES;
const FUENTES_ASYNC = new Set(["evolucion_serie", "estacionalidad_meses", "plata_parada_dias", "consulta"]);

const mesCorto = (lang, m) =>
  new Intl.DateTimeFormat(lang === "en" ? "en-US" : "es-AR", { month: "short" })
    .format(new Date(2026, m - 1, 1))
    .replace(".", "");

function serie(datos_fuente, data) {
  if (!data) return { esPlata: false, filas: [] };
  if (datos_fuente === "datos_a_corregir_por_tipo") {
    const a = data.alertas;
    return {
      esPlata: false,
      filas: [
        { name: "Fantasma", value: a.fantasmas.cantidad },
        { name: "Stock negativo", value: a.negativos.cantidad },
        { name: "Sin precio", value: a.sin_pvp.cantidad },
        { name: "Balanza", value: a.balanza.cantidad },
      ],
    };
  }
  if (datos_fuente === "estado_catalogo") {
    return {
      esPlata: false,
      filas: [
        { name: "Activos", value: data.resumen.activos },
        { name: "Anulados", value: data.resumen.anulados },
      ],
    };
  }
  // default: inmovilizado_por_producto
  return {
    esPlata: true,
    filas: data.top_inmovilizado.slice(0, 8).map((p) => ({ name: p.descripcion, value: p.inmovilizado })),
  };
}

export default function Widget({ widget, data, onQuitar }) {
  const t = useT();
  const lang = useLang();
  const esAsync = FUENTES_ASYNC.has(widget.datos_fuente);
  const [ext, setExt] = useState(null);
  useEffect(() => {
    if (widget.datos_fuente === "evolucion_serie") api.evolucion().then(setExt).catch(() => {});
    else if (widget.datos_fuente === "estacionalidad_meses") api.analisis().then(setExt).catch(() => {});
    // P19·C — el dato se RECALCULA en cada carga desde la misma derivación de
    // rotación del backend (nunca un número congelado en el widget).
    else if (widget.datos_fuente === "plata_parada_dias")
      api.widgetPlataParada(widget.dias || 120).then(setExt).catch(() => {});
    // P21 — widget generativo: la consulta validada viaja con el widget y el
    // server la re-ejecuta en cada entrada (lectura pura, nunca un número viejo).
    else if (widget.datos_fuente === "consulta")
      api.consultaSerie(widget.consulta || {}).then(setExt).catch(() => {});
  }, [widget.datos_fuente, widget.dias]);
  const { esPlata, filas } = serie(widget.datos_fuente, data);
  const fmt = (v) => (esPlata ? pesoCorto(v) : num(v));

  // --- fuentes async: sus filas salen del fetch propio ---
  let cuerpoAsync = null;
  if (esAsync) {
    if (!ext) {
      // Skeleton con la forma del chart (mismo alto: cero salto de layout)
      cuerpoAsync = <div className={`skeleton w-full ${widget.tipo === "card" ? "h-16" : "h-56"}`} />;
    } else if (widget.datos_fuente === "consulta") {
      cuerpoAsync = <CuerpoConsulta resultado={ext} tipo={widget.tipo} t={t} />;
    } else if (widget.datos_fuente === "plata_parada_dias") {
      // La card del dueño: número grande + el contexto honesto; tabla/barras
      // muestran el detalle (top productos de esa plata parada).
      if (!ext.disponible) {
        cuerpoAsync = <p className="py-4 text-[0.85rem] text-tinta-suave">{ext.motivo || t("widget.sin_datos")}</p>;
      } else if (widget.tipo === "tabla") {
        cuerpoAsync = (
          <table className="w-full text-left text-[0.85rem]">
            <tbody>
              {ext.top.map((f, i) => (
                <tr key={i} className="border-b border-linea/60 last:border-0">
                  <td className="py-1.5">{f.producto}</td>
                  <td className="plata py-1.5 text-right text-[0.78rem] text-tinta-suave">
                    {f.dias != null ? t("widget.parada_dias", { n: num(f.dias) }) : t("widget.parada_sin_venta")}
                  </td>
                  <td className="plata py-1.5 text-right font-medium text-hielo">{pesoCorto(f.inmovilizado)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      } else if (widget.tipo === "barras" || widget.tipo === "linea" || widget.tipo === "donut") {
        const filasTop = ext.top.slice(0, 8).map((f) => ({ name: f.producto, value: f.inmovilizado }));
        cuerpoAsync = (
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={filasTop} layout="vertical" margin={{ left: 8, right: 16 }}>
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11, fill: GRAFICO.tintaSuave }} tickFormatter={(s) => (s.length > 16 ? s.slice(0, 16) + "…" : s)} />
                <Tooltip formatter={(v) => pesoCorto(v)} cursor={{ fill: "rgba(27,25,22,0.04)" }} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {filasTop.map((f, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        );
      } else {
        cuerpoAsync = (
          <div>
            <p className="plata text-3xl font-medium text-hielo">{pesoCorto(ext.monto)}</p>
            <p className="mt-1 text-[0.82rem] text-tinta-suave">
              {t("widget.parada_sub", { n: num(ext.productos), dias: num(ext.dias_min), pct: ext.pct_del_stock })}
            </p>
          </div>
        );
      }
    } else if (widget.datos_fuente === "evolucion_serie") {
      const filasSerie = (ext.serie || []).slice(-24);
      cuerpoAsync = filasSerie.length === 0 ? (
        <p className="py-8 text-center text-[0.85rem] text-tinta-suave">{t("widget.sin_datos")}</p>
      ) : (
        <div className="h-56">
          <ResponsiveContainer>
            <LineChart data={filasSerie} margin={{ left: 8, right: 12, top: 6 }}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="mes" {...ejeX({ tickFormatter: (m) => m.slice(2), tick: { fontSize: 10 } })} />
              <YAxis {...ejeY({ tickFormatter: pesoCorto, width: 60, tick: { fontSize: 10 } })} />
              <Tooltip {...tooltipProps} formatter={(v, name) => [peso(v), name]} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="nominal" name={t("evolucion.serie_nominal")} stroke={GRIS_TENUE} strokeWidth={1.5} strokeDasharray="5 4" dot={false} />
              <Line type="monotone" dataKey="real" name={t("evolucion.serie_real")} stroke={GRAFICO.hielo} strokeWidth={STROKE_DATA} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      );
    } else {
      // estacionalidad_meses: promedio del índice mensual entre categorías
      const cats = ext.estacionalidad?.categorias || {};
      const porMes = {};
      for (const c of Object.values(cats)) {
        for (const [m, v] of Object.entries(c.indice || {})) {
          (porMes[m] = porMes[m] || []).push(v);
        }
      }
      const filasMes = Array.from({ length: 12 }, (_, i) => {
        const vs = porMes[String(i + 1)] || porMes[i + 1] || [];
        return { name: mesCorto(lang, i + 1), value: vs.length ? Math.round((vs.reduce((a, b) => a + b, 0) / vs.length) * 100) / 100 : null };
      }).filter((f) => f.value != null);
      const anios = ext.estacionalidad?.anios_analizados;
      cuerpoAsync = filasMes.length === 0 ? (
        <p className="py-8 text-center text-[0.85rem] text-tinta-suave">{t("widget.sin_datos")}</p>
      ) : (
        <div>
          {anios > 0 && (
            <p className="mb-1 text-[0.76rem] text-tinta-suave">{t("widget.est_sub", { n: anios })}</p>
          )}
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={filasMes} margin={{ left: 0, right: 8, top: 16 }}>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="name" {...ejeX({ tick: { fontSize: 10 } })} />
                <YAxis {...ejeY({ width: 34, domain: [0, "auto"], tick: { fontSize: 10 } })} />
                <Tooltip {...tooltipProps} formatter={(v) => [`${v}×`, t("widget.indice_mes")]} />
                <ReferenceLine
                  y={1}
                  stroke={GRAFICO.tintaSuave}
                  strokeDasharray="4 4"
                  strokeWidth={1}
                  label={{ value: t("widget.mes_promedio"), position: "insideTopRight", fontSize: 9, fill: GRAFICO.tintaSuave }}
                />
                <Bar
                  dataKey="value"
                  radius={[4, 4, 0, 0]}
                  label={{ position: "top", fontSize: 9, fill: GRAFICO.tintaSuave, formatter: (v) => `${v}×` }}
                >
                  {filasMes.map((f, i) => (
                    <Cell key={i} fill={f.value >= 1.2 ? GRAFICO.oro : GRAFICO.hielo} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      );
    }
  }

  return (
    <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="flex items-center gap-1.5 text-[0.78rem] font-semibold uppercase tracking-[0.12em] text-tinta-suave">
            <Sparkles size={13} className="text-violeta" /> {widget.titulo}
          </p>
          {/* P21 — la metadata honesta del widget generativo (unidad · ventana) */}
          {widget.subtitulo && (
            <p className="mt-0.5 text-[0.74rem] text-tinta-suave">{widget.subtitulo}</p>
          )}
        </div>
        {onQuitar && (
          <button onClick={() => onQuitar(widget.id)} title="Quitar" aria-label="Quitar" className="text-tinta-suave hover:text-tinta">
            <X size={15} />
          </button>
        )}
      </div>

      {esAsync ? (
        cuerpoAsync
      ) : widget.tipo === "tabla" ? (
        <table className="w-full text-left text-[0.85rem]">
          <tbody>
            {filas.map((f, i) => (
              <tr key={i} className="border-b border-linea/60 last:border-0">
                <td className="py-1.5">{f.name}</td>
                <td className="plata py-1.5 text-right font-medium text-hielo">{fmt(f.value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : widget.tipo === "card" ? (
        <div>
          <p className="plata text-3xl font-medium text-hielo">{fmt(filas[0]?.value || 0)}</p>
          <p className="text-[0.82rem] text-tinta-suave">{filas[0]?.name}</p>
        </div>
      ) : widget.tipo === "donut" ? (
        <div className="h-56">
          <ResponsiveContainer>
            <PieChart>
              <Pie data={filas} dataKey="value" nameKey="name" innerRadius={45} outerRadius={75} stroke="none">
                {filas.map((f, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip formatter={(v) => fmt(v)} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="h-56">
          <ResponsiveContainer>
            <BarChart data={filas} layout="vertical" margin={{ left: 8, right: 16 }}>
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11, fill: GRAFICO.tintaSuave }} tickFormatter={(s) => (s.length > 16 ? s.slice(0, 16) + "…" : s)} />
              <Tooltip formatter={(v) => fmt(v)} cursor={{ fill: "rgba(27,25,22,0.04)" }} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {filas.map((f, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

// P21 — render de CUALQUIER serie del contrato de consultas: línea (temporal,
// hasta 2 series), barras (dimensional u temporal corta), tabla, card KPI.
// Mismo theme de charts; la honestidad viene del server (meta.unidad/ventana).
// P27·C: exportado — los drill-downs de Alertas/Oportunidades renderizan su
// gráfico histórico con ESTE renderer (cero código de chart nuevo).
export function CuerpoConsulta({ resultado, tipo, t }) {
  if (!resultado.ok) {
    return <p className="py-4 text-[0.85rem] text-tinta-suave">{resultado.motivo || t("widget.sin_datos")}</p>;
  }
  const { series, meta } = resultado;
  const esPlata = (meta.unidad || "").includes("$");
  const fmtY = (v) => (meta.unidad === "%" ? `${v}%` : esPlata ? pesoCorto(v) : num(v));
  const s0 = series[0]?.puntos || [];
  if (!s0.length) {
    return <p className="py-4 text-[0.85rem] text-tinta-suave">{t("widget.sin_datos")}</p>;
  }

  if (tipo === "card") {
    // card = el número que resume: total de la serie temporal o el top 1
    const total = meta.temporal ? s0.reduce((a, p) => a + p.y, 0) : s0[0].y;
    const sub = meta.temporal
      ? t("widget.consulta_card_total", { n: num(s0.length) })
      : s0[0].x;
    return (
      <div>
        <p className="plata text-3xl font-medium text-hielo">{fmtY(Math.round(total * 100) / 100)}</p>
        <p className="mt-1 text-[0.82rem] text-tinta-suave">{sub}</p>
      </div>
    );
  }

  if (tipo === "tabla") {
    return (
      <table className="w-full text-left text-[0.85rem]">
        <tbody>
          {s0.slice(0, 15).map((p, i) => (
            <tr key={i} className="border-b border-linea/60 last:border-0">
              <td className="py-1.5">{p.x}</td>
              <td className="plata py-1.5 text-right font-medium text-hielo">{fmtY(p.y)}</td>
              {series[1] && (
                <td className="plata py-1.5 text-right font-medium text-oro-tinta">
                  {fmtY(series[1].puntos.find((q) => q.x === p.x)?.y ?? "—")}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  if (meta.temporal && tipo !== "barras") {
    // línea (default temporal): hasta 2 series sobre el mismo eje
    const xs = [...new Set(series.flatMap((s) => s.puntos.map((p) => p.x)))].sort();
    const data = xs.map((x) => {
      const fila = { x };
      series.forEach((s, i) => { fila[`s${i}`] = s.puntos.find((p) => p.x === x)?.y ?? null; });
      return fila;
    });
    const colores = [GRAFICO.hielo, GRAFICO.oro];
    return (
      <div className="h-56">
        <ResponsiveContainer>
          <LineChart data={data} margin={{ left: 8, right: 12, top: 6 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="x" {...ejeX({ tickFormatter: (m) => String(m).slice(2), tick: { fontSize: 10 } })} />
            <YAxis {...ejeY({ tickFormatter: fmtY, width: 62, tick: { fontSize: 10 } })} />
            <Tooltip {...tooltipProps} formatter={(v, name) => [fmtY(v), name]} />
            {series.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
            {series.map((s, i) => (
              <Line key={i} type="monotone" dataKey={`s${i}`} name={s.nombre}
                stroke={colores[i % colores.length]} strokeWidth={STROKE_DATA} dot={false} connectNulls />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // barras: horizontal para dimensional (nombres largos), vertical para temporal
  if (meta.temporal) {
    const data = s0.map((p) => ({ x: String(p.x).slice(2), y: p.y }));
    return (
      <div className="h-56">
        <ResponsiveContainer>
          <BarChart data={data} margin={{ left: 8, right: 12, top: 6 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="x" {...ejeX({ tick: { fontSize: 10 } })} />
            <YAxis {...ejeY({ tickFormatter: fmtY, width: 62, tick: { fontSize: 10 } })} />
            <Tooltip {...tooltipProps} formatter={(v) => [fmtY(v), series[0].nombre]} />
            <Bar dataKey="y" fill={GRAFICO.hielo} radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }
  const data = s0.map((p) => ({ name: p.x, value: p.y }));
  return (
    <div className="h-56">
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="name" width={130} tick={{ fontSize: 11, fill: GRAFICO.tintaSuave }} tickFormatter={(s) => (s.length > 18 ? s.slice(0, 18) + "…" : s)} />
          <Tooltip formatter={(v) => fmtY(v)} cursor={{ fill: "rgba(27,25,22,0.04)" }} />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {data.map((f, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
