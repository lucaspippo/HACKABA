// El equipo REAL del tenant, desde el backend (P9·C2, M3): para asignar
// responsables de verdad — sin nombres hardcodeados cross-tenant.
import { api } from "./api";

let _cache = null;

export async function equipoReal() {
  if (_cache) return _cache;
  const r = await api.equipoNombres();
  _cache = r.equipo || [];
  return _cache;
}

/** A quién delegarle una verificación operativa: alguien de administración si
 * hay, si no el primer empleado que no sea el dueño, si no el dueño mismo. */
export async function responsableVerificacion() {
  const eq = await equipoReal();
  const admin = eq.find((p) => /administra/i.test(p.rol));
  const otro = eq.find((p) => p.rol !== "Dueño");
  return (admin || otro || eq[0])?.nombre || "";
}
