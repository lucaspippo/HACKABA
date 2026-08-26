import { useEffect, useRef, useState } from "react";
import { AssistantRuntimeProvider, useAui, useAuiState, useLocalRuntime } from "@assistant-ui/react";
import { Camera, Mic, FileText, ChevronRight, Paperclip } from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import FacturaFlow from "../components/FacturaFlow";
import VozAngela from "../components/VozAngela";
import AngelaThread from "../components/assistant/AngelaThread";
import { textoFeed } from "../components/ActividadFeed";
import { fecha } from "../lib/format";
import { api } from "../lib/api";
import { angelaBus } from "../lib/angelaBus";
import { authStore } from "../lib/auth";
import { rolDe } from "../lib/roles";
import { equipoStore } from "../lib/equipoStore";
import { vistaStore } from "../lib/vistaStore";
import { useT } from "../lib/i18n";
import { crearAngelaModelAdapter } from "../lib/angelaRuntime";

// Chips: lk es lo que se MUESTRA (traducido); "enviar" es el payload que va al
// backend y queda en ES (el motor de Ángela entiende castellano). Los chips que
// llegan por props como strings simples se muestran y envían tal cual.
const CHIPS = [
  { lk: "angela.chip_manteca", enviar: "¿Cuánta plata tengo en manteca?" },
  { lk: "angela.chip_fantasma", enviar: "¿Cuáles son mis productos fantasma?" },
  { lk: "angela.chip_anota", enviar: "Anotá que Vanesa revise los precios de balanza" },
  { lk: "angela.chip_riesgo", enviar: "¿Dónde está el mayor riesgo de mi inventario?" },
];

// Chat de Ángela, compartido entre mobile (pantalla completa) y desktop (panel).
// Motor: assistant-ui (ver lib/angelaRuntime.js + components/assistant/*) hablando
// NDJSON con /api/angela/stream — el look de la superficie no cambió a propósito.
// onNavigate: si se pasa (desktop), Ángela puede llevar al usuario a una sección.
export default function AngelaView({
  saludoInicial,
  onNavigate,
  placeholderChips = CHIPS,
  inputInicial,
  user,
  onDatosCambiaron,
}) {
  const t = useT();
  const [adapter] = useState(() => crearAngelaModelAdapter({ vista: () => null }));
  const runtime = useLocalRuntime(adapter, {
    initialMessages: [
      {
        id: "saludo",
        role: "assistant",
        content: [{ type: "text", text: saludoInicial || t("angela.saludo_default") }],
        status: { type: "complete" },
        createdAt: new Date(),
      },
    ],
  });

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <AngelaChatBody
        onNavigate={onNavigate}
        placeholderChips={placeholderChips}
        inputInicial={inputInicial}
        user={user}
        onDatosCambiaron={onDatosCambiaron}
      />
    </AssistantRuntimeProvider>
  );
}

function AngelaChatBody({ onNavigate, placeholderChips, inputInicial, user, onDatosCambiaron }) {
  const t = useT();
  const aui = useAui();
  const mensajes = useAuiState((s) => s.thread.messages);
  const pensando = useAuiState((s) => s.thread.isRunning);
  const [vozAbierta, setVozAbierta] = useState(false);
  const [ejecutando, setEjecutando] = useState(false);
  const [fotoAbierta, setFotoAbierta] = useState(false);
  const [feed, setFeed] = useState([]);
  const ultimaConsulta = useRef(null);
  const aplicadosRef = useRef(new Set());

  // "Lo último que hice": la auditoría real del tenant, para que el panel
  // recién abierto muestre trabajo hecho, no una hoja en blanco.
  useEffect(() => {
    api.actividad().then((a) => setFeed((a.feed || []).slice(0, 3))).catch(() => {});
  }, []);

  // B1: los mensajes PROACTIVOS de Ángela (p. ej. el análisis al confirmarse una
  // carga por foto) entran al transcript como mensajes de ella, sin pregunta del
  // usuario. Si el panel estaba cerrado, quedaron en cola y se drenan al montar;
  // como quedan en el thread, viajan en el historial de la próxima consulta.
  useEffect(() => {
    const alTranscript = (p) =>
      aui.thread.append({ role: "assistant", content: [{ type: "text", text: p.content }] });
    angelaBus.drain().forEach(alTranscript);
    return angelaBus.subscribe(alTranscript);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cuando se entra con una consulta (buscador global, "que lo gestione Ángela",
  // banner de fase), Ángela la responde sola: pregunta → estás ahí.
  useEffect(() => {
    if (inputInicial && inputInicial !== ultimaConsulta.current) {
      ultimaConsulta.current = inputInicial;
      aui.thread.append(inputInicial);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputInicial]);

  const aplicarAcciones = (acciones = []) => {
    if (!acciones.length) return;
    equipoStore.aplicarAcciones(acciones); // recordatorios / objetivos
    for (const a of acciones) {
      if (a.type === "modify_view" && a.cambios) vistaStore.aplicar(a.cambios);
      if (a.type === "create_widget" && a.widget) vistaStore.agregarWidget(a.section, a.widget);
      if (a.type === "crear_pestana" && a.pestana) vistaStore.agregarPestana(a.pestana);
      // P19·A — Ángela recordó una preferencia: la vista se adapta EN EL
      // MOMENTO (el server ya la persistió; esto es el espejo local).
      if (a.type === "preferencia" && a.vista) vistaStore.hidratarServer({ vista: a.vista });
      // P19·B — el Home se reordena en el momento (server ya persistido).
      if (a.type === "orden_home") vistaStore.aplicar({ ordenHome: a.orden });
      // P24·B — el documento se ENTREGA en el chat (card de descarga, ver
      // components/assistant/DocCard); ya no se navega a un preview.
    }
    if (acciones.some((a) => a.type === "saneado")) onDatosCambiaron?.();
    // Si hay varios navigate en la misma respuesta (p.ej. el auto-navigate de
    // una tool + un navegar_a puntual), gana el ÚLTIMO: es la intención más
    // específica de Ángela (ej. "cliente-<id>" pisa al grupo "morosos").
    const nav = [...acciones].reverse().find((a) => a.type === "navigate");
    if (nav && onNavigate) onNavigate(nav.section, nav.highlight);
  };

  // Cada mensaje de Ángela trae su resultado completo (respuesta/modo/acciones/
  // opciones) en metadata.custom — el mismo shape que /api/angela siempre
  // devolvió (ver lib/angelaRuntime.js). Acá se aplican los efectos UNA vez
  // por mensaje, apenas termina de correr.
  useEffect(() => {
    for (const m of mensajes) {
      if (m.role !== "assistant" || m.status?.type !== "complete") continue;
      if (aplicadosRef.current.has(m.id)) continue;
      aplicadosRef.current.add(m.id);
      const custom = m.metadata?.custom;
      if (!custom) continue;
      aplicarAcciones(custom.acciones || []);
      if ((custom.acciones || []).some((a) => a.type === "plan_progreso")) onDatosCambiaron?.();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mensajes]);

  const modoActual = [...mensajes].reverse().find((m) => m.metadata?.custom?.modo)?.metadata?.custom?.modo;

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-3 pb-3 pt-1">
        <AngelaMark size={40} pulse={pensando} estado={ejecutando ? "ejecutando" : undefined} />
        <div>
          <h1 className="font-display text-xl font-bold leading-none">Ángela</h1>
          <p className="mt-0.5 flex items-center gap-1.5 text-[0.78rem] text-tinta-suave">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-salvia" />
            {modoActual === "simulado" ? t("angela.modo_datos") : t("angela.socia")}
          </p>
        </div>
      </header>

      <AngelaThread
        onEjecutando={setEjecutando}
        composerLeading={
          <>
            {authStore.tiene("cargar") && (
              <button
                onClick={() => setFotoAbierta(true)}
                title={t("foto.titulo")}
                className="grid h-11 w-11 shrink-0 place-items-center rounded-full text-tinta-suave transition-colors hover:text-violeta"
              >
                <Camera size={20} />
              </button>
            )}
            {/* P44·A2 — el micrófono es de todos: hablarle a Ángela en vez de
                tipearle no es una capacidad de depósito. */}
            <button
              onClick={() => setVozAbierta(true)}
              title={t("voz.titulo")}
              aria-label={t("voz.titulo")}
              className="grid h-11 w-11 shrink-0 place-items-center rounded-full text-tinta-suave transition-colors hover:text-violeta"
            >
              <Mic size={20} />
            </button>
          </>
        }
      />

      {mensajes.length <= 1 && (
        <div className="pb-3">
          {/* Lo último que Ángela hizo — auditoría real, no decoración */}
          {feed.length > 0 && (
            <div className="mb-3 space-y-1.5">
              <p className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-tinta-suave">{t("angela.ultimo")}</p>
              {feed.map((e, i) => (
                <div key={i} className="flex items-start gap-2.5 rounded-xl border border-linea bg-crema px-3 py-2 sombra-papel">
                  <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${e.tipo === "staging" ? "bg-salvia" : "bg-oro"}`} />
                  <span className="min-w-0 flex-1 text-[0.8rem] leading-snug text-tinta">{textoFeed(e, t)}</span>
                  <span className="shrink-0 text-[0.7rem] text-tinta-suave">{fecha(e.cuando)}</span>
                </div>
              ))}
            </div>
          )}
          {/* Acciones reales del agente (nada de features inventadas) */}
          <div className="mb-3 space-y-1.5">
            {authStore.tiene("cargar") && (
              <button
                onClick={() => setFotoAbierta(true)}
                className="flex w-full items-center gap-3 rounded-xl border border-linea bg-crema px-3 py-2.5 text-left sombra-papel transition-colors hover:border-violeta/40"
              >
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-violeta-suave text-violeta"><Paperclip size={16} /></span>
                <span className="min-w-0 flex-1">
                  <span className="block text-[0.85rem] font-semibold leading-tight">{t("angela.accion_foto")}</span>
                  <span className="block text-[0.74rem] text-tinta-suave">{t("angela.accion_foto_sub")}</span>
                </span>
                <ChevronRight size={15} className="text-tinta-suave" />
              </button>
            )}
            {onNavigate && authStore.tiene("documentos") && (
              <button
                onClick={() => onNavigate("documentos")}
                className="flex w-full items-center gap-3 rounded-xl border border-linea bg-crema px-3 py-2.5 text-left sombra-papel transition-colors hover:border-violeta/40"
              >
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-violeta-suave text-violeta"><FileText size={16} /></span>
                <span className="min-w-0 flex-1">
                  <span className="block text-[0.85rem] font-semibold leading-tight">{t("angela.accion_doc")}</span>
                  <span className="block text-[0.74rem] text-tinta-suave">{t("angela.accion_doc_sub")}</span>
                </span>
                <ChevronRight size={15} className="text-tinta-suave" />
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {placeholderChips.map((c) => (
              <button
                key={typeof c === "string" ? c : c.lk}
                onClick={() => aui.thread.append(typeof c === "string" ? c : c.enviar)}
                className="rounded-full border border-linea bg-crema px-3 py-1.5 text-left text-[0.82rem] font-medium text-tinta-suave transition-colors hover:border-violeta/40 hover:text-tinta"
              >
                {typeof c === "string" ? c : t(c.lk)}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* P10: la camarita — foto del comprobante desde el chat (la promesa
          "snap a photo and tell her to load it"). Solo roles con `cargar`. */}
      {fotoAbierta && (
        <FacturaFlow
          onCerrar={() => setFotoAbierta(false)}
          onCargado={() => onDatosCambiaron?.()}
          onPreguntar={(texto) => { setFotoAbierta(false); aui.thread.append(texto); }}
        />
      )}

      {/* P43·C1 — la voz, EN el chat. */}
      {vozAbierta && (
        <VozAngela
          rol={rolDe(user)?.id}
          onCerrar={() => setVozAbierta(false)}
          onListo={() => onDatosCambiaron?.()}
          onPreguntar={(texto) => { setVozAbierta(false); aui.thread.append(texto); }}
        />
      )}

    </div>
  );
}
