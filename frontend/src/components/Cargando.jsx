// Estado de carga suave (nada de pantalla vacía que parpadea): tres líneas
// de papel pulsando, estilo del sistema. También sirve de mensaje de error
// en criollo si la carga falló (e.criollo viene de lib/api).
export default function Cargando({ error = null }) {
  if (error) {
    return (
      <div className="rounded-[var(--radius-card)] border border-linea bg-papel-hondo/40 p-6 text-[0.92rem] text-tinta-suave">
        {error.criollo || "No pude traer los datos. Probá de nuevo en un toque."}
      </div>
    );
  }
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Cargando">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="h-16 animate-pulse rounded-[var(--radius-card)] border border-linea/60 bg-papel-hondo/50"
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </div>
  );
}
