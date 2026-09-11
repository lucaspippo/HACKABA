import { chromium } from "playwright";

const browser = await chromium.launch();

// --- MOBILE ---
const m = await browser.newPage({ viewport: { width: 402, height: 874 }, deviceScaleFactor: 2 });
await m.goto("http://localhost:5173/", { waitUntil: "networkidle" });
await m.waitForTimeout(1600);
const mobileTabs = [
  { tab: null, name: "m1-hoy" },
  { tab: "Oportunidades", name: "m2-oportunidades" },
  { tab: "Equipo", name: "m3-equipo" },
];
for (const v of mobileTabs) {
  if (v.tab) {
    await m.getByRole("button", { name: v.tab, exact: false }).first().click();
    await m.waitForTimeout(700);
  }
  await m.screenshot({ path: `../docs/shot-${v.name}.png` });
  console.log("mobile:", v.name);
}
await m.close();

// --- DESKTOP ---
const d = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
await d.goto("http://localhost:5173/", { waitUntil: "networkidle" });
await d.waitForTimeout(1600);
const desktopNav = [
  { nav: null, name: "d1-inicio" },
  { nav: "Inventario inteligente", name: "d2-inventario" },
  { nav: "Caja y finanzas", name: "d3-finanzas" },
  { nav: "Alertas y oportunidades", name: "d4-alertas" },
  { nav: "Cargar datos", name: "d5-cargar" },
];
for (const v of desktopNav) {
  if (v.nav) {
    await d.getByRole("button", { name: v.nav, exact: false }).first().click();
    await d.waitForTimeout(800);
  }
  await d.screenshot({ path: `../docs/shot-${v.name}.png` });
  console.log("desktop:", v.name);
}
// Ángela panel + navegación
await d.getByRole("button", { name: "Ángela", exact: false }).first().click();
await d.waitForTimeout(500);
await d.getByText("Mostrame las balanzas mal calibradas").click();
await d.waitForTimeout(2500);
await d.screenshot({ path: "../docs/shot-d6-angela-nav.png" });
console.log("desktop: d6-angela-nav");
await d.close();

await browser.close();
console.log("listo");
