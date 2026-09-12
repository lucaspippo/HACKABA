// EL PANEL DE EVALS — qué tan seguido acierta el motor, medido.
//
// Vive DENTRO del cerebro y no en el sidebar, y es a propósito: PRODUCT.md
// (Report Rule) dice que una pantalla con lecturas y sin acción persistida es
// EVIDENCIA, no un destino de primer nivel. Esto es evidencia sobre el motor
// de cruces, así que se muestra donde el motor se muestra.
//
// Tres reglas de la casa, y el componente las respeta de forma visible:
//   1. Muestra una CORRIDA GRABADA. Si nunca corrió, lo dice y da el comando;
//      jamás calcula al abrir (el endpoint tampoco — ver core/evals.py).
//   2. El DENOMINADOR va al lado del puntaje, siempre: "6 de 7", nunca "86%"
//      a secas. El porcentaje acompaña en chico, nunca solo.
//   3. La FECHA de la corrida se ve, y si tiene días encima se dice cuántos.
//
// Color (DESIGN.md, un color un significado): salvia = en orden, rojo =
// problema real. El azul NO se usa acá: es de Ángela, y esto no lo dice
// Ángela — lo dice el código midiéndose a sí mismo.
import { useState } from "react";
import { CheckCircle2, XCircle, FlaskConical, Clock, ChevronDown } from "lucide-react";
import { useApiQuery } from "../../lib/query";
import { useT } from "../../lib/i18n";

const SALVIA = "#2f7d5b";
const ROJO = "#d2372b";

// La barra: llena en salvia, vacía en línea. Sin gradientes ni animación —
// es un dato, no un logro.
function Barra({ aciertos, total }) {
  const pct = total ? (aciertos / total) * 100 : 0;
  const perfecto = total > 0 && aciertos === total;
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-linea">
      <div
        className="h-full rounded-full transition-[width] duration-500"
        style={{ width: `${pct}%`, background: perfecto ? SALVIA : ROJO }}
      />
    </div>
  );
}

// El puntaje. El denominador NO es letra chica: es parte del número.
function Puntaje({ aciertos, total }) {
  const perfecto = total > 0 && aciertos === total;
  const t = useT();
  return (
    <span className="flex items-baseline gap-1.5 font-mono tabular-nums">
      <span className="text-2xl font-medium" style={{ color: perfecto ? SALVIA : ROJO }}>
        {aciertos}
      </span>
      <span className="text-sm text-tinta-suave">{t("evals.de")} {total}</span>
    </span>
  );
}

function Suite({ suite }) {
  const t = useT();
  const [abierto, setAbierto] = useState(false);
  const fallas = (suite.casos || []).filter((c) => !c.ok);
  const cob = suite.cobertura_observada;
  return (
    <div className="border-t border-linea py-4 first:border-t-0 first:pt-0">
      <div className="flex items-start justify-between gap-6">
        <div className="min-w-0">
          <p className="font-label text-base font-semibold text-tinta">{suite.nombre}</p>
          {/* Qué pregunta contesta este número. Sin esto, un porcentaje es
              una decoración con dos decimales. */}
          <p className="mt-0.5 text-sm leading-snug text-tinta-suave">{suite.mide}</p>
        </div>
        <Puntaje aciertos={suite.aciertos} total={suite.total} />
      </div>
      <div className="mt-2.5">
        <Barra aciertos={suite.aciertos} total={suite.total} />
      </div>

      {fallas.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {fallas.map((c) => (
            <li key={c.id} className="flex gap-2 text-sm leading-snug">
              <XCircle className="mt-0.5 size-3.5 shrink-0" style={{ color: ROJO }} />
              <span className="text-tinta">
                <span className="font-mono text-xs text-tinta-suave">{c.id}</span>
                {" — "}{c.detalle}
              </span>
            </li>
          ))}
        </ul>
      )}

      {(suite.casos || []).length > 0 && (
        <button
          onClick={() => setAbierto((v) => !v)}
          className="mt-2 flex items-center gap-1 text-sm text-tinta-suave hover:text-tinta"
        >
          <ChevronDown className={`size-3.5 transition-transform ${abierto ? "rotate-180" : ""}`} />
          {abierto ? t("evals.ocultar_casos") : t("evals.ver_casos", { n: suite.casos.length })}
        </button>
      )}

      {abierto && (
        <ul className="mt-2 space-y-2 rounded-md bg-papel p-3">
          {suite.casos.map((c) => (
            <li key={c.id} className="flex gap-2 text-sm leading-snug">
              {c.ok
                ? <CheckCircle2 className="mt-0.5 size-3.5 shrink-0" style={{ color: SALVIA }} />
                : <XCircle className="mt-0.5 size-3.5 shrink-0" style={{ color: ROJO }} />}
              <span className="min-w-0">
                <span className="font-mono text-xs text-tinta-suave">{c.id}</span>
                <span className="text-tinta"> — {c.detalle}</span>
                {/* Por qué este caso está en el conjunto. Un eval sin esto es
                    una lista de nombres propios. */}
                {c.porque && (
                  <span className="mt-0.5 block text-tinta-suave">{c.porque}</span>
                )}
              </span>
            </li>
          ))}
          {cob && (
            <li className="border-t border-linea pt-2 text-sm leading-snug text-tinta-suave">
              <span className="font-label font-semibold text-tinta">
                {cob.emitidos.length} {t("evals.de")} {cob.del_catalogo}
              </span>{" "}
              {cob.nota}
            </li>
          )}
        </ul>
      )}
    </div>
  );
}

export default function PanelEvals() {
  const t = useT();
  const { data: datos, error } = useApiQuery("evals");

  if (error) {
    return (
      <div className="rounded-card border border-linea bg-crema p-5 text-sm text-tinta-suave">
        {error.criollo || String(error.message)}
      </div>
    );
  }
  if (!datos) {
    return (
      <div className="rounded-card border border-linea bg-crema p-5 text-sm text-tinta-suave">
        {t("evals.cargando")}
      </div>
    );
  }

  // El estado vacío es parte del producto, no un error: decir "todavía no
  // corrió" es más honesto que mostrar el último número que haya quedado.
  if (!datos.disponible) {
    return (
      <div className="rounded-card border border-linea bg-crema p-5">
        <div className="flex items-center gap-2">
          <FlaskConical className="size-4 text-tinta-suave" />
          <p className="font-label text-base font-semibold text-tinta">{t("evals.titulo")}</p>
        </div>
        <p className="mt-2 text-base leading-snug text-tinta-suave">{datos.motivo}</p>
        {datos.como && (
          <code className="mt-3 inline-block rounded-md bg-papel px-2.5 py-1 font-mono text-sm text-tinta">
            {datos.como}
          </code>
        )}
      </div>
    );
  }

  const r = datos.resumen || {};
  const dias = datos.antiguedad_dias;

  return (
    <div className="rounded-card border border-linea bg-crema p-5">
      {/* ------------------------------------------------------ encabezado */}
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-linea pb-4">
        <div>
          <div className="flex items-center gap-2">
            <FlaskConical className="size-4 text-tinta-suave" />
            <p className="font-label text-base font-semibold text-tinta">{t("evals.titulo")}</p>
          </div>
          <p className="mt-1 max-w-2xl text-base leading-snug text-tinta-suave">
            {t("evals.bajada")}
          </p>
          {/* La fecha de la corrida, y cuántos días tiene. Un número de
              calidad sin fecha es decoración (core/evals.py, regla 3). */}
          <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-tinta-suave">
            <Clock className="size-3.5" />
            <span className="font-mono tabular-nums">{datos.generado?.replace("T", " ")}</span>
            {dias > 0 && (
              <span style={{ color: dias >= 3 ? ROJO : undefined }}>
                · {t("evals.dias", { n: dias })}
              </span>
            )}
            <span>· {t("evals.hoy_dataset", { fecha: datos.hoy })}</span>
          </p>
          <p className="mt-1 text-sm text-tinta-suave">
            {t("evals.dataset")}: {datos.dataset}
          </p>
        </div>
        <div className="text-right">
          <p className="font-label text-sm uppercase tracking-wide text-tinta-suave">
            {t("evals.total")}
          </p>
          <Puntaje aciertos={r.aciertos || 0} total={r.total || 0} />
        </div>
      </div>

      {/* ---------------------------------------------------------- suites */}
      <div className="mt-4">
        {(datos.suites || []).map((s) => <Suite key={s.id} suite={s} />)}
      </div>

      {/* Lo que un eval no es. Decirlo acá evita que alguien lea el número
          como una garantía sobre un negocio real. */}
      <p className="mt-4 border-t border-linea pt-3 text-sm leading-snug text-tinta-suave">
        {t("evals.limite")}
      </p>
    </div>
  );
}
