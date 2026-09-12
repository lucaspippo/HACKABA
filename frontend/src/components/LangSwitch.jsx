import { langStore, useLang, t } from "../lib/i18n.js";

export default function LangSwitch({ className = "" }) {
  const lang = useLang();
  return (
    <div
      role="group"
      aria-label={t("lang.cambiar")}
      className={`plata flex items-center overflow-hidden rounded-full border border-linea text-2xs font-medium ${className}`}
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
