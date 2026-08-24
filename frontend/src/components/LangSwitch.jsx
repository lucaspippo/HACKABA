import { langStore, useLang, t } from "../lib/i18n.js";

// EN | ES — discreto pero encontrable, arriba a la derecha (Prompt 8).
// El mismo componente sirve en desktop, mobile, Login y Mi perfil.
export default function LangSwitch({ className = "" }) {
  const lang = useLang();
  return (
    <div
      role="group"
      aria-label={t("lang.cambiar")}
      className={`plata flex items-center overflow-hidden rounded-full border border-linea text-[0.68rem] font-medium ${className}`}
    >
      {["en", "es"].map((code) => (
        <button
          key={code}
          onClick={() => langStore.set(code)}
          aria-pressed={lang === code}
          className={`px-2 py-1 uppercase transition-colors ${
            lang === code
              ? "bg-tinta text-crema"
              : "text-tinta-suave hover:text-tinta"
          }`}
        >
          {code}
        </button>
      ))}
    </div>
  );
}
