// Shared chat runtime provider: ONE runtime (with a query history, persisted
// in localStorage) mounted once above the app, so the side panel and the
// fullscreen page show the SAME conversation instead of two independent
// threads — same idea as polfin's lib/assistant/runtime-provider.tsx, adapted
// to a backend without the AI SDK.
import { createContext, useCallback, useContext, useMemo, useState } from "react";
import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  useRemoteThreadListRuntime,
} from "@assistant-ui/react";
import { createLocalStorageAdapter, createSimpleTitleAdapter } from "@assistant-ui/core/react";
import { createChatModelAdapter } from "./chat/adapter";

const browserStorage = {
  async getItem(key) {
    try { return window.localStorage.getItem(key); } catch { return null; }
  },
  async setItem(key, value) {
    try { window.localStorage.setItem(key, value); } catch { /* storage full/disabled: silently doesn't persist */ }
  },
  async removeItem(key) {
    try { window.localStorage.removeItem(key); } catch { /* same as above */ }
  },
};

const DockContext = createContext(null);

// Outside the provider (e.g. mobile, which doesn't mount it): a "closed"
// panel and no-ops, so any component can call the hook without breaking.
export function useChatDock() {
  const value = useContext(DockContext);
  if (!value) {
    return { open: false, setOpen: () => {}, toggle: () => {}, fullscreen: false, setFullscreen: () => {} };
  }
  return value;
}

export function ChatRuntimeProvider({ children, storagePrefix = "polpilot.angela" }) {
  const threadListAdapter = useMemo(
    () => createLocalStorageAdapter({
      storage: browserStorage,
      prefix: storagePrefix,
      titleGenerator: createSimpleTitleAdapter(),
    }),
    [storagePrefix]
  );
  const modelAdapter = useMemo(() => createChatModelAdapter(), []);

  const runtime = useRemoteThreadListRuntime({
    runtimeHook: () => useLocalRuntime(modelAdapter),
    adapter: threadListAdapter,
  });

  // Cerrado por defecto: Ángela es un panel a pedido, no un tercio de
  // pantalla reservado de entrada — el usuario la abre desde el header
  // cuando la necesita.
  const [open, setOpen] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const toggle = useCallback(() => setOpen((v) => !v), []);
  const dock = useMemo(
    () => ({ open, setOpen, toggle, fullscreen, setFullscreen }),
    [open, toggle, fullscreen]
  );

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <DockContext.Provider value={dock}>{children}</DockContext.Provider>
    </AssistantRuntimeProvider>
  );
}
