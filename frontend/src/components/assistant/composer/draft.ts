export type Draft = { text: string; savedAt: number };

const PREFIX = "polpilot.angela.draft.";

function key(threadId: string) {
  return `${PREFIX}${threadId}`;
}

export function readDraft(threadId: string, storage: Storage): Draft | null {
  try {
    const raw = storage.getItem(key(threadId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<Draft>;
    if (typeof parsed.text !== "string" || !parsed.text.trim()) return null;
    return { text: parsed.text, savedAt: typeof parsed.savedAt === "number" ? parsed.savedAt : 0 };
  } catch {
    return null;
  }
}

export function writeDraft(threadId: string, text: string, storage: Storage, now = Date.now()) {
  try {
    if (!text.trim()) storage.removeItem(key(threadId));
    else storage.setItem(key(threadId), JSON.stringify({ text, savedAt: now }));
  } catch {
    // Storage full or disabled: a lost draft must never break the composer.
  }
}

export function clearDraft(threadId: string, storage: Storage) {
  try {
    storage.removeItem(key(threadId));
  } catch {
    // Same as above.
  }
}
