import { X, Mic, Loader2, ArrowRight, Unlink } from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import { camposDe } from "../lib/roles";
import { useApiQuery } from "../lib/query";
import { useT } from "../lib/i18n";

// LA HOJA DE CARGA — lo que abre el botón del centro, POR OFICIO.
//
// Las nueve acciones iguales para todos eran ruido en la pantalla de casi todo
// el mundo: nadie del depósito cobra, ni Walter levanta pedidos. Acá cada uno ve
// lo SUYO, que sale de `avisos_por_oficio.json` a través del rol — no del
// username, así que una persona nueva con el mismo puesto los hereda sola.
//
// Dos decisiones que cambian respecto de las imágenes de referencia:
//
//   · «Nota — agregar información» NO está. Una nota genérica nace sin
//     destinatario y se muere, que es el objeto que el modelo de flujo marcó
//     como roto. En su lugar están los avisos del oficio, cada uno con el
//     destinatario que Ángela propone y la persona confirma.
//   · «Voz» deja de ser un mosaico y pasa a ser la franja fija del pie. Como
//     mosaico competía con los otros ocho, cuando en realidad es OTRA FORMA de
//     hacer cualquiera de ellos. Siempre en el mismo lugar, siempre al pulgar.

export default function HojaDeCarga({ onCerrar, onAviso, onVoz, conVoz }) {
  const t = useT();
  const { data: d, isLoading } = useApiQuery("pisoAvisosOficio");

  const tocar = (a) => {
    onAviso({
      id: a.id, texto: a.texto, tipo: a.tipo, motivo: a.motivo,
      cruza_datos: a.cruza_datos, campos: camposDe(a.necesita),
      // El destinatario que declara la semilla. Cuando no hay regla se manda
      // `null` y el formulario cae en la propuesta por tipo: nunca se inventa
      // a quién le llega.
      destino: a.destinatario || null,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-tinta/40 sm:items-center sm:p-4"
      onClick={onCerrar}>
      <div onClick={(e) => e.stopPropagation()}
        className="max-h-[88vh] w-full max-w-md overflow-y-auto rounded-t-[var(--radius-card)] border border-linea bg-crema p-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] sombra-alta sm:rounded-[var(--radius-card)]">
        <div className="flex items-start justify-between gap-3">
          <h2 className="font-display text-xl font-bold leading-tight">{t("carga.titulo")}</h2>
          <button onClick={onCerrar} aria-label={t("common.cerrar")}
            className="text-tinta-suave hover:text-tinta"><X size={20} /></button>
        </div>

        {isLoading ? (
          <div className="py-8 text-center"><Loader2 size={18} className="mx-auto animate-spin text-tinta-suave" /></div>
        ) : !(d?.avisos?.length) ? (
          // Administración, compras y el dueño no tienen lista, y está dicho en
          // la semilla: son oficinas, escriben en vez de avisar desde el piso.
          <p className="mt-3 text-sm leading-snug text-tinta-suave">{t("carga.sin_lista")}</p>
        ) : (
          <>
            <p className="mt-1 text-sm leading-snug text-tinta-suave">{t("carga.sub")}</p>
            <div className="mt-4 grid grid-cols-1 gap-2">
              {d.avisos.map((a) => (
                <button key={a.id} onClick={() => tocar(a)}
                  className="flex min-h-14 items-center gap-3 rounded-[var(--radius-card)] border border-linea bg-papel px-4 py-3 text-left transition-colors active:scale-[0.99] sombra-papel">
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold leading-snug text-tinta">{a.texto}</span>
                    {a.destinatario ? (
                      <span className="block text-xs leading-snug text-tinta-suave">
                        {t("carga.lo_ve", { nombre: a.destinatario.nombre })}
                      </span>
                    ) : (
                      <span className="block text-xs leading-snug text-tinta-suave">
                        {t("carga.destino_a_confirmar")}
                      </span>
                    )}
                  </span>
                  {!a.cruza_datos && <Unlink size={14} className="shrink-0 text-tinta-suave" aria-hidden />}
                  <ArrowRight size={15} className="shrink-0 text-tinta-suave" />
                </button>
              ))}
            </div>
          </>
        )}

        {/* La franja de voz: siempre acá, siempre igual. Para el que tiene las
            manos ocupadas es la vía principal, no una alternativa. */}
        {conVoz && (
          <button onClick={onVoz}
            className="mt-4 flex min-h-14 w-full items-center gap-3 rounded-[var(--radius-card)] border border-violeta/30 bg-violeta/[0.06] px-4 py-3 text-left active:scale-[0.99]">
            <Mic size={19} className="shrink-0 text-violeta" />
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-semibold leading-snug text-tinta">{t("carga.hablando")}</span>
              <span className="block text-xs leading-snug text-tinta-suave">{t("carga.hablando_sub")}</span>
            </span>
            <AngelaMark size={22} />
          </button>
        )}
      </div>
    </div>
  );
}
