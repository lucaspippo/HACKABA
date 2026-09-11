import { FileText, ClipboardList, Receipt, Check } from "lucide-react";
import AngelaSays from "../components/AngelaSays";
import { useEquipo, equipoStore } from "../lib/equipoStore";
import { num } from "../lib/format";
import { useT } from "../lib/i18n";

// Vista de administración (oficina): carga, recordatorios y lo administrativo a reclamar.
// NO ve estrategia ni rentabilidad.
export default function Administracion({ data, onPreguntar }) {
  const t = useT();
  const equipo = useEquipo();
  const a = data.alertas;

  const tareas = [
    { icon: Receipt, label: t("administracion.tarea_boletas"), nota: t("administracion.tarea_boletas_nota") },
    { icon: ClipboardList, label: t("administracion.tarea_ordenes"), nota: t("administracion.tarea_ordenes_nota") },
    { icon: FileText, label: t("administracion.tarea_cierres"), nota: t("administracion.tarea_cierres_nota") },
  ];

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-2xl font-bold">{t("administracion.titulo")}</h1>
        <p className="mt-1 text-[0.9rem] text-tinta-suave">{t("administracion.subtitulo")}</p>
      </header>

      <AngelaSays>
        {t("administracion.angela")}
      </AngelaSays>

      {/* Tareas de carga */}
      <section>
        <h2 className="mb-3 font-display text-[1.1rem] font-bold">{t("administracion.lo_que_cargas")}</h2>
        <div className="space-y-2.5">
          {tareas.map((t) => {
            const Icon = t.icon;
            return (
              <div key={t.label} className="flex items-center gap-3 rounded-[var(--radius-card)] border border-linea bg-crema px-4 py-3 sombra-papel">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-papel-hondo text-tinta-suave">
                  <Icon size={17} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[0.92rem] font-semibold">{t.label}</p>
                  <p className="text-[0.78rem] text-tinta-suave">{t.nota}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* A reclamar / limpiar (alertas administrativas, no estratégicas) */}
      <section>
        <h2 className="mb-3 font-display text-[1.1rem] font-bold">{t("administracion.ordenar_sistema")}</h2>
        <div className="grid grid-cols-2 gap-3">
          <button onClick={() => onPreguntar("¿Cómo depuro los productos fantasma?")} className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 text-left">
            <p className="plata text-2xl font-medium text-oro-tinta">{num(a.fantasmas.cantidad)}</p>
            <p className="text-[0.84rem] text-tinta-suave">{t("administracion.fantasma_depurar")}</p>
          </button>
          <button onClick={() => onPreguntar("¿Qué productos están sin precio?")} className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 text-left">
            <p className="plata text-2xl font-medium text-oro-tinta">{num(a.sin_pvp.cantidad)}</p>
            <p className="text-[0.84rem] text-tinta-suave">{t("administracion.sin_precio")}</p>
          </button>
        </div>
      </section>

      {/* Recordatorios */}
      <section>
        <h2 className="mb-3 font-display text-[1.1rem] font-bold">{t("administracion.recordatorios")}</h2>
        <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema">
          {equipo.recordatorios.map((r) => (
            <button key={r.id} onClick={() => equipoStore.toggleRecordatorio(r.id)} className="flex w-full items-center gap-3 border-b border-linea px-4 py-2.5 text-left last:border-0">
              <span className={`grid h-5 w-5 shrink-0 place-items-center rounded-full border ${r.hecho ? "border-salvia bg-salvia text-crema" : "border-tinta-suave/40"}`}>
                {r.hecho && <Check size={13} />}
              </span>
              <span className={`flex-1 text-[0.88rem] ${r.hecho ? "text-tinta-suave line-through" : "text-tinta"}`}>{t(r.texto)}</span>
              <span className="shrink-0 text-[0.74rem] font-semibold text-tinta-suave">{r.responsable}</span>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
