// Node's own global `localStorage` (stable since Node 22) throws unless
// --localstorage-file points at a writable path, which breaks any test that
// transitively imports modules touching it (api.js -> auth.js/i18n.js) at
// module load time. Tests run in Vitest's "node" environment, not a browser,
// so provide a plain in-memory stand-in instead of wiring a real file.
class MemoryStorage {
  #store = new Map();
  getItem(key) {
    return this.#store.has(key) ? this.#store.get(key) : null;
  }
  setItem(key, value) {
    this.#store.set(key, String(value));
  }
  removeItem(key) {
    this.#store.delete(key);
  }
  clear() {
    this.#store.clear();
  }
}

globalThis.localStorage = new MemoryStorage();
