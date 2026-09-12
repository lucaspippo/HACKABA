import { useEffect, useRef, useState } from "react";
import { ChevronRight, LogOut, UserCircle } from "lucide-react";
import Avatar from "./Avatar";
import LangSwitch from "./LangSwitch";
import { authStore } from "../lib/auth";
import { useT, tRol } from "../lib/i18n";

// Menú corto con lo que de verdad es "de la cuenta" (idioma, cerrar sesión)
// y un link al perfil completo para lo que es demasiado grande para un
// dropdown (Qué hacés, Lo mío, Pedir acceso, Preferencias — ver MiPerfil.jsx).
export default function AccountMenu({ user, onVerPerfil }) {
  const t = useT();
  const [abierto, setAbierto] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!abierto) return;
    const onDown = (e) => { if (ref.current && !ref.current.contains(e.target)) setAbierto(false); };
    const onEsc = (e) => { if (e.key === "Escape") setAbierto(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onEsc);
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onEsc); };
  }, [abierto]);

  return (
    <div ref={ref} className="relative shrink-0">
      <button
        onClick={() => setAbierto((v) => !v)}
        aria-label={t("nav.cuenta")}
        className="rounded-full ring-linea transition-shadow hover:ring-2"
      >
        <Avatar persona={user} size={34} />
      </button>
      {abierto && (
        <div className="absolute right-0 top-[calc(100%+0.5rem)] z-40 w-64 overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-alta">
          <div className="flex items-center gap-3 border-b border-linea p-3">
            <Avatar persona={user} size={36} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold">{user.nombre}</p>
              <p className="truncate text-sm text-tinta-suave">{tRol(user.rol)}</p>
            </div>
          </div>
          <div className="flex items-center justify-between gap-3 border-b border-linea px-3 py-2.5">
            <span className="text-sm font-medium text-tinta-suave">{t("nav.idioma")}</span>
            <LangSwitch />
          </div>
          <button
            onClick={() => { setAbierto(false); onVerPerfil(); }}
            className="flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm font-medium text-tinta hover:bg-papel-hondo/60"
          >
            <UserCircle size={17} className="text-tinta-suave" />
            <span className="flex-1">{t("nav.ver_perfil")}</span>
            <ChevronRight size={15} className="text-tinta-suave" />
          </button>
          <button
            onClick={() => authStore.logout({ manual: true })}
            className="flex w-full items-center gap-3 border-t border-linea px-3 py-2.5 text-left text-sm font-medium text-rojo-hondo hover:bg-rojo/[0.05]"
          >
            <LogOut size={17} />
            {t("nav.salir")}
          </button>
        </div>
      )}
    </div>
  );
}
