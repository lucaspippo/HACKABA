import { ChevronRight } from "lucide-react";
import { useT } from "../../lib/i18n";

// Shared trail for the ingest pipeline. Order is the job: bring data in,
// review what is waiting, browse what landed, fix what is already live.
const STEPS = [
  { id: "cargar", lk: "nav.cargar" },
  { id: "conectores", lk: "nav.conectores" },
  { id: "staging", lk: "nav.pendientes" },
  { id: "imported", lk: "nav.imported" },
  { id: "saneamiento", lk: "nav.saneamiento" },
];

export default function IngestPipeline({ current, onNavigate }) {
  const t = useT();
  if (!onNavigate) return null;
  return (
    <nav aria-label={t("ingest.pipeline")} className="flex flex-wrap items-center gap-y-1">
      {STEPS.map((step, i) => {
        const active = current === step.id;
        return (
          <span key={step.id} className="inline-flex items-center">
            {i > 0 && <ChevronRight size={12} className="mx-0.5 text-tinta-suave/50" aria-hidden />}
            <button type="button" onClick={() => onNavigate(step.id)}
              aria-current={active ? "page" : undefined}
              className={`rounded-full px-2.5 py-1 text-[0.76rem] font-semibold ${
                active ? "bg-violeta text-crema" : "text-tinta-suave hover:text-tinta"}`}>
              {t(step.lk)}
            </button>
          </span>
        );
      })}
    </nav>
  );
}
