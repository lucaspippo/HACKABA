import ChatPanel from "./ChatPanel";

// The fullscreen chat page (desktop) — mirrors polfin's angela-fullscreen.tsx.
// Assumes it's mounted inside the SAME ChatRuntimeProvider as the docked
// panel (see desktop/DesktopApp.jsx), so expanding/collapsing never loses the
// conversation.
export default function ChatFullscreen({ onNavigate, placeholderChips, user, onDatosCambiaron, onCollapse }) {
  return (
    <div className="mx-auto h-full max-w-5xl">
      <ChatPanel
        variant="fullscreen"
        onNavigate={onNavigate}
        placeholderChips={placeholderChips}
        user={user}
        onDatosCambiaron={onDatosCambiaron}
        onCollapse={onCollapse}
      />
    </div>
  );
}
