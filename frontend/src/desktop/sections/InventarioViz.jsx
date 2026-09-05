import { useId, useMemo, useState } from "react";
import {
  Area, Bar, BarChart, CartesianGrid, Cell, ComposedChart, LabelList, Line,
  ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { ejeX, ejeY, gridProps, tooltipProps, GRIS_TENUE, STROKE_DATA } from "../../components/charts/tema";
import { GRAFICO, SERIES } from "../../lib/paleta";
import { num, pesoCorto } from "../../lib/format";
import { useT, tCat } from "../../lib/i18n";

const TICK_FONT = "Hanken Grotesk, system-ui, sans-serif";
const GRID_VALUE = { ...gridProps, horizontal: false, vertical: true };
const BAR_R = [0, 6, 6, 0];
const BAR_R_TOP = [6, 6, 0, 0];
const AGE_FILL = {
  "0_30": SERIES[3],
  "31_90": GRAFICO.hielo,
  "91_180": GRAFICO.oro,
  "181_365": SERIES[4],
  "365_plus": GRAFICO.rojo,
};

export function VizLock({ motivo }) {
  return (
    <p className="rounded-[var(--radius-card)] border border-linea bg-crema px-4 py-5 text-sm text-tinta-suave">
      {motivo}
    </p>
  );
}

function ChartFrame({ children, height = "h-64 sm:h-72", footer }) {
  return (
    <div className="rounded-[var(--radius-card)] border border-linea bg-crema px-4 py-4 sombra-papel sm:px-5 sm:py-5">
      <div className={height}>{children}</div>
      {footer}
    </div>
  );
}

function Leyenda({ items }) {
  return (
    <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
      {items.map((it) => (
        <li key={it.name} className="flex items-center gap-1.5 text-xs text-tinta-suave">
          {it.dash ? (
            <span className="w-3.5 border-t-2 border-dashed" style={{ borderColor: it.color }} />
          ) : (
            <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: it.color }} />
          )}
          {it.name}
        </li>
      ))}
    </ul>
  );
}

function ejeCat(x, t) {
  if (!x || x === "?") return t("inventario.viz_cat_otra");
  const s = tCat(x).replace(/\s*\([^)]*\)/g, "").trim();
  return s.length > 22 ? `${s.slice(0, 20)}…` : s;
}

function corto(s, n = 22) {
  const v = (s || "").trim() || "—";
  return v.length > n ? `${v.slice(0, n - 1)}…` : v;
}

export function ExcessByCat({ data }) {
  const t = useT();
  if (!data?.disponible || !data.categorias?.length) return null;
  const filas = data.categorias.map((c) => ({
    name: ejeCat(c.x, t),
    full: c.x === "?" ? t("inventario.viz_cat_otra") : tCat(c.x),
    necesario: Math.round(c.necesario / 1e6),
    excedente: Math.round(c.excedente / 1e6),
  }));
  return (
    <section data-nav-id="exceso" className="space-y-3">
      <div className="space-y-1">
        <h2 className="font-display text-lg font-bold">{t("inventario.viz_exceso_titulo")}</h2>
        <p className="max-w-2xl text-sm leading-snug text-tinta-suave">
          {t("inventario.viz_exceso_sub", {
            extra: pesoCorto(data.total_excedente),
            falta: pesoCorto(data.total_necesario),
          })}
        </p>
      </div>
      <ChartFrame
        height="h-[20rem] sm:h-[24rem]"
        footer={(
          <Leyenda items={[
            { name: t("inventario.viz_exceso_necesario"), color: GRAFICO.hielo },
            { name: t("inventario.viz_exceso_extra"), color: GRAFICO.oro },
          ]} />
        )}
      >
        <ResponsiveContainer>
          <BarChart data={filas} layout="vertical" margin={{ top: 4, right: 20, left: 8, bottom: 0 }} barCategoryGap="28%">
            <CartesianGrid {...GRID_VALUE} />
            <XAxis type="number" {...ejeX({ tickFormatter: (v) => `$${v}M` })} />
            <YAxis type="category" dataKey="name" width={160} interval={0} {...ejeY()} />
            <Tooltip
              {...tooltipProps}
              labelFormatter={(_, payload) => payload?.[0]?.payload?.full}
              formatter={(v, name) => [`$${num(v)}M`, name]}
            />
            <Bar dataKey="necesario" name={t("inventario.viz_exceso_necesario")}
              stackId="a" fill={GRAFICO.hielo} maxBarSize={22} isAnimationActive={false} />
            <Bar dataKey="excedente" name={t("inventario.viz_exceso_extra")}
              stackId="a" fill={GRAFICO.oro} radius={BAR_R} maxBarSize={22} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </ChartFrame>
    </section>
  );
}

export function ExpiryHorizon({ data }) {
  const t = useT();
  if (!data?.disponible || !(data.total_en_riesgo > 0)) return null;
  const filas = (data.weeks || []).map((w, i) => ({
    name: t("inventario.viz_venc_semana", { n: i + 1 }),
    monto: Math.round((w.monto || 0) / 1e5) / 10,
    lotes: w.lotes,
  }));
  if (!filas.some((f) => f.monto > 0)) return null;
  return (
    <section data-nav-id="venc-horizon" className="space-y-3">
      <div className="space-y-1">
        <h2 className="font-display text-lg font-bold">{t("inventario.viz_venc_titulo")}</h2>
        <p className="max-w-2xl text-sm leading-snug text-tinta-suave">
          {t("inventario.viz_venc_sub", { monto: pesoCorto(data.total_en_riesgo), n: num(data.lotes_en_riesgo) })}
        </p>
      </div>
      <ChartFrame>
        <ResponsiveContainer>
          <BarChart data={filas} margin={{ top: 8, right: 8, left: 4, bottom: 0 }} barCategoryGap="22%">
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="name" interval={0} {...ejeX()} />
            <YAxis {...ejeY({ tickFormatter: (v) => `$${v}M`, width: 44 })} />
            <Tooltip {...tooltipProps} formatter={(v) => [`$${v}M`, t("inventario.viz_venc_serie")]} />
            <Bar dataKey="monto" fill={GRAFICO.rojo} radius={BAR_R_TOP} maxBarSize={56} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </ChartFrame>
    </section>
  );
}

export function SeasonalityCover({ data }) {
  const t = useT();
  if (!data?.disponible || !data.featured) return null;
  const meses = t("inventario.viz_meses").split(",");
  const filas = (data.indice || []).map((idx, i) => ({
    name: meses[i] || String(i + 1),
    indice: idx,
  }));
  const pico = (data.proximos_picos || [])[0];
  return (
    <section data-nav-id="temporada" className="space-y-3">
      <div className="space-y-1">
        <h2 className="font-display text-lg font-bold">{t("inventario.viz_temp_titulo")}</h2>
        <p className="max-w-2xl text-sm leading-snug text-tinta-suave">
          {pico
            ? pico.aviso
            : t("inventario.viz_temp_sub", { cat: tCat(data.featured) })}
          {data.cover_dias != null && (
            <> {t("inventario.viz_temp_cover", { n: num(data.cover_dias), cat: tCat(data.featured) })}</>
          )}
        </p>
      </div>
      <ChartFrame
        footer={(
          <Leyenda items={[
            { name: t("inventario.viz_temp_indice"), color: GRAFICO.hielo },
            { name: t("inventario.viz_temp_normal"), color: GRAFICO.tintaSuave, dash: true },
            data.cover_ratio != null && { name: t("inventario.viz_temp_ratio"), color: GRAFICO.oro, dash: true },
          ].filter(Boolean)} />
        )}
      >
        <ResponsiveContainer>
          <ComposedChart data={filas} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="name" {...ejeX()} />
            <YAxis {...ejeY({ width: 36 })} domain={[0, "auto"]} />
            <Tooltip {...tooltipProps} />
            <ReferenceLine y={1} stroke={GRAFICO.tintaSuave} strokeDasharray="4 4" strokeOpacity={0.55} />
            {data.cover_ratio != null && (
              <ReferenceLine y={data.cover_ratio} stroke={GRAFICO.oro} strokeDasharray="5 4" strokeWidth={1.75} />
            )}
            <Area type="monotone" dataKey="indice" stroke="none" fill={GRAFICO.hielo} fillOpacity={0.12} isAnimationActive={false} />
            <Line type="monotone" dataKey="indice" name={t("inventario.viz_temp_indice")}
              stroke={GRAFICO.hielo} strokeWidth={STROKE_DATA} dot={false} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </ChartFrame>
    </section>
  );
}

export function CoverLeadScatter({ puntos, onSelect }) {
  const t = useT();
  const pts = useMemo(
    () => (puntos || []).filter((p) => p.cobertura_dias != null && (p.plata_en_riesgo || 0) > 0),
    [puntos],
  );
  if (pts.length < 3) return null;
  const xMax = Math.max(30, ...pts.map((p) => p.cobertura_dias));
  const yMax = Math.max(14, ...pts.map((p) => p.lead_dias));
  const mMax = Math.max(1, ...pts.map((p) => p.plata_en_riesgo || 0));
  return (
    <section className="space-y-3">
      <div className="space-y-1">
        <h2 className="font-display text-lg font-bold">{t("inventario.viz_runway_titulo")}</h2>
        <p className="max-w-2xl text-sm leading-snug text-tinta-suave">{t("inventario.viz_runway_sub")}</p>
      </div>
      <ScatterSvg
        points={pts}
        xOf={(p) => p.cobertura_dias}
        yOf={(p) => p.lead_dias}
        xMax={xMax}
        yMax={yMax}
        xLabel={t("inventario.viz_runway_x")}
        yLabel={t("inventario.viz_runway_y")}
        xTickFormat={(v) => `${Math.round(v)}d`}
        yTickFormat={(v) => `${Math.round(v)}d`}
        colorOf={(p) => (p.cobertura_dias < p.lead_dias ? GRAFICO.rojo : GRAFICO.salvia)}
        rOf={(p) => 3.2 + 5.5 * Math.sqrt((p.plata_en_riesgo || 0) / mMax)}
        labelOf={(p) => `${p.producto}\n${pesoCorto(p.plata_en_riesgo)}`}
        diagonal
        onSelect={onSelect}
        footer={(
          <Leyenda items={[
            { name: t("inventario.viz_runway_tarde"), color: GRAFICO.rojo },
            { name: t("inventario.viz_runway_ok"), color: GRAFICO.salvia },
          ]} />
        )}
      />
    </section>
  );
}

export function RotationScatter({ data, onSelect }) {
  const t = useT();
  if (!data?.disponible) return data?.motivo ? <VizLock motivo={data.motivo} /> : null;
  const pts = data.puntos || [];
  if (!pts.length) return null;
  const xMax = 160;
  const yMax = Math.max(10, ...pts.map((p) => p.inmovilizado / 1e6));
  const mMax = Math.max(1, ...pts.map((p) => p.inmovilizado || 0));
  const fill = { sano: GRAFICO.salvia, atencion: GRAFICO.oro, dormido: GRAFICO.rojo };
  return (
    <section data-nav-id="rotacion" className="space-y-3">
      <div className="space-y-1">
        <h2 className="font-display text-lg font-bold">{t("inventario.viz_rot_titulo")}</h2>
        <p className="max-w-2xl text-sm leading-snug text-tinta-suave">{t("inventario.viz_rot_sub")}</p>
      </div>
      <ScatterSvg
        points={pts}
        xOf={(p) => Math.min(xMax, p.dias || 0)}
        yOf={(p) => (p.inmovilizado || 0) / 1e6}
        xMax={xMax}
        yMax={yMax}
        xLabel={t("inventario.viz_rot_x")}
        yLabel={t("inventario.viz_rot_y")}
        xTickFormat={(v) => `${Math.round(v)}d`}
        yTickFormat={(v) => `$${v}M`}
        colorOf={(p) => fill[p.estado] || GRAFICO.hielo}
        rOf={(p) => 3 + 5 * Math.sqrt((p.inmovilizado || 0) / mMax)}
        labelOf={(p) => `${p.producto}\n${pesoCorto(p.inmovilizado)} · ${p.dias}d`}
        vlines={[data.cortes?.sano, data.cortes?.atencion]}
        bands={[
          { from: 0, to: data.cortes?.sano, fill: GRAFICO.salvia },
          { from: data.cortes?.sano, to: data.cortes?.atencion, fill: GRAFICO.oro },
          { from: data.cortes?.atencion, to: xMax, fill: GRAFICO.rojo },
        ]}
        onSelect={onSelect}
        footer={(
          <Leyenda items={[
            { name: t("inventario.viz_rot_sano"), color: GRAFICO.salvia },
            { name: t("inventario.viz_rot_atencion"), color: GRAFICO.oro },
            { name: t("inventario.viz_rot_dormido"), color: GRAFICO.rojo },
          ]} />
        )}
      />
    </section>
  );
}

export function AgingBars({ data }) {
  const t = useT();
  if (!data) return null;
  if (!data.disponible) return <VizLock motivo={data.motivo} />;
  const filas = (data.buckets || []).map((b) => ({
    id: b.id,
    name: t(`inventario.viz_age_${b.id}`),
    monto: Math.round((b.monto || 0) / 1e6),
    lotes: b.lotes,
  })).filter((f) => f.monto > 0);
  if (!filas.length) return null;
  return (
    <section className="space-y-3">
      <div className="space-y-1">
        <h2 className="font-display text-lg font-bold">{t("inventario.viz_age_titulo")}</h2>
        <p className="max-w-2xl text-sm leading-snug text-tinta-suave">
          {t("inventario.viz_age_sub", { pct: num(data.cubierto_pct) })}
        </p>
      </div>
      <ChartFrame height="h-56 sm:h-64">
        <ResponsiveContainer>
          <BarChart data={filas} layout="vertical" margin={{ top: 4, right: 44, left: 8, bottom: 0 }} barCategoryGap="28%">
            <CartesianGrid {...GRID_VALUE} />
            <XAxis type="number" {...ejeX({ tickFormatter: (v) => `$${v}M` })} />
            <YAxis type="category" dataKey="name" width={112} interval={0} {...ejeY()} />
            <Tooltip {...tooltipProps} formatter={(v) => [`$${v}M`, t("inventario.plata_parada")]} />
            <Bar dataKey="monto" radius={BAR_R} maxBarSize={22} isAnimationActive={false}>
              {filas.map((f) => (
                <Cell key={f.id} fill={AGE_FILL[f.id] || GRAFICO.oro} />
              ))}
              <LabelList
                dataKey="monto"
                position="right"
                formatter={(v) => (v > 0 ? `$${v}M` : "")}
                style={{ fontSize: 11, fill: GRAFICO.tintaSuave, fontFamily: TICK_FONT }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartFrame>
    </section>
  );
}

export function GmroiBars({ data }) {
  const t = useT();
  if (!data?.disponible || !data.grupos?.length) return data?.motivo ? <VizLock motivo={data.motivo} /> : null;
  const filas = data.grupos.map((g) => ({
    name: ejeCat(g.label || g.id, t),
    full: tCat(g.label || g.id),
    gmroi: g.gmroi,
    margen: g.margen_pct,
  }));
  return (
    <section className="space-y-3">
      <div className="space-y-1">
        <h2 className="font-display text-lg font-bold">{t("inventario.viz_gmroi_titulo")}</h2>
        <p className="max-w-2xl text-sm leading-snug text-tinta-suave">{t("inventario.viz_gmroi_sub")}</p>
      </div>
      <ChartFrame
        height="h-[20rem] sm:h-[24rem]"
        footer={(
          <Leyenda items={[
            { name: t("inventario.viz_gmroi_ok"), color: GRAFICO.salvia },
            { name: t("inventario.viz_gmroi_bajo"), color: GRAFICO.oro },
            { name: t("inventario.viz_gmroi_pago"), color: GRAFICO.oro, dash: true },
          ]} />
        )}
      >
        <ResponsiveContainer>
          <BarChart data={filas} layout="vertical" margin={{ top: 4, right: 44, left: 8, bottom: 0 }} barCategoryGap="28%">
            <CartesianGrid {...GRID_VALUE} />
            <XAxis type="number" {...ejeX({ tickFormatter: (v) => `${v}×` })} />
            <YAxis type="category" dataKey="name" width={160} interval={0} {...ejeY()} />
            <Tooltip
              {...tooltipProps}
              labelFormatter={(_, payload) => payload?.[0]?.payload?.full}
              formatter={(v) => [`${v}×`, t("inventario.viz_gmroi_serie")]}
            />
            <ReferenceLine x={1} stroke={GRAFICO.oro} strokeDasharray="4 4" />
            <Bar dataKey="gmroi" radius={BAR_R} maxBarSize={22} isAnimationActive={false}>
              {filas.map((f) => (
                <Cell key={f.name} fill={f.gmroi < 1 ? GRAFICO.oro : GRAFICO.salvia} />
              ))}
              <LabelList
                dataKey="gmroi"
                position="right"
                formatter={(v) => `${v}×`}
                style={{ fontSize: 11, fill: GRAFICO.tintaSuave, fontFamily: TICK_FONT }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartFrame>
    </section>
  );
}

export function LeadTruth({ data }) {
  const t = useT();
  if (!data) return null;
  if (!data.disponible) return <VizLock motivo={data.motivo} />;
  const filas = (data.proveedores || []).map((p) => ({
    name: corto(p.proveedor, 20),
    full: p.proveedor || "—",
    assumed: p.assumed,
    actual: p.actual_median,
  }));
  if (!filas.length) return null;
  return (
    <section className="space-y-3">
      <div className="space-y-1">
        <h2 className="font-display text-lg font-bold">{t("inventario.viz_lead_titulo")}</h2>
        <p className="max-w-2xl text-sm leading-snug text-tinta-suave">{t("inventario.viz_lead_sub")}</p>
      </div>
      <ChartFrame
        height="h-56 sm:h-72"
        footer={(
          <Leyenda items={[
            { name: t("inventario.viz_lead_assumed"), color: GRIS_TENUE },
            { name: t("inventario.viz_lead_actual"), color: GRAFICO.hielo },
          ]} />
        )}
      >
        <ResponsiveContainer>
          <BarChart data={filas} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }} barCategoryGap="36%" barGap={4}>
            <CartesianGrid {...GRID_VALUE} />
            <XAxis type="number" {...ejeX({ tickFormatter: (v) => `${v}d` })} />
            <YAxis type="category" dataKey="name" width={160} interval={0} {...ejeY()} />
            <Tooltip
              {...tooltipProps}
              labelFormatter={(_, payload) => payload?.[0]?.payload?.full}
              formatter={(v, name) => [`${v}d`, name]}
            />
            <Bar dataKey="assumed" name={t("inventario.viz_lead_assumed")}
              fill={GRIS_TENUE} radius={BAR_R} maxBarSize={14} isAnimationActive={false} />
            <Bar dataKey="actual" name={t("inventario.viz_lead_actual")}
              fill={GRAFICO.hielo} radius={BAR_R} maxBarSize={14} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </ChartFrame>
    </section>
  );
}

export function BurnChart({ data }) {
  const t = useT();
  if (!data?.disponible) return data?.motivo ? <p className="mt-3 text-sm text-tinta-suave">{data.motivo}</p> : null;
  const filas = data.dias.map((d, i) => ({
    name: d === 0 ? t("inventario.viz_burn_hoy") : `d+${d}`,
    sin: data.sin_camion[i],
    con: data.con_camion[i],
  }));
  const leadTick = `d+${data.lead_dias}`;
  return (
    <div className="mt-4 space-y-2">
      <p className="text-sm font-semibold text-tinta">{t("inventario.viz_burn_titulo")}</p>
      {data.stockout_day != null && (
        <p className="text-xs text-rojo">
          {t("inventario.viz_burn_quiebre", { n: num(data.stockout_day), lead: num(data.lead_dias) })}
        </p>
      )}
      <div className="h-48 rounded-[var(--radius-card)] border border-linea bg-crema px-3 py-3 sm:h-52">
        <ResponsiveContainer>
          <ComposedChart data={filas} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="name" {...ejeX()} />
            <YAxis {...ejeY({ width: 32 })} />
            <Tooltip {...tooltipProps} />
            {filas.some((f) => f.name === leadTick) && (
              <ReferenceLine x={leadTick} stroke={GRAFICO.tintaSuave} strokeDasharray="4 4" strokeOpacity={0.55} />
            )}
            <Area type="monotone" dataKey="sin" stroke="none" fill={GRAFICO.rojo} fillOpacity={0.1} isAnimationActive={false} />
            <Line type="monotone" dataKey="sin" name={t("inventario.viz_burn_sin")}
              stroke={GRAFICO.rojo} strokeWidth={STROKE_DATA} dot={false} isAnimationActive={false} />
            {data.incoming_qty > 0 && (
              <Line type="monotone" dataKey="con" name={t("inventario.viz_burn_con")}
                stroke={GRAFICO.salvia} strokeWidth={2} dot={false} isAnimationActive={false} />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <Leyenda items={[
        { name: t("inventario.viz_burn_sin"), color: GRAFICO.rojo },
        data.incoming_qty > 0 && { name: t("inventario.viz_burn_con"), color: GRAFICO.salvia },
      ].filter(Boolean)} />
    </div>
  );
}

function niceTicks(max, count = 4) {
  if (!(max > 0)) return [0];
  const raw = max / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const norm = raw / mag;
  const step = (norm >= 5 ? 5 : norm >= 2 ? 2 : 1) * mag;
  const ticks = [];
  for (let v = 0; v <= max + step / 2; v += step) ticks.push(Math.round(v * 100) / 100);
  return ticks;
}

function ScatterSvg({
  points, xOf, yOf, xMax, yMax, xLabel, yLabel, xTickFormat, yTickFormat,
  colorOf, rOf, labelOf, onSelect, diagonal, vlines, bands, footer,
}) {
  const [tip, setTip] = useState(null);
  const clipId = useId().replace(/:/g, "");
  const W = 720;
  const H = 380;
  const pad = { l: 58, r: 16, t: 16, b: 46 };
  const plotW = W - pad.l - pad.r;
  const plotH = H - pad.t - pad.b;
  const x = (v) => pad.l + (Math.max(0, v) / xMax) * plotW;
  const y = (v) => H - pad.b - (Math.max(0, v) / yMax) * plotH;
  const xTicks = niceTicks(xMax);
  const yTicks = niceTicks(yMax).filter((v) => v !== 0);
  const ordered = useMemo(
    () => [...points].sort((a, b) => rOf(b) - rOf(a)),
    [points, rOf],
  );
  const diag = Math.min(xMax, yMax);

  return (
    <div className="relative rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img">
        <defs>
          <clipPath id={clipId}>
            <rect x={pad.l} y={pad.t} width={plotW} height={plotH} />
          </clipPath>
        </defs>
        {(bands || []).filter((b) => b.from != null && b.to != null).map((b) => (
          <rect
            key={`${b.from}-${b.to}`}
            x={x(b.from)}
            y={pad.t}
            width={Math.max(0, x(b.to) - x(b.from))}
            height={plotH}
            fill={b.fill}
            opacity={0.07}
          />
        ))}
        {yTicks.map((v) => (
          <g key={`y${v}`}>
            <line x1={pad.l} y1={y(v)} x2={W - pad.r} y2={y(v)} stroke="rgba(33,32,29,0.06)" />
            <text x={pad.l - 8} y={y(v) + 4} fill={GRAFICO.tintaSuave} fontSize="11"
              fontFamily={TICK_FONT} textAnchor="end" style={{ fontVariantNumeric: "tabular-nums" }}>
              {yTickFormat ? yTickFormat(v) : v}
            </text>
          </g>
        ))}
        {xTicks.map((v) => (
          <text key={`x${v}`} x={x(v)} y={H - pad.b + 16} fill={GRAFICO.tintaSuave} fontSize="11"
            fontFamily={TICK_FONT} textAnchor="middle" style={{ fontVariantNumeric: "tabular-nums" }}>
            {xTickFormat ? xTickFormat(v) : v}
          </text>
        ))}
        <line x1={pad.l} y1={H - pad.b} x2={W - pad.r} y2={H - pad.b} stroke={GRAFICO.linea} />
        <g clipPath={`url(#${clipId})`}>
          {diagonal && (
            <line x1={x(0)} y1={y(0)} x2={x(diag)} y2={y(diag)}
              stroke={GRAFICO.linea} strokeDasharray="5 4" />
          )}
          {(vlines || []).filter((v) => v != null).map((v) => (
            <line key={`vl${v}`} x1={x(v)} y1={pad.t} x2={x(v)} y2={H - pad.b}
              stroke={GRAFICO.linea} strokeDasharray="3 4" />
          ))}
          {ordered.map((p, i) => (
            <circle
              key={p.codigo ?? i}
              cx={x(xOf(p))}
              cy={y(yOf(p))}
              r={rOf(p)}
              fill={colorOf(p)}
              stroke={GRAFICO.superficie}
              strokeWidth="1"
              opacity={0.88}
              role={onSelect ? "button" : undefined}
              tabIndex={onSelect ? 0 : undefined}
              aria-label={labelOf(p)}
              style={{ cursor: onSelect ? "pointer" : "default", outline: "none" }}
              onMouseEnter={() => setTip({ text: labelOf(p), px: x(xOf(p)), py: y(yOf(p)) })}
              onMouseLeave={() => setTip(null)}
              onFocus={() => setTip({ text: labelOf(p), px: x(xOf(p)), py: y(yOf(p)) })}
              onBlur={() => setTip(null)}
              onClick={() => onSelect?.(p)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect?.(p); }
              }}
            />
          ))}
        </g>
        {(vlines || []).filter((v) => v != null).map((v) => (
          <text key={`vt${v}`} x={x(v) + 4} y={pad.t + 12} fill={GRAFICO.tintaSuave} fontSize="10" fontFamily={TICK_FONT}>
            {xTickFormat ? xTickFormat(v) : v}
          </text>
        ))}
        <text x={pad.l + plotW / 2} y={H - 8} fill={GRAFICO.tintaSuave} fontSize="11"
          fontFamily={TICK_FONT} textAnchor="middle">{xLabel}</text>
        <text
          x={14}
          y={pad.t + plotH / 2}
          fill={GRAFICO.tintaSuave}
          fontSize="11"
          fontFamily={TICK_FONT}
          textAnchor="middle"
          transform={`rotate(-90 14 ${pad.t + plotH / 2})`}
        >
          {yLabel}
        </text>
      </svg>
      {tip && (
        <div
          className="pointer-events-none absolute z-10 max-w-[16rem] rounded-xl border border-linea bg-crema px-3 py-2 text-xs leading-snug text-tinta sombra-papel"
          style={{
            left: `${(tip.px / W) * 100}%`,
            top: `${(tip.py / H) * 100}%`,
            transform: "translate(12px, -110%)",
            fontFamily: TICK_FONT,
            fontVariantNumeric: "tabular-nums",
            whiteSpace: "pre-line",
          }}
        >
          {tip.text}
        </div>
      )}
      {footer && <div className="px-5 pb-4">{footer}</div>}
    </div>
  );
}
