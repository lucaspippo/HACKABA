import { useEffect, useState } from "react";
import { Tag, ArrowRight, Loader2 } from "lucide-react";
import { peso, num } from "../lib/format";
import { api } from "../lib/api";
import { useT, useLang } from "../lib/i18n";

// EL COSTO VIEJO, DONDE ALGUIEN PUEDE HACER ALGO.
//
// El dato ya existía: `quality.py` marca los costos de más de un año y son una
// de las categorías del libro triado del dueño. Lo que faltaba era el lugar. El
// jamón cocido de balanza tiene el costo cargado hace 535 días y su precio de
// venta salió de ahí; quien mira ese precio todos los días es la que está en el
// mostrador, no el dueño en un análisis de escritorio.
//
// No hay total (PRODUCT.md, The Counting Rule): el costo viejo no dice cuánto
// se pierde, dice que no se sabe cuánto se gana. Sumarlo daría un número que
// parece plata en juego y no lo es.

export default function CostoViejo({ onAvisar }) {
  const t = useT();
  const lang = useLang();
  const [d, setD] = useState(null);

  useEffect(() => {
    api.mostradorCostosViejos().then(setD).catch(() => setD({ items: [] }));
  }, [lang]);

  if (!d) return <div className="py-6 text-center"><Loader2 size={16} className="mx-auto animate-spin text-tinta-suave" /></div>;
  if (!d.items?.length) return null;   // sin costos viejos, la sección no existe

  return (
    <section>
      <h2 className="mb-2 font-display text-lg font-bold">{t("costo.titulo")}</h2>
      <div className="overflow-hidden rounded-[var(--radius-card)] border border-oro/30 bg-oro/[0.05] sombra-papel">
        <p className="border-b border-oro/20 px-4 py-2.5 text-xs leading-snug text-tinta-suave">
          {t("costo.explica", { dias: num(d.umbral_dias) })}
        </p>
        {d.items.map((x) => (
          <div key={x.codigo} className="border-b border-oro/20 px-4 py-3 last:border-0">
            <p className="text-sm font-semibold leading-snug text-tinta">{x.producto}</p>
            <p className="mt-0.5 text-sm text-tinta-suave">
              {t("costo.hace_dias", { dias: num(x.dias) })}
            </p>
            {/* Los dos números, uno al lado del otro. El de la casa puede venir
                por duplicado: la fiambrería se vende feteada (80%) y en pieza
                entera (30%), y elegir uno sería decidir por ella cuál es. */}
            <p className="mt-1 text-xs leading-snug text-tinta-suave">
              {t("costo.precio_hoy", { pvp: peso(x.pvp) })}
              {x.recargo_actual_pct != null && (
                <> · {t("costo.recargo_actual", { pct: num(x.recargo_actual_pct) })}</>
              )}
            </p>
            {x.grupos?.length > 0 && (
              <p className="mt-0.5 text-xs leading-snug text-tinta-suave">
                {t("costo.recargo_casa")}{" "}
                {x.grupos.map((g, i) => (
                  <span key={g.id}>
                    {i > 0 && " · "}
                    {g.presentacion ? `${g.presentacion}: ` : ""}
                    {num(g.recargo_esperado_pct)}%
                  </span>
                ))}
              </p>
            )}
            <button onClick={() => onAvisar?.(x)}
              className="mt-2 inline-flex min-h-11 items-center gap-1.5 rounded-full border border-tinta/25 bg-crema px-4 py-2 text-sm font-semibold text-tinta active:scale-95">
              <Tag size={14} /> {t("costo.avisar")} <ArrowRight size={14} />
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
