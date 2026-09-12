import { useState } from "react";
import { Check, ArrowRight } from "lucide-react";
import AngelaMark from "./AngelaMark";
import { useT } from "../lib/i18n";

// The propose -> approve -> done pattern, reusable by any surface where
// Ángela leaves an action assembled and waits for a human yes.
//
// It is deliberately domain-agnostic: it never mentions purchase orders. The
// caller supplies the copy (`proposal`) and, when the action has already run,
// the record it produced (`actionTaken`) — which comes from the server, not
// from local state, so the done view survives a reload and looks the same to
// every user.
export default function AngelaProposal({ proposal, onApprove, working,
                                         actionTaken, onDismiss }) {
  const t = useT();
  const [postponed, setPostponed] = useState(false);

  // Done wins over pending: if the record exists, the decision is made.
  if (actionTaken) {
    return (
      <div className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1 rounded-xl border border-salvia/25 bg-salvia/[0.06] px-3.5 py-2.5 text-[0.84rem]">
        <Check size={15} className="shrink-0 text-salvia" />
        <span className="plata font-semibold text-tinta">{actionTaken.label}</span>
        {actionTaken.actor && (
          <span className="text-tinta-suave">
            · {t("angelaprop.hecho_por", { actor: actionTaken.actor })}
          </span>
        )}
        {actionTaken.onOpen && (
          <button type="button" onClick={actionTaken.onOpen}
            className="ml-auto inline-flex items-center gap-1 font-semibold text-tinta-suave hover:text-tinta">
            {t("angelaprop.ver")} <ArrowRight size={13} />
          </button>
        )}
      </div>
    );
  }

  if (!proposal || postponed) return null;

  return (
    <div className="mt-4 rounded-xl border border-violeta/25 bg-violeta/[0.05] p-4">
      <p className="flex items-center gap-1.5 text-[0.84rem] font-semibold text-violeta">
        <AngelaMark size={14} /> {t("angelaprop.titulo")}
      </p>
      <p className="mt-1 font-display text-[1rem] font-bold leading-tight">{proposal.title}</p>
      {proposal.detail && (
        <p className="mt-1 text-[0.88rem] leading-snug text-tinta">{proposal.detail}</p>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button onClick={onApprove} disabled={working}
          className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.84rem] font-semibold text-crema disabled:opacity-50">
          <Check size={15} /> {working ? t("angelaprop.trabajando") : t("angelaprop.aprobar")}
        </button>
        <button onClick={() => { setPostponed(true); onDismiss?.(); }} disabled={working}
          className="rounded-full border border-linea px-4 py-2 text-[0.84rem] font-semibold text-tinta-suave hover:text-tinta disabled:opacity-50">
          {t("angelaprop.despues")}
        </button>
      </div>
      <p className="mt-2 text-[0.72rem] leading-snug text-tinta-suave">{t("angelaprop.nota")}</p>
    </div>
  );
}
