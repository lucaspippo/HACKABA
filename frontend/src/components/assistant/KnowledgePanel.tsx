import { useEffect, useMemo, useRef, useState } from "react";
import { Brain, Check, Pause, Play, Search, Trash2, X } from "lucide-react";
import { SettingsPanel } from "./settings-panel";
import { api } from "../../lib/api";
import { toast } from "../../lib/toastStore";
import { useT } from "../../lib/i18n";
import { useSession } from "../../lib/auth";

type Piece = {
  id: string;
  texto: string;
  texto_en?: string | null;
  nodo: string;
  entidad?: string | null;
  estado: string;
  tipo: string;
  quien?: string | null;
  cuando?: string | null;
};

const SETTING_KEYS = ["knowledge_capture", "knowledge_in_context"] as const;
type SettingKey = (typeof SETTING_KEYS)[number];

function matches(piece: Piece, query: string): boolean {
  if (!query) return true;
  const q = query.toLowerCase();
  return [piece.texto, piece.texto_en, piece.entidad, piece.nodo].some(
    (field) => (field ?? "").toLowerCase().includes(q),
  );
}

const STATE_TONE: Record<string, string> = {
  activo: "bg-salvia/10 text-salvia",
  pausado: "bg-tinta/[0.06] text-tinta-suave",
  pendiente: "bg-oro/12 text-oro-tinta",
};

export default function KnowledgePanel({ onClose }: { onClose: () => void }) {
  const t = useT();
  const [pieces, setPieces] = useState<Piece[]>([]);
  const [query, setQuery] = useState("");
  const [node, setNode] = useState<string | null>(null);
  const [settings, setSettings] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const searchRef = useRef<HTMLInputElement>(null);
  const isAdmin = Boolean(useSession()?.usuario?.es_admin);

  useEffect(() => {
    let live = true;
    Promise.all([
      api.conocimiento().catch(() => ({ piezas: [] })),
      api.conocimientoPendientes().catch(() => ({ piezas: [] })),
      api.preferencias().catch(() => ({ vista: {} })),
    ]).then(([activas, pendientes, prefs]) => {
      if (!live) return;
      setPieces([...(pendientes.piezas ?? []), ...(activas.piezas ?? [])]);
      setSettings((prefs.vista ?? {}) as Record<string, boolean>);
      setLoading(false);
    });
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    searchRef.current?.focus();
  }, []);

  const nodes = useMemo(
    () => [...new Set(pieces.map((p) => p.nodo))].sort(),
    [pieces],
  );
  const shown = pieces.filter((p) => matches(p, query) && (!node || p.nodo === node));
  const pending = pieces.filter((p) => p.estado === "pendiente").length;

  const replace = (id: string, next: Piece | null) =>
    setPieces((prev) =>
      next ? prev.map((p) => (p.id === id ? next : p)) : prev.filter((p) => p.id !== id),
    );

  const act = async (id: string, run: () => Promise<unknown>, next: Piece | null) => {
    const before = pieces;
    replace(id, next);
    try {
      await run();
    } catch {
      setPieces(before);
      toast(t("chat.knowledge.error"), "error");
    }
  };

  const toggleSetting = async (key: string) => {
    const next = !(settings[key] ?? true);
    setSettings((prev) => ({ ...prev, [key]: next }));
    try {
      await api.preferenciaSet(key, next);
    } catch {
      setSettings((prev) => ({ ...prev, [key]: !next }));
      toast(t("chat.settings.error"), "error");
    }
  };

  return (
    <div
      role="dialog"
      aria-label={t("chat.knowledge.title")}
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          e.stopPropagation();
          onClose();
        }
      }}
      className="absolute inset-0 z-20 flex flex-col bg-papel"
    >
      <div className="flex items-center gap-2 border-b border-linea px-3 py-2.5">
        <Brain size={15} className="shrink-0 text-oro-tinta" aria-hidden />
        <h2 className="min-w-0 flex-1 truncate text-sm font-semibold text-tinta">
          {t("chat.knowledge.title")}
        </h2>
        <button
          type="button"
          aria-label={t("chat.knowledge.close")}
          onClick={onClose}
          className="grid size-7 shrink-0 place-items-center rounded-full text-tinta-suave outline-none transition-colors hover:bg-papel-hondo hover:text-tinta focus-visible:ring-2 focus-visible:ring-violeta/40"
        >
          <X size={14} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3">
        <div className="relative mb-2.5">
          <Search
            size={13}
            aria-hidden
            className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-tinta-suave"
          />
          <input
            ref={searchRef}
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("chat.knowledge.search")}
            aria-label={t("chat.knowledge.search")}
            className="w-full rounded-xl border border-linea bg-crema py-1.5 pr-2.5 pl-7 text-sm text-tinta outline-none transition-shadow placeholder:text-tinta-suave focus-visible:ring-2 focus-visible:ring-violeta/40"
          />
        </div>

        {nodes.length > 1 && (
          <div className="mb-2.5 flex flex-wrap gap-1">
            {[null, ...nodes].map((n) => (
              <button
                key={n ?? "all"}
                type="button"
                aria-pressed={node === n}
                onClick={() => setNode(n)}
                className={`rounded-full px-2.5 py-1 text-xs transition-colors ${
                  node === n
                    ? "bg-tinta text-crema"
                    : "bg-papel-hondo text-tinta-suave hover:text-tinta"
                }`}
              >
                {n ?? t("chat.knowledge.all_nodes")}
              </button>
            ))}
          </div>
        )}

        {!loading && (
          <p className="mb-2 text-xs text-tinta-suave">
            {t("chat.knowledge.count", { n: String(pieces.length) })}
            {pending > 0 && ` · ${t("chat.knowledge.pending_n", { n: String(pending) })}`}
          </p>
        )}

        {!loading && pieces.length === 0 && (
          <p className="py-8 text-center text-sm text-tinta-suave">
            {t("chat.knowledge.empty")}
          </p>
        )}
        {!loading && pieces.length > 0 && shown.length === 0 && (
          <p className="py-8 text-center text-sm text-tinta-suave">
            {t("chat.knowledge.no_results", { q: query })}
          </p>
        )}

        <ul className="flex flex-col gap-1.5">
          {shown.map((piece) => (
            <li
              key={piece.id}
              className="rounded-xl border border-linea bg-crema px-2.5 py-2"
            >
              <p className="text-sm leading-snug text-tinta">{piece.texto}</p>
              <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                <span
                  className={`rounded-full px-1.5 py-0.5 text-2xs ${
                    STATE_TONE[piece.estado] ?? STATE_TONE.pausado
                  }`}
                >
                  {t(`chat.knowledge.state.${piece.estado}`)}
                </span>
                <span className="text-2xs text-tinta-suave">{piece.nodo}</span>
                {piece.entidad && (
                  <span className="min-w-0 truncate text-2xs text-tinta-suave">
                    · {piece.entidad}
                  </span>
                )}
                {piece.quien && (
                  <span className="text-2xs text-tinta-suave">
                    · {t("chat.knowledge.taught_by", { who: piece.quien, when: piece.cuando ?? "" })}
                  </span>
                )}
                <span className="flex-1" />
                {piece.estado === "pendiente" && (
                  <>
                    <PieceAction
                      label={t("chat.knowledge.approve")}
                      onClick={() =>
                        act(piece.id, () => api.conocimientoAprobar(piece.id), {
                          ...piece,
                          estado: "activo",
                        })
                      }
                    >
                      <Check size={12} />
                    </PieceAction>
                    <PieceAction
                      label={t("chat.knowledge.reject")}
                      onClick={() =>
                        act(piece.id, () => api.conocimientoRechazar(piece.id), null)
                      }
                    >
                      <X size={12} />
                    </PieceAction>
                  </>
                )}
                {isAdmin && piece.estado === "activo" && (
                  <PieceAction
                    label={t("chat.knowledge.pause")}
                    onClick={() =>
                      act(piece.id, () => api.knowledgeSetState(piece.id, "pausado"), {
                        ...piece,
                        estado: "pausado",
                      })
                    }
                  >
                    <Pause size={12} />
                  </PieceAction>
                )}
                {isAdmin && piece.estado === "pausado" && (
                  <PieceAction
                    label={t("chat.knowledge.resume")}
                    onClick={() =>
                      act(piece.id, () => api.knowledgeSetState(piece.id, "activo"), {
                        ...piece,
                        estado: "activo",
                      })
                    }
                  >
                    <Play size={12} />
                  </PieceAction>
                )}
                {isAdmin && piece.estado !== "pendiente" && (
                  <PieceAction
                    label={t("chat.knowledge.delete")}
                    onClick={() => act(piece.id, () => api.knowledgeDelete(piece.id), null)}
                  >
                    <Trash2 size={12} />
                  </PieceAction>
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div className="border-t border-linea px-3 py-3">
        <p className="mb-2 text-xs font-semibold text-tinta-suave">
          {t("chat.knowledge.settings")}
        </p>
        <SettingsPanel
          toggles={SETTING_KEYS.map((key: SettingKey) => ({
            key,
            label: t(key === "knowledge_capture" ? "chat.settings.capture" : "chat.settings.context"),
            detail: t(
              key === "knowledge_capture"
                ? "chat.settings.capture_detail"
                : "chat.settings.context_detail",
            ),
            on: settings[key] ?? true,
          }))}
          onToggle={toggleSetting}
        />
      </div>
    </div>
  );
}

function PieceAction({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className="grid size-6 shrink-0 place-items-center rounded-full text-tinta-suave outline-none transition-colors hover:bg-papel-hondo hover:text-tinta focus-visible:ring-2 focus-visible:ring-violeta/40"
    >
      {children}
    </button>
  );
}
