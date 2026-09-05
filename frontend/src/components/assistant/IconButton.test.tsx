// @vitest-environment jsdom
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import IconButton from "./IconButton";

describe("IconButton", () => {
  it("names the button with its label", () => {
    render(<IconButton label="Cerrar" onClick={() => {}}><span /></IconButton>);
    expect(screen.getByRole("button", { name: "Cerrar" })).toBeInTheDocument();
  });

  it("carries no title attribute, so the native tooltip cannot double up", () => {
    render(<IconButton label="Cerrar" onClick={() => {}}><span /></IconButton>);
    expect(screen.getByRole("button")).not.toHaveAttribute("title");
  });

  it("reveals the tooltip on keyboard focus", async () => {
    const user = userEvent.setup();
    render(<IconButton label="Cerrar" onClick={() => {}}><span /></IconButton>);
    expect(screen.queryByTestId("icon-button-tooltip")).toBeNull();
    await user.tab();
    expect(screen.getByTestId("icon-button-tooltip")).toHaveTextContent("Cerrar");
  });

  it("reveals the tooltip on hover", async () => {
    const user = userEvent.setup();
    render(<IconButton label="Cerrar" onClick={() => {}}><span /></IconButton>);
    await user.hover(screen.getByRole("button"));
    expect(screen.getByTestId("icon-button-tooltip")).toBeInTheDocument();
  });

  it("dismisses the tooltip on Escape without moving focus", async () => {
    const user = userEvent.setup();
    render(<IconButton label="Cerrar" onClick={() => {}}><span /></IconButton>);
    await user.tab();
    const button = screen.getByRole("button");
    expect(screen.getByTestId("icon-button-tooltip")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByTestId("icon-button-tooltip")).toBeNull();
    expect(button).toHaveFocus();
  });

  it("lets Escape through once no tooltip is showing", async () => {
    const user = userEvent.setup();
    const onEscape = vi.fn();
    render(
      <div onKeyDown={(e) => e.key === "Escape" && onEscape()}>
        <IconButton label="Cerrar" onClick={() => {}}><span /></IconButton>
      </div>,
    );
    await user.tab();
    await user.keyboard("{Escape}");
    expect(onEscape).not.toHaveBeenCalled();
    await user.keyboard("{Escape}");
    expect(onEscape).toHaveBeenCalledOnce();
  });

  it("hides the tooltip from assistive tech, which already reads the label", async () => {
    const user = userEvent.setup();
    render(<IconButton label="Cerrar" onClick={() => {}}><span /></IconButton>);
    await user.tab();
    expect(screen.getByTestId("icon-button-tooltip")).toHaveAttribute("aria-hidden", "true");
  });
});
