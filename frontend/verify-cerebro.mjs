// EL CEREBRO — verificación real en Chromium: que el toggle no rompa el mapa,
// que el grafo pinte, que el foco ilumine vecinos y que el camino de un
// hallazgo encienda nodos y aristas.
import { chromium } from "playwright";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
const errores = [];
page.on("console", (m) => m.type() === "error" && errores.push(m.text()));
page.on("pageerror", (e) => errores.push("PAGEERROR " + e.message));

// networkidle no sirve acá: /api/oportunidades tarda ~4s (preexistente) y la
// app poletea. Se espera por lo que importa, no por la red.
await page.goto("http://localhost:5174/", { waitUntil: "domcontentloaded" });

// --- 1 · el mapa de árbol sigue intacto detrás del toggle -------------------
const irAlMapa = page.getByRole("button", { name: /mapa de tu negocio|Business Map/i }).first();
await irAlMapa.waitFor({ state: "visible", timeout: 60000 });
await irAlMapa.click();
// el mapa de árbol pide 7 endpoints en paralelo y en dev tarda 16-25s en
// pintar. Medido contra el código SIN el toggle: es su ritmo de siempre, no
// algo que trajo el cerebro. Por eso la espera es generosa.
await page.waitForSelector(".react-flow__node", { timeout: 120000 });
await page.waitForTimeout(1500);
const arbol = await page.evaluate(() => ({
  nodos: document.querySelectorAll(".react-flow__node").length,
  edges: document.querySelectorAll(".react-flow__edge").length,
}));
console.log("1· mapa de árbol (debe seguir igual):", JSON.stringify(arbol));
await page.screenshot({ path: "../docs/shot-cerebro-0-mapa-intacto.png" });

// --- 2 · pasar al cerebro ---------------------------------------------------
await page.getByRole("button", { name: /^Cerebro$|^Brain$/ }).first().click();
await page.waitForSelector("canvas", { timeout: 30000 });
await page.waitForTimeout(16000); // que la simulación se asiente y haga sus encuadres

const meta = await page.evaluate(() => {
  const txt = document.body.innerText;
  const c = document.querySelector("canvas");
  return {
    // el demo arranca en EN: los textos se leen en los dos idiomas
    bajada: (txt.match(/[\d.,]+ (entidades reales|real entities)[^\n]*/) || [])[0] || null,
    canvas: c ? { w: c.width, h: c.height } : null,
    chips: [...document.querySelectorAll("button")].filter((b) =>
      /concentran|morosos|enfriando|quebrar|estrella|Ventana|dormido|margen|ofrece|carry too much|overdue customers|cooling off|run out of|is slipping|Buying window|sleeping stock|is offering|margin/i
        .test(b.innerText)).length,
  };
});
console.log("2· cerebro:", JSON.stringify(meta));
await page.screenshot({ path: "../docs/shot-cerebro-1-reposo.png" });

// ¿el canvas pintó de verdad, o es un rectángulo negro?
const pintado = await page.evaluate(() => {
  const c = document.querySelector("canvas");
  const ctx = c.getContext("2d");
  const d = ctx.getImageData(0, 0, c.width, c.height).data;
  const colores = new Set();
  let noFondo = 0;
  for (let i = 0; i < d.length; i += 4 * 97) {
    const k = `${d[i]},${d[i + 1]},${d[i + 2]}`;
    if (d[i] > 25 || d[i + 1] > 27 || d[i + 2] > 29) { noFondo++; colores.add(k); }
  }
  return { pixelesNoFondo: noFondo, coloresDistintos: colores.size };
});
console.log("   canvas pintado:", JSON.stringify(pintado));

// --- 3 · foco: click en un nodo del núcleo → panel + vecinos ---------------
const chipNucleo = page.locator("button", { hasText: /conexiones|connections/ }).first();
await chipNucleo.click();
await page.waitForTimeout(2500);
const panel = await page.evaluate(() => {
  const p = [...document.querySelectorAll("div")].find((d) =>
    d.className.includes("w-[318px]"));
  return p ? p.innerText.slice(0, 420) : null;
});
console.log("3· panel de la entidad:\n" + (panel || "NO ABRIÓ"));
await page.screenshot({ path: "../docs/shot-cerebro-2-foco.png" });

// --- 4 · el camino de un hallazgo ------------------------------------------
const chipHallazgo = page.locator("button", { hasText: /Vas a quebrar stock|going to run out of/i }).first();
if (await chipHallazgo.count()) {
  await chipHallazgo.click();
  await page.waitForTimeout(3000);
  const camino = await page.evaluate(() => {
    const t = document.body.innerText;
    return (t.match(/Camino encendido · \d+ entidades cruzadas|Path lit · \d+ entities crossed/) || [])[0] || null;
  });
  console.log("4· camino encendido:", camino);
  await page.screenshot({ path: "../docs/shot-cerebro-3-camino.png" });
} else {
  console.log("4· NO se encontró el chip del quiebre");
}

// --- 5 · el mismo recorrido en español (el idioma de la grabación) ---------
// el botón dice "es" en el DOM (el uppercase es CSS): el nombre accesible es minúscula
await page.getByRole("button", { name: /^es$/i }).first().click();
await page.waitForTimeout(9000);
const es = await page.evaluate(() => {
  const txt = document.body.innerText;
  return {
    titulo: /El cerebro de tu negocio/.test(txt),
    bajada: (txt.match(/[\d.,]+ entidades reales[^\n]*/) || [])[0] || null,
    // ninguna clave i18n sin traducir puede quedar a la vista
    crudas: (txt.match(/cerebro\.[a-z_]+/g) || []).slice(0, 5),
  };
});
console.log("5· en español:", JSON.stringify(es, null, 1));
await page.screenshot({ path: "../docs/shot-cerebro-4-es.png" });

console.log("errores de consola:", errores.length ? errores.slice(0, 6) : "ninguno");
await browser.close();
