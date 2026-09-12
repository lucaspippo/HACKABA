// @vitest-environment jsdom
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import KnowledgeCite from "./KnowledgeCite";
import { KnowledgeOpenProvider } from "./KnowledgeOpen";

const lookup = vi.hoisted(() => vi.fn());

vi.mock("./knowledgeStore", async () => {
  const actual =
    await vi.importActual<typeof import("./knowledgeStore")>("./knowledgeStore");
  return { ...actual, useKnowledgeLookup: lookup };
});

const piece = {
  id: "k01",
  texto: "mercadería fallada → recargo del 20% al proveedor",
  nodo: "inventario",
  entidad: null,
  estado: "activo",
  quien: "aldo",
  cuando: "2026-07-01",
};

describe("KnowledgeCite", () => {
  it("holds a loading mark until the store is ready", () => {
    lookup.mockReturnValue({ piece: null, ready: false });
    render(<KnowledgeCite id="k01" />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("renders nothing for a missing piece once the store is ready", () => {
    lookup.mockReturnValue({ piece: null, ready: true });
    const { container } = render(<KnowledgeCite id="missing" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("opens the memory panel on the cited piece, from inside the preview", async () => {
    lookup.mockReturnValue({ piece, ready: true });
    const onOpen = vi.fn();
    render(
      <KnowledgeOpenProvider onOpen={onOpen}>
        <KnowledgeCite id="k01" />
      </KnowledgeOpenProvider>,
    );
    await userEvent.click(screen.getByRole("button"));
    await userEvent.click(
      await screen.findByRole("button", { name: /Ver en la memoria/ }),
    );
    expect(onOpen).toHaveBeenCalledWith("k01", piece.texto);
  });
});
