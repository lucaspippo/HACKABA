// Verifica que la descripción de perfil se lea en el idioma de la pantalla, en
// las DOS vistas donde aparece (Mi perfil y Equipo), y en los dos idiomas.
//
//   POLPILOT_API=http://127.0.0.1:8003 POLPILOT_APP=http://127.0.0.1:8003/ node verify-perfil-idioma.mjs
import { readFileSync } from "node:fs";
import { chromium } from "playwright";

const CREDS = JSON.parse(readFileSync("../data-demo/credenciales.json", "utf-8")).plain;
const API = process.env.POLPILOT_API || "http://127.0.0.1:8003";
const APP = process.env.POLPILOT_APP || "http://127.0.0.1:8003/";

// castellano que delataría el seed sin traducir
const ES = /\b(fund[ée]|distribuidora|me encargo|todos los días|decido sobre|camioneta|dep[óo]sito central|ma[ñn]ana)\b/i;
const EN = /\b(My role|I take care of|Every day I look at|I decide on)\b/;

const login = async (u) => {
  const r = await fetch(`${API}/api/login`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: u, password: CREDS[u] }),
  });
  return r.json();
};

const browser = await chromium.launch();
let fallas = 0;
const di = (ok, msg) => { console.log(`${ok ? "  OK  " : " FALLA"} ${msg}`); if (!ok) fallas++; };

// El idioma de la sesión lo decide el servidor (perfiles.idioma_de); acá se
// fuerza el del CLIENTE para leer la misma pantalla en los dos idiomas sin
// tocar el perfil de nadie (el bug conocido del toggle no se roza).
const abrir = async (usuario, idioma) => {
  const sesion = await login(usuario);
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  await ctx.addInitScript(([s, l]) => {
    localStorage.setItem("polpilot.session.v1", s);
    localStorage.setItem("polpilot.lang.v1", l);
  }, [JSON.stringify({ ...sesion, usuario: { ...sesion.usuario, idioma } }), idioma]);
  const page = await ctx.newPage();
  await page.goto(APP, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(6000);
  return { ctx, page };
};

for (const idioma of ["en", "es"]) {
  console.log(`\n== idioma ${idioma.toUpperCase()} ==`);

  // 1 · Mi perfil. OJO: esta vista re-sincroniza el idioma con el del SERVIDOR
  // (authStore.refresh → /api/me), así que no alcanza con forzarlo en el
  // cliente: para el pase en castellano se usa una persona cuyo perfil está
  // realmente en ES (se setea y se restaura por el mecanismo real, ver abajo).
  {
    const quien = idioma === "es" ? "tomas" : "aldo";
    const { ctx, page } = await abrir(quien, idioma);
    await page.locator("nav button").filter({ hasText: /^(My profile|Mi perfil)/ }).first().click();
    await page.waitForTimeout(3500);
    const txt = await page.locator("main").innerText();
    const bloque = txt.slice(txt.search(/WHAT YOU DO|QU[ÉE] HAC[ÉE]S/i), 900);
    console.log("   ", bloque.split("\n").filter(Boolean).slice(1, 4).join(" | ").slice(0, 170));
    di(idioma === "en" ? EN.test(bloque) && !ES.test(bloque) : ES.test(bloque),
       `Mi perfil · descripción en ${idioma}`);
    await ctx.close();
  }

  // 2 · Equipo: la descripción de Kevin + su puesto, dentro de su fila
  {
    const { ctx, page } = await abrir("aldo", idioma);
    await page.locator("nav button").filter({ hasText: /^(Team|Equipo)/ }).first().click();
    await page.waitForTimeout(4000);
    await page.locator("button").filter({ hasText: /Kevin/ }).first().click();
    await page.waitForTimeout(2500);
    const txt = await page.locator("main").innerText();
    const i = txt.search(/In their own words|Se describi[óo] as[íi]/);
    const ficha = i >= 0 ? txt.slice(i, i + 620) : "";
    console.log("   ", ficha.replace(/\n+/g, " | ").slice(0, 240));
    di(!!ficha, "Equipo · se abre la ficha de Kevin");
    di(idioma === "en" ? EN.test(ficha) && !ES.test(ficha) : ES.test(ficha),
       `Equipo · descripción y puesto de Kevin en ${idioma}`);
    await ctx.close();
  }
}

await browser.close();
console.log(fallas === 0 ? "\nVERDE — perfiles en el idioma de la pantalla" : `\nROJO — ${fallas} fallas`);
process.exit(fallas === 0 ? 0 : 1);
