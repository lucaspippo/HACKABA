import { Sparkles } from "lucide-react";
import { t } from "../lib/i18n";

// P·onboarding — EL CHIP DE "NUEVO". La lista del equipo tiene gente con 22, 14
// y 9 años adentro; el que entró la semana pasada no se puede leer igual. Acá
// vive esa distinción, en UN solo lugar, para que "Ver como", la lista del
// equipo y el celular digan lo mismo.
//
// No es una etiqueta que alguien prende a mano: `antiguedad` la calcula el
// backend con la fecha de ingreso del perfil contra el "hoy" del sistema
// (auth.antiguedad). Sin fecha de ingreso no hay chip — los 13 de siempre
// quedan exactamente como estaban.

/** "1 semana", "3 días", "2 meses" — la unidad que se entiende sola. */
export function antiguedadTexto(a) {
  if (!a) return "";
  if (a.dias < 7) return t(a.dias === 1 ? "onb.ant_dias_1" : "onb.ant_dias", { n: a.dias });
  if (a.dias < 35) return t(a.semanas === 1 ? "onb.ant_semanas_1" : "onb.ant_semanas", { n: a.semanas });
  return t(a.meses === 1 ? "onb.ant_meses_1" : "onb.ant_meses", { n: a.meses });
}

export default function BadgeNuevo({ persona, compacto = false }) {
  const a = persona?.antiguedad;
  if (!a?.nuevo) return null;
  const ant = antiguedadTexto(a);
  return (
    <span
      title={t("equipo.badge_nuevo_title", { ant })}
      className="inline-flex shrink-0 items-center gap-1 rounded-full border border-hielo/35 bg-hielo/[0.10] px-2 py-0.5 text-[0.68rem] font-semibold text-hielo"
    >
      <Sparkles size={11} className="shrink-0" />
      {t("equipo.badge_nuevo")}
      {!compacto && <span className="font-normal opacity-80">· {ant}</span>}
    </span>
  );
}
