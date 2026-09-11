import { useEffect, useState } from "react";
import { Target, TrendingUp, PauseCircle, CheckCircle2, User } from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import { useSession } from "../lib/auth";
import { pesoCorto, num } from "../lib/format";
import { useT, useLang } from "../lib/i18n";

// P36·E4 — Objetivos que Ángela MIDE SOLA contra datos reales. El valor actual
// es en vivo (del backend, misma fuente que el resto de la app); el progreso se
// calcula. Cada objetivo muestra de qué cruce sale, su responsable real, y una
// barra con la referencia de dónde venía (para ver si avanza o está estancado).

const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s);

function progresoDe(baseline, valor, meta, direccion) {
  const rango = Math.abs(baseline - meta) || 1;
  const avance = direccion === "menor" ? baseline - valor : valor - baseline;
  return Math.max(0, Math.min(1, avance / rango));
}

function metricaTexto(o, t) {
  if (o.unidad === "pesos")
    return `${pesoCorto(o.actual)} / ${pesoCorto(o.meta)} ${t("obj.liberado")}`;
  const u = o.unidad === "pct" ? "%" : ` ${t(`obj.u_${o.unidad}`)}`;
  const a = o.unidad === "pct" ? num(o.actual) : num(Math.round(o.actual));
  return `${a}${u} → ${num(o.meta)}${o.unidad === "pct" ? "%" : ""}`;
}

const ESTADO = {
  avanza: { lk: "obj.estado_avanza", Icon: TrendingUp, cls: "bg-salvia/12 text-salvia", barra: "bg-salvia" },
  casi: { lk: "obj.estado_casi", Icon: TrendingUp, cls: "bg-violeta/10 text-violeta", barra: "bg-violeta" },
  estancado: { lk: "obj.estado_estancado", Icon: PauseCircle, cls: "bg-oro/15 text-oro-tinta", barra: "bg-oro" },
  cumplido: { lk: "obj.estado_cumplido", Icon: CheckCircle2, cls: "bg-salvia/15 text-salvia", barra: "bg-salvia" },
};

function ObjetivoCard({ o }) {
  const t = useT();
  const estadoKey = o.estado === "avanza" && o.progreso >= 0.85 ? "casi" : o.estado;
  const est = ESTADO[estadoKey] || ESTADO.avanza;
  const prev = o.historial?.length >= 2 ? o.historial[o.historial.length - 2].valor : o.baseline;
  const prevProg = progresoDe(o.baseline, prev, o.meta, o.direccion);
  const pct = Math.round(o.progreso * 100);

  return (
    <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
      <div className="flex items-start justify-between gap-3">
        <p className="font-display text-[1rem] font-bold leading-tight">{t(`obj.o_${o.id}`)}</p>
        <span className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[0.72rem] font-semibold ${est.cls}`}>
          <est.Icon size={12} /> {t(est.lk)}
        </span>
      </div>

      <div className="mt-2 flex items-baseline justify-between gap-2">
        <span className="plata text-lg font-medium text-tinta">{metricaTexto(o, t)}</span>
        <span className="plata text-[0.9rem] font-semibold text-tinta-suave">{pct}%</span>
      </div>

      {/* barra con referencia temporal: el tick marca dónde venía la semana pasada */}
      <div className="relative mt-2 h-2.5 overflow-hidden rounded-full bg-papel-hondo">
        <div className={`h-full rounded-full ${est.barra}`} style={{ width: `${pct}%` }} />
        <span
          className="absolute top-1/2 h-3.5 w-0.5 -translate-y-1/2 rounded bg-tinta/40"
          style={{ left: `calc(${Math.round(prevProg * 100)}% - 1px)` }}
          title={`${Math.round(prevProg * 100)}%`}
        />
      </div>

      <div className="mt-2.5 flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-[0.78rem] text-tinta-suave">
        <span className="inline-flex items-center gap-1">
          <User size={12} /> {cap(o.responsable)}
        </span>
        <span className="inline-flex items-center gap-1">
          <AngelaMark size={12} /> {t("obj.mide_desde")}: {t(o.fuente_lk)}
        </span>
      </div>
    </div>
  );
}

export default function ObjetivosPanel() {
  const t = useT();
  const lang = useLang();
  const session = useSession();
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!session?.token) return;
    fetch(`/api/objetivos-medidos?token=${encodeURIComponent(session.token)}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r)))
      .then(setData)
      .catch(() => setData({ objetivos: [], resumen: {} }));
  }, [session?.token, lang]);

  if (data === null) {
    return (
      <div className="space-y-2.5">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-24 animate-pulse rounded-[var(--radius-card)] border border-linea/60 bg-papel-hondo/50" />
        ))}
      </div>
    );
  }

  const objs = data.objetivos || [];
  const r = data.resumen || {};
  if (objs.length === 0) {
    return (
      <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-6 text-center sombra-papel">
        <Target size={22} className="mx-auto text-tinta-suave" />
        <p className="mt-2 text-[0.9rem] text-tinta-suave">{t("obj.vacio")}</p>
      </div>
    );
  }
  const masCerca = objs.find((o) => o.id === r.mas_cerca);

  return (
    <section>
      <div className="mb-3">
        <h2 className="flex items-center gap-2 font-display text-[1.1rem] font-bold">
          <Target size={18} className="text-violeta" /> {t("obj.titulo")}
        </h2>
        <p className="mt-1 text-[0.85rem] text-tinta-suave">{t("obj.sub")}</p>
        {/* Cabecera con datos reales: activos · avanzaron · más cerca */}
        <div className="mt-2 flex flex-wrap gap-2 text-[0.78rem]">
          <span className="rounded-full bg-papel-hondo px-3 py-1 font-semibold text-tinta">
            {num(r.activos ?? objs.length)} {t("obj.res_activos")}
          </span>
          <span className="rounded-full bg-salvia/12 px-3 py-1 font-semibold text-salvia">
            {num(r.avanzaron ?? 0)} {t("obj.res_avanzaron")}
          </span>
          {masCerca && (
            <span className="rounded-full bg-violeta/10 px-3 py-1 font-semibold text-violeta">
              {t("obj.res_mas_cerca")}: {t(`obj.o_${masCerca.id}`).split(" ").slice(0, 3).join(" ")}… {r.mas_cerca_pct}%
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {objs.map((o) => <ObjetivoCard key={o.id} o={o} />)}
      </div>
    </section>
  );
}
