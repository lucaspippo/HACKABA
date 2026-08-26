import { useMemo, useRef, useState } from "react";
import { useAui, useAuiState } from "@assistant-ui/react";
import { History, Plus, Search } from "lucide-react";

// Reads the thread list the runtime already maintains (persisted in
// localStorage via chatRuntimeProvider) and groups it by day — same
// pattern as polfin (components/assistant/chat-toolbar.tsx), styled to match
// this app.
function useVisibleThreads() {
  const threadItems = useAuiState((s) => s.threads.threadItems);
  return useMemo(
    () =>
      threadItems
        .filter((t) => t.remoteId && t.status === "regular")
        .map((t) => ({
          remoteId: t.remoteId,
          title: t.title?.trim() || "Sin título",
          lastMessageAt: t.lastMessageAt ?? new Date(),
        }))
        .sort((a, b) => b.lastMessageAt.getTime() - a.lastMessageAt.getTime()),
    [threadItems]
  );
}

function isSameDay(a, b) {
  return a.toDateString() === b.toDateString();
}

function groupByDay(threads) {
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const groups = [
    { label: "Hoy", items: [] },
    { label: "Ayer", items: [] },
    { label: "Anteriores", items: [] },
  ];
  for (const t of threads) {
    if (isSameDay(t.lastMessageAt, today)) groups[0].items.push(t);
    else if (isSameDay(t.lastMessageAt, yesterday)) groups[1].items.push(t);
    else groups[2].items.push(t);
  }
  return groups.filter((g) => g.items.length > 0);
}

export function useActiveThreadTitle(fallback = "Ángela") {
  return useAuiState((s) => s.threadListItem.title)?.trim() || fallback;
}

const BUTTON = "grid size-8 shrink-0 place-items-center rounded-full text-tinta-suave transition-colors hover:bg-crema hover:text-tinta";

export function NewChatButton({ className = "" }) {
  const aui = useAui();
  return (
    <button
      type="button"
      onClick={() => aui.threads.switchToNewThread()}
      title="Nueva consulta"
      aria-label="Nueva consulta"
      className={`${BUTTON} ${className}`}
    >
      <Plus size={16} />
    </button>
  );
}

export function HistoryDropdown() {
  const aui = useAui();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const inputRef = useRef(null);
  const threads = useVisibleThreads();

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return threads;
    return threads.filter((t) => t.title.toLowerCase().includes(q));
  }, [threads, query]);

  const groups = useMemo(() => groupByDay(filtered), [filtered]);

  const openMenu = () => {
    setOpen((v) => !v);
    queueMicrotask(() => inputRef.current?.focus());
  };

  return (
    <div className="relative">
      <button type="button" onClick={openMenu} title="Historial de consultas" aria-label="Historial de consultas" className={BUTTON}>
        <History size={16} />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-10 z-50 w-80 rounded-2xl border border-linea bg-crema p-2 shadow-lg">
            <div className="mb-2 flex items-center gap-2 rounded-xl border border-linea bg-papel px-3 py-2">
              <Search size={14} className="shrink-0 text-tinta-suave" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Buscar consultas…"
                className="w-full bg-transparent text-[0.82rem] text-tinta outline-none placeholder:text-tinta-suave"
              />
            </div>
            <div className="max-h-80 overflow-y-auto">
              {groups.length === 0 && (
                <p className="px-3 py-4 text-center text-[0.78rem] text-tinta-suave">Sin consultas todavía</p>
              )}
              {groups.map((g) => (
                <div key={g.label} className="mb-2 last:mb-0">
                  <div className="px-2 pb-1 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-tinta-suave/80">
                    {g.label}
                  </div>
                  <div className="flex flex-col gap-0.5">
                    {g.items.map((t) => (
                      <button
                        key={t.remoteId}
                        type="button"
                        onClick={() => { setOpen(false); aui.threads.switchToThread(t.remoteId); }}
                        className="w-full truncate rounded-xl px-3 py-1.5 text-left text-[0.82rem] text-tinta hover:bg-papel"
                      >
                        {t.title}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
