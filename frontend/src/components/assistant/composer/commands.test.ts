import { describe, expect, it } from "vitest";
import { SLASH_COMMANDS, availableCommands, matchCommands, slashQuery } from "./commands";

const nameOf = (c: { id: string }) => c.id;
const all = () => true;

describe("slashQuery", () => {
  it("reads the query after a lone slash", () => {
    expect(slashQuery("/pri")).toBe("pri");
  });

  it("treats a bare slash as an empty query, not as no query", () => {
    expect(slashQuery("/")).toBe("");
  });

  it("ignores a slash that is not at the start", () => {
    expect(slashQuery("cuánto es 10/2")).toBeNull();
  });

  it("ignores a slash command followed by prose, which is a real message", () => {
    expect(slashQuery("/caja y además contame otra cosa")).toBeNull();
  });

  it("ignores plain text", () => {
    expect(slashQuery("hola")).toBeNull();
  });

  it("accepts accented command names", () => {
    expect(slashQuery("/día")).toBe("día");
  });
});

describe("availableCommands", () => {
  it("keeps ungated commands for everyone", () => {
    const ids = availableCommands(() => false).map((c) => c.id);
    expect(ids).toContain("priorities");
    expect(ids).toContain("new_thread");
  });

  it("hides commands whose feature the user lacks", () => {
    const ids = availableCommands((f) => f !== "caja").map((c) => c.id);
    expect(ids).not.toContain("cash");
  });

  it("shows a gated command to a user who has the feature", () => {
    const ids = availableCommands(all).map((c) => c.id);
    expect(ids).toContain("cash");
  });
});

describe("matchCommands", () => {
  it("filters by prefix", () => {
    const matches = matchCommands("/st", SLASH_COMMANDS, nameOf);
    expect(matches.map((c) => c.id)).toEqual(["stock"]);
  });

  it("offers everything for a bare slash", () => {
    expect(matchCommands("/", SLASH_COMMANDS, nameOf)).toHaveLength(SLASH_COMMANDS.length);
  });

  it("offers nothing for ordinary text", () => {
    expect(matchCommands("hola", SLASH_COMMANDS, nameOf)).toEqual([]);
  });
});

describe("the command catalogue", () => {
  it("gives every command a unique id", () => {
    const ids = SLASH_COMMANDS.map((c) => c.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("gives every command exactly one of prompt, action or template", () => {
    for (const command of SLASH_COMMANDS) {
      const kinds = [command.prompt, command.action, command.templateKey].filter(Boolean);
      expect(kinds.length, command.id).toBe(1);
    }
  });

  it("offers a remember command that the user finishes typing", () => {
    const remember = SLASH_COMMANDS.find((c) => c.id === "remember");
    expect(remember?.templateKey).toBeTruthy();
    expect(remember?.prompt).toBeUndefined();
  });

  it("matches the remember command by name", () => {
    expect(matchCommands("/rem", SLASH_COMMANDS, nameOf).map((c) => c.id)).toContain("remember");
  });
});
