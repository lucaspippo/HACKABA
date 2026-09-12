import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { keys } from "../../lib/query/keys";
import { queries } from "../../lib/query/queries";
import { queryClient } from "../../lib/query/client";

export type KnowledgePiece = {
  id: string;
  texto: string;
  nodo: string;
  entidad?: string | null;
  estado: string;
  quien?: string | null;
  cuando?: string | null;
};

/** Reloads without blanking chips that are already on screen. */
export function invalidateKnowledge() {
  return queryClient.invalidateQueries({ queryKey: keys.conocimiento() });
}

/** Display name for a knowledge node; unknown ids stay as stored. */
export function knowledgeNodeLabel(nodo: string, translate: (key: string) => string): string {
  const key = `chat.knowledge.node.${nodo}`;
  const label = translate(key);
  return label === key ? nodo : label;
}

/**
 * The cited piece, or null while it loads and if it does not exist. Ángela
 * cites by id; a rule someone deleted, or one outside this reader's scope,
 * has to render as nothing rather than as a dead marker. `ready` is false
 * only on the first fetch — a missing id after that is a real absence.
 */
export function useKnowledgeLookup(id: string): { piece: KnowledgePiece | null; ready: boolean } {
  const active = useQuery({
    ...queries.conocimiento(),
    throwOnError: false,
  });
  const pending = useQuery({
    ...queries.conocimientoPendientes(),
    throwOnError: false,
  });
  const pieces = useMemo(() => {
    const next: Record<string, KnowledgePiece> = {};
    for (const p of [...(active.data?.piezas ?? []), ...(pending.data?.piezas ?? [])]) {
      next[p.id] = p;
    }
    return next;
  }, [active.data, pending.data]);
  return {
    piece: pieces[id] ?? null,
    ready: active.isFetched && pending.isFetched,
  };
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
