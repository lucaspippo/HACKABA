import { ChatRuntimeProvider } from "../lib/chatRuntimeProvider";
import ChatPanel from "./ChatPanel";
import { useT } from "../lib/i18n";

// Chips: lk is what's SHOWN (translated); "enviar" is the payload sent to
// the backend and stays in ES (Angela's engine understands Spanish). Chips
// arriving via props as plain strings are shown and sent as-is.
const CHIPS = [
  { lk: "angela.chip_manteca", enviar: "¿Cuánta plata tengo en manteca?" },
  { lk: "angela.chip_fantasma", enviar: "¿Cuáles son mis productos fantasma?" },
  { lk: "angela.chip_anota", enviar: "Anotá que Vanesa revise los precios de balanza" },
  { lk: "angela.chip_riesgo", enviar: "¿Dónde está el mayor riesgo de mi inventario?" },
];

// Angela's chat, used fullscreen on mobile. Mounts its own runtime provider
// (mobile doesn't share a docked panel with a fullscreen page like desktop
// does — see desktop/DesktopApp.jsx, which mounts ChatRuntimeProvider once
// for both ChatPanel and ChatFullscreen).
// onNavigate: if passed (desktop), Angela can take the user to a section.
export default function AngelaView({
  saludoInicial,
  onNavigate,
  placeholderChips = CHIPS,
  inputInicial,
  user,
  onDatosCambiaron,
}) {
  const t = useT();
  return (
    <ChatRuntimeProvider storagePrefix="polpilot.angela.mobile">
      <ChatPanel
        onNavigate={onNavigate}
        placeholderChips={placeholderChips}
        inputInicial={inputInicial}
        user={user}
        onDatosCambiaron={onDatosCambiaron}
        saludoInicial={saludoInicial || t("angela.saludo_default")}
      />
    </ChatRuntimeProvider>
  );
}
