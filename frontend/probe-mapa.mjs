// Sonda de auditoría: ¿el mapa de árbol dibuja nodos Y aristas?
// Chromium real (compone frames), a diferencia del panel embebido.
import { chromium } from "playwright";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
const errores = [];
page.on("console", (m) => m.type() === "error" && errores.push(m.text().slice(0, 200)));
page.on("pageerror", (e) => errores.push("PAGEERROR " + e.message.slice(0, 200)));

await page.goto("http://localhost:5174/", { waitUntil: "domcontentloaded" });
await page.waitForTimeout(5000);

// ir al mapa
await page.getByRole("button", { name: /^(Your Business Map|El mapa de tu negocio)$/ }).first().click();
const t0 = Date.now();
await page.waitForFunction(() => document.querySelectorAll(".react-flow__node").length > 0, { timeout: 90000 })
  .catch(() => console.log("MAPA: nunca aparecieron nodos en 90s"));
console.log("MAPA tardo (ms):", Date.now() - t0);
await page.waitForTimeout(3000);

const medida = await page.evaluate(() => {
  const ns = Array.from(document.querySelectorAll(".react-flow__node"));
  const cont = document.querySelector(".react-flow__edges");
  return {
    nodos: ns.length,
    ocultos: ns.filter((n) => n.style.visibility === "hidden").length,
    edgePaths: cont ? cont.querySelectorAll("path.react-flow__edge-path").length : -1,
    viewport: document.querySelector(".react-flow__viewport")?.style.transform,
    contenedor: (() => { const r = document.querySelector(".react-flow"); return r && { w: r.clientWidth, h: r.clientHeight }; })(),
  };
});
console.log("MAPA:", JSON.stringify(medida));
await page.screenshot({ path: "../docs/probe-mapa.png" });

// y el cerebro, para comparar
await page.getByRole("button", { name: /^(Brain|Cerebro)$/ }).first().click();
await page.waitForTimeout(10000);
const cerebro = await page.evaluate(() => ({
  canvas: document.querySelectorAll("canvas").length,
  ancho: document.querySelector("canvas")?.width || 0,
}));
console.log("CEREBRO:", JSON.stringify(cerebro));
await page.screenshot({ path: "../docs/probe-cerebro.png" });

console.log("ERRORES:", errores.length ? JSON.stringify(errores.slice(0, 6)) : "ninguno");
await browser.close();
