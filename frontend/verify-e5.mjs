// P35·E5 — verificación contra el BUILD servido por el backend (localhost:8000),
// mismo origen que Render. Densidad + mapa (innegociable) + branding + overflow.
import { chromium } from "playwright";
const URL = "http://localhost:8000/";
const browser = await chromium.launch();

async function homeMetrics(w, h) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h } });
  const p = await ctx.newPage();
  await p.goto(URL, { waitUntil: "networkidle" });
  await p.waitForSelector("aside nav button", { timeout: 15000 });
  await p.waitForTimeout(1500);
  const r = await p.evaluate(() => {
    const grids = [...document.querySelectorAll("main .grid")];
    let cols = null, cardW = null;
    for (const g of grids) {
      const hijos = [...g.children];
      if (hijos.length !== 4) continue;
      const rects = hijos.map((c) => c.getBoundingClientRect());
      if (rects.every((x) => x.width > 140 && x.height > 100)) {
        const top0 = Math.round(rects[0].top);
        cols = rects.filter((x) => Math.abs(x.top - top0) < 4).length;
        cardW = Math.round(rects[0].width);
        break;
      }
    }
    const logos = [...document.querySelectorAll("aside img")].map((i) => i.getAttribute("src"));
    return {
      rootFont: getComputedStyle(document.documentElement).fontSize,
      hallazgosCols: cols, cardW,
      branding: logos.some((s) => s?.includes("litoral")) ? "litoral" : logos.some((s) => s?.includes("piloto")) ? "piloto" : "?",
      overflowX: document.documentElement.scrollWidth > window.innerWidth + 2,
    };
  });
  console.log(`HOME ${w}x${h}:`, JSON.stringify(r));
  await p.screenshot({ path: `../docs/shot-p35-home-${w}.png` });
  await ctx.close();
}
await homeMetrics(1440, 900);
await homeMetrics(1280, 800);
await homeMetrics(1920, 1080);

// MAPA — innegociable
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const p = await ctx.newPage();
const errs = [];
p.on("pageerror", (e) => errs.push(e.message));
await p.goto(URL, { waitUntil: "networkidle" });
await p.waitForSelector("aside nav button", { timeout: 15000 });
await p.waitForTimeout(1500);
await p.locator("aside nav button", { hasText: /Business Map/i }).first().click();
await p.waitForSelector(".react-flow__node", { timeout: 20000 }).catch(() => {});
await p.waitForTimeout(2500);
const mapa = await p.evaluate(() => {
  const rf = document.querySelector(".react-flow");
  const nodos = document.querySelectorAll(".react-flow__node");
  const rfr = rf?.getBoundingClientRect();
  let fuera = 0;
  for (const n of nodos) {
    const b = n.getBoundingClientRect();
    if (rfr && (b.right < rfr.left - 1 || b.left > rfr.right + 1 || b.bottom < rfr.top - 1 || b.top > rfr.bottom + 1)) fuera++;
  }
  return { rf: !!rf, nodos: nodos.length, canvasH: Math.round(rfr?.height || 0), nodosFuera: fuera,
           overflowX: document.documentElement.scrollWidth > window.innerWidth + 2 };
});
console.log("MAPA 1440x900:", JSON.stringify(mapa), "errs:", errs.slice(0, 2));
await p.screenshot({ path: "../docs/shot-p35-mapa-1440.png" });
await ctx.close();
await browser.close();
