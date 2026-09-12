import { useAuiState } from "@assistant-ui/react";
import { AlertCircle } from "lucide-react";
import { useT } from "../../../lib/i18n";
import type { Notice } from "../../../lib/chat/protocol";

/**
 * A degraded-mode explanation (message cap, no model, tool loop exhausted).
 * Visually distinct on purpose: the v1 bug was a reply produced WITHOUT the
 * model being indistinguishable from a real one (design doc D5/D9).
 */
export default function MessageNotices() {
  const t = useT();
  const notices = (useAuiState((s) => s.message.metadata?.custom?.notices) ?? []) as Notice[];
  if (notices.length === 0) return null;
  return (
    <div className="mt-2 space-y-1.5">
      {notices.map((n, i) => {
        // The wire carries only `kind`; the copy is ours. An unrecognised
        // kind falls back to a generic line rather than rendering blank.
        const key = `chat.notice.${n.kind}`;
        const text = t(key);
        return (
          <p
            key={i}
            className="flex items-start gap-2 rounded-xl border border-oro/40 bg-oro/5 px-2.5 py-1.5 text-xs leading-snug text-oro-tinta"
          >
            <AlertCircle size={14} className="mt-0.5 shrink-0" />
            <span>{text === key ? t("chat.notice.generico") : text}</span>
          </p>
        );
      })}
    </div>
  );
}
