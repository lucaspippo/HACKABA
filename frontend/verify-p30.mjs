// P30 — verificación: números defendibles + expansión por botón + oportunidades.
import { chromium } from "playwright";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } });
const errores = [];
page.on("pageerror", (e) => errores.push(e.message));
await page.goto("http://localhost:5174/", { waitUntil: "networkidle" });
await page.waitForTimeout(2500);
await page.reload({ waitUntil: "networkidle" });
await page.waitForTimeout(2000);

// --- A: números del mapa ---
await page.getByRole("button", { name: /Business Map|mapa de tu negocio/i }).first().click({ timeout: 20000 });
await page.waitForSelector(".react-flow__node", { timeout: 15000 });
await page.waitForTimeout(1600);
const mapa = await page.evaluate(() => {
  const main = document.querySelector("main")?.innerText || "";
  const frase = main.split("\n").find((l) => l.includes("years of sales") || l.includes("años de ventas")) || "";
  const recuperable = main.split("\n").find((l) => /Recoverable capital|Capital recuperable/i.test(l));
  const idx = main.split("\n").findIndex((l) => /Recoverable capital|Capital recuperable/i.test(l));
  const bloque = main.split("\n").slice(idx, idx + 8).join(" | ");
  const fuentes = (main.match(/Connected sources|Fuentes conectadas/) || [])[0];
  const fuentesLine = main.split("\n").find((l) => /Connected sources|Fuentes conectadas/.test(l));
  return { frase, recuperableBloque: bloque, fuentesLine };
});
console.log("FRASE:", JSON.stringify(mapa.frase));
console.log("RECUPERABLE:", JSON.stringify(mapa.recuperableBloque));
console.log("FUENTES:", JSON.stringify(mapa.fuentesLine));
await page.screenshot({ path: "../docs/shot-p30-mapa.png" });

// --- B: expansión con el botón [+] ---
const antes = await page.evaluate(() => document.querySelectorAll(".react-flow__node").length);
const clicOK = await page.evaluate(() => {
  const n = document.querySelector('[data-id="clientes"]');
  const btn = n?.querySelector('[data-expand]');
  if (!btn) return "sin boton";
  const r = btn.getBoundingClientRect();
  const o = { bubbles: true, cancelable: true, clientX: r.x + r.width/2, clientY: r.y + r.height/2, button: 0 };
  btn.dispatchEvent(new MouseEvent("mousedown", o));
  btn.dispatchEvent(new MouseEvent("mouseup", o));
  btn.dispatchEvent(new MouseEvent("click", o));
  return "click enviado";
});
await page.waitForTimeout(1000);
const despues = await page.evaluate(() => ({
  nodos: document.querySelectorAll(".react-flow__node").length,
  subs: [...document.querySelectorAll(".react-flow__node")].filter((n) => (n.getAttribute("data-id")||"").startsWith("clientes:")).map((n) => n.textContent),
  breadcrumb: [...document.querySelectorAll(".backdrop-blur")].map((e)=>e.innerText).find((x)=>x&&(x.includes("›")||x.includes("Client"))),
}));
console.log("EXPANSIÓN botón:", clicOK, "| nodos", antes, "->", despues.nodos, "| segmentos:", JSON.stringify(despues.subs), "| bc:", JSON.stringify(despues.breadcrumb));
await page.screenshot({ path: "../docs/shot-p30-expand.png" });

// --- C: Oportunidades curadas ---
await page.locator("aside nav button", { hasText: /Opportunities|Oportunidades/ }).first().click();
await page.waitForTimeout(1200);
const ops = await page.evaluate(() => {
  const main = document.querySelector("main")?.innerText || "";
  return {
    verTodas: /See all|Ver todas/.test(main),
    riesgos: /Risks to watch|Riesgos a vigilar/.test(main),
    concentracionEnGrilla: main.indexOf("carry too much") >= 0 || main.indexOf("concentran demasiado") >= 0,
    chipRiesgo: /\bRisk\b|\bRiesgo\b/.test(main),
  };
});
console.log("OPORTUNIDADES:", JSON.stringify(ops));
await page.screenshot({ path: "../docs/shot-p30-oportunidades.png" });

console.log("ERRORES:", errores.length, errores.slice(0, 3));
await browser.close();
