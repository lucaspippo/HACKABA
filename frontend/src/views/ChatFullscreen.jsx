import ChatPanel from "./ChatPanel";

export default function ChatFullscreen({ onNavigate, user, onDatosCambiaron, onCollapse }) {
  return (
    <div className="mx-auto h-full">
      <ChatPanel
        variant="fullscreen"
        onNavigate={onNavigate}
        user={user}
        onDatosCambiaron={onDatosCambiaron}
        onCollapse={onCollapse}
      />
    </div>
  );
}
