// Sonda de auditoría integral: recorre TODAS las secciones en los dos idiomas
// y busca (a) claves i18n crudas en pantalla, (b) mezcla de idiomas,
// (c) placeholders olvidados, (d) errores de consola.
import { chromium } from "playwright";

const SECCIONES_EN = ["Home", "Your Business Map", "Alerts", "Opportunities", "Trend",
  "Cash & finances", "Daily register", "Customer accounts", "Collections",
  "Smart inventory", "Data to fix", "Warehouse", "Team", "Load data", "Documents",
  "Audit trail", "My profile"];
const SECCIONES_ES = ["Inicio", "El mapa de tu negocio", "Alertas", "Oportunidades", "Evolución",
  "Caja y finanzas", "Caja diaria", "Cuentas corrientes", "Cobranzas",
  "Inventario inteligente", "Datos a corregir", "Depósito", "Equipo", "Cargar datos",
  "Documentos", "Registro", "Mi perfil"];

// Una clave i18n cruda: "cerebro.buscar", "audit.tile_total"...
const RE_CLAVE = /\b[a-z][a-z0-9]*(?:_[a-z0-9]+)*\.[a-z][a-z0-9_]{2,}\b/g;
// Palabras que sólo existen en uno de los dos idiomas (marcadores de mezcla).
const MARCA_ES = /\b(cobranzas|depósito|proveedor(es)?|clientes|ventas|inventario|plata|deuda|vencimiento|entidades|hallazgo|aprobar|cargar)\b/i;
const MARCA_EN = /\b(collections|warehouse|suppliers?|customers|sales|inventory|money|debt|expiry|entities|finding|approve|upload)\b/i;
const PLACEHOLDERS = /(lorem ipsum|TODO:|FIXME|coming soon|próximamente|proximamente|placeholder|xxx+|\bTBD\b)/i;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
const errores = [];
page.on("console", (m) => m.type() === "error" && errores.push(m.text().slice(0, 220)));
page.on("pageerror", (e) => errores.push("PAGEERROR " + e.message.slice(0, 220)));
const fallosRed = [];
page.on("response", (r) => {
  if (r.url().includes("/api/") && r.status() >= 400)
    fallosRed.push(`${r.status()} ${r.url().replace(/^https?:\/\/[^/]+/, "")}`);
});

await page.goto("http://localhost:5174/", { waitUntil: "domcontentloaded" });
await page.waitForTimeout(6000);

async function recorrer(lista, idioma) {
  const hallazgos = [];
  for (const s of lista) {
    const btn = page.getByRole("button", { name: new RegExp(`^${s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`) }).first();
    if (!(await btn.count())) { hallazgos.push([s, "SIN BOTON"]); continue; }
    await btn.click().catch(() => {});
    // el mapa tarda: esperar a que deje de decir "cruzando"
    await page.waitForTimeout(s.includes("Map") || s.includes("mapa") ? 14000 : 2800);
    const txt = await page.locator("main").innerText().catch(() => "");
    const claves = [...new Set((txt.match(RE_CLAVE) || []))]
      // los nombres de archivo y dominios no son claves i18n
      .filter((k) => !/\.(csv|xlsx?|json|png|jpe?g|pdf|com|ar|py|js)$/i.test(k));
    const ph = txt.match(PLACEHOLDERS);
    const mezcla = idioma === "en" ? (txt.match(MARCA_ES) || [])[0] : (txt.match(MARCA_EN) || [])[0];
    if (claves.length || ph || mezcla)
      hallazgos.push([s, { claves: claves.slice(0, 6), placeholder: ph && ph[0], mezcla }]);
  }
  return hallazgos;
}

console.log("=== EN === (salteado, ya verificado)");

// cambiar a ES
await page.evaluate(() => Array.from(document.querySelectorAll("button")).find((b) => b.innerText.trim() === "ES")?.click());
await page.waitForTimeout(6000);
console.log("=== ES ===");
console.log(JSON.stringify(await recorrer(SECCIONES_ES, "es"), null, 1));

// volver a EN (default del tenant)
await page.evaluate(() => Array.from(document.querySelectorAll("button")).find((b) => b.innerText.trim() === "EN")?.click());
await page.waitForTimeout(4000);

console.log("=== CONSOLA ===", errores.length ? JSON.stringify([...new Set(errores)].slice(0, 8)) : "sin errores");
console.log("=== RED 4xx/5xx ===", fallosRed.length ? JSON.stringify([...new Set(fallosRed)].slice(0, 10)) : "ninguno");
await browser.close();
