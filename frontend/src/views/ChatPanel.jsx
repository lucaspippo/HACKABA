import { useEffect, useRef, useState } from "react";
import { useAui, useAuiState } from "@assistant-ui/react";
import {
  Camera,
  ChevronRight,
  Maximize2,
  Minimize2,
  Brain,
  X,
} from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import FacturaFlow from "../components/FacturaFlow";
import ChatThread from "../components/assistant/ChatThread";
import IconButton from "../components/assistant/IconButton";
import NewChatButton from "../components/assistant/NewChatButton";
import HistoryDropdown from "../components/assistant/HistoryDropdown";
import KnowledgePanel from "../components/assistant/KnowledgePanel";
import { useActiveThreadTitle } from "../components/assistant/threads";
import { angelaBus } from "../lib/angelaBus";
import { authStore, useSession } from "../lib/auth";
import { equipoStore } from "../lib/equipoStore";
import { vistaStore } from "../lib/vistaStore";
import { suggestionPromptsFor } from "../lib/chat/suggestionPrompts";
import { useT } from "../lib/i18n";
import { useHasCamera } from "../lib/useMediaQuery";

// The chat body — SHARED between the side panel (desktop), the fullscreen
// page (desktop, see ChatFullscreen) and mobile. Assumes it's already mounted
// inside an AssistantRuntimeProvider (see lib/chatRuntimeProvider for desktop,
// or the provider AngelaView sets up on its own for mobile) — that way the
// panel and the fullscreen page share the SAME conversation thread.
//
// variant: "dock" (narrow panel, with a button to expand to fullscreen)
// | "fullscreen" (wide, centered, with a button to collapse back to the panel).
export default function ChatPanel({
  onNavigate,
  inputInicial,
  onDatosCambiaron,
  variant = "dock",
  onExpand,
  onCollapse,
}) {
  const t = useT();
  const aui = useAui();
  const session = useSession();
  const hasCamera = useHasCamera();
  const messages = useAuiState((s) => s.thread.messages);
  const activeThreadTitle = useActiveThreadTitle(undefined);
  const [, setExecuting] = useState(false);
  const [photoOpen, setPhotoOpen] = useState(false);
  const [knowledgeOpen, setKnowledgeOpen] = useState(false);
  const lastInitialQuery = useRef(null);
  const appliedRef = useRef(new Set());
  const prompts = suggestionPromptsFor((feature) =>
    !!session?.usuario?.features?.includes(feature),
  );

  // Angela's PROACTIVE messages (e.g. the analysis when a photo upload gets
  // confirmed) enter the transcript as her own messages, without a user
  // question. If the panel was closed, they queued up and drain on mount;
  // since they land in the thread, they travel in the history of the next
  // query too.
  useEffect(() => {
    const onProactive = (p) =>
      aui.thread.append({
        role: "assistant",
        content: [{ type: "text", text: p.content }],
      });
    angelaBus.drain().forEach(onProactive);
    return angelaBus.subscribe(onProactive);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // When entering with a query already in hand (global search, "let Angela
  // handle it", the phase banner), Angela answers it on her own: the
  // question is already there when the panel opens.
  useEffect(() => {
    if (inputInicial && inputInicial !== lastInitialQuery.current) {
      lastInitialQuery.current = inputInicial;
      aui.thread.append(inputInicial);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputInicial]);

  const applyActions = (actions = []) => {
    if (!actions.length) return;
    equipoStore.aplicarAcciones(actions); // reminders / goals
    for (const a of actions) {
      if (a.type === "modify_view" && a.cambios) vistaStore.aplicar(a.cambios);
      if (a.type === "create_widget" && a.widget)
        vistaStore.agregarWidget(a.section, a.widget);
      if (a.type === "crear_pestana" && a.pestana)
        vistaStore.agregarPestana(a.pestana);
      // A remembered preference: the view adapts IMMEDIATELY (the server
      // already persisted it; this is the local mirror).
      if (a.type === "preferencia" && a.vista)
        vistaStore.hidratarServer({ vista: a.vista });
      // The Home reorders immediately too (server already persisted it).
      if (a.type === "orden_home") vistaStore.aplicar({ ordenHome: a.orden });
      // The document is DELIVERED in the chat (download card, see
      // components/assistant/DocCard); no more navigating to a preview.
    }
    if (actions.some((a) => a.type === "saneado")) onDatosCambiaron?.();
    // If several navigate actions land in the same reply (e.g. a tool's
    // auto-navigate plus a specific navegar_a), the LAST one wins: it's
    // Angela's most specific intent (e.g. "cliente-<id>" overrides the
    // "morosos" group).
    const nav = [...actions].reverse().find((a) => a.type === "navigate");
    if (nav && onNavigate) onNavigate(nav.section, nav.highlight);
  };

  // Every assistant message carries its full result (answer/mode/actions/
  // options) in metadata.custom — the same shape /api/angela has always
  // returned (see lib/chat/adapter.ts). Side effects apply here ONCE per
  // message, as soon as it finishes running.
  useEffect(() => {
    for (const m of messages) {
      if (m.role !== "assistant" || m.status?.type !== "complete") continue;
      if (appliedRef.current.has(m.id)) continue;
      appliedRef.current.add(m.id);
      const custom = m.metadata?.custom;
      if (!custom) continue;
      applyActions(custom.actions || []);
      if ((custom.actions || []).some((a) => a.type === "plan_progreso"))
        onDatosCambiaron?.();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages]);

  const width = variant === "fullscreen" ? "mx-auto w-full max-w-3xl" : "";

  const emptyState = (
    <>
      <div className="flex flex-1 flex-col items-center justify-center px-2 text-center">
        <AngelaMark size={variant === "fullscreen" ? 44 : 48} />
        <h2 className="mt-3 font-display text-lg font-bold tracking-tight text-tinta">
          {t("angela.hola")}
        </h2>
      </div>
      <div className="flex w-full flex-col gap-1">
        {prompts.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => aui.thread.append(p.prompt)}
            className="group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium leading-snug text-tinta transition-colors hover:bg-crema"
          >
            <span className="min-w-0 flex-1">{t(p.labelKey)}</span>
            <ChevronRight
              size={15}
              className="shrink-0 text-tinta-suave/40 transition-colors group-hover:text-tinta"
            />
          </button>
        ))}
      </div>
    </>
  );

  return (
    // The dock sits flush against the aside's border, so it pads itself;
    // fullscreen is already inset by its own centred column.
    <div className={`relative flex h-full flex-col ${variant === "dock" ? "px-3 pb-3 pt-4" : "pt-1"}`}>
      {knowledgeOpen && <KnowledgePanel onClose={() => setKnowledgeOpen(false)} />}
      <header className="flex items-center gap-3 pb-4">
        <div className="min-w-0 flex-1">
          <h1 className="truncate font-display text-xl font-bold leading-none">
            {activeThreadTitle}
          </h1>
        </div>
        <IconButton
          label={t("chat.knowledge.open")}
          onClick={() => setKnowledgeOpen(true)}
        >
          <Brain size={16} />
        </IconButton>
        <NewChatButton />
        <HistoryDropdown />
        {variant === "dock" && onExpand && (
          <IconButton label={t("chat.control.expand")} onClick={onExpand}>
            <Maximize2 size={16} />
          </IconButton>
        )}
        {variant === "dock" && onCollapse && (
          <IconButton label={t("chat.control.close")} onClick={onCollapse}>
            <X size={16} />
          </IconButton>
        )}
        {variant === "fullscreen" && onCollapse && (
          <IconButton label={t("chat.control.collapse")} onClick={onCollapse}>
            <Minimize2 size={16} />
          </IconButton>
        )}
      </header>

      <div className={`min-h-0 flex-1 ${width}`}>
        <ChatThread
          onExecutingChange={setExecuting}
          emptyState={emptyState}
          onAttach={authStore.tiene("cargar") ? () => setPhotoOpen(true) : undefined}
          composerLeading={
            hasCamera && authStore.tiene("cargar") && (
              // Only where there is a camera to take the photo with. The
              // composer's mic is dictation now; this stays the document
              // path: FacturaFlow reads the photo and stages it for an OK.
              <IconButton
                label={t("chat.control.photo")}
                onClick={() => setPhotoOpen(true)}
                shape="composer"
                placement="top"
              >
                <Camera size={18} />
              </IconButton>
            )
          }
        />
      </div>

      {/* Receipt photo from the chat (the promise: "snap a photo and tell
          her to load it"). Only roles with `cargar`. */}
      {photoOpen && (
        <FacturaFlow
          onCerrar={() => setPhotoOpen(false)}
          onCargado={() => onDatosCambiaron?.()}
          onPreguntar={(texto) => {
            setPhotoOpen(false);
            aui.thread.append(texto);
          }}
        />
      )}
    </div>
  );
}
