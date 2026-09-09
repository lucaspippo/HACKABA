import { FileText, HandCoins, ClipboardList, Tag, Camera, TriangleAlert,
         ListChecks, Truck, PackageCheck, ShieldCheck, Boxes, Wallet, PackagePlus,
         PackageX, Scale, BookOpen, ClipboardCheck, Waypoints } from "lucide-react";
import { accionesDe } from "../lib/roles";
import { useT } from "../lib/i18n";

// ACCIONES RÁPIDAS — la fila de cuadraditos de la imagen de referencia.
//
// Misma composición: encabezado con «Ver todas» a la derecha, y debajo una fila
// de cuadrados con el ícono adentro y el rótulo abajo. Lo que cambia es QUÉ hay
// adentro: las acciones del OFICIO de esta persona, no las nueve iguales para
// todos. Nadie del depósito cobra y Walter no levanta pedidos.
//
// ÁNGELA NO ESTÁ ACÁ. Vive en la barra, y ponerla también en esta fila la
// convierte en una acción más entre ocho cuando es la que las contiene a todas.
//
// EL COLOR. La imagen pinta cada cuadradito de un pastel distinto —azul, verde,
// naranja, rojo, violeta— y eso es color decorativo: el celeste del escáner no
// significa nada distinto del verde de la cámara. DESIGN.md lo prohíbe dos
// veces (One Meaning Rule: cada color semántico tiene UN significado y sólo uno;
// y el azul es exclusivamente de Ángela). Así que la composición se copia entera
// y el relleno va en `papel-hondo` con el ícono en `tinta`: el ritmo visual de
// la fila lo dan la forma y el espaciado, que es de donde venía de verdad, y no
// hay ningún color diciendo algo que no es.

const ICONO = { FileText, HandCoins, ClipboardList, Tag, Camera, TriangleAlert,
                ListChecks, Truck, PackageCheck, ShieldCheck, Boxes, Wallet,
                PackagePlus, PackageX, Scale, BookOpen, ClipboardCheck, Waypoints };

// Cuántas entran antes de que el rótulo se corte. Cuatro en 375px con holgura.
const VISIBLES = 4;

export default function AccionesRapidas({ user, onAccion, onVerTodas }) {
  const t = useT();
  const acciones = accionesDe(user);
  if (acciones.length === 0) return null;

  const visibles = acciones.slice(0, VISIBLES);

  return (
    <section className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 className="font-display text-base font-bold">{t("acc.titulo")}</h2>
        {/* «Ver todas» sólo cuando hay a dónde ir: para el piso es su hoja de
            carga, que tiene el resto. El dueño no tiene una pantalla con todas
            sus acciones, así que no se le ofrece un link que no lleva a nada. */}
        {onVerTodas && (
          <button onClick={onVerTodas} className="text-sm font-semibold text-tinta-suave">
            {t("acc.ver_todas")}
          </button>
        )}
      </div>

      <div className="grid grid-cols-4 gap-2">
        {visibles.map((a) => {
          const Icon = ICONO[a.icon] || ClipboardList;
          return (
            <button key={a.id} onClick={() => onAccion?.(a)}
              className="flex flex-col items-center gap-1.5 active:scale-95">
              <span className="grid h-14 w-14 place-items-center rounded-2xl bg-papel-hondo text-tinta">
                <Icon size={22} strokeWidth={1.9} />
              </span>
              <span className="line-clamp-2 text-center text-2xs font-semibold leading-tight text-tinta-suave">
                {t(`rol.acc_${a.id}`)}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
