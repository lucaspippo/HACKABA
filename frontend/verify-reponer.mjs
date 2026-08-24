// QUÉ REPONER PRIMERO — verificación real en Chromium.
// No escribe nada: es una vista de lectura, no hace falta restaurar el dataset.
import { chromium } from "playwright";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
const errores = [];
page.on("console", (m) => m.type() === "error" && errores.push(m.text()));
page.on("pageerror", (e) => errores.push("PAGEERROR " + e.message));

await page.goto("http://localhost:5174/", { waitUntil: "domcontentloaded" });
const navInv = page.getByRole("button", { name: /Inventario inteligente|Smart inventory/i }).first();
await navInv.waitFor({ state: "visible", timeout: 60000 });
await navInv.click();

const tab = page.getByRole("button", { name: /^Qué reponer$|^What to restock$/ }).first();
await tab.waitFor({ state: "visible", timeout: 30000 });
console.log("1· pestaña presente: OK");
await tab.click();
await page.waitForSelector("text=/won't reach|no les llega/", { timeout: 30000 });
await page.waitForTimeout(1200);

const v = await page.evaluate(() => {
  const txt = (document.querySelector("main") || document.body).innerText;
  return {
    titular: (txt.match(/[^\n]*(won't reach|no les llega)[^\n]*/) || [])[0],
    sub: (txt.match(/[^\n]*(stockout zone|zona de quiebre)[^\n]*/) || [])[0],
    filas: (txt.match(/\d+(\.\d+)? d late|\d+(\.\d+)? d tarde/g) || []).length,
    proveedores: (txt.match(/[^\n]*(takes \d+ days|tarda \d+ días)[^\n]*/g) || []).length,
    cuenta: /calculation, not an estimate|de una cuenta, no de una estimación/.test(txt),
  };
});
console.log("2· la vista:", JSON.stringify(v, null, 1));
await page.screenshot({ path: "../docs/shot-reponer.png" });

console.log("errores de consola:", errores.length ? errores.slice(0, 5) : "ninguno");
await browser.close();
