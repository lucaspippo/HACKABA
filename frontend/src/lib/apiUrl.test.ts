import { afterEach, describe, expect, it, vi } from "vitest";
import { apiUrl } from "./apiUrl";

afterEach(() => { vi.unstubAllEnvs(); });

describe("apiUrl", () => {
  it("leaves the path untouched when no base is configured", () => {
    // The deployed default: the backend serves the bundle, so the API is
    // same-origin and every request URL must stay exactly as it was.
    vi.stubEnv("VITE_API_BASE", "");
    expect(apiUrl("/api/health")).toBe("/api/health");
    expect(apiUrl("/api/preferencias/foo?x=1")).toBe("/api/preferencias/foo?x=1");
  });

  it("prefixes an absolute base", () => {
    vi.stubEnv("VITE_API_BASE", "https://api.example.com");
    expect(apiUrl("/api/health")).toBe("https://api.example.com/api/health");
  });

  it("does not double the slash when the base has a trailing one", () => {
    vi.stubEnv("VITE_API_BASE", "https://api.example.com/");
    expect(apiUrl("/api/health")).toBe("https://api.example.com/api/health");
  });

  it("leaves an already-absolute URL alone", () => {
    vi.stubEnv("VITE_API_BASE", "https://api.example.com");
    expect(apiUrl("https://other.example.com/x")).toBe("https://other.example.com/x");
  });
});
