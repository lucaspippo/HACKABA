import { useApiQuery } from "../../lib/query";
import { useT } from "../../lib/i18n";
import { AgingBars, RotationScatter } from "./InventarioViz";

export default function Rotacion({ onSelect, viz }) {
  const t = useT();
  const { data: fetched, isError } = useApiQuery("inventarioViz", [], { enabled: !viz });
  const local = viz || (isError ? {} : fetched);

  if (!local) return <div className="skeleton h-64 w-full rounded-[var(--radius-card)]" />;

  return (
    <div className="space-y-8">
      <p className="max-w-2xl text-base leading-snug text-tinta-suave">{t("inventario.tab_rotacion_sub")}</p>
      <RotationScatter
        data={local.rotation}
        onSelect={(p) => onSelect?.({ codigo: p.codigo, descripcion: p.producto, inmovilizado: p.inmovilizado })}
      />
      <AgingBars data={local.aging} />
    </div>
  );
}
