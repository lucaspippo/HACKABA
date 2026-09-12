import { useEffect, useState } from "react";
import { Check, XCircle } from "lucide-react";

// The plan checklist: the steps already ran on the server (in this order,
// each with its own backup); here they're revealed one by one with a
// checkmark so the work becomes visible. While revealing, the mark switches
// to "executing".
export default function PlanChecklist({ plan, onExecutingChange }) {
  const [visibleCount, setVisibleCount] = useState(0);
  const steps = plan.pasos || [];
  useEffect(() => {
    onExecutingChange?.(true);
    let k = 0;
    const id = setInterval(() => {
      k += 1;
      setVisibleCount(k);
      if (k >= steps.length) {
        clearInterval(id);
        onExecutingChange?.(false);
      }
    }, 550);
    return () => { clearInterval(id); onExecutingChange?.(false); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <div className="mt-2.5 space-y-1.5 border-t border-linea/70 pt-2.5">
      {steps.slice(0, visibleCount).map((p, i) => (
        <div key={i} className="flex items-start gap-2 text-sm">
          {p.ok ? (
            <Check size={15} className="mt-0.5 shrink-0 text-salvia" />
          ) : (
            <XCircle size={15} className="mt-0.5 shrink-0 text-rojo" />
          )}
          <span className={p.ok ? "text-tinta" : "text-rojo-hondo"}>
            {p.titulo}
            {p.detalle && <span className="text-tinta-suave"> — {p.detalle}</span>}
            {p.error && <span className="text-rojo-hondo"> — {p.error}</span>}
          </span>
        </div>
      ))}
      {visibleCount < steps.length && (
        <p className="plata text-xs font-semibold text-tinta-suave">
          {visibleCount}/{steps.length}…
        </p>
      )}
    </div>
  );
}
