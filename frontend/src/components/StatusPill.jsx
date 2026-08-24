// Estado en palabras, no en semáforos genéricos.
export default function StatusPill({ nivel, label }) {
  const map = {
    requiere_accion: { dot: "bg-rojo", text: "text-rojo-hondo", ring: "ring-rojo/20" },
    atencion: { dot: "bg-oro", text: "text-oro-tinta", ring: "ring-oro/25" },
    en_orden: { dot: "bg-salvia", text: "text-salvia", ring: "ring-salvia/20" },
  };
  const s = map[nivel] || map.atencion;
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full bg-crema px-3 py-1 text-[0.8rem] font-semibold ring-1 ${s.ring} ${s.text}`}
    >
      <span className={`h-2 w-2 rounded-full ${s.dot}`} />
      {label}
    </span>
  );
}
