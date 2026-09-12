import { useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { useAui } from "@assistant-ui/react";
import { History, Search } from "lucide-react";
import IconButton from "./IconButton";
import { groupByDay, useVisibleThreads } from "./threads";
import { useT } from "../../lib/i18n";

export default function HistoryDropdown() {
  const aui = useAui();
  const t = useT();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const threads = useVisibleThreads(t("chat.history.untitled"));

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return threads;
    return threads.filter((thread) => thread.title.toLowerCase().includes(q));
  }, [threads, query]);

  const groups = useMemo(
    () =>
      groupByDay(filtered, {
        today: t("chat.history.today"),
        yesterday: t("chat.history.yesterday"),
        older: t("chat.history.older"),
      }),
    [filtered, t],
  );

  const openMenu = () => {
    setOpen((v) => !v);
    queueMicrotask(() => inputRef.current?.focus());
  };

  // Escape closes the dropdown before it can reach the dock, which closes on
  // Escape too; the innermost overlay wins.
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Escape" || !open) return;
    event.stopPropagation();
    setOpen(false);
    triggerRef.current?.focus();
  };

  return (
    <div className="relative" onKeyDown={onKeyDown}>
      <IconButton label={t("chat.control.history")} onClick={openMenu} buttonRef={triggerRef}>
        <History size={16} />
      </IconButton>
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
                placeholder={t("chat.history.search")}
                className="w-full bg-transparent text-[0.82rem] text-tinta outline-none placeholder:text-tinta-suave"
              />
            </div>
            <div className="max-h-80 overflow-y-auto">
              {groups.length === 0 && (
                <p className="px-3 py-4 text-center text-[0.78rem] text-tinta-suave">
                  {t("chat.history.empty")}
                </p>
              )}
              {groups.map((group) => (
                <div key={group.label} className="mb-2 last:mb-0">
                  <div className="px-2 pb-1 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-tinta-suave/80">
                    {group.label}
                  </div>
                  <div className="flex flex-col gap-0.5">
                    {group.items.map((thread) => (
                      <button
                        key={thread.remoteId}
                        type="button"
                        onClick={() => {
                          setOpen(false);
                          aui.threads.switchToThread(thread.remoteId);
                        }}
                        className="w-full truncate rounded-xl px-3 py-1.5 text-left text-[0.82rem] text-tinta hover:bg-papel"
                      >
                        {thread.title}
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
