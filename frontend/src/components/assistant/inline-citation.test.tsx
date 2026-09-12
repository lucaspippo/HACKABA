// @vitest-environment jsdom
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Citation } from "./inline-citation";

const source = {
  heading: "mandale foto del lote y el remito",
  meta: "Proveedores · Campo Alegre",
  detail: "se lo enseñó Celeste el 18/06/2026",
};

describe("Citation", () => {
  it("announces a busy chip, and offers nothing to click, while the piece loads", () => {
    render(
      <Citation loading tone="knowledge" ariaLabel="Cargando la memoria…" label="M" />,
    );
    expect(
      screen.getByRole("status", { name: "Cargando la memoria…" }),
    ).toHaveAttribute("aria-busy", "true");
    // A half-loaded chip that opens an empty preview is worse than no chip.
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("opens the preview on click, not only on hover", async () => {
    render(
      <Citation tone="knowledge" ariaLabel="cita" label="M" source={source} />,
    );
    expect(screen.queryByText(source.heading)).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "cita" }));
    expect(await screen.findByText(source.heading)).toBeInTheDocument();
  });

  it("hands the reader off to the memory panel from inside the preview", async () => {
    const onOpen = vi.fn();
    render(
      <Citation
        tone="knowledge"
        ariaLabel="cita"
        label="M"
        source={source}
        onOpen={onOpen}
        openLabel="Ver en la memoria"
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "cita" }));
    await userEvent.click(
      await screen.findByRole("button", { name: "Ver en la memoria" }),
    );
    expect(onOpen).toHaveBeenCalledOnce();
  });

  it("shows no hand-off button when there is nowhere to hand off to", async () => {
    render(
      <Citation tone="knowledge" ariaLabel="cita" label="M" source={source} />,
    );
    await userEvent.click(screen.getByRole("button", { name: "cita" }));
    await screen.findByText(source.heading);
    expect(screen.queryByRole("button", { name: "Ver en la memoria" })).toBeNull();
  });
});
