import { useSyncExternalStore } from "react";
import { api } from "../../lib/api";

export type KnowledgePiece = {
  id: string;
  texto: string;
  nodo: string;
  entidad?: string | null;
  estado: string;
};

let pieces: Record<string, KnowledgePiece> = {};
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
      emit();
    })
    .catch(() => {});
  return loading;
}

/** Drops the cache so the next citation re-reads it (a rule was just saved). */
export function invalidateKnowledge() {
  loading = null;
  pieces = {};
  emit();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  load();
  return () => listeners.delete(listener);
}

/**
 * The cited piece, or null while it loads and if it does not exist. Ángela
 * cites by id; a rule someone deleted, or one outside this reader's scope,
 * has to render as nothing rather than as a dead marker.
 */
export function useKnowledgePiece(id: string): KnowledgePiece | null {
  const all = useSyncExternalStore(
    subscribe,
    () => pieces,
    () => pieces,
  );
  return all[id] ?? null;
}

export const CITATION_SCHEME = "memoria:";

export function citedId(href: string | undefined): string | null {
  if (!href || !href.startsWith(CITATION_SCHEME)) return null;
  return href.slice(CITATION_SCHEME.length).trim() || null;
}
