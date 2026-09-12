import { describe, expect, it } from "vitest";
import { citedId } from "./knowledgeStore";

describe("citedId", () => {
  it("reads the piece id out of a memoria link", () => {
    expect(citedId("memoria:k3f8a1c2")).toBe("k3f8a1c2");
  });

  it("ignores an ordinary link", () => {
    expect(citedId("https://example.com")).toBeNull();
  });

  it("ignores a missing href", () => {
    expect(citedId(undefined)).toBeNull();
  });

  it("treats a scheme with no id as no citation", () => {
    expect(citedId("memoria:")).toBeNull();
    expect(citedId("memoria:   ")).toBeNull();
  });

  it("does not match a url that merely mentions the word", () => {
    expect(citedId("https://x.com/memoria:k01")).toBeNull();
  });
});
