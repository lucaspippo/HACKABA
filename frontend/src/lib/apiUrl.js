// The single place a PolPilot request path becomes a URL.
//
// VITE_API_BASE is empty in every current deployment: the backend serves the
// compiled bundle itself, so the API is same-origin and these paths stay
// relative. The variable exists so that serving the frontend from its own
// origin (a CDN static site) needs a build-time value here instead of an edit
// at every call site — see deploy/ARCHITECTURE.md §3.
//
// This module imports nothing on purpose: api.js already imports authStore
// from auth.js, so living in api.js would make that pair circular.
//
// Read on every call (not cached at module load): vi.stubEnv in tests
// mutates import.meta.env after this module has already been imported, and a
// module-level const would freeze the value from the first import instead of
// reflecting the stub.
export function apiUrl(path) {
  if (/^https?:\/\//.test(path)) return path;
  const base = (import.meta.env?.VITE_API_BASE ?? "").replace(/\/$/, "");
  return base ? `${base}${path}` : path;
}
