import { useState } from "react";
import { Check, Loader2, Eye, CircleDot, Sparkles } from "lucide-react";
import { toast } from "../lib/toastStore";
import { useT } from "../lib/i18n";
import { useApiMutation, useApiQuery } from "../lib/query";

// P·círculo — LO QUE PASÓ CON LO QUE DIJE.
//
// La mitad que faltaba. El backend guardaba el reporte, el dueño lo resolvía, y
// el que lo había cargado no se enteraba nunca: `api.piso.reportes` existía y no
// lo llamaba ninguna pantalla. Ocho cajas rotas se reclamaban, se cobraban, y el
// que las vio volvía al grupo de WhatsApp, donde por lo menos alguien contesta.
//
// Tres bloques, y cada uno responde una pregunta distinta que esta persona sí se
// hace. Ninguno es un tablero: no hay plata de la empresa acá, ni hallazgos de
// otros. Cada uno ve su tramo y el resultado de lo que originó.
//
//   1. LO QUE TE MANDARON  — lo único accionable, y por eso va primero.
//   2. TU AVISO SIRVIÓ     — el hallazgo que se armó con algo que dijiste.
//   3. LO QUE REPORTASTE   — con su estado real, no con un tilde decorativo.
//
// El bloque desaparece cuando no hay nada: una sección vacía todos los días
// enseña a ignorarla.

const PUNTO = { nuevo: "bg-oro", visto: "bg-violeta", resuelto: "bg-salvia" };

function Estado({ r, t }) {
  // El estado se dice con palabras y con color, nunca sólo con color: estas
  // pantallas se miran al sol.
  const clave = r.estado === "resuelto" ? "resuelto" : r.visto ? "visto" : "enviado";
  return (
    <span className="mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-xs text-tinta-suave">
      <span className={`h-2 w-2 shrink-0 rounded-full ${PUNTO[r.estado] || "bg-linea"}`} />
      {/* `<campo>_nombre` es el nombre de pantalla que resuelve el backend
          (mis_avisos._con_nombres); el username es el fallback y no debería
          verse nunca — «celeste lo cerró» en minúscula era eso. */}
      {clave === "resuelto"
        ? t("circulo.est_resuelto", { quien: r.resuelto_por_nombre || r.resuelto_por || "" })
        : clave === "visto"
          ? t("circulo.est_visto", { quien: r.visto_por_nombre || r.visto_por || "" })
          : t("circulo.est_enviado", { quien: r.destinatario_nombre || r.destinatario || "" })}
    </span>
  );
}

function titulo(r, t) {
  const d = r.datos || {};
  if (d.producto) return t("circulo.item_producto", { producto: d.producto, n: d.cantidad ?? d.contado ?? "" });
  if (d.cliente) return d.cliente;
  return t(`rol.reporte_t_${r.tipo}`);
}

export default function LoQueReporte({ onCambio }) {
  const t = useT();
  const { data: d } = useApiQuery("pisoMios");
  const resolveReport = useApiMutation("pisoResolver");
  const markSeen = useApiMutation("pisoVisto");
  const [cerrando, setCerrando] = useState(null);

  if (!d) return null;
  const mandados = d.me_mandaron || [];
  const mios = d.reporte || [];
  const sirvio = d.sirvio_para || [];
  if (!mandados.length && !mios.length && !sirvio.length) return null;

  const cerrar = async (r) => {
    setCerrando(r.id);
    try {
      await resolveReport.mutateAsync([r.id]);
      toast(t("circulo.cerrado_ok"));
      onCambio?.();
    } catch {
      toast(t("circulo.cerrado_error"), "error");
    }
    setCerrando(null);
  };

  const abrir = async (r) => {
    if (r.visto) return;
    try { await markSeen.mutateAsync([r.id]); } catch { /* el acuse no molesta */ }
  };

  return (
    <>
      {/* 1 · lo que está esperando por mí */}
      {mandados.length > 0 && (
        <section>
          <h2 className="mb-2 font-display text-lg font-bold">{t("circulo.me_mandaron")}</h2>
          <div className="overflow-hidden rounded-[var(--radius-card)] border border-oro/30 bg-oro/[0.05] px-3 sombra-papel">
            {mandados.map((r) => (
              <div key={r.id} className="border-b border-linea/70 py-3 last:border-0">
                <button onClick={() => abrir(r)} className="w-full text-left">
                  <p className="text-sm font-semibold leading-snug text-tinta">{titulo(r, t)}</p>
                  <p className="text-xs text-tinta-suave">
                    {t("circulo.de_quien", { quien: r.actor_nombre || r.actor })} · {t(`rol.reporte_t_${r.tipo}`)}
                  </p>
                </button>
                {r.estado !== "resuelto" && (
                  <button onClick={() => cerrar(r)} disabled={cerrando === r.id}
                    className="mt-2 inline-flex min-h-11 items-center gap-1.5 rounded-full bg-tinta px-4 py-2 text-sm font-semibold text-crema active:scale-95 disabled:opacity-50">
                    {cerrando === r.id ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                    {t("circulo.cerrar")}
                  </button>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 2 · tu aviso en el mapa, sin el lienzo: qué dijiste, con qué se cruzó,
             qué salió. El mapa de escritorio es una herramienta de exploración
             y explorar no es lo que hace alguien con guantes; lo que sí le
             sirve es ver que lo suyo se usó. */}
      {sirvio.length > 0 && (
        <section>
          <h2 className="mb-2 font-display text-lg font-bold">{t("circulo.sirvio")}</h2>
          <div className="space-y-2">
            {sirvio.map((h) => (
              <div key={h.id} className="rounded-[var(--radius-card)] border border-violeta/25 bg-violeta/[0.05] p-4 sombra-papel">
                <div className="flex items-start gap-2.5">
                  <Sparkles size={17} className="mt-0.5 shrink-0 text-violeta-hondo" />
                  <div className="min-w-0">
                    <p className="font-display text-sm font-bold leading-snug">{h.titulo}</p>
                    <p className="mt-0.5 text-xs leading-snug text-tinta-suave">{h.resumen}</p>
                  </div>
                </div>
                {h.mis_notas.map((n) => (
                  <p key={n.id} className="mt-2 border-l-2 border-violeta/40 pl-2.5 text-xs italic leading-snug text-tinta-suave">
                    «{n.texto}» — {n.fecha}
                  </p>
                ))}
                {h.personas > 1 && (
                  <p className="mt-2 text-xs font-semibold text-violeta-hondo">
                    {t("circulo.tambien_lo_dijeron", { n: h.personas - 1 })}
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 3 · lo que mandé, con su estado real */}
      {mios.length > 0 && (
        <section>
          <h2 className="mb-2 font-display text-lg font-bold">{t("circulo.reporte")}</h2>
          <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema px-3 sombra-papel">
            {mios.slice(0, 6).map((r) => (
              <div key={r.id} className="flex items-start gap-2.5 border-b border-linea py-3 last:border-0">
                {r.estado === "resuelto" ? <Check size={16} className="mt-0.5 shrink-0 text-salvia" />
                  : r.visto ? <Eye size={16} className="mt-0.5 shrink-0 text-violeta-hondo" />
                  : <CircleDot size={16} className="mt-0.5 shrink-0 text-oro" />}
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium leading-snug text-tinta">{titulo(r, t)}</p>
                  <Estado r={r} t={t} />
                  {r.nota_dueno && (
                    <p className="mt-1 text-xs leading-snug text-tinta">«{r.nota_dueno}»</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
