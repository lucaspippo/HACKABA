// The product's "today": frozen in the demo tenant, real calendar otherwise.
// Date-range presets must use this, not the browser clock, or July demo data
// disappears the moment someone opens the app in August.

import { queryClient } from "./query/client";
import { queries } from "./query/queries";

let _hoy = null;

function localIso(d = new Date()) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function isoHoy() {
  return _hoy || localIso();
}

export function ensureHoy() {
  return queryClient.ensureQueryData(queries.health())
    .then((h) => {
      if (h?.hoy) _hoy = h.hoy;
      return isoHoy();
    })
    .catch(() => isoHoy());
}

export function parseIso(iso) {
  if (!iso) return null;
  const [y, m, d] = String(iso).slice(0, 10).split("-").map(Number);
  if (!y || !m || !d) return null;
  return new Date(y, m - 1, d);
}

export function toIso(d) {
  if (!d || Number.isNaN(d.getTime())) return "";
  return localIso(d);
}

export function addDays(d, n) {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
  return x;
}
