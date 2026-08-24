import { useState } from "react";
import { LogIn } from "lucide-react";
import AngelaMark from "./AngelaMark";
import LangSwitch from "./LangSwitch";
import { authStore } from "../lib/auth";
import { useEmpresa } from "../lib/useEmpresa";
import { useT } from "../lib/i18n";

// Login real por usuario. Cada persona entra y ve SU PolPilot. La marca del
// cliente sale del tenant (piloto = logo; demo = texto), así nunca decís
// "Horizonte" en la instancia del Litoral.
export default function Login() {
  const t = useT();
  // P37 — el logo del cliente sale del backend (meta.logo por tenant); nada
  // hardcodeado. Skeleton hasta que health resuelve.
  const { empresa, logo, resuelto } = useEmpresa();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(false);

  const entrar = async (e) => {
    e?.preventDefault();
    if (!username || !password) return;
    setCargando(true);
    setError(null);
    try {
      await authStore.login(username, password);
    } catch (err) {
      setError(err.message);
      setCargando(false);
    }
  };

  return (
    <div className="relative flex min-h-[100dvh] items-center justify-center bg-papel px-5">
      <LangSwitch className="absolute right-4 top-4" />
      <div className="w-full max-w-sm">
        <div className="mb-7 flex flex-col items-center text-center">
          <img src="/logos/polpilot.png" alt="PolPilot" className="h-9 w-auto" draggable="false" />
          <div className="mt-3 flex items-center gap-2">
            <span className="text-[0.66rem] font-semibold uppercase tracking-[0.14em] text-tinta-suave">
              {t("brand.para")}
            </span>
            {!resuelto ? (
              <span className="h-7 w-28 animate-pulse rounded bg-papel-hondo" />
            ) : logo ? (
              <img src={logo} alt={empresa || ""} className="h-8 w-auto" draggable="false" />
            ) : (
              <span className="font-display text-[1rem] font-bold text-hielo">{empresa}</span>
            )}
          </div>
        </div>

        <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-6 sombra-alta">
          <div className="mb-5 flex items-center gap-3">
            <AngelaMark size={36} />
            <div>
              <p className="font-display text-[1.05rem] font-bold leading-tight">{t("login.titulo")}</p>
              <p className="text-[0.8rem] text-tinta-suave">{t("login.subtitulo")}</p>
            </div>
          </div>

          <form onSubmit={entrar} className="space-y-3">
            <div>
              <label className="mb-1 block text-[0.78rem] font-semibold text-tinta-suave">{t("login.usuario")}</label>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoCapitalize="none"
                autoFocus
                placeholder={t("login.placeholder_usuario")}
                className="w-full rounded-xl border border-linea bg-papel px-3.5 py-2.5 text-[0.95rem] outline-none focus:border-tinta/40"
              />
            </div>
            <div>
              <label className="mb-1 block text-[0.78rem] font-semibold text-tinta-suave">{t("login.password")}</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-xl border border-linea bg-papel px-3.5 py-2.5 text-[0.95rem] outline-none focus:border-tinta/40"
              />
            </div>

            {error && (
              <p className="rounded-lg bg-rojo/10 px-3 py-2 text-[0.85rem] font-medium text-rojo-hondo">{error}</p>
            )}

            <button
              type="submit"
              disabled={cargando || !username || !password}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-tinta px-4 py-2.5 text-[0.95rem] font-semibold text-crema transition-transform active:scale-[0.99] disabled:opacity-40"
            >
              <LogIn size={17} /> {cargando ? t("login.entrando") : t("login.entrar")}
            </button>
          </form>
        </div>

        <p className="mt-4 text-center text-[0.78rem] text-tinta-suave">
          {t("login.olvido")}
        </p>
      </div>
    </div>
  );
}
