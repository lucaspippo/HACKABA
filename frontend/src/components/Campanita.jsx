import { useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { authStore } from "../lib/auth";
import { useT } from "../lib/i18n";
import { useApiMutation, useApiQuery } from "../lib/query";

// Shared poll for the desktop bell and the mobile Más sheet. Soft 30s
// refresh; a module-change notice also refreshes the session so the nav
// shows (or hides) the section immediately.
export function useNotificaciones(token) {
  const q = useApiQuery("notificaciones", [token], {
    enabled: !!token,
    refetchInterval: 30_000,
  });
  const marcar = useApiMutation("notificacionLeida");

  const items = q.data?.notificaciones || [];
  const noLeidas = q.data?.no_leidas || 0;

  useEffect(() => {
    if (items.some((n) => !n.leida && (n.tipo === "solicitud_resuelta" || n.tipo === "modulo_cambiado"))) {
      authStore.refresh();
    }
  }, [items]);

  const cargar = () => { q.refetch(); };

  const marcarLeida = async (n) => {
    if (!n.leida) {
      try { await marcar.mutateAsync([n.id, token]); } catch { /* retry on reload */ }
    }
  };

  return { items, noLeidas, cargar, marcarLeida };
}

export function NotificacionesLista({ items, esAdmin, onPick }) {
  const t = useT();
  if (items.length === 0) {
    return <p className="px-2 py-1 text-sm text-tinta-suave">{t("campanita.vacio")}</p>;
  }
  return (
    <div className="max-h-80 space-y-1 overflow-y-auto">
      {items.slice(0, 12).map((n) => (
        <button
          key={n.id}
          onClick={() => onPick(n)}
          className={`block w-full rounded-xl px-2.5 py-2 text-left transition-colors hover:bg-papel-hondo/60 ${n.leida ? "opacity-60" : ""}`}
        >
          <p className="text-sm font-semibold leading-tight">
            {!n.leida && <span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-oro" />}
            {n.titulo}
          </p>
          <p className="mt-0.5 text-sm leading-snug text-tinta-suave">{n.cuerpo}</p>
          {n.tipo === "solicitud_modulo" && esAdmin && (
            <span className="mt-1 inline-block text-xs font-semibold text-oro-tinta">{t("campanita.ver_solicitud")} →</span>
          )}
        </button>
      ))}
    </div>
  );
}

// Desktop header bell. Mobile mounts the list inside MasSheet instead —
// a popover anchored to a vanished topbar has nowhere to open.
export default function Campanita({ token, esAdmin, onVerSolicitud }) {
  const t = useT();
  const { items, noLeidas, cargar, marcarLeida } = useNotificaciones(token);
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const cerrar = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", cerrar);
    return () => document.removeEventListener("mousedown", cerrar);
  }, []);

  const clickNotif = async (n) => {
    await marcarLeida(n);
    if (n.tipo === "solicitud_modulo" && esAdmin) {
      setOpen(false);
      onVerSolicitud?.();
    }
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => { setOpen((v) => !v); if (!open) cargar(); }}
        className="relative grid h-10 w-10 place-items-center rounded-full border border-linea bg-crema text-tinta-suave hover:text-tinta"
      >
        <Bell size={18} />
        {noLeidas > 0 && (
          <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-oro px-1 text-2xs font-bold text-crema ring-2 ring-papel">
            {noLeidas}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-12 z-40 w-80 rounded-[var(--radius-card)] border border-linea bg-crema p-2 sombra-alta">
          <p className="px-2 pb-1.5 pt-1 text-xs font-semibold uppercase tracking-[0.14em] text-tinta-suave">
            {t("campanita.titulo")}
          </p>
          <NotificacionesLista items={items} esAdmin={esAdmin} onPick={clickNotif} />
        </div>
      )}
    </div>
  );
}
