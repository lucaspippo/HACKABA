import { useEffect, useState } from "react";
import { Check, XCircle } from "lucide-react";

// P19·D — el checklist del plan: los pasos YA corrieron en el server (en este
// orden, cada uno con su backup); acá se revelan uno a uno con su checkmark
// para que el trabajo se vea. Mientras revela, la esfera pasa a "ejecutando".
export default function PlanChecklist({ plan, onEjecutando }) {
  const [visibles, setVisibles] = useState(0);
  const pasos = plan.pasos || [];
  useEffect(() => {
    onEjecutando?.(true);
    let k = 0;
    const id = setInterval(() => {
      k += 1;
      setVisibles(k);
      if (k >= pasos.length) {
        clearInterval(id);
        onEjecutando?.(false);
      }
    }, 550);
    return () => { clearInterval(id); onEjecutando?.(false); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <div className="mt-2.5 space-y-1.5 border-t border-linea/70 pt-2.5">
      {pasos.slice(0, visibles).map((p, i) => (
        <div key={i} className="flex items-start gap-2 text-[0.88rem]">
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
      {visibles < pasos.length && (
        <p className="plata text-[0.78rem] font-semibold text-tinta-suave">
          {visibles}/{pasos.length}…
        </p>
      )}
    </div>
  );
}
