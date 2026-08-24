import { Sparkles, Lock, ArrowRight } from "lucide-react";
import AngelaMark from "./AngelaMark";
import { pesoCorto } from "../lib/format";
import { useT } from "../lib/i18n";

// Una oportunidad: plata que se puede capturar. Distinta visualmente de una alerta
// (la alerta es un problema; la oportunidad es upside). Verde/salvia, no rojo.
export default function OportunidadCard({ op, onGestionar }) {
  const t = useT();
  if (op.estado === "pendiente_datos") {
    return (
      <div className="overflow-hidden rounded-[var(--radius-card)] border border-dashed border-linea bg-papel-hondo/40 p-4">
        <div className="flex items-center gap-2 text-tinta-suave">
          <Lock size={15} />
          <h3 className="font-display text-[1rem] font-bold leading-tight">{op.titulo}</h3>
        </div>
        <p className="mt-1.5 text-[0.88rem] leading-snug text-tinta-suave">{op.descripcion}</p>
        <p className="mt-2 inline-flex rounded-full bg-papel-hondo px-2.5 py-0.5 text-[0.72rem] font-semibold uppercase tracking-wide text-tinta-suave">
          {t("oportunidades.falta", { que: op.falta })}
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-[var(--radius-card)] border border-salvia/30 bg-salvia/[0.05] sombra-papel">
      <div className="flex items-stretch">
        <div className="w-1.5 shrink-0 bg-salvia" />
        <div className="flex-1 p-4">
          <div className="flex items-center gap-1.5 text-salvia">
            <Sparkles size={15} />
            <span className="text-[0.72rem] font-bold uppercase tracking-[0.12em]">{t("oportunidades.card_label")}</span>
          </div>
          <h3 className="mt-1 font-display text-[1.05rem] font-bold leading-tight text-tinta">
            {op.titulo}
          </h3>
          <p className="mt-1.5 text-[0.9rem] leading-snug text-tinta-suave">{op.descripcion}</p>

          {op.impacto_pesos > 0 && (
            <p className="mt-2.5 inline-flex items-baseline gap-1.5 rounded-full bg-crema px-3 py-1">
              <span className="plata text-[0.95rem] font-medium text-salvia">
                {pesoCorto(op.impacto_pesos)}
              </span>
              <span className="text-[0.72rem] font-semibold text-tinta-suave">{op.impacto_label}</span>
            </p>
          )}

          <button
            onClick={() => onGestionar?.(op)}
            className="mt-3 flex items-center gap-2 rounded-full border border-salvia/40 bg-crema px-3 py-1.5 text-[0.82rem] font-semibold text-salvia transition-colors hover:bg-salvia hover:text-crema"
          >
            <AngelaMark size={18} />
            {t("oportunidades.gestionar")}
            <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
