import { useEffect, useRef, useState } from "react";
import { useAui, useAuiState } from "@assistant-ui/react";
import {
  Camera,
  FileText,
  ChevronRight,
  Paperclip,
  Maximize2,
  Minimize2,
  X,
} from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import FacturaFlow from "../components/FacturaFlow";
import ChatThread from "../components/assistant/ChatThread";
import IconButton from "../components/assistant/IconButton";
import NewChatButton from "../components/assistant/NewChatButton";
import HistoryDropdown from "../components/assistant/HistoryDropdown";
import { useActiveThreadTitle } from "../components/assistant/threads";
import { textoFeed } from "../components/ActividadFeed";
import { fecha } from "../lib/format";
import { api } from "../lib/api";
import { angelaBus } from "../lib/angelaBus";
import { authStore } from "../lib/auth";
import { equipoStore } from "../lib/equipoStore";
import { vistaStore } from "../lib/vistaStore";
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
  placeholderChips = [],
  inputInicial,
  user,
  onDatosCambiaron,
  variant = "dock",
  onExpand,
  onCollapse,
  saludoInicial,
}) {
  const t = useT();
  const aui = useAui();
  const hasCamera = useHasCamera();
  const messages = useAuiState((s) => s.thread.messages);
  const isRunning = useAuiState((s) => s.thread.isRunning);
  const activeThreadTitle = useActiveThreadTitle(
    variant === "fullscreen" ? "Ángela" : undefined,
  );
  const [executing, setExecuting] = useState(false);
  const [photoOpen, setPhotoOpen] = useState(false);
  const [feed, setFeed] = useState([]);
  const lastInitialQuery = useRef(null);
  const appliedRef = useRef(new Set());

  // "What Angela already did": the tenant's real audit log, so a freshly
  // opened panel shows finished work, not a blank page.
  useEffect(() => {
    api
      .actividad()
      .then((a) => setFeed((a.feed || []).slice(0, 3)))
      .catch(() => {});
  }, []);

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
      <AngelaMark size={variant === "fullscreen" ? 40 : 48} />
      <h2 className="mt-3 font-display text-[1.05rem] font-bold tracking-tight text-tinta">
        {t("angela.hola")}
      </h2>
      <p className="mt-1.5 max-w-[280px] text-[0.85rem] leading-relaxed text-tinta-suave">
        {saludoInicial || t("angela.saludo_default")}
      </p>
      <div className="mt-5 w-full max-w-sm text-left">
        {/* What Angela already did — real audit log, not decoration */}
        {feed.length > 0 && (
          <div className="mb-3 space-y-1.5">
            <p className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-tinta-suave">
              {t("angela.ultimo")}
            </p>
            {feed.map((e, i) => (
              <div
                key={i}
                className="flex items-start gap-2.5 rounded-xl border border-linea bg-crema px-3 py-2 sombra-papel"
              >
                <span
                  className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${e.tipo === "staging" ? "bg-salvia" : "bg-oro"}`}
                />
                <span className="min-w-0 flex-1 text-[0.8rem] leading-snug text-tinta">
                  {textoFeed(e, t)}
                </span>
                <span className="shrink-0 text-[0.7rem] text-tinta-suave">
                  {fecha(e.cuando)}
                </span>
              </div>
            ))}
          </div>
        )}
        {/* Real agent actions (no made-up features) */}
        <div className="mb-3 space-y-1.5">
          {authStore.tiene("cargar") && (
            <button
              onClick={() => setPhotoOpen(true)}
              className="flex w-full items-center gap-3 rounded-xl border border-linea bg-crema px-3 py-2.5 text-left sombra-papel transition-colors hover:border-violeta/40"
            >
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-violeta-suave text-violeta">
                <Paperclip size={16} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-[0.85rem] font-semibold leading-tight">
                  {t("angela.accion_foto")}
                </span>
                <span className="block text-[0.74rem] text-tinta-suave">
                  {t("angela.accion_foto_sub")}
                </span>
              </span>
              <ChevronRight size={15} className="text-tinta-suave" />
            </button>
          )}
          {onNavigate && authStore.tiene("documentos") && (
            <button
              onClick={() => onNavigate("documentos")}
              className="flex w-full items-center gap-3 rounded-xl border border-linea bg-crema px-3 py-2.5 text-left sombra-papel transition-colors hover:border-violeta/40"
            >
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-violeta-suave text-violeta">
                <FileText size={16} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-[0.85rem] font-semibold leading-tight">
                  {t("angela.accion_doc")}
                </span>
                <span className="block text-[0.74rem] text-tinta-suave">
                  {t("angela.accion_doc_sub")}
                </span>
              </span>
              <ChevronRight size={15} className="text-tinta-suave" />
            </button>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {placeholderChips.map((c) => (
            <button
              key={typeof c === "string" ? c : c.lk}
              onClick={() =>
                aui.thread.append(typeof c === "string" ? c : c.enviar)
              }
              className="rounded-full border border-linea bg-crema px-3 py-1.5 text-left text-[0.82rem] font-medium text-tinta-suave transition-colors hover:border-violeta/40 hover:text-tinta"
            >
              {typeof c === "string" ? c : t(c.lk)}
            </button>
          ))}
        </div>
      </div>
    </>
  );

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-3 pb-3 pt-1">
        <div className="min-w-0 flex-1">
          <h1 className="truncate font-display text-xl font-bold leading-none">
            {activeThreadTitle}
          </h1>
        </div>
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
