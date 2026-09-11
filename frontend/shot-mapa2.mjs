// P29·C — verificación del "mapa que produce": caminos, conclusiones,
// expansión multinivel, fila inferior. Chromium real (compositing).
import { chromium } from "playwright";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } });
const errores = [];
page.on("pageerror", (e) => errores.push(e.message));
await page.goto("http://localhost:5174/", { waitUntil: "networkidle" });
await page.waitForTimeout(1500);
await page.getByRole("button", { name: /mapa de tu negocio|Business Map/i }).first().click();
await page.waitForSelector(".react-flow__node", { timeout: 15000 });
await page.waitForTimeout(1600);

const base = await page.evaluate(() => ({
  nodos: document.querySelectorAll(".react-flow__node").length,
  edges: document.querySelectorAll(".react-flow__edge").length,
  contadores: [...document.querySelectorAll(".react-flow__node .bg-violeta")].map((e) => e.textContent).filter((x) => /^\d+$/.test(x)),
  filaAbajo: [...document.querySelectorAll("main button")].map((b) => b.innerText.replace(/\n/g, " | ")).filter((x) => x.includes("|") && (x.includes("$") || /\d/.test(x))).slice(-4),
}));
console.log("BASE:", JSON.stringify(base, null, 1));
await page.screenshot({ path: "../docs/shot-p29-mapa.png" });

// --- CAMINO: tocar el hallazgo top del pulso ("Últimos cruces") ---------------
const cruce = page.locator("aside").last().getByRole("button").filter({ hasText: /\$/ }).first();
// mejor: el primer HallazgoChip del pulso (panel izquierdo)
const chip = page.locator("button", { hasText: /Ventana de compra|Buying window|3 clientes|3 customers|capital/ }).first();
await chip.click();
await page.waitForTimeout(1800); // deja correr la animación del camino
const camino = await page.evaluate(() => ({
  edgesCamino: document.querySelectorAll(".react-flow__edge[data-id^='cam-']").length ||
    [...document.querySelectorAll(".react-flow__edge")].filter((e) => (e.getAttribute("data-id") || "").startsWith("cam-")).length,
  panel: (document.querySelector("aside:last-of-type")?.innerText || "").slice(0, 400),
}));
console.log("CAMINO:", JSON.stringify(camino, null, 1));
await page.screenshot({ path: "../docs/shot-p29-camino.png" });

// --- CONCLUSIONES: click en el nodo Clientes ----------------------------------
await page.evaluate(() => {
  const n = document.querySelector('[data-id="clientes"]');
  const r = n.getBoundingClientRect();
  const o = { bubbles: true, cancelable: true, clientX: r.x + r.width / 2, clientY: r.y + r.height / 2, button: 0 };
  n.dispatchEvent(new MouseEvent("mousedown", o));
  n.dispatchEvent(new MouseEvent("mouseup", o));
  n.dispatchEvent(new MouseEvent("click", o));
});
await page.waitForTimeout(700);
const concl = await page.evaluate(() => (document.querySelector("aside:last-of-type")?.innerText || "").slice(0, 500));
console.log("CONCLUSIONES clientes:", JSON.stringify(concl));

// --- EXPANSIÓN multinivel: doble-click Clientes → segmentos → doble sub -------
await page.evaluate(() => {
  const n = document.querySelector('[data-id="clientes"]');
  const r = n.getBoundingClientRect();
  n.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, clientX: r.x + 10, clientY: r.y + 10, detail: 2 }));
});
await page.waitForTimeout(900);
const nivel1 = await page.evaluate(() =>
  [...document.querySelectorAll(".react-flow__node")].filter((n) => (n.getAttribute("data-id") || "").startsWith("clientes:")).map((n) => n.textContent));
console.log("NIVEL 1 (segmentos):", JSON.stringify(nivel1));
// expandir el segmento "en riesgo"
await page.evaluate(() => {
  const n = document.querySelector('[data-id="clientes:riesgoso"]');
  if (!n) return;
  const r = n.getBoundingClientRect();
  n.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, clientX: r.x + 10, clientY: r.y + 10, detail: 2 }));
});
await page.waitForTimeout(1200);
const nivel2 = await page.evaluate(() => ({
  hijos: [...document.querySelectorAll(".react-flow__node")].filter((n) => (n.getAttribute("data-id") || "").includes(":riesgoso>") || (n.getAttribute("data-id") || "").includes(">")).map((n) => n.textContent),
  breadcrumb: [...document.querySelectorAll(".backdrop-blur")].map((e) => e.innerText).find((x) => x && x.includes("›")) || [...document.querySelectorAll("button")].map((b) => b.textContent).filter((x) => /Client|riesg|risk/i.test(x)).slice(0, 3),
}));
console.log("NIVEL 2:", JSON.stringify(nivel2));
await page.screenshot({ path: "../docs/shot-p29-expansion.png" });

console.log("ERRORES:", errores.length, errores.slice(0, 3));
await browser.close();
