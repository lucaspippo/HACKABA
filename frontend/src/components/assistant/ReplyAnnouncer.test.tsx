// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import ReplyAnnouncer from "./ReplyAnnouncer";

describe("ReplyAnnouncer", () => {
  it("stays silent while the reply is still streaming", () => {
    render(<ReplyAnnouncer text="Tenés $85.700.000 en mora." isRunning label="Ángela respondió:" />);
    expect(screen.getByRole("status")).toHaveTextContent("");
  });

  it("publishes the reply once the run finishes", () => {
    const { rerender } = render(
      <ReplyAnnouncer text="Tenés $85.700.000" isRunning label="Ángela respondió:" />,
    );
    rerender(<ReplyAnnouncer text="Tenés $85.700.000" isRunning={false} label="Ángela respondió:" />);
    expect(screen.getByRole("status")).toHaveTextContent("Ángela respondió: Tenés $85.700.000");
  });

  it("publishes nothing when the finished run produced no text", () => {
    render(<ReplyAnnouncer text="" isRunning={false} label="Ángela respondió:" />);
    expect(screen.getByRole("status")).toHaveTextContent("");
  });

  it("keeps the region out of the visual layout", () => {
    render(<ReplyAnnouncer text="Hola" isRunning={false} label="Ángela respondió:" />);
    expect(screen.getByRole("status")).toHaveClass("sr-only");
  });
});

describe("ReplyAnnouncer markdown handling", () => {
  it("announces prose, never the markdown source", () => {
    render(<ReplyAnnouncer text="Tenés **$85.700.000** en mora." isRunning={false} label="Ángela respondió:" />);
    const status = screen.getByRole("status");
    expect(status.textContent).not.toContain("**");
    expect(status).toHaveTextContent("Ángela respondió: Tenés $85.700.000 en mora.");
  });
});
