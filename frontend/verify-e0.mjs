// E0 — verificación: los sub-nodos de categoría (Inventario y Ventas) se
// traducen EN/ES; el rol del sub-nodo de Equipo también. Nombres propios
// (proveedores, clientes, SKUs) NO se traducen. Solo se muestran 6 de 8 rubros
// (top por $), así que la aserción es: en EN ningún rubro en español se cuela y
// aparecen ≥3 en inglés; y a la inversa en ES.
import { chromium } from "playwright";
const browser = await chromium.launch();

const CAT_ES = ["aceites y aderezos", "almacén seco", "bebidas", "congelados",
  "fiambres y quesos (balanza)", "galletitas y golosinas", "limpieza y perfumería", "lácteos"];
const CAT_EN = ["Oils & dressings", "Dry goods", "Beverages", "Frozen",
  "Cold cuts & cheese (scale)", "Cookies & candy", "Cleaning & toiletries", "Dairy"];

async function expandirYleer(page, dominio) {
  // colapsar cualquier otro y expandir este (solo uno abierto a la vez)
  await page.click(`[data-id="${dominio}"] button[data-expand="1"]`).catch(() => {});
  await page.waitForTimeout(1600); // fetch async de consulta-serie
  return page.evaluate(() =>
    [...document.querySelectorAll(".react-flow__node")]
      .filter((n) => (n.getAttribute("data-id") || "").includes(":"))
      .map((n) => n.innerText.replace(/\n+/g, " ").trim()).join(" | "));
}

async function run(lang) {
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 950 } });
  const page = await ctx.newPage();
  const errores = [];
  page.on("pageerror", (e) => errores.push(e.message));
  await page.goto("http://localhost:5174/", { waitUntil: "networkidle" });
  await page.waitForTimeout(1200);
  await page.locator("header button", { hasText: new RegExp(`^${lang}$`, "i") }).first().click().catch(() => {});
  await page.waitForTimeout(2600); // POST idioma + authStore.refresh + re-fetch
  await page.getByRole("button", { name: /mapa de tu negocio|Business Map/i }).first().click();
  await page.waitForSelector(".react-flow__node", { timeout: 20000 });
  await page.waitForTimeout(1200);

  const inv = await expandirYleer(page, "inventario");
  await page.screenshot({ path: `../docs/shot-e0-mapa-${lang}.png` });
  const ven = await expandirYleer(page, "ventas");
  const eq = await expandirYleer(page, "equipo");
  const texto = [inv, ven].join(" | ");

  const propias = lang === "en" ? CAT_EN : CAT_ES;
  const ajenas = lang === "en" ? CAT_ES : CAT_EN;
  const presentes = propias.filter((s) => texto.includes(s));
  const coladas = ajenas.filter((s) => texto.includes(s));
  const rolTraducido = lang === "en"
    ? /Warehouse|Sales rep|Front counter|Purchasing|Administration|Owner|Manager/.test(eq)
    : /depósito|Preventista|Mostrador|Compras|Administración|Dueño|Encargad/.test(eq);
  const rolAjeno = lang === "en"
    ? /Encargado de depósito|Preventista|Mostrador · Casa/.test(eq)
    : /Warehouse manager|Sales rep|Front counter/.test(eq);

  const ok = presentes.length >= 3 && coladas.length === 0 && rolTraducido && !rolAjeno && errores.length === 0;
  console.log(`\n[${lang}] ${ok ? "OK ✓" : "FALLA ✗"}`);
  console.log(`  rubros propios presentes (${presentes.length}/6 visibles):`, JSON.stringify(presentes));
  console.log(`  rubros del otro idioma colados:`, JSON.stringify(coladas));
  console.log(`  rol equipo traducido:`, rolTraducido, "| rol ajeno colado:", rolAjeno);
  console.log(`  equipo subs:`, JSON.stringify(eq.slice(0, 260)));
  if (errores.length) console.log(`  pageerror:`, JSON.stringify(errores));
  await ctx.close();
  return ok;
}

const a = await run("en");
const b = await run("es");
await browser.close();
console.log(`\n=== E0 ${a && b ? "VERIFICADO ✓" : "CON FALLAS ✗"} ===`);
process.exit(a && b ? 0 : 1);
