import { useSyncExternalStore } from "react";
import { api } from "../../lib/api";

export type KnowledgePiece = {
  id: string;
  texto: string;
  nodo: string;
  entidad?: string | null;
  estado: string;
  quien?: string | null;
  cuando?: string | null;
};

let pieces: Record<string, KnowledgePiece> = {};
let ready = false;
let loading: Promise<void> | null = null;
const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

function load() {
  if (loading) return loading;
  loading = Promise.all([
    api.conocimiento().catch(() => ({ piezas: [] })),
    api.conocimientoPendientes().catch(() => ({ piezas: [] })),
  ])
    .then(([active, pending]) => {
      const next: Record<string, KnowledgePiece> = {};
      for (const p of [...(active.piezas ?? []), ...(pending.piezas ?? [])]) next[p.id] = p;
      pieces = next;
      ready = true;
      emit();
    })
    .catch(() => {
      ready = true;
      emit();
    });
  return loading;
}

/** Reloads without blanking chips that are already on screen. */
export function invalidateKnowledge() {
  loading = null;
  load();
}

/** Display name for a knowledge node; unknown ids stay as stored. */
export function knowledgeNodeLabel(nodo: string, translate: (key: string) => string): string {
  const key = `chat.knowledge.node.${nodo}`;
  const label = translate(key);
  return label === key ? nodo : label;
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  load();
  return () => listeners.delete(listener);
}

/**
 * The cited piece, or null while it loads and if it does not exist. Ángela
 * cites by id; a rule someone deleted, or one outside this reader's scope,
 * has to render as nothing rather than as a dead marker. `ready` is false
 * only on the first fetch — a missing id after that is a real absence.
 */
export function useKnowledgeLookup(id: string): { piece: KnowledgePiece | null; ready: boolean } {
  const all = useSyncExternalStore(
    subscribe,
    () => pieces,
    () => pieces,
  );
  useSyncExternalStore(
    subscribe,
    () => ready,
    () => ready,
  );
  return { piece: all[id] ?? null, ready };
}

export function useKnowledgePiece(id: string): KnowledgePiece | null {
  return useKnowledgeLookup(id).piece;
}

// A hash URL, not a "memoria:" scheme: react-markdown's default
// urlTransform blanks any href whose protocol it does not know, so a custom
// scheme reached the link slot as href="" and rendered as a stray dot.
export const CITATION_SCHEME = "#memoria-";

export function citedId(href: string | undefined): string | null {
  if (!href || !href.startsWith(CITATION_SCHEME)) return null;
  return href.slice(CITATION_SCHEME.length).trim() || null;
}
