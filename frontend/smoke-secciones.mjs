// P29·A3 — TEST DE HUMO: recorre TODAS las secciones del sidebar con el rol
// dueño y con 2 roles de empleado, verificando que cada una renderiza
// contenido (no blanco, no estado de error). Corre contra el demo levantado
// (localhost:5174 / API 8001). Sale con código 1 si algo quedó mudo.
//
//   node smoke-secciones.mjs
import { readFileSync } from "node:fs";
import { chromium } from "playwright";

// Las credenciales del TENANT demo (auth.CREDS_FILE es por-tenant: en el demo
// vive en data-demo/, no en backend/).
const CREDS = JSON.parse(readFileSync("../data-demo/credenciales.json", "utf-8")).plain;
const ROLES = ["aldo", "marta", "celeste"]; // dueño + administración + compras
// puerto configurable: el demo de una sesión paralela puede estar en otro
const API = process.env.POLPILOT_API || "http://localhost:8001";
const APP = process.env.POLPILOT_APP || "http://localhost:5174/";

const login = async (username) => {
  const r = await fetch(`${API}/api/login`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password: CREDS[username] }),
  });
  if (!r.ok) throw new Error(`login ${username}: ${r.status}`);
  return r.json(); // {token, usuario}
};

const browser = await chromium.launch();
let fallas = 0;

for (const username of ROLES) {
  const sesion = await login(username);
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 950 } });
  await ctx.addInitScript(([k, v]) => localStorage.setItem(k, v),
    ["polpilot.session.v1", JSON.stringify(sesion)]);
  const page = await ctx.newPage();
  const errores = [];
  page.on("pageerror", (e) => errores.push(e.message.slice(0, 200)));

  await page.goto(APP, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(3500);
  await page.waitForTimeout(1200);

  const botones = await page.evaluate(() =>
    [...document.querySelectorAll("nav button")].map((b) => b.innerText.trim()).filter(Boolean));
  console.log(`\n=== ${username} — ${botones.length} secciones: ${botones.join(" · ")}`);

  for (const nombre of botones) {
    errores.length = 0;
    await page.getByRole("button", { name: nombre, exact: true }).first().click();
    // Mudo = NUNCA aparece contenido: poll hasta 10s (los estados de carga
    // legítimos con backend frío no son fallas; una pantalla eternamente en
    // blanco o el estado de error del boundary, sí).
    let estado = { largo: 0, enError: false };
    const limite = Date.now() + 10_000;
    do {
      await page.waitForTimeout(500);
      estado = await page.evaluate(() => {
        const main = document.querySelector("main");
        const texto = (main?.innerText || "").trim();
        const enError = texto.includes("tuvo un problema") || texto.includes("hit a problem");
        return { largo: texto.length, enError };
      });
      if (estado.enError || errores.length) break;
    } while (estado.largo <= 40 && Date.now() < limite);
    const ok = estado.largo > 40 && !estado.enError && errores.length === 0;
    console.log(`  ${ok ? "OK " : "FALLA"} ${nombre} (chars=${estado.largo}${estado.enError ? ", ERROR-STATE" : ""}${errores.length ? ", pageerror: " + errores[0] : ""})`);
    if (!ok) fallas++;
  }
  await ctx.close();
}

await browser.close();
if (fallas > 0) {
  console.error(`\n${fallas} sección(es) mudas o rotas.`);
  process.exit(1);
}
console.log("\nTODAS las secciones renderizan con los 3 roles.");
