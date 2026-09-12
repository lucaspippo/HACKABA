import {
  ThreadPrimitive,
  MessagePrimitive,
  ComposerPrimitive,
  useAui,
  useAuiState,
} from "@assistant-ui/react";
import { Send } from "lucide-react";
import AngelaMark from "../AngelaMark";
import ToolCallCard from "./ToolCallCard";
import PlanChecklist from "./PlanChecklist";
import DocCard from "./DocCard";
import { useT } from "../../lib/i18n";

function UserMessage() {
  return (
    <MessagePrimitive.Root className="flex justify-end">
      <div className="max-w-[85%] whitespace-pre-line rounded-2xl rounded-tr-md bg-tinta px-3.5 py-2.5 text-[0.95rem] leading-snug text-crema">
        <MessagePrimitive.Parts />
      </div>
    </MessagePrimitive.Root>
  );
}

// Los "extras" de un mensaje de Ángela (checklist de plan, card de documento)
// NO son content parts — viajan en metadata.custom.acciones (el mismo shape
// que /api/angela siempre devolvió). Se leen acá, con el mensaje ya en scope
// por MessagePrimitive.Root.
function ExtrasDelMensaje({ onEjecutando }) {
  const t = useT();
  const aui = useAui();
  const acciones = useAuiState((s) => s.message.metadata?.custom?.acciones) || [];
  const opciones = useAuiState((s) => s.message.metadata?.custom?.opciones) || [];
  const corriendo = useAuiState((s) => s.thread.isRunning);
  const plan = acciones.find((a) => a.type === "plan_progreso");
  const docAccion = acciones.find((a) => a.type === "documento");
  return (
    <>
      {plan && <PlanChecklist plan={{ pasos: plan.pasos, resumen: plan.resumen }} onEjecutando={onEjecutando} />}
      {docAccion?.documento && <DocCard documento={docAccion.documento} t={t} />}
      {opciones.length > 0 && (
        <div className="mt-2 flex flex-col gap-1.5">
          {opciones.map((op, k) => (
            <button
              key={k}
              onClick={() => aui.thread.append(op.enviar)}
              disabled={corriendo}
              className="rounded-xl border border-violeta/30 bg-crema px-3 py-2 text-left text-[0.86rem] font-semibold text-violeta transition-colors hover:bg-violeta hover:text-crema disabled:opacity-50"
            >
              {op.label}
            </button>
          ))}
        </div>
      )}
    </>
  );
}

// Puntitos de "pensando": sólo mientras el mensaje está corriendo y todavía
// no llegó ni un token ni un tool-call (apenas se manda la pregunta).
function Puntitos() {
  return (
    <span className="flex gap-1 px-0.5 py-1">
      {[0, 1, 2].map((d) => (
        <span
          key={d}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-tinta-suave"
          style={{ animationDelay: `${d * 0.15}s` }}
        />
      ))}
    </span>
  );
}

function AssistantMessage({ onEjecutando }) {
  const sinNadaAun = useAuiState(
    (s) => s.message.status?.type === "running" && (s.message.content?.length ?? 0) === 0
  );
  return (
    <MessagePrimitive.Root className="flex gap-2.5">
      <AngelaMark size={28} />
      <div className="max-w-[88%]">
        <div className="whitespace-pre-line rounded-2xl rounded-tl-md border border-linea bg-crema px-3.5 py-2.5 text-[0.95rem] leading-snug text-tinta sombra-papel">
          {sinNadaAun ? (
            <Puntitos />
          ) : (
            <MessagePrimitive.Parts>
              {({ part }) => {
                if (part.type === "text") return <span>{part.text}</span>;
                if (part.type === "tool-call") return part.toolUI ?? <ToolCallCard part={part} />;
                return null;
              }}
            </MessagePrimitive.Parts>
          )}
          <ExtrasDelMensaje onEjecutando={onEjecutando} />
        </div>
      </div>
    </MessagePrimitive.Root>
  );
}

function Composer({ leading }) {
  const t = useT();
  const isRunning = useAuiState((s) => s.thread.isRunning);
  return (
    <ComposerPrimitive.Root className="flex items-center gap-2 rounded-full border border-linea bg-crema p-1.5 pl-2 sombra-papel">
      {leading}
      <ComposerPrimitive.Input
        placeholder={isRunning ? t("angela.ph_trabajando") : t("angela.ph_input")}
        rows={1}
        className="flex-1 resize-none bg-transparent text-[0.95rem] outline-none placeholder:text-tinta-suave/70 disabled:opacity-60"
      />
      <ComposerPrimitive.Send asChild>
        <button
          disabled={isRunning}
          className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-violeta text-crema transition-transform active:scale-90 disabled:opacity-40"
        >
          <Send size={18} />
        </button>
      </ComposerPrimitive.Send>
    </ComposerPrimitive.Root>
  );
}

// El Thread: assistant-ui maneja el streaming/estado; el look calca el chat
// previo (bg-crema, sombra-papel, burbujas redondeadas) para que el cambio de
// motor no se note en la superficie visible.
export default function AngelaThread({ onEjecutando, composerLeading }) {
  return (
    <ThreadPrimitive.Root className="flex h-full flex-col">
      <ThreadPrimitive.Viewport className="flex-1 space-y-3 overflow-y-auto pb-2">
        <ThreadPrimitive.Messages>
          {({ message }) =>
            message.role === "user" ? <UserMessage /> : <AssistantMessage onEjecutando={onEjecutando} />
          }
        </ThreadPrimitive.Messages>
      </ThreadPrimitive.Viewport>
      <Composer leading={composerLeading} />
    </ThreadPrimitive.Root>
  );
}
