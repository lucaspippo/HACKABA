import ChatPanel from "./ChatPanel";

export default function ChatFullscreen({ onNavigate, placeholderChips, user, onDatosCambiaron, onCollapse }) {
  return (
    <div className="mx-auto h-full">
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
