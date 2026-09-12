import { describe, expect, it } from "vitest";
import { RATES, formatElapsed, nextRate, splitWords, wordIndexAt } from "./readAloud";

const TEXT = "Tenés cuatro clientes en mora";

describe("splitWords", () => {
  it("splits on whitespace and drops the gaps", () => {
    expect(splitWords(TEXT)).toEqual(["Tenés", "cuatro", "clientes", "en", "mora"]);
  });

  it("survives newlines and repeated spaces", () => {
    expect(splitWords("uno  dos\n\ntres")).toEqual(["uno", "dos", "tres"]);
  });

  it("returns nothing for blank text", () => {
    expect(splitWords("   ")).toEqual([]);
  });
});

describe("wordIndexAt", () => {
  it("starts on the first word", () => {
    expect(wordIndexAt(TEXT, 0)).toBe(0);
  });

  it("reports the word the offset falls inside", () => {
    expect(wordIndexAt(TEXT, TEXT.indexOf("clientes"))).toBe(2);
  });

  it("reports the last word for an offset at the end", () => {
    expect(wordIndexAt(TEXT, TEXT.indexOf("mora"))).toBe(4);
  });

  it("does not run past the last word", () => {
    expect(wordIndexAt(TEXT, TEXT.length)).toBe(4);
  });

  it("treats a negative offset as the start", () => {
    expect(wordIndexAt(TEXT, -5)).toBe(0);
  });
});

describe("nextRate", () => {
  it("cycles through the offered rates and wraps", () => {
    let rate: number = RATES[0];
    const seen: number[] = [rate];
    for (let i = 0; i < RATES.length - 1; i++) {
      rate = nextRate(rate);
      seen.push(rate);
    }
    expect(new Set(seen).size).toBe(RATES.length);
    expect(nextRate(rate)).toBe(RATES[0]);
  });

  it("recovers from a rate that is not in the list", () => {
    expect(nextRate(3)).toBe(RATES[0]);
  });
});

describe("formatElapsed", () => {
  it("pads the seconds", () => {
    expect(formatElapsed(5000)).toBe("0:05");
  });

  it("rolls over into minutes", () => {
    expect(formatElapsed(65000)).toBe("1:05");
  });

  it("never shows a negative time", () => {
    expect(formatElapsed(-1)).toBe("0:00");
  });
});
