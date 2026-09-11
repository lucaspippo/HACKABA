import { chromium } from "playwright";

// Capturas de las vistas por rol (tenant piloto de ejemplo). Las contraseñas NO
// viven en el repo: se generan en el primer arranque y quedan en
// backend/credenciales.json (piloto) o <data dir>/credenciales.json (demo).
// Pasalas por env antes de correr el script:
//   POLPILOT_PASS_DUENO / POLPILOT_PASS_VENDEDOR / POLPILOT_PASS_DEPOSITO
const PASS_DUENO = process.env.POLPILOT_PASS_DUENO || "";
const PASS_VENDEDOR = process.env.POLPILOT_PASS_VENDEDOR || "";
const PASS_DEPOSITO = process.env.POLPILOT_PASS_DEPOSITO || "";

const browser = await chromium.launch();

async function login(page, user, pass) {
  await page.getByPlaceholder("tu usuario").fill(user);
  await page.getByPlaceholder("••••••••").fill(pass);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForTimeout(1800);
}
async function logout(page) {
  // botón de logout (ícono) — el último botón del sidebar/header
  await page.locator("button:has(svg.lucide-log-out)").first().click();
  await page.waitForTimeout(1000);
}

// ---------- DESKTOP ----------
const d = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
await d.goto("http://localhost:5173/", { waitUntil: "networkidle" });
await d.waitForTimeout(800);
await d.screenshot({ path: "shots/s2-login.png" });
console.log("login");

await login(d, "emilio", PASS_DUENO);
await d.screenshot({ path: "shots/s2-dueno-inicio.png" });
console.log("dueño inicio");

await d.getByRole("button", { name: "Inventario inteligente", exact: false }).first().click();
await d.waitForTimeout(1200);
await d.screenshot({ path: "shots/s2-dueno-inventario.png", fullPage: true });
console.log("dueño inventario (charts)");

await d.getByRole("button", { name: "Gestión de equipo", exact: false }).first().click();
await d.waitForTimeout(900);
await d.screenshot({ path: "shots/s2-dueno-gestion.png", fullPage: true });
console.log("dueño gestion equipo");

await logout(d);
await d.screenshot({ path: "shots/s2-logout-login.png" });

await login(d, "vendedor", PASS_VENDEDOR);
await d.screenshot({ path: "shots/s2-vendedor.png" });
console.log("vendedor");

await logout(d);
await login(d, "deposito", PASS_DEPOSITO);
await d.screenshot({ path: "shots/s2-deposito.png", fullPage: true });
console.log("deposito");
await d.close();

// ---------- MOBILE (dueño) ----------
const m = await browser.newPage({ viewport: { width: 402, height: 874 }, deviceScaleFactor: 2 });
await m.goto("http://localhost:5173/", { waitUntil: "networkidle" });
await m.waitForTimeout(600);
await login(m, "emilio", PASS_DUENO);
await m.screenshot({ path: "shots/s2-m-dueno-hoy.png" });
console.log("mobile dueño hoy");
await m.close();

await browser.close();
console.log("listo");
