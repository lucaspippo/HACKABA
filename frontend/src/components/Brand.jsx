// Cabecera de marca: PolPilot (el producto) "para" el cliente del tenant.
// Cada tenant con logo cargado lo muestra (piloto y demo); cualquier otro,
// marca de texto — nunca el logo de un cliente que no corresponde.
import { useEmpresa } from "../lib/useEmpresa";
import { useT } from "../lib/i18n";

export default function Brand({ variant = "desktop" }) {
  const t = useT();
  // P37 — el logo del cliente lo decide el BACKEND por tenant (meta.logo); el
  // frontend NO conoce ningún cliente. Hasta que health resuelve, `logo` y
  // `empresa` son null → no se pinta nada (skeleton), nunca un default del piloto.
  const { empresa, logo, resuelto } = useEmpresa();

  // P35·E1 — Header mobile: sin la palabra "FOR" (comía espacio), logo del
  // cliente MÁS GRANDE y sin deformar (object-contain respeta el aspect-ratio),
  // en una sola fila. El toggle EN/ES ya no vive acá: el idioma se hereda de la
  // sesión (POLPILOT_DEFAULT_LANG / preferencia del usuario), no se fija.
  if (variant === "mobile") {
    // P37·AJUSTE 2 — En mobile, Brand renderiza SOLO el logo del CLIENTE (la
    // columna central del header). PolPilot y los iconos son las columnas
    // laterales del grid en MobileApp; con columnas laterales de igual peso
    // (1fr auto 1fr) este logo queda CENTRADO en el viewport, sobre el mismo
    // eje que el botón de Ángela de la barra inferior. Caja h-9 + object-contain.
    return !resuelto ? (
      <span className="h-7 w-24 animate-pulse rounded bg-papel-hondo" />
    ) : logo ? (
      <span className="flex h-9 max-w-[9.5rem] items-center justify-center">
        <img
          src={logo}
          alt={empresa || ""}
          className="max-h-full w-auto select-none object-contain"
          draggable="false"
        />
      </span>
    ) : (
      <span className="truncate font-display text-[0.95rem] font-bold leading-tight text-hielo">
        {empresa}
      </span>
    );
  }

  return (
    <div className="flex items-center justify-between gap-3">
      <img
        src="/logos/polpilot.png"
        alt="PolPilot"
        className="h-7 w-auto select-none"
        draggable="false"
      />
      <div className="flex items-center gap-2">
        <span className="text-[0.66rem] font-semibold uppercase tracking-[0.14em] text-tinta-suave">
          {t("brand.para")}
        </span>
        {!resuelto ? (
          <span className="h-7 w-28 animate-pulse rounded bg-papel-hondo" />
        ) : logo ? (
          <img
            src={logo}
            alt={empresa || ""}
            className="h-9 w-auto select-none"
            draggable="false"
          />
        ) : (
          <span className="font-display text-[0.95rem] font-bold leading-tight text-hielo">
            {empresa}
          </span>
        )}
      </div>
    </div>
  );
}
