import { useEffect, useState } from "react";
import { Eye, Undo2, Smartphone } from "lucide-react";
import Avatar from "./Avatar";
import BadgeNuevo from "./BadgeNuevo";
import { api } from "../lib/api";
import { authStore, useSession } from "../lib/auth";
import { equipoReal } from "../lib/equipoReal";
import { toast } from "../lib/toastStore";
import { useT, tRol } from "../lib/i18n";
import { useEmpresa } from "../lib/useEmpresa";
import { useIsDesktop } from "../lib/useViewport";

// "View as / Ver como" — SOLO TENANT DEMO (P9·E). Los reviewers de YC ven el
// producto desde los ojos de CADA empleado sin pelear con logins. El switch
// emite una sesión LEGÍTIMA server-side (feature flag POLPILOT_DEMO_ROLE_SWITCH);
// en el piloto ni el botón ni el endpoint existen.

export async function cambiarA(username, t) {
  try {
    const s = await api.verComo(username);
    authStore.adoptar(s);
    toast(t("vercomo.ahora", { nombre: s.usuario.nombre }));
  } catch {
    toast(t("vercomo.error"), "error");
  }
}

export async function volverAlDueno(t) {
  try {
    const eq = await equipoReal();
    const dueno = eq.find((p) => p.rol === "Dueño");
    if (dueno) await cambiarA(dueno.username, t);
  } catch {
    toast(t("vercomo.error"), "error");
  }
}

/** Card del perfil: la lista completa del equipo para mirar como cualquiera. */
export function VerComoSelector() {
  const t = useT();
  const session = useSession();
  const { roleSwitch } = useEmpresa();
  const isDesktop = useIsDesktop();
  const [equipo, setEquipo] = useState([]);

  useEffect(() => {
    if (!roleSwitch) return;
    equipoReal().then(setEquipo).catch(() => {});
  }, [roleSwitch]);

  // P39·1.1 — la nómina es UNA sola: acá están TODOS, los mismos que en "Lo que
  // pasó con tu equipo" y en "Quién ve qué" (antes desktop filtraba por
  // `superficies` y mostraba 7 contra 13 — la misma empresa con tres listas
  // distintas). Los roles de piso siguen siendo de celular: eso ahora se DICE
  // con un ícono, no se resuelve escondiendo a la persona.
  const visibles = equipo;

  if (!roleSwitch || !visibles.length) return null;
  const actual = session?.usuario?.username;

  return (
    <section>
      <h2 className="mb-1 flex items-center gap-2 font-display text-[1.1rem] font-bold">
        <Eye size={17} className="text-hielo" /> {t("vercomo.titulo")}
      </h2>
      <p className="mb-3 text-[0.84rem] leading-snug text-tinta-suave">{t("vercomo.sub")}</p>
      <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema">
        {visibles.map((p) => (
          <button
            key={p.username}
            disabled={p.username === actual}
            onClick={() => cambiarA(p.username, t)}
            className={`flex w-full items-center gap-3 border-b border-linea px-4 py-2.5 text-left last:border-0 ${
              p.username === actual ? "bg-hielo/[0.06]" : "hover:bg-papel-hondo/50"
            }`}
          >
            <Avatar persona={p} size={32} />
            <span className="min-w-0 flex-1">
              {/* P·onboarding — el que recién entró se distingue de los que
                  llevan años. El chip sale de su antigüedad real (el endpoint
                  la manda con cada persona), no de una lista aparte. */}
              <span className="flex items-center gap-1.5">
                <span className="truncate text-[0.9rem] font-semibold text-tinta">{p.nombre}</span>
                <BadgeNuevo persona={p} compacto />
              </span>
              <span className="block text-[0.74rem] text-tinta-suave">{tRol(p.rol)}</span>
            </span>
            {/* La superficie de cada uno se DICE (el de piso trabaja del celular),
                en vez de sacarlo de la lista — P39·1.1 */}
            {isDesktop && !(p.superficies || []).includes("desktop") && (
              <span title={t("vercomo.solo_mobile")}
                className="hidden shrink-0 items-center gap-1 rounded-full bg-papel-hondo px-2 py-0.5 text-[0.68rem] font-semibold text-tinta-suave sm:inline-flex">
                <Smartphone size={11} /> {t("vercomo.solo_mobile")}
              </span>
            )}
            {p.username === actual ? (
              <span className="shrink-0 text-[0.74rem] font-semibold text-hielo">{t("vercomo.actual")}</span>
            ) : (
              <span className="shrink-0 text-[0.78rem] font-semibold text-tinta">{t("vercomo.mirar")}</span>
            )}
          </button>
        ))}
      </div>
    </section>
  );
}

/** Chip del header: con quién estás mirando + volver al dueño en UN click. */
export function VerComoChip() {
  const t = useT();
  const session = useSession();
  const { roleSwitch } = useEmpresa();
  const u = session?.usuario;
  if (!roleSwitch || !u || u.rol === "Dueño") return null;
  return (
    <div className="flex shrink-0 items-center gap-2 rounded-full border border-hielo/30 bg-hielo/[0.07] py-1 pl-3 pr-1">
      <Eye size={13} className="shrink-0 text-hielo" />
      <span className="max-w-[180px] truncate text-[0.76rem] font-semibold text-hielo">
        {t("vercomo.chip", { nombre: u.nombre, rol: tRol(u.rol) })}
      </span>
      <button
        onClick={() => volverAlDueno(t)}
        className="flex shrink-0 items-center gap-1 rounded-full bg-hielo px-2.5 py-1 text-[0.72rem] font-semibold text-crema"
      >
        <Undo2 size={11} /> {t("vercomo.volver")}
      </button>
    </div>
  );
}
