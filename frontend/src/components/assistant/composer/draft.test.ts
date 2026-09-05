import { beforeEach, describe, expect, it } from "vitest";
import { clearDraft, readDraft, writeDraft } from "./draft";

function memoryStorage(): Storage {
  const map = new Map<string, string>();
  return {
    get length() { return map.size; },
    clear: () => map.clear(),
    getItem: (k: string) => map.get(k) ?? null,
    key: (i: number) => [...map.keys()][i] ?? null,
    removeItem: (k: string) => { map.delete(k); },
    setItem: (k: string, v: string) => { map.set(k, v); },
  };
}

function throwingStorage(): Storage {
  const fail = () => { throw new Error("storage disabled"); };
  return {
    get length(): number { return fail(); },
    clear: fail, getItem: fail, key: fail, removeItem: fail, setItem: fail,
  } as unknown as Storage;
}

let storage: Storage;
beforeEach(() => { storage = memoryStorage(); });

describe("draft persistence", () => {
  it("round-trips a draft for its thread", () => {
    writeDraft("t1", "media consulta", storage, 1000);
    expect(readDraft("t1", storage)).toEqual({ text: "media consulta", savedAt: 1000 });
  });

  it("keeps drafts of different threads apart", () => {
    writeDraft("t1", "uno", storage);
    writeDraft("t2", "dos", storage);
    expect(readDraft("t1", storage)?.text).toBe("uno");
    expect(readDraft("t2", storage)?.text).toBe("dos");
  });

  it("treats blank text as no draft", () => {
    writeDraft("t1", "   ", storage);
    expect(readDraft("t1", storage)).toBeNull();
  });

  it("erases the stored draft when the text is cleared", () => {
    writeDraft("t1", "algo", storage);
    writeDraft("t1", "", storage);
    expect(readDraft("t1", storage)).toBeNull();
  });

  it("clears on demand", () => {
    writeDraft("t1", "algo", storage);
    clearDraft("t1", storage);
    expect(readDraft("t1", storage)).toBeNull();
  });

  it("returns null for corrupt JSON rather than throwing", () => {
    storage.setItem("polpilot.angela.draft.t1", "{not json");
    expect(readDraft("t1", storage)).toBeNull();
  });

  it("survives storage being disabled", () => {
    const dead = throwingStorage();
    expect(() => writeDraft("t1", "algo", dead)).not.toThrow();
    expect(readDraft("t1", dead)).toBeNull();
    expect(() => clearDraft("t1", dead)).not.toThrow();
  });
});
