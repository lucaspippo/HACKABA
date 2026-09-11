// P28 — verificación REAL del mapa en un Chromium con compositing:
// carga, edges, hover-focus, click→insight, expandir, y screenshots de prueba.
import { chromium } from "playwright";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
await page.goto("http://localhost:5174/", { waitUntil: "networkidle" });
await page.waitForTimeout(1500);

// entrar al mapa
await page.getByRole("button", { name: /mapa de tu negocio|Business Map/i }).first().click();
await page.waitForSelector(".react-flow__node", { timeout: 15000 });
await page.waitForTimeout(1500); // medición + fitView

const estado = await page.evaluate(() => ({
  nodos: document.querySelectorAll(".react-flow__node").length,
  visibles: [...document.querySelectorAll(".react-flow__node")]
    .filter((n) => getComputedStyle(n).visibility !== "hidden").length,
  edges: document.querySelectorAll(".react-flow__edge").length,
  animados: document.querySelectorAll(".react-flow__edge.animated").length,
  viewport: document.querySelector(".react-flow__viewport")?.style.transform,
}));
console.log("estado inicial:", JSON.stringify(estado));

await page.screenshot({ path: "../docs/shot-p28-mapa.png" });

// hover sobre Clientes: sus conexiones se iluminan, el resto se atenúa
await page.hover('[data-id="clientes"]');
await page.waitForTimeout(400);
const hover = await page.evaluate(() => ({
  apagados: [...document.querySelectorAll(".react-flow__node .rf-apagado")]
    .map((n) => n.closest(".react-flow__node").getAttribute("data-id")),
}));
console.log("hover clientes -> apagados:", JSON.stringify(hover.apagados));
await page.screenshot({ path: "../docs/shot-p28-mapa-hover.png" });

// click: insight en el panel de Ángela
await page.click('[data-id="clientes"]');
await page.waitForTimeout(600);
const insight = await page.evaluate(() => {
  const asides = [...document.querySelectorAll("aside")];
  return asides[asides.length - 1]?.innerText.slice(0, 300);
});
console.log("insight:", JSON.stringify(insight));

// expandir: doble click en clientes
await page.dblclick('[data-id="proveedores"]');
await page.waitForTimeout(700);
const subs = await page.evaluate(() =>
  [...document.querySelectorAll(".react-flow__node")]
    .filter((n) => (n.getAttribute("data-id") || "").includes(":")).length);
console.log("sub-nodos tras expandir proveedores:", subs);
await page.screenshot({ path: "../docs/shot-p28-mapa-expandido.png" });

await browser.close();
console.log("listo");
