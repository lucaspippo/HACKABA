import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { langStore } from "./i18n.js";
import { equipoStore } from "./equipoStore.js";
import { queries } from "./query";

// La identidad del tenant (empresa, tenant, LOGO) viene ENTERA de /api/health.
// P37 — INCIDENTE DE PRIVACIDAD: el frontend NO hardcodea ningún cliente. Hasta
// que health resuelve, `empresa`/`logo` son null (skeleton) y `tenant` es null;
// así el nombre/logo de un tenant (en particular el piloto REAL) jamás puede
// pintarse antes de tiempo ni por un default. El logo lo decide el backend por
// tenant (meta.logo): el del piloto se sirve de su data dir, nunca del bundle.

function metaFromHealth(h) {
  if (!h) return null;
  return {
    empresa: h.meta?.empresa || null,
    tenant: h.tenant || null,
    logo: h.meta?.logo || null,
    roleSwitch: !!h.role_switch,
    fuente: h.meta?.fuente || "",
    idiomaDefault: h.idioma_default,
  };
}

export function useEmpresa() {
  const health = useQuery(queries.health());
  const meta = health.isError
    ? { empresa: null, tenant: null, logo: null, roleSwitch: false, fuente: "" }
    : metaFromHealth(health.data);

  useEffect(() => {
    if (!health.data) return;
    // Pre-sesión (Login): el default de idioma del tenant (demo=en, piloto=es).
    langStore.syncDefaultTenant(health.data.idioma_default);
    // El tablero del equipo se siembra POR TENANT (P9·C1) — solo con el
    // tenant YA resuelto (nunca con un default, que filtraría el piloto).
    if (health.data.tenant) equipoStore.setTenant(health.data.tenant);
  }, [health.data]);

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
