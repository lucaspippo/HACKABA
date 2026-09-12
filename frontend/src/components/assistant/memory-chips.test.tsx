// @vitest-environment jsdom
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryChips } from "./memory-chips";

const labels = {
  memory: "memoria",
  remembered: (n: number) => `guardado ${n}`,
  save: (text: string) => `Guardar «${text}»`,
  dismiss: (text: string) => `Descartar «${text}»`,
  keep: "Guardar",
  discard: "Descartar",
  saved: "Guardado",
  pending: "Va a revisión",
  applyRuleLabel: "También aplicarla",
  contextOnlyLabel: "Solo recordarlo",
};

describe("MemoryChips", () => {
  it("shows the full proposal and named keep/discard actions", async () => {
    const onSave = vi.fn();
    const onDismiss = vi.fn();
    render(
      <MemoryChips
        chips={[
          {
            id: "r1",
            text: "mercadería fallada → recargo del 20% al proveedor",
            change: "proposed",
          },
        ]}
        labels={labels}
        onSave={onSave}
        onDismiss={onDismiss}
      />,
    );
    expect(
      screen.getByText("mercadería fallada → recargo del 20% al proveedor"),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Guardar/ }));
    expect(onSave).toHaveBeenCalledWith("r1");
    await userEvent.click(screen.getByRole("button", { name: /Descartar/ }));
    expect(onDismiss).toHaveBeenCalledWith("r1");
  });
});
