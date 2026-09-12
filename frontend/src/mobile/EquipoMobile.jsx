import { Check, Clock, MessageSquare } from "lucide-react";
import AngelaSays from "../components/AngelaSays";
import { ActividadEquipo } from "../sections/GestionEquipo";
import ObjetivosPanel from "../sections/ObjetivosPanel";
import { useSession } from "../lib/auth";
import { useEquipo, equipoStore, ESTADO_LABEL } from "../lib/equipoStore";
import { useT } from "../lib/i18n";
import { useApiQuery } from "../lib/query";

// El estado de las cosas, no un chat. El dueño coordina sin llamar a nadie.
export default function EquipoMobile() {
  const t = useT();
  const equipo = useEquipo();
  const session = useSession();
  const esAdmin = !!session?.usuario?.es_admin;
  const token = session?.token;
  // P34·2.F — el dueño ve el PANEL DE GESTIÓN (lista de personas con indicadores,
  // expandible) también en el celular. Los insumos: perfiles + solicitudes.
  const { data: profilesData } = useApiQuery("perfiles", [token], { enabled: !!token && esAdmin });
  const { data: requestsData } = useApiQuery("solicitudes", [token, "pendiente"], { enabled: !!token && esAdmin });
  const perfiles = profilesData?.perfiles || [];
  const solicitudes = requestsData?.solicitudes || [];

  return (
    <div className="space-y-6 pb-4">
      <header className="pt-1">
        <h1 className="font-display text-2xl font-bold">{t("equipo.mob_titulo")}</h1>
        <p className="mt-1 text-base text-tinta-suave">
          {t("equipo.mob_sub")}
        </p>
      </header>

      {/* P36·E4 — los objetivos que Ángela mide sola (cada uno ve los suyos) */}
      <ObjetivosPanel />

      {/* P34·2.F — el panel de gestión de equipo (dueño): personas + detalle */}
      {esAdmin && session?.token && (
        <ActividadEquipo token={session.token} perfiles={perfiles} equipo={equipo} solicitudes={solicitudes} />
      )}

      {/* Objetivos activos */}
      <section>
        <h2 className="mb-3 font-display text-lg font-bold">{t("equipo.objetivos_titulo")}</h2>
        <div className="space-y-2.5">
          {equipo.objetivos.map((o) => (
            <div key={o.id} className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
              <p className="font-display text-base font-bold leading-tight">{t(o.nombre)}</p>
              <div className="mt-2.5 flex items-center justify-between">
                <span className="text-sm text-tinta-suave">
                  {o.responsable} · {t(o.fecha)}
                </span>
                <button
                  onClick={() => equipoStore.cicloEstado(o.id)}
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    o.estado === "listo"
                      ? "bg-salvia/15 text-salvia"
                      : o.estado === "en_proceso"
                      ? "bg-oro/15 text-oro-tinta"
                      : "bg-papel-hondo text-tinta-suave"
                  }`}
                >
                  {t(ESTADO_LABEL[o.estado])}
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Recordatorios */}
      <section>
        <h2 className="mb-3 font-display text-lg font-bold">{t("equipo.recordatorios_titulo")}</h2>
        <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema">
          {equipo.recordatorios.map((r) => (
            <button
              key={r.id}
              onClick={() => equipoStore.toggleRecordatorio(r.id)}
              className="flex w-full items-center gap-3 border-b border-linea px-4 py-3 text-left last:border-0"
            >
              <span
                className={`grid h-5 w-5 shrink-0 place-items-center rounded-full border ${
                  r.hecho ? "border-salvia bg-salvia text-crema" : "border-tinta-suave/40"
                }`}
              >
                {r.hecho && <Check size={13} />}
              </span>
              <span
                className={`flex-1 text-sm ${
                  r.hecho ? "text-tinta-suave line-through" : "text-tinta"
                }`}
              >
                {t(r.texto)}
              </span>
              <span className="shrink-0 text-xs font-semibold text-tinta-suave">{r.responsable}</span>
            </button>
          ))}
        </div>
        <p className="mt-2 flex items-center gap-1.5 px-1 text-sm text-tinta-suave">
          <Clock size={13} /> {t("equipo.mob_anota_tip")}
        </p>
      </section>

      {/* Novedades del equipo (placeholder WhatsApp) */}
      <section>
        <h2 className="mb-3 font-display text-lg font-bold">{t("equipo.mob_novedades_titulo")}</h2>
        <div className="rounded-[var(--radius-card)] border border-dashed border-linea bg-papel-hondo/40 p-4">
          <div className="flex items-center gap-2 text-tinta-suave">
            <MessageSquare size={16} />
            <p className="text-sm font-semibold">{t("equipo.mob_conecta_wsp")}</p>
          </div>
          <p className="mt-1.5 text-sm leading-snug text-tinta-suave">
            {t("equipo.mob_novedades_detalle")}
          </p>
        </div>
      </section>

      <AngelaSays>
        {t("equipo.mob_angela")}
      </AngelaSays>
    </div>
  );
}
