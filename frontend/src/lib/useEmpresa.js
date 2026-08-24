import { useEffect, useState } from "react";
import { langStore } from "./i18n.js";
import { equipoStore } from "./equipoStore.js";

// La identidad del tenant (empresa, tenant, LOGO) viene ENTERA de /api/health.
// P37 — INCIDENTE DE PRIVACIDAD: el frontend NO hardcodea ningún cliente. Hasta
// que health resuelve, `empresa`/`logo` son null (skeleton) y `tenant` es null;
// así el nombre/logo de un tenant (en particular el piloto REAL) jamás puede
// pintarse antes de tiempo ni por un default. El logo lo decide el backend por
// tenant (meta.logo): el del piloto se sirve de su data dir, nunca del bundle.
let _cache = null;

export function useEmpresa() {
  const [meta, setMeta] = useState(_cache);
  useEffect(() => {
    if (_cache) { setMeta(_cache); return; }
    fetch("/api/health")
      .then((r) => r.json())
      .then((h) => {
        _cache = {
          empresa: h.meta?.empresa || null,
          tenant: h.tenant || null,
          logo: h.meta?.logo || null,
          roleSwitch: !!h.role_switch,
          fuente: h.meta?.fuente || "",
        };
        // Pre-sesión (Login): el default de idioma del tenant (demo=en, piloto=es).
        langStore.syncDefaultTenant(h.idioma_default);
        // El tablero del equipo se siembra POR TENANT (P9·C1) — solo con el
        // tenant YA resuelto (nunca con un default, que filtraría el piloto).
        if (h.tenant) equipoStore.setTenant(h.tenant);
        setMeta(_cache);
      })
      .catch(() => setMeta({ empresa: null, tenant: null, logo: null, roleSwitch: false, fuente: "" }));
  }, []);
  return {
    empresa: meta?.empresa || null,
    tenant: meta?.tenant || null,
    logo: meta?.logo || null,
    resuelto: !!meta,                       // ¿health ya resolvió? (para el skeleton)
    esPiloto: meta?.tenant === "piloto",
    roleSwitch: !!meta?.roleSwitch,
    // P18·C: el demo declara su ERP SIMULADO (fuente "…(DEMO)"); el piloto no.
    erpSimulado: (meta?.fuente || "").includes("(DEMO)"),
  };
}
