import { useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { api } from "../lib/api";
import { authStore } from "../lib/auth";
import { useT } from "../lib/i18n";

// La campanita: notificaciones internas de PolPilot (emitidas por el sistema).
// Poll suave cada 30s; al abrir se refresca. Si llega un cambio de módulos,
// refresca la sesión para que el nav muestre (o esconda) la sección al toque.
export default function Campanita({ token, esAdmin, onVerSolicitud }) {
  const t = useT();
  const [items, setItems] = useState([]);
  const [noLeidas, setNoLeidas] = useState(0);
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  const cargar = () => {
    if (!token) return;
    api.notificaciones(token).then((d) => {
      setItems(d.notificaciones || []);
      setNoLeidas(d.no_leidas || 0);
      if ((d.notificaciones || []).some((n) => !n.leida && (n.tipo === "solicitud_resuelta" || n.tipo === "modulo_cambiado"))) {
        authStore.refresh();
      }
    }).catch(() => {});
  };

  useEffect(() => {
    cargar();
    const t = setInterval(cargar, 30000);
    return () => clearInterval(t);
  }, [token]);

  useEffect(() => {
    const cerrar = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", cerrar);
    return () => document.removeEventListener("mousedown", cerrar);
  }, []);

  const clickNotif = async (n) => {
    if (!n.leida) {
      try { await api.notificacionLeida(n.id, token); } catch { /* se reintenta al recargar */ }
      cargar();
    }
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
          <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-oro px-1 text-[0.66rem] font-bold text-crema ring-2 ring-papel">
            {noLeidas}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-12 z-40 w-80 rounded-[var(--radius-card)] border border-linea bg-crema p-2 sombra-alta">
          <p className="px-2 pb-1.5 pt-1 text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-tinta-suave">
            {t("campanita.titulo")}
          </p>
          {items.length === 0 ? (
            <p className="px-2 pb-2 text-[0.86rem] text-tinta-suave">{t("campanita.vacio")}</p>
          ) : (
            <div className="max-h-80 space-y-1 overflow-y-auto">
              {items.slice(0, 12).map((n) => (
                <button
                  key={n.id}
                  onClick={() => clickNotif(n)}
                  className={`block w-full rounded-xl px-2.5 py-2 text-left transition-colors hover:bg-papel-hondo/60 ${n.leida ? "opacity-60" : ""}`}
                >
                  <p className="text-[0.85rem] font-semibold leading-tight">
                    {!n.leida && <span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-oro" />}
                    {n.titulo}
                  </p>
                  <p className="mt-0.5 text-[0.8rem] leading-snug text-tinta-suave">{n.cuerpo}</p>
                  {n.tipo === "solicitud_modulo" && esAdmin && (
                    <span className="mt-1 inline-block text-[0.78rem] font-semibold text-oro-tinta">{t("campanita.ver_solicitud")} →</span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
