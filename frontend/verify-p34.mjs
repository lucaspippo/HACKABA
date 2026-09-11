// P34 — verifica (1) mapa sin truncados/superposición a 1366/1920, (2) el panel
// de equipo: todos listados, expandible, resumen real, sin conversaciones.
import { chromium } from "playwright";
const browser = await chromium.launch();

async function mapa(w, h) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h } });
  const p = await ctx.newPage();
  await p.goto("http://localhost:5174/", { waitUntil: "networkidle" });
  await p.waitForTimeout(2000);
  await p.locator("aside nav button", { hasText: /Business Map|mapa de tu negocio/i }).first().click();
  await p.waitForSelector(".react-flow__node", { timeout: 15000 });
  await p.waitForTimeout(1600);
  const r = await p.evaluate(() => {
    const cortados = [];
    for (const el of document.querySelectorAll("main .line-clamp-3"))
      if (el.scrollHeight > el.clientHeight + 1) cortados.push((el.textContent || "").slice(0, 40));
    const panel = document.querySelector("main .overflow-y-auto");
    const tile = [...document.querySelectorAll("main .grid button")].find(t => /Conex|Cross/i.test(t.textContent));
    let overlap = false;
    if (panel && tile) {
      const pr = panel.getBoundingClientRect(), tr = tile.getBoundingClientRect();
      overlap = pr.bottom > tr.top + 2 && pr.right > tr.left + 2 && pr.left < tr.right - 2;
    }
    return { cortados, overlap, overflowX: document.documentElement.scrollWidth > window.innerWidth + 2 };
  });
  console.log(`MAPA @${w}x${h}:`, JSON.stringify(r));
  await ctx.close();
}
await mapa(1366, 768);
await mapa(1920, 1080);

// EQUIPO
const ctx = await browser.newContext({ viewport: { width: 1600, height: 950 } });
const p = await ctx.newPage();
const errs = [];
p.on("pageerror", e => errs.push(e.message));
await p.goto("http://localhost:5174/", { waitUntil: "networkidle" });
await p.waitForTimeout(1800);
await p.locator("aside nav button", { hasText: /^Team$|^Equipo$|Team|Equipo/ }).first().click();
await p.waitForTimeout(1200);
// ir a la tab "Lo que pasó / actividad"
const tabAct = p.locator("button", { hasText: /What happened|Lo que pasó|Actividad|Activity/ }).first();
if (await tabAct.count()) { await tabAct.click(); await p.waitForTimeout(1400); }
const eq = await p.evaluate(() => {
  const main = document.querySelector("main")?.innerText || "";
  const filas = [...document.querySelectorAll("main .overflow-hidden > div")].length;
  return {
    resumen: /Used PolPilot|Usaron PolPilot|Team actions|Acciones del equipo/.test(main),
    filas,
    sinActividad: /No activity recorded|Sin actividad registrada/.test(main),
    whatsapp: /WhatsApp/.test(main),
    marta: main.includes("Marta"), nahuel: main.includes("Nahuel"),
  };
});
console.log("EQUIPO:", JSON.stringify(eq), "err:", errs.length, errs.slice(0,2));
// expandir la primera fila (Marta) y leer el detalle
const primera = p.locator("main .overflow-hidden > div button").first();
await primera.click();
await p.waitForTimeout(700);
const det = await p.evaluate(() => {
  const main = document.querySelector("main")?.innerText || "";
  return {
    consulta: /Asks Ángela|Le consulta/.test(main),
    hizo: /Did in the business|Hizo en el negocio/.test(main),
    modulos: /Has access to|Tiene habilitado/.test(main),
    acciones: /View as|Ver como/.test(main) && /Assign|Asignar/.test(main),
  };
});
console.log("DETALLE:", JSON.stringify(det));
await p.screenshot({ path: "../docs/shot-p34-equipo.png" });
await ctx.close();
await browser.close();
