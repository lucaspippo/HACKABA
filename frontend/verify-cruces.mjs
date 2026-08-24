// P·cruces — VERIFICACIÓN REAL del cerebro con los hallazgos nuevos.
// Chromium de verdad (el browser embebido no compone el lienzo del grafo).
//
//   node verify-cruces.mjs
//
// Qué mira:
//   1. Los chips de hallazgos son los CRUCES (y no las alertas de una fuente).
//   2. Al encender uno, se lee qué dominios cruzó y la cadena de razonamiento.
//   3. El camino iluminado toca entidades de tipos distintos, la nota del
//      equipo incluida.
//   4. La leyenda muestra el tipo nuevo (nota) y el lienzo dibuja sin errores.
import { readFileSync } from "node:fs";
import { chromium } from "playwright";

const CREDS = JSON.parse(readFileSync("../data-demo/credenciales.json", "utf-8")).plain;
const API = process.env.POLPILOT_API || "http://localhost:8002";
const APP = process.env.POLPILOT_APP || "http://localhost:5175/";

const login = async (u) => {
  const r = await fetch(`${API}/api/login`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: u, password: CREDS[u] }),
  });
  if (!r.ok) throw new Error(`login ${u}: ${r.status}`);
  return r.json();
};

let fallas = 0;
const di = (ok, msg) => { console.log(`${ok ? "  OK  " : " FALLA"} ${msg}`); if (!ok) fallas++; };

const browser = await chromium.launch();
const sesion = await login("aldo");
const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
await ctx.addInitScript(([k, v]) => localStorage.setItem(k, v),
  ["polpilot.session.v1", JSON.stringify(sesion)]);
const page = await ctx.newPage();
const errores = [];
page.on("pageerror", (e) => errores.push(e.message.slice(0, 160)));
await page.goto(APP, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(3000);

// al mapa, y de ahí a la pestaña del CEREBRO (el toggle de MapaSeccion)
await page.locator('nav button').filter({ hasText: /business map|mapa de tu negocio/i }).first().click();
await page.waitForTimeout(2500);
await page.locator('button[aria-pressed]').filter({ hasText: /cerebro|brain/i }).first().click();
await page.waitForSelector('canvas', { timeout: 30000 }).catch(() => {});
await page.waitForTimeout(5000);

// --- 1 · los chips son los cruces --------------------------------------------
const chips = await page.evaluate(() => {
  const cont = [...document.querySelectorAll("div")].find(
    (d) => d.className.includes("rounded-card") && d.querySelector("button"));
  const botones = [...document.querySelectorAll("button")]
    .filter((b) => /\d+⨯\s*\d+$/.test(b.innerText.replace(/\s+/g, " ").trim()));
  return botones.map((b) => b.innerText.replace(/\s+/g, " ").trim());
});
console.log("\n== chips de hallazgos ==");
chips.forEach((c) => console.log("   ·", c));
di(chips.length >= 6, `${chips.length} hallazgos con dominios cruzados`);
di(!chips.some((c) => /quebrar|run out|margen|margin|18% off/i.test(c)),
   "ninguna alerta de una sola fuente entre los chips");

// --- 2 · encender uno: dominios + razonamiento -------------------------------
const primero = await page.locator("button").filter({ hasText: /⨯/ }).first();
await primero.click();
await page.waitForTimeout(1500);
const panel = await page.evaluate(() => {
  const txt = document.querySelector("main").innerText;
  const i = txt.search(/Cruzó:|Crossed:/);
  return i >= 0 ? txt.slice(i, i + 420) : null;
});
console.log("\n== hallazgo encendido ==");
console.log(panel ? panel.split("\n").map((l) => "   " + l).join("\n") : "   (sin panel)");
di(!!panel, "el hallazgo muestra qué cruzó");
di(!!panel && (panel.match(/\n/g) || []).length >= 3, "muestra la cadena de razonamiento");

// --- 3 · el camino toca tipos distintos --------------------------------------
const camino = await page.evaluate(async () => {
  const s = JSON.parse(localStorage.getItem("polpilot.session.v1"));
  const g = await (await fetch("/api/grafo", { headers: { Authorization: "Bearer " + s.token } })).json();
  return {
    meta: { nodos: g.meta.nodos, aristas: g.meta.aristas, notas: g.meta.por_tipo.nota,
            compra: g.meta.por_relacion.compra, menciona: g.meta.por_relacion.menciona,
            afinidad: g.meta.por_relacion.afinidad || 0 },
    caminos: g.caminos.map((c) => ({ id: c.id, tipos: c.tipos, dominios: c.dominios,
                                     nodos: c.nodos.length })),
  };
});
console.log("\n== grafo ==");
console.log("  ", JSON.stringify(camino.meta));
camino.caminos.forEach((c) => console.log(`   ${c.id.padEnd(26)} ${c.dominios.join(" · ")}  [${c.tipos.join(",")}]`));
di(camino.caminos.every((c) => c.tipos.length >= 3), "todos los caminos cruzan ≥3 tipos de entidad");
di(camino.caminos.filter((c) => c.tipos.includes("nota")).length >= 3,
   "al menos 3 caminos iluminan una nota del equipo");
di(camino.meta.notas >= 15 && camino.meta.compra > 100, "el grafo trae notas y compras reales");

// --- 4 · leyenda y lienzo -----------------------------------------------------
const leyenda = await page.evaluate(() => {
  const t = document.querySelector("main").innerText;
  return { notas: /Notas del equipo|Team notes/i.test(t) };
});
di(leyenda.notas, "la leyenda declara el tipo nuevo (notas del equipo)");
di(errores.length === 0, `sin errores de página (${errores.join(" | ")})`);
await page.screenshot({ path: "../docs/shot-cruces-cerebro.png" });

await browser.close();
console.log(fallas === 0 ? "\nVERDE — cruces ok" : `\nROJO — ${fallas} fallas`);
process.exit(fallas === 0 ? 0 : 1);
