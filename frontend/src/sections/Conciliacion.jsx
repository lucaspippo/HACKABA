import { useEffect, useState } from "react";
import { Check, MessageCircle, Scale } from "lucide-react";
import Cargando from "../components/Cargando";
import ConfidenceIndicator from "../components/ConfidenceIndicator";
import { api } from "../lib/api";
import { toast } from "../lib/toastStore";
import { num, peso } from "../lib/format";
import { useT } from "../lib/i18n";

function hasEvidence(hip) {
  const ev = hip?.evidencia || {};
  if (ev.venta || ev.recepcion || (ev.uncounted_lots || []).length) return true;
  return (ev.buscado_en || []).length > 0;
}

function qualitativeBand(confianza) {
  return ["high", "medium", "low"].includes(confianza) ? confianza : null;
}

export default function Conciliacion({ onPreguntar, onNavegar, puedeMovimientos }) {
  const t = useT();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [abierta, setAbierta] = useState(null);
  const [aceptando, setAceptando] = useState(null);
  const [tarasOpen, setTarasOpen] = useState(false);

  const load = () => {
    setError(null);
    api.conciliacion().then(setData).catch((e) => setError(e));
  };
  useEffect(load, []);

  const aceptar = async (id) => {
    setAceptando(id);
    try {
      await api.conciliacionAceptar(id);
      toast(t("conc.aceptado"));
      load();
    } catch {
      toast(t("conc.error"), "error");
    } finally {
      setAceptando(null);
    }
  };

  const preguntar = (row) => {
    const hip = row.hipotesis || {};
    onPreguntar?.(hip.texto || t(hip.lk || "conc.hip.sin_explicacion", hip.params));
  };

  if (!data && !error) return <div className="pt-2"><Cargando /></div>;
  if (error) return <div className="pt-2"><Cargando error={error} /></div>;

  const r = data.resumen || {};
  const diffs = data.diferencias || [];
  const taras = data.taras || [];

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Scale size={24} className="text-tinta-suave" />
          <div>
            <h1 className="font-display text-2xl font-bold leading-none">{t("conc.titulo")}</h1>
            <p className="mt-1 text-[0.9rem] text-tinta-suave">{t("conc.subtitulo")}</p>
          </div>
        </div>
        {puedeMovimientos && onNavegar && (
          <button type="button" onClick={() => onNavegar("movimientos", "discrepancias")}
            className="text-[0.84rem] font-semibold text-hielo">
            {t("conc.ver_movimientos")}
          </button>
        )}
      </header>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Tile label={t("conc.abiertas")} value={num(r.abiertas || 0)} tone={r.abiertas ? "text-oro-tinta" : "text-tinta-suave"} />
        <Tile label={t("conc.taras_tile")} value={num(r.taras || 0)} tone="text-tinta-suave" />
        <Tile label={t("conc.impacto")} value={r.impacto == null ? t("conc.sin_costo") : peso(r.impacto)}
          tone={r.impacto ? "text-rojo" : "text-tinta-suave"} wide />
      </div>

      {diffs.length === 0 && (
        <p className="rounded-[var(--radius-card)] border border-linea bg-crema px-4 py-6 text-[0.92rem] text-tinta-suave">
          {t("conc.vacio")}
        </p>
      )}

      {diffs.map((row) => {
        const hip = row.hipotesis || {};
        const evidOpen = abierta === row.id;
        const acciones = hip.acciones || [];
        return (
          <article key={row.id} className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
            <div className="flex flex-wrap items-start justify-between gap-3 border-b border-linea px-4 py-3">
              <div className="min-w-0">
                <p className="font-display text-[1.05rem] font-bold leading-tight">{row.producto}</p>
                <p className="text-[0.78rem] text-tinta-suave">
                  {[row.lote, row.ubicacion, row.codigo != null && t("inventario.cod", { codigo: row.codigo })]
                    .filter(Boolean).join(" · ")}
                </p>
              </div>
              <div className="text-right">
                <p className={`plata text-xl font-medium ${row.diferencia < 0 ? "text-rojo" : "text-salvia"}`}>
                  {row.diferencia > 0 ? "+" : ""}{num(row.diferencia)}
                </p>
                <p className="text-[0.72rem] text-tinta-suave">
                  {row.impacto == null ? t("conc.sin_costo") : peso(row.impacto)}
                </p>
              </div>
            </div>
            <div className="grid gap-3 px-4 py-3 sm:grid-cols-2">
              <div className="rounded-xl border border-linea bg-papel px-3 py-2">
                <p className="text-[0.68rem] font-semibold uppercase tracking-wide text-tinta-suave">{t("conc.declarado")}</p>
                <p className="plata mt-0.5 text-lg font-medium">{num(row.cantidad)}</p>
              </div>
              <div className="rounded-xl border border-linea bg-papel px-3 py-2">
                <p className="text-[0.68rem] font-semibold uppercase tracking-wide text-tinta-suave">{t("conc.contado")}</p>
                <p className="plata mt-0.5 text-lg font-medium">{num(row.counted_qty)}</p>
              </div>
            </div>
            <div className="space-y-3 px-4 pb-4">
              <p className="text-[0.9rem] leading-snug text-tinta">{t(hip.lk, hip.params) !== hip.lk ? t(hip.lk, hip.params) : hip.texto}</p>
              <ConfidenceIndicator
                hasEvidence={hasEvidence(hip)}
                qualitativeBand={qualitativeBand(hip.confianza)}
                onViewEvidence={() => setAbierta(evidOpen ? null : row.id)}
              />
              {evidOpen && <Evidence hip={hip} t={t} />}
              <div className="flex flex-wrap gap-2">
                {acciones.includes("aceptar_conteo") && (
                  <button type="button" onClick={() => aceptar(row.id)} disabled={aceptando === row.id}
                    className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.84rem] font-semibold text-crema disabled:opacity-50">
                    <Check size={14} /> {t("conc.aceptar")}
                  </button>
                )}
                {acciones.includes("preguntar_angela") && onPreguntar && (
                  <button type="button" onClick={() => preguntar(row)}
                    className="inline-flex items-center gap-1.5 rounded-full border border-linea px-4 py-2 text-[0.84rem] font-semibold text-tinta-suave hover:text-tinta">
                    <MessageCircle size={14} /> {t("conc.preguntar")}
                  </button>
                )}
              </div>
            </div>
          </article>
        );
      })}

      {taras.length > 0 && (
        <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema">
          <button type="button" onClick={() => setTarasOpen((v) => !v)}
            className="flex w-full items-center justify-between px-4 py-3 text-left">
            <span className="text-[0.88rem] font-semibold">{t("conc.taras_titulo", { n: num(taras.length) })}</span>
            <span className="text-[0.78rem] text-tinta-suave">{tarasOpen ? t("conc.ocultar") : t("conc.ver")}</span>
          </button>
          {tarasOpen && taras.map((row) => (
            <div key={row.id} className="flex items-center justify-between gap-3 border-t border-linea px-4 py-2.5">
              <p className="min-w-0 truncate text-[0.88rem]">{row.producto}</p>
              <span className="plata shrink-0 text-[0.82rem] text-tinta-suave">
                {num(row.cantidad)} → {num(row.counted_qty)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Tile({ label, value, tone, wide }) {
  return (
    <div className={`rounded-[var(--radius-card)] border border-linea bg-crema p-3.5 sombra-papel ${wide ? "col-span-2 sm:col-span-1" : ""}`}>
      <p className={`plata text-xl font-medium leading-none ${tone}`}>{value}</p>
      <p className="mt-1 text-[0.76rem] leading-snug text-tinta-suave">{label}</p>
    </div>
  );
}

function Evidence({ hip, t }) {
  const ev = hip.evidencia || {};
  const buscado = ev.buscado_en || [];
  return (
    <div className="rounded-xl border border-linea bg-papel px-3 py-2.5 text-[0.82rem]">
      {ev.venta && (
        <p>{t("conc.ev_venta", { qty: ev.venta.cantidad, fecha: ev.venta.fecha || "—" })}</p>
      )}
      {ev.recepcion && (
        <p>{t("conc.ev_recepcion", { qty: ev.recepcion.cantidad, fecha: ev.recepcion.fecha || "—" })}</p>
      )}
      {(ev.uncounted_lots || []).map((s) => (
        <p key={s.id}>{t("conc.ev_hermano", { lote: s.lote || "—", ubi: s.ubicacion || "—" })}</p>
      ))}
      {buscado.length > 0 && (
        <p className="mt-1 text-tinta-suave">{t("conc.buscado_en", { lugares: buscado.map((k) => t(`conc.buscado.${k}`, {}) === `conc.buscado.${k}` ? k : t(`conc.buscado.${k}`)).join(", ") })}</p>
      )}
    </div>
  );
}
