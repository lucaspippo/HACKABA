import { pesoCorto } from "../lib/format";
import { useT } from "../lib/i18n";

// El patrón de decisión unificado (P14): toda propuesta que espera el OK del
// dueño se encuadra igual — eyebrow "Espera tu OK", el preview de la acción
// concreta, el impacto en $ (solo si es real) y los botones de cada flujo.
// Wrapper visual puro: cero lógica; handlers y labels los pone cada pantalla.
export default function PanelDecision({ impacto, extra, acciones, children, className = "" }) {
  const t = useT();
  return (
    <div className={`rounded-[var(--radius-card)] border border-oro/30 bg-crema p-4 sombra-papel ${className}`}>
      <div className="mb-2.5 flex items-center justify-between gap-3">
        <p className="text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-oro-tinta">
          {t("decision.espera_ok")}
        </p>
        <div className="flex items-center gap-2.5">
          {extra}
          {impacto != null && impacto > 0 && (
            <span className="plata text-lg font-medium leading-none text-tinta">{pesoCorto(impacto)}</span>
          )}
        </div>
      </div>
      {children}
      {acciones && (
        <div className="mt-3.5 flex flex-wrap items-center gap-2 border-t border-linea pt-3">{acciones}</div>
      )}
    </div>
  );
}
