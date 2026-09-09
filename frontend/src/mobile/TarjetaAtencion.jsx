import { ArrowRight } from "lucide-react";
import { peso } from "../lib/format";
import { useT } from "../lib/i18n";

// LA TARJETA DE ATENCIÓN — lo primero de la pantalla, y lo único grande.
//
// El inicio abría con un saludo y una caja de preguntar. Un saludo no es una
// decisión: quien abre la app a las siete de la mañana no necesita que le digan
// hola, necesita saber qué hay que resolver AHORA. Ésta es esa card, y va antes
// que todo lo demás.
//
// La forma es la de la imagen de referencia: fondo tenue del color del estado,
// el rótulo en ese color, el hecho en grande, el contexto abajo, un botón de
// contorno, y la evidencia a la derecha.
//
// LA EVIDENCIA ES LA FOTO REAL, no una ilustración. Cuando el hecho viene de un
// reporte del piso con prueba (`piso.py` la guarda como archivo y la sirve por
// endpoint), es ESA foto la que se muestra: el remito firmado, la caja rota.
// Una ilustración de cajas de stock decora; la foto del que estaba ahí prueba.
// Sin foto la card se arma igual, sin hueco.
//
// Los colores son los tres estados y nada más (DESIGN.md, One Meaning Rule):
// rojo = un problema activo, oro = una decisión esperando al dueño. No hay un
// tercer tono decorativo, y no hay azul: el azul es de Ángela.

const TONO = {
  rojo: { caja: "border-rojo/30 bg-rojo/[0.06]", texto: "text-rojo-hondo",
          borde: "border-rojo/40" },
  oro: { caja: "border-oro/30 bg-oro/[0.07]", texto: "text-oro-tinta",
         borde: "border-oro/45" },
};

export default function TarjetaAtencion({ tono = "oro", rotulo, hecho, contexto,
                                          monto, foto, cta, onCta }) {
  const t = useT();
  const c = TONO[tono] || TONO.oro;
  if (!hecho) return null;

  return (
    <section className={`rounded-[var(--radius-card)] border p-4 sombra-papel ${c.caja}`}>
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className={`text-2xs font-semibold uppercase tracking-wide ${c.texto}`}>
            {rotulo || t("atencion.rotulo")}
          </p>
          <p className="mt-1 font-display text-lg font-bold leading-tight text-tinta">{hecho}</p>
          {contexto && (
            <p className="mt-1 text-sm leading-snug text-tinta-suave">{contexto}</p>
          )}
          {monto ? (
            <p className="plata mt-1.5 font-display text-xl font-bold text-tinta">{peso(monto)}</p>
          ) : null}
        </div>

        {/* La evidencia, donde la imagen tiene la ilustración. Cuadrada y
            chica: es una prueba, no una galería — se abre al tocarla. */}
        {foto && (
          <button onClick={onCta} className="shrink-0" aria-label={t("atencion.ver_prueba")}>
            <img src={foto} alt="" loading="lazy"
              className="h-20 w-20 rounded-xl border border-linea object-cover" />
          </button>
        )}
      </div>

      {cta && (
        <button onClick={onCta}
          className={`mt-3 inline-flex min-h-11 items-center gap-1.5 rounded-full border bg-crema px-4 py-2 text-sm font-semibold text-tinta active:scale-95 ${c.borde}`}>
          {cta} <ArrowRight size={15} />
        </button>
      )}
    </section>
  );
}
