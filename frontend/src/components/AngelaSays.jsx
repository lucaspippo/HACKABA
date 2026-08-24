import AngelaMark from "./AngelaMark";

// La "voz de Ángela": nunca una burbuja de chat fría. Una nota cálida, firmada,
// que aparece junto al dato para explicarlo en lenguaje humano.
export default function AngelaSays({ children, tone = "neutral", className = "" }) {
  const accent =
    tone === "urgente"
      ? "border-rojo/30 bg-rojo/[0.04]"
      : tone === "atencion" // P9·D: antes caía a neutral — ahora tiene su oro
      ? "border-oro/40 bg-oro/[0.06]"
      : tone === "ok"
      ? "border-salvia/30 bg-salvia/[0.05]"
      : "border-linea bg-crema";

  return (
    <div className={`flex gap-3 rounded-[var(--radius-card)] border ${accent} p-3.5 ${className}`}>
      <AngelaMark size={30} />
      <div className="min-w-0 pt-0.5">
        <p className="text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-tinta-suave">
          Ángela
        </p>
        <div className="mt-0.5 text-[0.95rem] leading-snug text-tinta">{children}</div>
      </div>
    </div>
  );
}
