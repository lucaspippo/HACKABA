import { useEffect, useState } from "react";
import { Check, Trash2, ArrowRight, PackageCheck, Sparkles, Wand2, Undo2 } from "lucide-react";
import AngelaMark from "../../components/AngelaMark";
import { api } from "../../lib/api";
import { toast } from "../../lib/toastStore";
import { pesoCorto, num } from "../../lib/format";
import { useT } from "../../lib/i18n";

// La zona de revisión: los datos nuevos pasan por acá antes de entrar al sistema.
// Ángela los analiza y el dueño resuelve con reglas (no caso por caso).
export default function StagingArea({ onCambio, onRecargar }) {
  const t = useT();
  const [batches, setBatches] = useState([]);
  const [preview, setPreview] = useState({});
  const [resultado, setResultado] = useState(null);
  const [custom, setCustom] = useState({});

  const cargar = () => api.stagingListar().then((d) => {
    setBatches(d.batches);
    onCambio?.(d.batches.length);
    d.batches.forEach((b) => api.stagingPreview(b.id).then((p) => setPreview((s) => ({ ...s, [b.id]: p }))));
  });
  useEffect(() => { cargar(); }, []);

  const resolver = async (bid, obs, accion, params) => {
    await api.stagingResolver(bid, obs.id, accion, params);
    await cargar();
  };

  const resolverCustom = (bid, obs) => {
    const txt = (custom[obs.id] || "").toLowerCase();
    const m = txt.match(/(\d+)/);
    if ((obs.tipo === "precio_perdida" || obs.tipo === "sin_precio") && m) {
      resolver(bid, obs, "set_margen", { margen: parseInt(m[1]) });
    } else {
      resolver(bid, obs, "mantener", {});
    }
    setCustom((s) => ({ ...s, [obs.id]: "" }));
  };

  const integrar = async (bid) => {
    const r = await api.stagingIntegrar(bid);
    setResultado(r);
    await cargar();
    onRecargar?.();
  };

  const [detalleNorm, setDetalleNorm] = useState({});
  const revertirNorm = async (bid) => {
    await api.stagingRevertirNormalizacion(bid);
    toast(t("staging.toast_norm_deshecha"));
    await cargar();
  };

  if (batches.length === 0 && !resultado) {
    return (
      <div className="space-y-4">
        <h1 className="font-display text-3xl font-bold">{t("staging.titulo")}</h1>
        <div className="rounded-[var(--radius-card)] border border-dashed border-linea bg-papel-hondo/40 p-8 text-center">
          <PackageCheck size={28} className="mx-auto text-tinta-suave" />
          <p className="mt-2 text-[0.95rem] text-tinta-suave">{t("staging.vacio")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-2">
        <Sparkles size={24} className="text-violeta" />
        <div>
          <h1 className="font-display text-3xl font-bold leading-none">{t("staging.titulo")}</h1>
          <p className="mt-1 text-[0.9rem] text-tinta-suave">{t("staging.sub")}</p>
        </div>
      </header>

      {resultado && (
        <div className="flex items-start gap-3 rounded-[var(--radius-card)] border border-salvia/40 bg-salvia/[0.07] p-5">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-salvia text-crema"><Check size={18} /></span>
          <p className="text-[1rem] text-tinta">{resultado.mensaje}</p>
        </div>
      )}

      {batches.map((b) => {
        const total = b.observaciones.length;
        const done = b.resueltas;
        const pendientes = b.observaciones.filter((o) => !o.resuelta);
        const pv = preview[b.id];
        return (
          <div key={b.id} className="space-y-4 rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
            <div className="flex items-start gap-3">
              <AngelaMark size={34} estado="esperando" />
              <div className="flex-1">
                <p className="font-display text-[1.1rem] font-bold">
                  {t("staging.revisando", { n: num(b.total_filas), que: t(b.tipo === "venta" ? "staging.ventas" : "staging.productos"), nombre: b.nombre })}
                </p>
                <p className="text-[0.84rem] text-tinta-suave">{t("staging.resolve_regla")}</p>
              </div>
              <button onClick={() => api.stagingDescartar(b.id).then(cargar)} className="inline-flex items-center gap-1.5 rounded-full border border-linea px-3 py-1.5 text-[0.78rem] font-semibold text-tinta-suave hover:text-rojo">
                <Trash2 size={13} /> {t("staging.descartar")}
              </button>
            </div>

            {/* Nivel 1: lo mecánico se normalizó solo — visible, con detalle y reversa */}
            {b.normalizaciones?.total_cambios > 0 && (
              <div className="rounded-xl border border-salvia/30 bg-salvia/[0.06] p-4">
                <div className="flex items-start gap-2.5">
                  <Wand2 size={16} className="mt-0.5 shrink-0 text-salvia" />
                  <div className="min-w-0 flex-1">
                    <p className="text-[0.88rem] leading-snug text-tinta">{b.normalizaciones.resumen}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button onClick={() => setDetalleNorm((s) => ({ ...s, [b.id]: !s[b.id] }))}
                        className="rounded-full border border-linea bg-crema px-3 py-1 text-[0.78rem] font-semibold text-tinta-suave hover:text-tinta">
                        {t(detalleNorm[b.id] ? "staging.ocultar_detalle" : "staging.ver_detalle")}
                      </button>
                      <button onClick={() => revertirNorm(b.id)}
                        className="inline-flex items-center gap-1 rounded-full border border-linea bg-crema px-3 py-1 text-[0.78rem] font-semibold text-tinta-suave hover:text-rojo">
                        <Undo2 size={12} /> {t("staging.revertir_norm")}
                      </button>
                    </div>
                    {detalleNorm[b.id] && (
                      <div className="mt-2 max-h-44 overflow-y-auto rounded-lg border border-linea/60 bg-crema p-2 text-[0.78rem]">
                        {b.normalizaciones.cambios.slice(0, 60).map((c, k) => (
                          <p key={k} className="border-b border-linea/40 py-1 last:border-0">
                            {t("staging.fila", { n: c.fila + 1, col: c.columna })} <span className="text-tinta-suave line-through">{c.original}</span>
                            {" → "}<span className="font-medium">{c.normalizado}</span>
                          </p>
                        ))}
                        {b.normalizaciones.cambios.length > 60 && (
                          <p className="pt-1 text-tinta-suave">{t("staging.y_mas", { n: b.normalizaciones.cambios.length - 60 })}</p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Plan de integración: tipo detectado + relaciones + qué se activa */}
            {b.plan?.apartado_nuevo && (
              <div className="rounded-xl border border-hielo/25 bg-hielo-claro p-4">
                <p className="text-[0.9rem] leading-snug text-tinta">
                  {t("staging.plan_detecte")} <b>{b.plan.nombre}</b>{t("staging.plan_crear")}
                  {b.plan.relaciona_con?.length ? <> {t("staging.plan_conectar")} <b>{b.plan.relaciona_con.join(t("staging.plan_y"))}</b></> : null}.
                </p>
                {b.plan.activa?.length > 0 && (
                  <p className="mt-1.5 text-[0.84rem] text-tinta-suave">
                    {t("staging.plan_activa", { lista: b.plan.activa.join(" · ") })}
                  </p>
                )}
              </div>
            )}

            {/* Progreso */}
            <div>
              <div className="mb-1 flex justify-between text-[0.78rem] text-tinta-suave">
                <span>{t("staging.progreso", { done, total })}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-papel-hondo">
                <div className="h-full bg-salvia transition-all" style={{ width: `${total ? (done / total) * 100 : 100}%` }} />
              </div>
            </div>

            {/* Observaciones (ordenadas por impacto) */}
            <div className="space-y-3">
              {b.observaciones.map((o) => (
                <div key={o.id} className={`rounded-xl border p-4 ${o.resuelta ? "border-salvia/30 bg-salvia/[0.05]" : "border-linea bg-papel"}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-tinta">
                        {o.resuelta && <Check size={14} className="mr-1 inline text-salvia" />}
                        {o.titulo} <span className="plata text-tinta-suave">{t("staging.items", { n: num(o.items) })}</span>
                      </p>
                      <p className="mt-0.5 text-[0.86rem] text-tinta-suave">{o.descripcion}</p>
                    </div>
                    {o.impacto_pesos > 0 && (
                      <span className="plata shrink-0 rounded-full bg-papel-hondo px-2.5 py-0.5 text-[0.74rem] font-semibold text-hielo">{pesoCorto(o.impacto_pesos)}</span>
                    )}
                  </div>
                  {!o.resuelta && (
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      {o.opciones.map((op, k) => (
                        <button key={k} onClick={() => resolver(b.id, o, op.accion, op.params)}
                          className="rounded-full border border-violeta/30 bg-crema px-3 py-1.5 text-[0.8rem] font-semibold text-violeta hover:bg-violeta hover:text-crema">
                          {op.label}
                        </button>
                      ))}
                      <input
                        value={custom[o.id] || ""}
                        onChange={(e) => setCustom((s) => ({ ...s, [o.id]: e.target.value }))}
                        onKeyDown={(e) => e.key === "Enter" && resolverCustom(b.id, o)}
                        placeholder={t("staging.custom_ph")}
                        className="min-w-64 flex-1 rounded-full border border-linea bg-papel px-3 py-1.5 text-[0.8rem] outline-none focus:border-violeta/40"
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Integrar */}
            {pendientes.length === 0 ? (
              <div className="rounded-xl border border-hielo/20 bg-hielo-claro p-4">
                <p className="text-[0.9rem] text-tinta">
                  {t("staging.todo_resuelto")} <b>{pv?.a_integrar ?? b.total_filas}</b> {t("staging.productos_entran")}
                  {pv?.descartados ? t("staging.descarto_dup", { n: pv.descartados }) : ""}.
                  {pv?.cambios?.length ? t("staging.cambios", { lista: pv.cambios.join("; ") }) : ""}
                </p>
                <button onClick={() => integrar(b.id)} className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.85rem] font-semibold text-crema">
                  {t("staging.integrar_btn")} <ArrowRight size={15} />
                </button>
              </div>
            ) : (
              <p className="text-[0.82rem] text-tinta-suave">{t("staging.faltan", { n: pendientes.length })}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
