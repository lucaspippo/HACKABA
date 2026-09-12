import { ChatRuntimeProvider } from "../lib/chatRuntimeProvider";
import ChatPanel from "./ChatPanel";

// Angela's chat, used fullscreen on mobile. Mounts its own runtime provider
// (mobile doesn't share a docked panel with a fullscreen page like desktop
// does — see desktop/DesktopApp.jsx, which mounts ChatRuntimeProvider once
// for both ChatPanel and ChatFullscreen).
// onNavigate: if passed (desktop), Angela can take the user to a section.
export default function AngelaView({
  onNavigate,
  inputInicial,
  user,
  onDatosCambiaron,
}) {
  return (
    <ChatRuntimeProvider storagePrefix="polpilot.angela.mobile">
      <ChatPanel
        onNavigate={onNavigate}
        inputInicial={inputInicial}
        user={user}
        onDatosCambiaron={onDatosCambiaron}
      />
    </ChatRuntimeProvider>
  );
}
