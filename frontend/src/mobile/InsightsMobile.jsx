import { useEffect, useState } from "react";
import { ArrowRight, Radar } from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import { DrillNegocio } from "../components/CardNegocio";
import FiltrosAccion from "../components/FiltrosAccion";
import { api } from "../lib/api";
import { toast } from "../lib/toastStore";
import { useSession } from "../lib/auth";
import { pesoCorto } from "../lib/format";
import { useT } from "../lib/i18n";
import { accionDe, estiloAccion } from "../lib/prioridadAccion";

// Mobile Prioridades: same ranked inbox as desktop, compact rows + overlay drill —
// same drill props too (confidence, propuesta approval, pattern feedback,
// involucrado drill-through), not a read-only summary of the desktop version.

let _cachePrio = { lang: null, data: null };

// Mirrors Prioridades.jsx's INVOLUCRADO_NAV — where an involucrado's `kind`
// sends the reader when tapped.
const INVOLUCRADO_NAV = {
  client: { section: "cuentas", anchor: (id) => `cliente-${id}` },
  product: { section: "inventario", anchor: (id) => `producto-${id}` },
};

function rowOf(it) {
  return {
    id: it.id,
    tono: it.tono,
    tipo: it.tipo,
    chip: it.chip,
    piso: it.piso,
    titulo: it.titulo,
    detalle: it.resumen,
    monto: it.monto,
    montoLabel: it.monto_label,
    cifraTexto: it.cifra_texto,
    fuentes: it.fuentes || [],
    origen: it.origen || [],
    porque: it.drill?.porque || [],
    grafico: it.drill?.grafico,
    involucrados: it.drill?.involucrados || [],
    supuestos: it.drill?.supuestos || [],
    confidence: it.drill?.confidence,
    metricas: it.drill?.metricas || [],
    macro: it.macro,
    chat: it.accion_chat,
    navegar: it.navegar,
    propuesta: it.propuesta,
    reportes: it.reportes,
  };
}

function Fila({ item, selected, onOpen }) {
  const acc = estiloAccion(item);
  const Icon = acc.icon;
  return (
    <button
      type="button"
      onClick={() => onOpen(item)}
      aria-current={selected || undefined}
      className="flex w-full items-start gap-3 border-b border-linea px-1 py-3 text-left last:border-0"
    >
      <span className="min-w-0 flex-1">
        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[0.68rem] font-semibold ${acc.cls}`}>
          <Icon size={11} /> {item.chip}
        </span>
        <span className="mt-1 block text-[0.9rem] leading-snug text-tinta line-clamp-2">{item.titulo}</span>
      </span>
      {item.monto ? (
        <span className="plata mt-1 shrink-0 text-[0.95rem] font-medium text-tinta">{pesoCorto(item.monto)}</span>
      ) : item.cifraTexto ? (
        <span className="plata mt-1 shrink-0 text-[0.9rem] text-tinta-suave">{item.cifraTexto}</span>
      ) : null}
    </button>
  );
}

export default function InsightsMobile({ onPreguntar, onNavegar }) {
  const t = useT();
  const langKey = useSession()?.usuario?.idioma || "es";
  const [data, setData] = useState(_cachePrio.lang === langKey ? _cachePrio.data : null);
  const [abierta, setAbierta] = useState(null);
  const [filtro, setFiltro] = useState(null);
  const [propResultado, setPropResultado] = useState({});
  const [propTrabajando, setPropTrabajando] = useState(false);
  const [feedbackBusy, setFeedbackBusy] = useState(false);

  useEffect(() => {
    let vivo = true;
    api.prioridades()
      .then((d) => {
        _cachePrio = { lang: langKey, data: d };
        if (vivo) setData(d);
      })
      .catch(() => { if (vivo) setData({ act: [], watch: [], hay_ventas: false }); });
    return () => { vivo = false; };
  }, [langKey]);

  const cargar = () => {
    api.prioridades()
      .then((d) => {
        _cachePrio = { lang: langKey, data: d };
        setData(d);
      })
      .catch(() => setData({ act: [], watch: [], hay_ventas: false }));
  };

  const cargando = data === null;
  const actRaw = data?.act || [];
  const watchRaw = data?.watch || [];
  const todos = [...actRaw, ...watchRaw];
  const act = (filtro ? actRaw.filter((i) => accionDe(i) === filtro) : actRaw).map(rowOf);
  const watch = (filtro ? watchRaw.filter((i) => accionDe(i) === filtro) : watchRaw).map(rowOf);
  const vacio = !cargando && actRaw.length === 0 && watchRaw.length === 0;
  const filtroVacio = !vacio && filtro && act.length === 0 && watch.length === 0;

  useEffect(() => {
    if (!abierta || !filtro) return;
    if (accionDe(abierta) !== filtro) setAbierta(null);
  }, [filtro, abierta]);

  const accAbierta = abierta ? estiloAccion(abierta) : null;

  // Same drill capabilities as desktop's Prioridades.jsx — mirrored here
  // rather than shared because the two screens' surrounding state (row
  // shape, selection model) differ enough that a shared hook would need to
  // abstract more than it'd save.
  const canGiveFeedback = (item) =>
    (item.origen || []).some((o) => o.startsWith("oportunidad:") || o.startsWith("patron:"));

  const aprobarPropuesta = async (c) => {
    const p = c.propuesta;
    if (!p) return;
    setPropTrabajando(true);
    try {
      const r = await api.ordenCompraPreparar({
        codigo: p.codigo, producto: p.producto, proveedor: p.proveedor,
        cantidad: p.cantidad, motivo: c.titulo, origen: c.id,
      });
      setPropResultado((s) => ({ ...s, [c.id]: r.mensaje }));
      toast(r.mensaje);
    } catch {
      toast(t("oportunidades.prop_error"));
    }
    setPropTrabajando(false);
  };

  const giveFeedback = (item, action) => {
    setFeedbackBusy(true);
    api.patronFeedback(item.id, action)
      .then(() => {
        toast(t("aprendizaje.feedback_ok"));
        setAbierta(null);
        cargar();
      })
      .catch(() => toast(t("aprendizaje.feedback_error"), "error"))
      .finally(() => setFeedbackBusy(false));
  };

  const onVerInvolucrado = (iv) => {
    const target = iv.kind && INVOLUCRADO_NAV[iv.kind];
    if (target && iv.id != null) onNavegar?.(target.section, target.anchor(iv.id));
  };

  return (
    <div className="space-y-5 pb-2">
      <header>
        <h1 className="font-display text-2xl font-bold leading-none">{t("nav.prioridades")}</h1>
        <p className="mt-1 text-[0.9rem] text-tinta-suave">
          {actRaw.length > 0 ? t("prioridades.sub_conteo", { n: actRaw.length }) : t("prioridades.sub")}
          {data?.recuperable?.disponible && (
            <span className="plata ml-2 font-semibold text-salvia">
              · {t("prioridades.recuperable", { monto: pesoCorto(data.recuperable.total) })}
            </span>
          )}
        </p>
        {todos.length > 0 && (
          <div className="mt-3">
            <FiltrosAccion items={todos} filtro={filtro} onFiltro={setFiltro} />
          </div>
        )}
      </header>

      {cargando && (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-[var(--radius-card)] border border-linea/60 bg-papel-hondo/50" />
          ))}
        </div>
      )}

      {vacio && (
        <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-8 text-center sombra-papel">
          <Radar size={22} className="mx-auto text-tinta-suave" />
          <p className="mt-2 text-[0.95rem] text-tinta">
            {data?.hay_ventas ? t("insights.vacio") : t("prioridades.sin_datos")}
          </p>
        </div>
      )}

      {act.length > 0 && (
        <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema px-3 sombra-papel">
          {act.map((item) => (
            <Fila key={item.id} item={item} selected={abierta?.id === item.id} onOpen={setAbierta} />
          ))}
        </div>
      )}

      {watch.length > 0 && (
        <section>
          <h2 className="mb-2 text-[0.8rem] font-semibold uppercase tracking-wide text-oro-tinta">
            {t("prioridades.watch")}
          </h2>
          <div className="overflow-hidden rounded-[var(--radius-card)] border border-oro/30 bg-crema px-3 sombra-papel">
            {watch.map((item) => (
              <Fila key={item.id} item={item} selected={abierta?.id === item.id} onOpen={setAbierta} />
            ))}
          </div>
        </section>
      )}

      {filtroVacio && (
        <p className="px-2 py-6 text-center text-[0.88rem] text-tinta-suave">
          {t("prioridades.filtro_vacio")}
        </p>
      )}

      {abierta && (
        <DrillNegocio
          tono={abierta.tono}
          titulo={abierta.titulo}
          monto={abierta.monto}
          montoLabel={abierta.montoLabel}
          cifraTexto={abierta.cifraTexto}
          porque={abierta.porque || []}
          macro={abierta.macro}
          grafico={abierta.grafico}
          involucrados={abierta.involucrados || []}
          supuestos={abierta.supuestos || []}
          fuentes={abierta.fuentes || []}
          origen={abierta.origen || []}
          confidence={abierta.confidence}
          metricas={abierta.metricas || []}
          propuesta={abierta.propuesta}
          propuestaTrabajando={propTrabajando}
          propuestaResultado={propResultado[abierta.id]}
          onAprobarPropuesta={() => aprobarPropuesta(abierta)}
          onFeedback={canGiveFeedback(abierta) ? (action) => giveFeedback(abierta, action) : undefined}
          feedbackBusy={feedbackBusy}
          onVerInvolucrado={onVerInvolucrado}
          chip={abierta.chip}
          chipIcon={accAbierta.icon}
          chipCls={accAbierta.cls}
          onCerrar={() => setAbierta(null)}
          acciones={
            <>
              {abierta.chat && (
                <button
                  onClick={() => { onPreguntar?.(abierta.chat); setAbierta(null); }}
                  className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.84rem] font-semibold text-crema"
                >
                  <AngelaMark size={15} /> {t("insights.accionar_angela")}
                </button>
              )}
              {abierta.navegar && (
                <button
                  onClick={() => { onNavegar?.(abierta.navegar); setAbierta(null); }}
                  className="inline-flex items-center gap-1.5 rounded-full border border-linea px-4 py-2 text-[0.84rem] font-semibold text-tinta-suave hover:text-tinta"
                >
                  {t("insights.ver_analisis")} <ArrowRight size={13} />
                </button>
              )}
            </>
          }
        />
      )}
    </div>
  );
}
