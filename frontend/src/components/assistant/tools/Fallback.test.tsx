// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import type { ToolCallMessagePartProps } from "@assistant-ui/react";
import ToolFallback from "./Fallback";

function props(partial: Partial<ToolCallMessagePartProps>): ToolCallMessagePartProps {
  return {
    toolName: "propose_rule",
    toolCallId: "t1",
    args: {},
    argsText: "{}",
    status: { type: "complete" },
    ...partial,
  } as ToolCallMessagePartProps;
}

describe("ToolFallback", () => {
  it("does not dump a propose_rule proposal as a key/value widget", () => {
    const { container } = render(
      <ToolFallback
        {...props({
          result: {
            ok: true,
            proposal: {
              description: "mercadería fallada → recargo del 20%",
              condition: { field: "damaged", operator: "eq", value: true },
              action: [{ type: "mark_receipt_partial" }],
              node: "inventario",
              scope: "global",
            },
          },
        })}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("still surfaces a failed tool as an error", () => {
    const { container } = render(
      <ToolFallback
        {...props({
          result: { ok: false, motivo: "condition must reference '$entity'" },
        })}
      />,
    );
    expect(container).toHaveTextContent("condition must reference '$entity'");
  });

  it("still draws an items table", () => {
    const { container } = render(
      <ToolFallback
        {...props({
          toolName: "mis_recordatorios",
          result: { items: [{ titulo: "cobrar a Elsa", cuando: "hoy" }] },
        })}
      />,
    );
    expect(container.querySelector("table")).toBeTruthy();
    expect(container).toHaveTextContent("cobrar a Elsa");
  });
});
