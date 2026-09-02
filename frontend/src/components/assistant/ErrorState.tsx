import { AlertTriangle, RotateCw } from "lucide-react";
import { useAui, useAuiState } from "@assistant-ui/react";
import { useT } from "../../lib/i18n";
import { authStore } from "../../lib/auth";
import type { ChatErrorCode } from "../../lib/chat/errors";

const CODES: readonly ChatErrorCode[] = [
  "session_expired", "rate_limit", "network", "server", "stream",
];

/** The failure's code, read off the message's incomplete status. */
function useErrorCode(): ChatErrorCode {
  return useAuiState((s) => {
    const status = s.message.status;
    if (status?.type !== "incomplete" || status.reason !== "error") return "server";
    const err = status.error as { code?: string } | string | undefined;
    const code = typeof err === "object" && err !== null ? err.code : undefined;
    return (CODES as readonly string[]).includes(code ?? "")
      ? (code as ChatErrorCode)
      : "server";
  });
}

/** What the user sees when a run fails. */
export default function ErrorState() {
  const t = useT();
  const aui = useAui();
  const code = useErrorCode();
  const retrying = useAuiState((s) => s.message.status?.type === "running");

  const isSession = code === "session_expired";

  return (
    <div
      role="alert"
      className="mt-2 rounded-2xl border border-rojo/30 bg-rojo/5 px-3.5 py-2.5"
    >
      <p className="flex items-center gap-2 text-[0.86rem] font-semibold text-rojo-hondo">
        <AlertTriangle size={15} className="shrink-0" />
        {t(`chat.error.${code}.titulo`)}
      </p>
      <p className="mt-1 text-[0.8rem] leading-snug text-tinta-suave">
        {t(`chat.error.${code}.detalle`)}
      </p>
      <button
        type="button"
        disabled={retrying}
        onClick={() =>
          isSession ? authStore.logout({ manual: true }) : aui.message.reload()
        }
        className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-rojo/40 px-3 py-1.5 text-[0.8rem] font-semibold text-rojo-hondo transition-colors hover:bg-rojo/10 disabled:opacity-50"
      >
        {!isSession && (
          <RotateCw
            size={13}
            className={retrying ? "animate-spin motion-reduce:animate-none" : undefined}
          />
        )}
        {isSession
          ? t("chat.error.session_expired.accion")
          : retrying
            ? t("chat.error.reintentando")
            : t("chat.error.reintentar")}
      </button>
    </div>
  );
}
