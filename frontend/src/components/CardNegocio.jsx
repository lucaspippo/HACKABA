import { ArrowRight, X, Check, Sparkles } from "lucide-react";
import { useState } from "react";
import { CuerpoConsulta } from "./Widget";
import { pesoCorto, peso } from "../lib/format";
import { useT } from "../lib/i18n";

// P27·C — LA anatomía de card de negocio, una sola para Alertas y
// Oportunidades: chip de tipo (lucide + color semántico) → título en lenguaje
// de dueño → una línea de dato → la cifra grande (tabular-nums) → "Crucé:
// [fuentes]" → acción. La diferencia entre secciones es el ACENTO (rojo/oro/
// azul vs verde) y el chip — nunca dos layouts distintos.

// Acento semántico: rojo = pérdida activa/riesgo serio · oro = atención ·
// azul = informativa · salvia = oportunidad (upside).
export const ACENTO = {
  rojo: { chip: "bg-rojo/10 text-rojo", cifra: "text-rojo", borde: "border-rojo/25" },
  oro: { chip: "bg-oro/15 text-oro-tinta", cifra: "text-oro-tinta", borde: "border-oro/30" },
  azul: { chip: "bg-hielo/15 text-hielo", cifra: "text-hielo", borde: "border-hielo/25" },
  salvia: { chip: "bg-salvia/12 text-salvia", cifra: "text-salvia", borde: "border-salvia/25" },
};

// La cifra grande: plata formateada o un conteo crudo (hay alertas sin $ —
// ahí la verdad grande es el número de ítems, no un peso inventado).
function Cifra({ monto, texto, cls, label }) {
  if (monto == null && !texto) return null;
  return (
    <p className={`plata mt-3 text-2xl font-medium ${cls}`}>
      {monto != null ? pesoCorto(monto) : texto}
      {/* P30·A2 — etiqueta del $ cuando NO es plata a cobrar (facturación, etc.) */}
      {label && <span className="ml-1.5 align-middle text-[0.66rem] font-normal text-tinta-suave">{label}</span>}
    </p>
  );
}

export function CardNegocio({ tono = "salvia", icon: Icon, chip, chipCls, titulo,
                              dato, monto, montoLabel, cifraTexto, fuentes, accion, onClick }) {
  const t = useT();
  const a = ACENTO[tono] || ACENTO.salvia;
  return (
    <button onClick={onClick}
      className="card-hover flex flex-col rounded-[var(--radius-card)] border border-linea bg-crema p-5 text-left sombra-papel">
      <span className={`inline-flex items-center gap-1.5 self-start rounded-full px-2.5 py-1 text-[0.7rem] font-semibold ${chipCls || a.chip}`}>
        {Icon && <Icon size={12} />} {chip}
      </span>
      <p className="mt-2.5 font-display text-[1.05rem] font-bold leading-tight">{titulo}</p>
      {dato && <p className="mt-1 flex-1 text-[0.82rem] leading-snug text-tinta-suave">{dato}</p>}
      <Cifra monto={monto} texto={cifraTexto} cls={a.cifra} label={montoLabel} />
      {fuentes?.length > 0 && (
        <p className="mt-2 text-[0.7rem] leading-snug text-tinta-suave/80">
          {t("cardneg.cruce")} {fuentes.join(" · ")}
        </p>
      )}
      <span className="mt-2 inline-flex items-center gap-1 self-start text-[0.8rem] font-semibold text-tinta">
        {accion || t("cardneg.ver_por_que")} <ArrowRight size={13} />
      </span>
    </button>
  );
}

// El drill-down, consistente en AMBAS secciones: el porqué narrado + el
// gráfico histórico (renderer P21) + los ítems involucrados + los supuestos
// declarados + las acciones que cada sección arma (adoptar / Ángela / ir).
// P38·B — la PROPUESTA con aprobación dentro del drill: Ángela deja la acción
// armada (una orden de compra, una promoción) y espera el OK. Aprobar no
// ejecuta contra nadie: deja el borrador firmado. Human-in-the-loop visible.
function Propuesta({ propuesta, onAprobar, resultado, trabajando }) {
  const t = useT();
  const [pospuesta, setPospuesta] = useState(false);
  if (!propuesta || pospuesta) return null;
  return (
    <div className="mt-4 rounded-xl border border-violeta/25 bg-violeta/[0.05] p-4">
      <p className="flex items-center gap-1.5 text-[0.84rem] font-semibold text-violeta">
        <Sparkles size={14} /> {t("cardneg.prop_titulo")}
      </p>
      <p className="mt-1 font-display text-[1rem] font-bold leading-tight">{propuesta.titulo}</p>
      {propuesta.detalle && <p className="mt-1 text-[0.88rem] leading-snug text-tinta">{propuesta.detalle}</p>}
      {resultado ? (
        <p className="mt-3 flex items-start gap-1.5 text-[0.86rem] font-semibold text-salvia">
          <Check size={15} className="mt-0.5 shrink-0" /> {resultado}
        </p>
      ) : (
        <>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button onClick={onAprobar} disabled={trabajando}
              className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.84rem] font-semibold text-crema disabled:opacity-50">
              <Check size={15} /> {trabajando ? t("cardneg.prop_trabajando") : t("cardneg.prop_aprobar")}
            </button>
            <button onClick={() => setPospuesta(true)}
              className="rounded-full border border-linea px-4 py-2 text-[0.84rem] font-semibold text-tinta-suave hover:text-tinta">
              {t("cardneg.prop_despues")}
            </button>
          </div>
          <p className="mt-2 text-[0.72rem] leading-snug text-tinta-suave">{t("cardneg.prop_nota")}</p>
        </>
      )}
    </div>
  );
}

export function DrillNegocio({ tono = "salvia", titulo, monto, montoLabel, cifraTexto,
                               porque = [], macro, grafico, involucrados = [],
                               supuestos = [], fuentes = [], acciones, onCerrar,
                               propuesta, onAprobarPropuesta, propuestaResultado,
                               propuestaTrabajando }) {
  const t = useT();
  const a = ACENTO[tono] || ACENTO.salvia;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-tinta/40 p-4" onClick={onCerrar}>
      <div onClick={(e) => e.stopPropagation()}
        className="max-h-[88vh] w-full max-w-xl overflow-y-auto rounded-[var(--radius-card)] border border-linea bg-crema p-6 sombra-alta">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-xl font-bold leading-tight">{titulo}</h2>
            {(monto != null || cifraTexto) && (
              <p className={`plata mt-1 text-3xl font-medium ${a.cifra}`}>
                {monto != null ? peso(monto) : cifraTexto}
                {montoLabel && <span className="ml-2 align-middle text-[0.72rem] font-normal text-tinta-suave">{montoLabel}</span>}
              </p>
            )}
          </div>
          <button onClick={onCerrar} className="text-tinta-suave hover:text-tinta"><X size={20} /></button>
        </div>

        {porque.length > 0 && (
          <>
            <h3 className="mt-4 text-[0.76rem] font-semibold uppercase tracking-wide text-tinta-suave">{t("cardneg.drill_porque")}</h3>
            <div className="mt-1.5 space-y-1.5">
              {porque.map((p, i) => (
                <p key={i} className="text-[0.92rem] leading-snug text-tinta">{p}</p>
              ))}
              {macro?.inflacion != null && (
                <p className="rounded-lg border border-hielo/25 bg-hielo/[0.06] px-3 py-2 text-[0.84rem] text-hielo">
                  {t("cardneg.drill_macro", { ipc: macro.inflacion, fuente: macro.fuente || "", fecha: macro.fecha || "" })}
                </p>
              )}
            </div>
          </>
        )}

        {grafico && (
          <div className="mt-4 rounded-xl border border-linea bg-papel p-3">
            <CuerpoConsulta resultado={grafico} t={t} />
            {grafico.meta?.ventana && (
              <p className="mt-1 text-[0.7rem] text-tinta-suave">{grafico.meta.ventana}</p>
            )}
          </div>
        )}

        {involucrados.length > 0 && (
          <>
            <h3 className="mt-4 text-[0.76rem] font-semibold uppercase tracking-wide text-tinta-suave">{t("cardneg.drill_involucrados")}</h3>
            <div className="mt-1.5 overflow-hidden rounded-xl border border-linea">
              {involucrados.map((iv, i) => (
                <div key={i} className="flex items-baseline justify-between gap-3 border-b border-linea/60 px-3 py-2 text-[0.86rem] last:border-0">
                  <span className="min-w-0 flex-1">{iv.nombre}{iv.detalle && <span className="text-tinta-suave"> — {iv.detalle}</span>}</span>
                  {iv.monto != null && <span className="plata shrink-0 font-medium text-hielo">{pesoCorto(iv.monto)}</span>}
                </div>
              ))}
            </div>
          </>
        )}

        <Propuesta propuesta={propuesta} onAprobar={onAprobarPropuesta}
          resultado={propuestaResultado} trabajando={propuestaTrabajando} />

        {supuestos.length > 0 && (
          <p className="mt-3 rounded-lg bg-papel-hondo/50 px-3 py-2 text-[0.78rem] leading-snug text-tinta-suave">
            {supuestos.join(" · ")}
          </p>
        )}

        {fuentes.length > 0 && (
          <p className="mt-3 text-[0.72rem] text-tinta-suave/80">{t("cardneg.cruce")} {fuentes.join(" · ")}</p>
        )}

        {acciones && (
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-linea pt-4">
            {acciones}
          </div>
        )}
      </div>
    </div>
  );
}
