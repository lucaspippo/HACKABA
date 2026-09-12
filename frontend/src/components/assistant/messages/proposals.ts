/**
 * Chips that ask the user to keep something Ángela proposed. Two tools share
 * the same confirm UI: `proponer_conocimiento` (free-text memory) and
 * `propose_rule` (a structured IF/THEN). Each writes nothing until the chip
 * is tapped — the tool result is only a validated proposal.
 */

export type KnowledgeProposal = {
  texto: string;
  nodo: string;
  tipo: string;
  ambito: string;
  efecto: string;
  entidad: string | null;
};

export type RuleProposal = {
  description: string;
  condition: Record<string, unknown>;
  action: unknown[];
  node: string;
  scope: string;
  entity_name: string | null;
  entity_type: string | null;
};

export type ChipProposal =
  | {
      kind: "knowledge";
      id: string;
      text: string;
      alreadySaved: boolean;
      knowledge: KnowledgeProposal;
      narrativeAlternative?: KnowledgeProposal;
    }
  | {
      kind: "rule";
      id: string;
      text: string;
      alreadySaved: boolean;
      rule: RuleProposal;
    };

type ToolPart = {
  type?: string;
  toolName?: string;
  toolCallId?: string;
  result?: {
    ok?: boolean;
    proposal?: unknown;
    already_saved?: string;
    also_narrative?: unknown;
  };
};

function asKnowledge(value: unknown): KnowledgeProposal | null {
  if (!value || typeof value !== "object") return null;
  const p = value as Record<string, unknown>;
  if (typeof p.texto !== "string" || !p.texto.trim()) return null;
  if (typeof p.nodo !== "string" || typeof p.tipo !== "string") return null;
  if (typeof p.ambito !== "string" || typeof p.efecto !== "string") return null;
  return {
    texto: p.texto,
    nodo: p.nodo,
    tipo: p.tipo,
    ambito: p.ambito,
    efecto: p.efecto,
    entidad: typeof p.entidad === "string" ? p.entidad : null,
  };
}

function asRule(value: unknown): RuleProposal | null {
  if (!value || typeof value !== "object") return null;
  const p = value as Record<string, unknown>;
  if (typeof p.description !== "string" || !p.description.trim()) return null;
  if (!p.condition || typeof p.condition !== "object" || Array.isArray(p.condition)) return null;
  if (!Array.isArray(p.action)) return null;
  if (typeof p.node !== "string" || typeof p.scope !== "string") return null;
  return {
    description: p.description,
    condition: p.condition as Record<string, unknown>,
    action: p.action,
    node: p.node,
    scope: p.scope,
    entity_name: typeof p.entity_name === "string" ? p.entity_name : null,
    entity_type: typeof p.entity_type === "string" ? p.entity_type : null,
  };
}

/** Pull keep-able proposals out of a message's tool-call parts. */
export function proposalsFromContent(content: readonly unknown[]): ChipProposal[] {
  const out: ChipProposal[] = [];
  for (const raw of content) {
    const p = raw as ToolPart;
    if (p.type !== "tool-call" || !p.toolCallId || !p.result?.ok || !p.result.proposal) continue;

    if (p.toolName === "proponer_conocimiento") {
      const knowledge = asKnowledge(p.result.proposal);
      if (!knowledge) continue;
      const narrative = asKnowledge(p.result.also_narrative);
      out.push({
        kind: "knowledge",
        id: p.toolCallId,
        text: knowledge.texto,
        alreadySaved: Boolean(p.result.already_saved),
        knowledge,
        ...(narrative ? { narrativeAlternative: narrative } : {}),
      });
      continue;
    }

    if (p.toolName === "propose_rule") {
      const rule = asRule(p.result.proposal);
      if (!rule) continue;
      out.push({
        kind: "rule",
        id: p.toolCallId,
        text: rule.description,
        alreadySaved: false,
        rule,
      });
    }
  }
  return out;
}
