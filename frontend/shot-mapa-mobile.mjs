// P29·D — el mapa en mobile: versión apilada navegable. Hallazgos arriba
// (tap → explicación + camino textual), dominios como lista tocable con
// contador y semáforo, tap → conclusiones inline.
import { chromium } from "playwright";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 402, height: 874 }, deviceScaleFactor: 2 });
await page.goto("http://localhost:5174/", { waitUntil: "networkidle" });
await page.waitForTimeout(1500);

const abrir = async () => {
  const directo = page.getByRole("button", { name: /mapa de tu negocio|Business Map/i });
  if (await directo.count()) { await directo.first().click(); return true; }
  const mas = page.getByRole("button", { name: /^Más$|^More$/ });
  if (await mas.count()) {
    await mas.first().click();
    await page.waitForTimeout(400);
    const enMas = page.getByRole("button", { name: /mapa de tu negocio|Business Map/i });
    if (await enMas.count()) { await enMas.first().click(); return true; }
  }
  return false;
};
console.log("abrió mapa:", await abrir());
await page.waitForTimeout(2200);
await page.screenshot({ path: "../docs/shot-p29-mobile.png" });

// tap en un hallazgo → explicación + camino textual
const hall = page.getByText(/Ventana de compra|Buying window|3 clientes|3 customers/).first();
await hall.click();
await page.waitForTimeout(600);
const txt = await page.evaluate(() => (document.querySelector("main")?.innerText || ""));
console.log("hallazgo con camino:", JSON.stringify(txt.split("\n").filter((l) => l.includes("→") || l.includes("crucé") || l.includes("crossed") || l.includes("Crucé")).slice(0, 3)));

// tap en un dominio → conclusiones inline
await page.getByText(/^Clientes$|^Customers$/).first().click();
await page.waitForTimeout(500);
const concl = await page.evaluate(() => {
  const main = document.querySelector("main")?.innerText || "";
  return main.split("\n").filter((l) => l.startsWith("·")).slice(0, 3);
});
console.log("conclusiones inline:", JSON.stringify(concl));
await page.screenshot({ path: "../docs/shot-p29-mobile-nodo.png" });
await browser.close();
console.log("listo");
