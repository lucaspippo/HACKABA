import { CircleHelp, Shield, ShieldAlert, ShieldQuestion } from "lucide-react";
import { useT } from "../lib/i18n";

const BANDS = {
  high: { lk: "conf.high", icon: Shield, cls: "bg-salvia/15 text-salvia" },
  medium: { lk: "conf.medium", icon: ShieldAlert, cls: "bg-oro/20 text-oro-tinta" },
  low: { lk: "conf.low", icon: ShieldQuestion, cls: "bg-rojo/12 text-rojo" },
  unverified: { lk: "conf.unverified", icon: CircleHelp, cls: "bg-papel-hondo text-tinta-suave" },
};

export function resolveBand({ hasEvidence, qualitativeBand }) {
  if (!hasEvidence) return "unverified";
  if (qualitativeBand && ["high", "medium", "low"].includes(qualitativeBand)) {
    return qualitativeBand;
  }
  return "unverified";
}

export default function ConfidenceIndicator({
  hasEvidence, qualitativeBand, onViewEvidence, hedge,
}) {
  const t = useT();
  const band = resolveBand({ hasEvidence, qualitativeBand });
  const meta = BANDS[band];
  const Icon = meta.icon;
  return (
    <div className="min-w-0">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[0.72rem] font-semibold ${meta.cls}`}>
          <Icon size={12} /> {t(meta.lk)}
        </span>
        {onViewEvidence && hasEvidence && (
          <button type="button" onClick={onViewEvidence}
            className="text-[0.78rem] font-semibold text-hielo hover:underline">
            {t("conf.ver_evidencia")}
          </button>
        )}
      </div>
      <p className="mt-1 text-[0.76rem] leading-snug text-tinta-suave">
        {hedge || t("conf.hedge")}
      </p>
    </div>
  );
}
