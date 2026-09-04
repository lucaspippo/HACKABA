// The single place a PolPilot request path becomes a URL. VITE_API_BASE is
// empty in every current deployment (the backend serves the bundle, so the
// API is same-origin) — see deploy/ARCHITECTURE.md §3 for what it is for.
//
// Two things here resist tidying:
//   - this module imports nothing, because api.js already imports authStore
//     from auth.js — moving apiUrl into api.js would make that pair circular;
//   - the env is read per call, not into a module-level const, because
//     vi.stubEnv mutates import.meta.env after import and a const would
//     freeze the pre-stub value.
export function apiUrl(path) {
  if (/^https?:\/\//.test(path)) return path;
  const base = (import.meta.env?.VITE_API_BASE ?? "").replace(/\/$/, "");
  return base ? `${base}${path}` : path;
}
