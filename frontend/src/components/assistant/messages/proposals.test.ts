import { describe, expect, it } from "vitest";
import { proposalsFromContent } from "./proposals";

const knowledgeProposal = {
  texto: "no fiar a clientes nuevos",
  nodo: "ventas",
  tipo: "regla",
  ambito: "global",
  efecto: "contexto_para_angela",
  entidad: null,
};

const ruleProposal = {
  description: "mercadería fallada → recargo del 20% al proveedor",
  condition: { field: "damaged", operator: "eq", value: true },
  action: [{ type: "apply_discount", params: { percent: 20 } }],
  node: "inventario",
  scope: "global",
};

describe("proposalsFromContent", () => {
  it("reads a knowledge proposal from proponer_conocimiento", () => {
    expect(
      proposalsFromContent([
        {
          type: "tool-call",
          toolName: "proponer_conocimiento",
          toolCallId: "k1",
          result: { ok: true, proposal: knowledgeProposal },
        },
      ]),
    ).toEqual([
      {
        kind: "knowledge",
        id: "k1",
        text: "no fiar a clientes nuevos",
        alreadySaved: false,
        knowledge: knowledgeProposal,
      },
    ]);
  });

  it("reads a structured rule from propose_rule so the confirm chip can fire", () => {
    expect(
      proposalsFromContent([
        {
          type: "tool-call",
          toolName: "propose_rule",
          toolCallId: "r1",
          result: { ok: true, proposal: ruleProposal },
        },
      ]),
    ).toEqual([
      {
        kind: "rule",
        id: "r1",
        text: "mercadería fallada → recargo del 20% al proveedor",
        alreadySaved: false,
        rule: {
          ...ruleProposal,
          entity_name: null,
          entity_type: null,
        },
      },
    ]);
  });

  it("keeps both kinds from the same message, in order", () => {
    const chips = proposalsFromContent([
      {
        type: "tool-call",
        toolName: "propose_rule",
        toolCallId: "r1",
        result: { ok: true, proposal: ruleProposal },
      },
      {
        type: "tool-call",
        toolName: "proponer_conocimiento",
        toolCallId: "k1",
        result: { ok: true, proposal: knowledgeProposal },
      },
    ]);
    expect(chips.map((c) => c.kind)).toEqual(["rule", "knowledge"]);
  });

  it("ignores a failed or shapeless propose_rule result", () => {
    expect(
      proposalsFromContent([
        {
          type: "tool-call",
          toolName: "propose_rule",
          toolCallId: "r1",
          result: { ok: false, motivo: "bad action" },
        },
        {
          type: "tool-call",
          toolName: "propose_rule",
          toolCallId: "r2",
          result: { ok: true, proposal: { description: "x" } },
        },
        { type: "text", text: "lista la propuesta" },
      ]),
    ).toEqual([]);
  });

  it("marks an already-saved knowledge piece so the chip is not a decision", () => {
    const chips = proposalsFromContent([
      {
        type: "tool-call",
        toolName: "proponer_conocimiento",
        toolCallId: "k1",
        result: { ok: true, proposal: knowledgeProposal, already_saved: "p9" },
      },
    ]);
    expect(chips[0]?.alreadySaved).toBe(true);
  });
});
