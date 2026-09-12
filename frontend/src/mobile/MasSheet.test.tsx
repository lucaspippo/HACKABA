// @vitest-environment jsdom
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import MasSheet from "./MasSheet";

const aldo = { username: "aldo", nombre: "Aldo", rol: "Dueño", es_admin: true };

function renderSheet(props: Partial<ComponentProps<typeof MasSheet>> = {}) {
  const onCerrar = vi.fn();
  const onBuscar = vi.fn();
  const onVerPerfil = vi.fn();
  render(
    <MasSheet
      user={aldo}
      conBuscar
      items={[]}
      esAdmin
      onCerrar={onCerrar}
      onBuscar={onBuscar}
      onVerPerfil={onVerPerfil}
      onPickNotif={vi.fn()}
      {...props}
    />,
  );
  return { onCerrar, onBuscar, onVerPerfil };
}

describe("MasSheet", () => {
  it("names the person, not a generic account heading", () => {
    renderSheet();
    expect(screen.getByRole("dialog", { name: "Aldo" })).toBeInTheDocument();
  });

  it("offers search only to whoever looks things up", () => {
    const { unmount } = render(<MasSheet
      user={aldo} conBuscar items={[]} esAdmin
      onCerrar={vi.fn()} onBuscar={vi.fn()} onVerPerfil={vi.fn()} onPickNotif={vi.fn()}
    />);
    expect(screen.getByRole("button", { name: /buscar|search/i })).toBeInTheDocument();
    unmount();
    render(<MasSheet
      user={{ username: "walter", nombre: "Walter", rol: "Reparto · camión 1" }}
      conBuscar={false} items={[]} esAdmin={false}
      onCerrar={vi.fn()} onBuscar={vi.fn()} onVerPerfil={vi.fn()} onPickNotif={vi.fn()}
    />);
    expect(screen.queryByRole("button", { name: /buscar|search/i })).toBeNull();
  });

  it("sends search and profile out through the callbacks", async () => {
    const user = userEvent.setup();
    const { onBuscar, onVerPerfil } = renderSheet();
    await user.click(screen.getByRole("button", { name: /buscar|search/i }));
    expect(onBuscar).toHaveBeenCalledOnce();
    await user.click(screen.getByRole("button", { name: /perfil|profile/i }));
    expect(onVerPerfil).toHaveBeenCalledOnce();
  });

  it("closes on Escape", async () => {
    const user = userEvent.setup();
    const { onCerrar } = renderSheet();
    await user.keyboard("{Escape}");
    expect(onCerrar).toHaveBeenCalledOnce();
  });

  it("lists notifications when there are any", () => {
    renderSheet({
      items: [{ id: 1, titulo: "Pedido de acceso", cuerpo: "Marta pidió Caja", leida: false, tipo: "solicitud_modulo" }],
    });
    expect(screen.getByText("Pedido de acceso")).toBeInTheDocument();
    expect(screen.queryByText(/nada nuevo|nothing new/i)).toBeNull();
  });
});
