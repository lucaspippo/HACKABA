import { useEffect } from "react";
import { ChevronRight, LogOut, Search, UserCircle, X } from "lucide-react";
import Avatar from "../components/Avatar";
import LangSwitch from "../components/LangSwitch";
import { NotificacionesLista } from "../components/Campanita";
import { authStore } from "../lib/auth";
import { useT, tRol } from "../lib/i18n";

// Account sheet for mobile: everything the old topbar held (search, inbox,
// profile, language, sign-out) without a second strip of chrome. Opens from
// the avatar on the bottom bar — thumb zone, not a fifth destination.
export default function MasSheet({
  user,
  conBuscar,
  items,
  esAdmin,
  onCerrar,
  onBuscar,
  onVerPerfil,
  onVerSolicitud,
  onPickNotif,
}) {
  const t = useT();

  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onCerrar(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCerrar]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-tinta/40"
      onClick={onCerrar}
    >
      <div
        id="mas-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="mas-titulo"
        onClick={(e) => e.stopPropagation()}
        className="max-h-[88vh] w-full max-w-md overflow-y-auto rounded-t-[var(--radius-card)] border border-linea bg-crema px-5 pt-4 pb-[max(1.25rem,env(safe-area-inset-bottom))] sombra-alta"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <Avatar persona={user} size={44} />
            <div className="min-w-0">
              <h2 id="mas-titulo" className="truncate font-display text-xl font-bold leading-tight">
                {user.nombre}
              </h2>
              <p className="truncate text-sm text-tinta-suave">{tRol(user.rol)}</p>
            </div>
          </div>
          <button onClick={onCerrar} aria-label={t("common.cerrar")} className="text-tinta-suave hover:text-tinta">
            <X size={20} />
          </button>
        </div>

        <div className="mt-4 space-y-1">
          {conBuscar && (
            <Fila icon={Search} label={t("buscar.titulo")} onClick={onBuscar} />
          )}
          <Fila icon={UserCircle} label={t("nav.ver_perfil")} onClick={onVerPerfil} />
          <div className="flex items-center justify-between gap-3 rounded-xl px-3 py-2.5">
            <span className="text-sm font-medium text-tinta">{t("nav.idioma")}</span>
            <LangSwitch />
          </div>
        </div>

        <section className="mt-5">
          <h3 className="font-display text-lg font-bold">{t("campanita.titulo")}</h3>
          <div className="mt-2">
            <NotificacionesLista
              items={items}
              esAdmin={esAdmin}
              onPick={(n) => {
                onPickNotif(n);
                if (n.tipo === "solicitud_modulo" && esAdmin) onVerSolicitud?.();
              }}
            />
          </div>
        </section>

        <button
          onClick={() => authStore.logout({ manual: true })}
          className="mt-5 flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium text-rojo-hondo hover:bg-rojo/[0.05]"
        >
          <LogOut size={17} />
          {t("nav.salir")}
        </button>
      </div>
    </div>
  );
}

function Fila({ icon: Icon, label, onClick }) {
  return (
    <button
      onClick={onClick}
      className="flex min-h-11 w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium text-tinta hover:bg-papel-hondo/60"
    >
      <Icon size={17} className="text-tinta-suave" />
      <span className="flex-1">{label}</span>
      <ChevronRight size={15} className="text-tinta-suave" />
    </button>
  );
}
