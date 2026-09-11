import { chromium } from "playwright";

const views = [
  { tab: null, name: "01-inicio" },
  { tab: "Inventario", name: "02-inventario" },
  { tab: "Ángela", name: "03-angela" },
  { tab: "Alertas", name: "04-alertas" },
  { tab: "Equipo", name: "05-equipo" },
];

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 402, height: 874 },
  deviceScaleFactor: 2,
});
await page.goto("http://localhost:5173/", { waitUntil: "networkidle" });
await page.waitForTimeout(1800); // dejar correr el count-up

for (const v of views) {
  if (v.tab) {
    await page.getByRole("button", { name: v.tab, exact: false }).first().click();
    await page.waitForTimeout(900);
  }
  await page.screenshot({ path: `../docs/shot-${v.name}.png` });
  console.log("shot:", v.name);
}
await browser.close();
console.log("listo");
