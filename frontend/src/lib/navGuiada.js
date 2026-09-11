// Navegación guiada: cuando Ángela te lleva a algo, el elemento exacto queda
// TITILANDO hasta que lo tocás (o hasta un límite de seguridad). Un solo lugar
// para el comportamiento; el CSS vive en index.css (.nav-pulse).

// P9·D: 4,5 s (antes 3 s) para que el titileo se LEA bien en video; el que
// graba/embebe puede ajustarlo pasando duracionMs.
const LIMITE_MS = 4500;

export function resaltar(el, duracionMs = LIMITE_MS) {
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  el.classList.add("nav-pulse");

  const apagar = () => {
    el.classList.remove("nav-pulse");
    el.removeEventListener("pointerdown", apagar);
    clearTimeout(t);
  };
  const t = setTimeout(apagar, duracionMs);
  // El pulso vive hasta que el usuario interactúa con EL elemento señalado.
  el.addEventListener("pointerdown", apagar);
}

export function resaltarPorId(navId, delayMs = 360) {
  // La sección destino puede estar fetcheando sus datos cuando llega el
  // highlight: si el ancla todavía no existe, se reintenta un ratito en vez
  // de perder el pulso (P13 — las cards del Home navegan apenas montadas).
  let intentos = 0;
  let t;
  const buscar = () => {
    const el = document.querySelector(`[data-nav-id="${navId}"]`);
    if (el) return resaltar(el);
    if (++intentos < 8) t = setTimeout(buscar, 300);
  };
  t = setTimeout(buscar, delayMs);
  return () => clearTimeout(t);
}
