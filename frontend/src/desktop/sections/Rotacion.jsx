import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { useT } from "../../lib/i18n";
import { AgingBars, RotationScatter } from "./InventarioViz";

export default function Rotacion({ onSelect, viz }) {
  const t = useT();
  const [local, setLocal] = useState(viz || null);

  useEffect(() => {
    if (viz) { setLocal(viz); return; }
    api.inventarioViz().then(setLocal).catch(() => setLocal({}));
  }, [viz]);

  if (!local) return <div className="skeleton h-64 w-full rounded-[var(--radius-card)]" />;

  return (
    <div className="space-y-8">
      <p className="max-w-2xl text-[0.95rem] leading-snug text-tinta-suave">{t("inventario.tab_rotacion_sub")}</p>
      <RotationScatter
        data={local.rotation}
        onSelect={(p) => onSelect?.({ codigo: p.codigo, descripcion: p.producto, inmovilizado: p.inmovilizado })}
      />
      <AgingBars data={local.aging} />
    </div>
  );
}
