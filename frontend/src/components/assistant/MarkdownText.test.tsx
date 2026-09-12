// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { TextMessagePartProvider } from "@assistant-ui/react";
import MarkdownText from "./MarkdownText";

function renderMarkdown(text: string) {
  return render(
    <TextMessagePartProvider text={text} isRunning={false}>
      <MarkdownText />
    </TextMessagePartProvider>,
  );
}

describe("MarkdownText", () => {
  it("renders emphasis as markup instead of literal asterisks", () => {
    const { container } = renderMarkdown("Tenés **$85.700.000** en mora.");
    expect(container.querySelector("strong")).toHaveTextContent("$85.700.000");
    expect(container.textContent).not.toContain("**");
  });

  it("renders an ordered list as a real list", () => {
    const { container } = renderMarkdown("1. Uno\n2. Dos\n3. Tres");
    expect(container.querySelectorAll("ol > li")).toHaveLength(3);
  });

  it("renders an unordered list as a real list", () => {
    const { container } = renderMarkdown("- Uno\n- Dos");
    expect(container.querySelectorAll("ul > li")).toHaveLength(2);
  });

  it("renders GitHub-flavoured tables", () => {
    const { container } = renderMarkdown("| Cliente | Saldo |\n| --- | --- |\n| Elsa | 19 |");
    expect(container.querySelector("table")).toBeInTheDocument();
    expect(container.querySelectorAll("tbody tr")).toHaveLength(1);
  });

  it("opens links in a new tab without leaking the referrer", () => {
    renderMarkdown("[Cuentas](https://example.com)");
    const link = screen.getByRole("link", { name: "Cuentas" });
    expect(link).toHaveAttribute("href", "https://example.com");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noreferrer"));
  });

  it("keeps plain text intact", () => {
    const { container } = renderMarkdown("Sin formato.");
    expect(container.textContent).toContain("Sin formato.");
  });
});
