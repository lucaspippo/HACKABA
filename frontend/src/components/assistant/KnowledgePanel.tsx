import { useEffect, useMemo, useRef, useState } from "react";
import { Brain, Check, Pause, Pencil, Play, Plus, Search, Settings, Trash2, X } from "lucide-react";
import { SettingsPanel } from "./settings-panel";
import { useApiQuery, useApiMutation } from "../../lib/query";
import { toast } from "../../lib/toastStore";
import { useT } from "../../lib/i18n";
import { useSession } from "../../lib/auth";
import { knowledgeNodeLabel } from "./knowledgeStore";

// Mirrors core/conocimiento.py's TIPOS/AMBITOS/NODOS/EFECTOS catalogs.
const TIPOS = ["regla", "excepcion", "protocolo", "contexto"] as const;
const AMBITOS = ["cliente", "proveedor", "categoria", "empleado", "global"] as const;
const NODOS_CATALOGO = [
  "ventas", "inventario", "deposito", "proveedores",
  "clientes", "caja", "equipo", "contexto",
] as const;
const EFECTOS = [
  "ajusta_umbral", "suprime_alerta", "genera_alerta",
  "contexto_para_angela", "requiere_aprobacion",
] as const;

type Piece = {
  id: string;
  texto: string;
  texto_en?: string | null;
  nodo: string;
  entidad?: string | null;
  estado: string;
  tipo: string;
  ambito?: string;
  efecto?: string;
  quien?: string | null;
  cuando?: string | null;
  superseded_by_texto?: string | null;
  freshness?: "fresco" | "atencion" | "revisar" | null;
  needs_review?: boolean;
};

type Tab = "active" | "review" | "archived";
type PiezasPayload = { piezas?: Piece[] };
type PrefsPayload = { vista?: Record<string, boolean> };

function runMut<T = unknown>(mut: { mutateAsync: (vars: never) => Promise<unknown> }, vars: unknown) {
  return mut.mutateAsync(vars as never) as Promise<T>;
}
const ARCHIVED_ESTADOS = new Set(["archivada", "superada"]);

const FRESHNESS_TONE: Record<string, string> = {
  fresco: "bg-salvia",
  atencion: "bg-oro",
  revisar: "bg-tinta/30",
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
  revisar: "bg-oro/12 text-oro-tinta",
  superada: "bg-tinta/[0.06] text-tinta-suave",
  archivada: "bg-tinta/[0.06] text-tinta-suave",
};

export default function KnowledgePanel({
  onClose,
  focusId,
  focusQuery,
}: {
  onClose: () => void;
  focusId?: string;
  focusQuery?: string;
}) {
  const t = useT();
  const [pieces, setPieces] = useState<Piece[]>([]);
  const [query, setQuery] = useState(focusQuery ?? "");
  const [node, setNode] = useState<string | null>(null);
  const [settings, setSettings] = useState<Record<string, boolean>>({});
  const [editing, setEditing] = useState<Piece | null>(null); // null = create mode when formOpen
  const [formOpen, setFormOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [tab, setTab] = useState<Tab>("active");
  const searchRef = useRef<HTMLInputElement>(null);
  const session = useSession();
  const isAdmin = Boolean(session?.usuario?.es_admin);
  const username = session?.usuario?.username;
  const activasQ = useApiQuery("conocimiento", [{ incluir_archivadas: true }]);
  const pendQ = useApiQuery("conocimientoPendientes");
  const prefsQ = useApiQuery("preferencias");
  const aprobar = useApiMutation("conocimientoAprobar");
  const rechazar = useApiMutation("conocimientoRechazar");
  const reconfirmar = useApiMutation("conocimientoReconfirmar");
  const archivar = useApiMutation("conocimientoArchivar");
  const setStateMut = useApiMutation("knowledgeSetState");
  const deleteMut = useApiMutation("knowledgeDelete");
  const editar = useApiMutation("conocimientoEditar");
  const crear = useApiMutation("conocimientoCrear");
  const prefSet = useApiMutation("preferenciaSet");
  const loading = (activasQ.isPending && !activasQ.data)
    || (pendQ.isPending && !pendQ.data)
    || (prefsQ.isPending && !prefsQ.data);

  useEffect(() => {
    if (activasQ.isPending && pendQ.isPending && !activasQ.data && !pendQ.data) return;
    const pendientes = (pendQ.data ?? {}) as PiezasPayload;
    const activas = (activasQ.data ?? {}) as PiezasPayload;
    setPieces([...(pendientes.piezas ?? []), ...(activas.piezas ?? [])]);
  }, [activasQ.data, pendQ.data, activasQ.isPending, pendQ.isPending]);

  useEffect(() => {
    if (prefsQ.data) setSettings(((prefsQ.data as PrefsPayload).vista ?? {}));
  }, [prefsQ.data]);

  useEffect(() => {
    if (focusQuery) return;
    searchRef.current?.focus();
  }, [focusQuery]);

  const nodes = useMemo(
    () => [...new Set(pieces.map((p) => p.nodo))].sort(),
    [pieces],
  );
  const needsReview = (p: Piece) => p.estado === "revisar" || Boolean(p.needs_review);
  const byTab: Record<Tab, (p: Piece) => boolean> = {
    archived: (p) => ARCHIVED_ESTADOS.has(p.estado),
    review: (p) => !ARCHIVED_ESTADOS.has(p.estado) && needsReview(p),
    active: (p) => !ARCHIVED_ESTADOS.has(p.estado) && !needsReview(p),
  };
  const shown = pieces
    .filter(byTab[tab])
    .filter((p) => matches(p, query) && (!node || p.nodo === node));

  useEffect(() => {
    if (!focusId || loading) return;
    const piece = pieces.find((p) => p.id === focusId);
    if (!piece) return;
    if (ARCHIVED_ESTADOS.has(piece.estado)) setTab("archived");
    else if (piece.estado === "revisar" || piece.needs_review) setTab("review");
    else setTab("active");
  }, [focusId, loading, pieces]);

  useEffect(() => {
    if (!focusId) return;
    document
      .querySelector(`[data-knowledge-id="${CSS.escape(focusId)}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }, [focusId, shown, tab]);

  const pending = pieces.filter((p) => p.estado === "pendiente").length;
  const counts: Record<Tab, number> = {
    active: pieces.filter(byTab.active).length,
    review: pieces.filter(byTab.review).length,
    archived: pieces.filter(byTab.archived).length,
  };

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
      await runMut(prefSet, [key, next]);
    } catch {
      setSettings((prev) => ({ ...prev, [key]: !next }));
      toast(t("chat.settings.error"), "error");
    }
  };

  const openCreate = () => {
    setEditing(null);
    setFormOpen(true);
  };

  const openEdit = (piece: Piece) => {
    setEditing(piece);
    setFormOpen(true);
  };

  const submitForm = async (fields: PieceFormFields) => {
    if (editing) {
      const updated = await runMut<{ pieza: Piece }>(editar, [editing.id, fields]);
      setPieces((prev) => prev.map((p) => (p.id === editing.id ? updated.pieza : p)));
    } else {
      const created = await runMut<{ pieza: Piece }>(crear, [fields]);
      setPieces((prev) => [...prev, created.pieza]);
    }
    setFormOpen(false);
  };

  return (
    <div
      role="dialog"
      aria-label={t("chat.knowledge.title")}
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          e.stopPropagation();
          if (settingsOpen) {
            setSettingsOpen(false);
          } else {
            onClose();
          }
        }
      }}
      className="absolute inset-0 z-20 flex flex-col bg-papel"
    >
      <div className="flex items-center gap-2 border-b border-linea px-3 py-2.5">
        <Brain size={15} className="shrink-0 text-oro-tinta" aria-hidden />
        <h2 className="min-w-0 flex-1 truncate text-sm font-semibold text-tinta">
          {t("chat.knowledge.title")}
        </h2>
        <div className="relative shrink-0">
          <button
            type="button"
            aria-label={t("chat.knowledge.settings")}
            aria-pressed={settingsOpen}
            onClick={() => setSettingsOpen((v) => !v)}
            className="grid size-7 place-items-center rounded-full text-tinta-suave outline-none transition-colors hover:bg-papel-hondo hover:text-tinta focus-visible:ring-2 focus-visible:ring-violeta/40"
          >
            <Settings size={14} />
          </button>
          {settingsOpen && (
            <div className="absolute right-0 top-9 z-40 w-64 rounded-xl border border-linea bg-crema p-3 shadow-lg">
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
          )}
        </div>
        <button
          type="button"
          aria-label={t("chat.knowledge.close")}
          onClick={onClose}
          className="grid size-7 shrink-0 place-items-center rounded-full text-tinta-suave outline-none transition-colors hover:bg-papel-hondo hover:text-tinta focus-visible:ring-2 focus-visible:ring-violeta/40"
        >
          <X size={14} />
        </button>
      </div>

      {settingsOpen && (
        <div className="fixed inset-0 z-30" onClick={() => setSettingsOpen(false)} />
      )}

      <div className="flex-1 overflow-y-auto px-3 py-3">
        <div className="mb-2.5 flex gap-1 rounded-full bg-papel-hondo p-0.5 text-xs">
          {(["active", "review", "archived"] as const).map((tabKey) => (
            <button
              key={tabKey}
              type="button"
              aria-pressed={tab === tabKey}
              onClick={() => setTab(tabKey)}
              className={`flex-1 rounded-full py-1 transition-colors ${
                tab === tabKey ? "bg-tinta text-crema" : "text-tinta-suave hover:text-tinta"
              }`}
            >
              {t(`chat.knowledge.tab_${tabKey}`)}
              {counts[tabKey] > 0 && ` (${counts[tabKey]})`}
            </button>
          ))}
        </div>

        <div className="mb-2.5 flex gap-1.5">
          <div className="relative min-w-0 flex-1">
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
            <select
              value={node ?? ""}
              onChange={(e) => setNode(e.target.value || null)}
              aria-label={t("chat.knowledge.all_nodes")}
              className="shrink-0 rounded-xl border border-linea bg-crema px-2 text-xs text-tinta outline-none focus-visible:ring-2 focus-visible:ring-violeta/40"
            >
              <option value="">{t("chat.knowledge.all_nodes")}</option>
              {nodes.map((n) => (
                <option key={n} value={n}>{knowledgeNodeLabel(n, t)}</option>
              ))}
            </select>
          )}
          <button
            type="button"
            aria-label={t("chat.knowledge.create")}
            onClick={openCreate}
            className="grid size-8 shrink-0 place-items-center rounded-xl bg-tinta text-crema outline-none transition-colors hover:bg-tinta/90 focus-visible:ring-2 focus-visible:ring-violeta/40"
          >
            <Plus size={14} />
          </button>
        </div>

        {!loading && pending > 0 && tab === "active" && (
          <p className="mb-2 text-xs text-tinta-suave">
            {t("chat.knowledge.pending_n", { n: String(pending) })}
          </p>
        )}

        {!loading && pieces.length === 0 && (
          <p className="py-8 text-center text-sm text-tinta-suave">
            {t("chat.knowledge.empty")}
          </p>
        )}
        {!loading && pieces.length > 0 && shown.length === 0 && (
          <p className="py-8 text-center text-sm text-tinta-suave">
            {query ? t("chat.knowledge.no_results", { q: query }) : t("chat.knowledge.tab_empty")}
          </p>
        )}

        <ul className="flex flex-col gap-1.5">
          {shown.map((piece) => (
            <li
              key={piece.id}
              data-knowledge-id={piece.id}
              className={`rounded-xl border px-2.5 py-2 ${
                piece.id === focusId
                  ? "border-oro/50 bg-oro/[0.07]"
                  : "border-linea bg-crema"
              }`}
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
                <span className="text-2xs text-tinta-suave">{knowledgeNodeLabel(piece.nodo, t)}</span>
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
                {piece.superseded_by_texto && (
                  <span className="min-w-0 truncate text-2xs text-tinta-suave">
                    · {t("chat.knowledge.superseded_by", { text: piece.superseded_by_texto })}
                  </span>
                )}
                {piece.freshness && !ARCHIVED_ESTADOS.has(piece.estado) && piece.estado !== "pendiente" && (
                  <span
                    role="img"
                    aria-label={t(`chat.knowledge.freshness.${piece.freshness}`)}
                    title={t(`chat.knowledge.freshness.${piece.freshness}`)}
                    className={`size-1.5 shrink-0 rounded-full ${FRESHNESS_TONE[piece.freshness] ?? ""}`}
                  />
                )}
                <span className="flex-1" />
                {piece.estado === "pendiente" && (
                  <>
                    <PieceAction
                      label={t("chat.knowledge.approve")}
                      onClick={() =>
                        act(piece.id, () => runMut(aprobar, [piece.id]), {
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
                        act(piece.id, () => runMut(rechazar, [piece.id]), null)
                      }
                    >
                      <X size={12} />
                    </PieceAction>
                  </>
                )}
                {(isAdmin || piece.quien === username) &&
                  piece.estado !== "pendiente" && !ARCHIVED_ESTADOS.has(piece.estado) && (
                  <PieceAction label={t("chat.knowledge.edit")} onClick={() => openEdit(piece)}>
                    <Pencil size={12} />
                  </PieceAction>
                )}
                {(isAdmin || piece.quien === username) && piece.estado === "revisar" && (
                  <>
                    <PieceAction
                      label={t("chat.knowledge.reconfirm")}
                      onClick={() =>
                        act(piece.id, () => runMut(reconfirmar, [piece.id]), {
                          ...piece,
                          estado: "activo",
                        })
                      }
                    >
                      <Check size={12} />
                    </PieceAction>
                    <PieceAction
                      label={t("chat.knowledge.archive")}
                      onClick={() =>
                        act(piece.id, () => runMut(archivar, [piece.id]), {
                          ...piece,
                          estado: "archivada",
                        })
                      }
                    >
                      <Trash2 size={12} />
                    </PieceAction>
                  </>
                )}
                {isAdmin && piece.estado === "activo" && (
                  <PieceAction
                    label={t("chat.knowledge.pause")}
                    onClick={() =>
                      act(piece.id, () => runMut(setStateMut, [piece.id, "pausado"]), {
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
                      act(piece.id, () => runMut(setStateMut, [piece.id, "activo"]), {
                        ...piece,
                        estado: "activo",
                      })
                    }
                  >
                    <Play size={12} />
                  </PieceAction>
                )}
                {isAdmin && piece.estado !== "pendiente" && !ARCHIVED_ESTADOS.has(piece.estado) && (
                  <PieceAction
                    label={t("chat.knowledge.delete")}
                    onClick={() => act(piece.id, () => runMut(deleteMut, [piece.id]), null)}
                  >
                    <Trash2 size={12} />
                  </PieceAction>
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>

      {formOpen && (
        <PieceForm
          piece={editing}
          onCancel={() => setFormOpen(false)}
          onSubmit={submitForm}
        />
      )}
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

type PieceFormFields = {
  texto: string;
  texto_en?: string;
  tipo: string;
  ambito: string;
  nodo?: string;
  efecto: string;
  entidad?: string;
};

function PieceForm({
  piece,
  onCancel,
  onSubmit,
}: {
  piece: Piece | null;
  onCancel: () => void;
  onSubmit: (fields: PieceFormFields) => Promise<void>;
}) {
  const t = useT();
  const [texto, setTexto] = useState(piece?.texto ?? "");
  const [tipo, setTipo] = useState(piece?.tipo ?? TIPOS[0]);
  const [ambito, setAmbito] = useState(piece?.ambito ?? "global");
  const [nodo, setNodo] = useState(piece?.nodo ?? NODOS_CATALOGO[0]);
  const [efecto, setEfecto] = useState(piece?.efecto ?? EFECTOS[0]);
  const [entidad, setEntidad] = useState(piece?.entidad ?? "");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await onSubmit({
        texto,
        tipo,
        ambito,
        efecto,
        entidad: entidad || undefined,
        ...(piece ? {} : { nodo }),
      });
    } catch {
      setError(t("chat.knowledge.error"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-label={t(piece ? "chat.knowledge.edit" : "chat.knowledge.create")}
      className="absolute inset-0 z-30 flex flex-col bg-papel"
    >
      <div className="flex items-center gap-2 border-b border-linea px-3 py-2.5">
        <h3 className="min-w-0 flex-1 truncate text-sm font-semibold text-tinta">
          {t(piece ? "chat.knowledge.edit" : "chat.knowledge.create")}
        </h3>
        <button
          type="button"
          aria-label={t("chat.knowledge.close")}
          onClick={onCancel}
          className="grid size-7 shrink-0 place-items-center rounded-full text-tinta-suave outline-none transition-colors hover:bg-papel-hondo hover:text-tinta focus-visible:ring-2 focus-visible:ring-violeta/40"
        >
          <X size={14} />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto px-3 py-3">
        <label className="mb-2 block text-xs text-tinta-suave">
          {t("chat.knowledge.form.texto")}
          <textarea
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            required
            rows={3}
            className="mt-1 w-full rounded-xl border border-linea bg-crema p-2 text-sm text-tinta outline-none focus-visible:ring-2 focus-visible:ring-violeta/40"
          />
        </label>

        <div className="mb-2 grid grid-cols-2 gap-2">
          <label className="text-xs text-tinta-suave">
            {t("chat.knowledge.form.tipo")}
            <select
              value={tipo}
              onChange={(e) => setTipo(e.target.value)}
              className="mt-1 w-full rounded-xl border border-linea bg-crema p-1.5 text-sm text-tinta outline-none focus-visible:ring-2 focus-visible:ring-violeta/40"
            >
              {TIPOS.map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          </label>

          <label className="text-xs text-tinta-suave">
            {t("chat.knowledge.form.ambito")}
            <select
              value={ambito}
              onChange={(e) => setAmbito(e.target.value)}
              className="mt-1 w-full rounded-xl border border-linea bg-crema p-1.5 text-sm text-tinta outline-none focus-visible:ring-2 focus-visible:ring-violeta/40"
            >
              {AMBITOS.map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          </label>

          {!piece && (
            <label className="text-xs text-tinta-suave">
              {t("chat.knowledge.form.nodo")}
              <select
                value={nodo}
                onChange={(e) => setNodo(e.target.value)}
                className="mt-1 w-full rounded-xl border border-linea bg-crema p-1.5 text-sm text-tinta outline-none focus-visible:ring-2 focus-visible:ring-violeta/40"
              >
                {NODOS_CATALOGO.map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            </label>
          )}

          <label className="text-xs text-tinta-suave">
            {t("chat.knowledge.form.efecto")}
            <select
              value={efecto}
              onChange={(e) => setEfecto(e.target.value)}
              className="mt-1 w-full rounded-xl border border-linea bg-crema p-1.5 text-sm text-tinta outline-none focus-visible:ring-2 focus-visible:ring-violeta/40"
            >
              {EFECTOS.map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          </label>
        </div>

        {ambito !== "global" && (
          <label className="mb-2 block text-xs text-tinta-suave">
            {t("chat.knowledge.form.entidad")}
            <input
              type="text"
              value={entidad}
              onChange={(e) => setEntidad(e.target.value)}
              required
              className="mt-1 w-full rounded-xl border border-linea bg-crema p-2 text-sm text-tinta outline-none focus-visible:ring-2 focus-visible:ring-violeta/40"
            />
          </label>
        )}

        {error && <p className="mb-2 text-xs text-rojo">{error}</p>}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-full px-3 py-1.5 text-xs text-tinta-suave hover:text-tinta"
          >
            {t("chat.knowledge.form.cancel")}
          </button>
          <button
            type="submit"
            disabled={saving}
            className="rounded-full bg-tinta px-3 py-1.5 text-xs text-crema disabled:opacity-60"
          >
            {t("chat.knowledge.form.save")}
          </button>
        </div>
      </form>
    </div>
  );
}
