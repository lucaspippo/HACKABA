import { describe, expect, it } from "vitest";
import { applyMention, matchMentions, mentionQuery } from "./mentions";

const TEAM = [
  { name: "Vanesa", role: "Administración" },
  { name: "Aldo", role: "Dueño" },
  { name: "Valentina", role: "Depósito" },
];

describe("mentionQuery", () => {
  it("reads a mention at the end of the text", () => {
    expect(mentionQuery("Anotá que revise @Va")).toBe("va");
  });

  it("reads a bare @ as an empty query", () => {
    expect(mentionQuery("decile a @")).toBe("");
  });

  it("reads a mention that starts the message", () => {
    expect(mentionQuery("@Al")).toBe("al");
  });

  it("ignores an email address", () => {
    expect(mentionQuery("mandale a aldo@litoral.com")).toBeNull();
  });

  it("ignores a mention the user has already finished", () => {
    expect(mentionQuery("@Vanesa que revise")).toBeNull();
  });

  it("ignores plain text", () => {
    expect(mentionQuery("hola")).toBeNull();
  });
});

describe("matchMentions", () => {
  it("filters the team by prefix", () => {
    expect(matchMentions("@Va", TEAM).map((p) => p.name)).toEqual(["Vanesa", "Valentina"]);
  });

  it("offers the whole team for a bare @", () => {
    expect(matchMentions("@", TEAM)).toHaveLength(3);
  });

  it("offers nobody when the caret is not in a mention", () => {
    expect(matchMentions("hola", TEAM)).toEqual([]);
  });

  it("is case-insensitive", () => {
    expect(matchMentions("@VANE", TEAM).map((p) => p.name)).toEqual(["Vanesa"]);
  });
});

describe("applyMention", () => {
  it("completes the mention and leaves a trailing space", () => {
    expect(applyMention("Anotá que revise @Va", "Vanesa")).toBe("Anotá que revise @Vanesa ");
  });

  it("completes a bare @", () => {
    expect(applyMention("decile a @", "Aldo")).toBe("decile a @Aldo ");
  });

  it("leaves earlier mentions alone", () => {
    expect(applyMention("@Aldo y @Va", "Vanesa")).toBe("@Aldo y @Vanesa ");
  });
});
