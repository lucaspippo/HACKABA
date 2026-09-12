// COBRANZA AGÉNTICA — verificación real en Chromium.
//
// ESCRIBE de verdad al registrar la gestión: restaura el dataset al terminar.
import { chromium } from "playwright";
import { rmSync } from "node:fs";

const RAIZ = "../..";
const restaurar = () =>
  rmSync(`${RAIZ}/polpilot-demo/data-demo/cobranza.json`, { force: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
const errores = [];
page.on("console", (m) => m.type() === "error" && errores.push(m.text()));
page.on("pageerror", (e) => errores.push("PAGEERROR " + e.message));
const zona = () => page.evaluate(() =>
  (document.querySelector("main") || document.body).innerText);

// OJO: "Cobranzas" es la vista del PREVENTISTA (diego/lucia), no la del dueño
// — el autologin entra como Aldo, que no tiene esa feature. Se entra como
// preventista, que es de quien es la pantalla.
await page.goto("http://localhost:5174/", { waitUntil: "domcontentloaded" });
await page.waitForTimeout(2500);
// login por API y sesión escrita directo: el autologin del demo vuelve a
// entrar como Aldo apenas se limpia, y pelear con el formulario no prueba nada
// que importe acá.
await page.evaluate(async () => {
  const r = await fetch("/api/login", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: "diego",
      // La contraseña fija que siembra data-demo/seed_db.py. Antes acá
      // había una generada al azar, pegada a mano y ya vencida: una
      // credencial literal en el repo que además no servía.
      password: process.env.POLPILOT_DEMO_PASSWORD || "demo-password",
    }),
  });
  localStorage.setItem("polpilot.session.v1", JSON.stringify(await r.json()));
  sessionStorage.setItem("polpilot.logout.manual", "1");   // que no re-autologuee
});
await page.reload({ waitUntil: "domcontentloaded" });

const nav = page.getByRole("button", { name: /^Cobranzas$|^Collections$/ }).first();
await nav.waitFor({ state: "visible", timeout: 60000 });
await nav.click();
await page.waitForSelector("text=/Start here|Por acá empezá/", { timeout: 30000 });
await page.waitForTimeout(1000);

// --- 1 · el orden: deber menos puede ir antes -----------------------------
const t1 = await zona();
const orden = (t1.match(/^\d+\n?.*$/gm) || []);
const clientes = [...t1.matchAll(/(Autoservicio 9 de Julio|Despensa Doña Elsa|Almacén San Martín)/g)]
  .map((m) => m[1]);
console.log("1· orden de cobranza:", JSON.stringify(clientes));
console.log("   liquidez:", (t1.match(/[^\n]*(comes in if you collect|entra si cobrás)[^\n]*/) || [])[0]);
await page.screenshot({ path: "../docs/shot-cobranza-0-orden.png" });

// --- 2 · la propuesta: Ángela redacta, nadie manda todavía -----------------
await page.locator("button").filter({ hasText: /Despensa Doña Elsa/ }).first().click();
await page.waitForSelector("text=/Shall I send|Le mando esto/", { timeout: 20000 });
await page.waitForTimeout(700);
const t2 = await zona();
console.log("2· propuesta:", JSON.stringify({
  pregunta: (t2.match(/[^\n]*(Shall I send|Le mando esto)[^\n]*/) || [])[0],
  mensajeTieneMonto: /19[.,]200[.,]000|19,200,000/.test(t2),
  mensajeTieneDias: /66/.test(t2),
}, null, 1));
await page.screenshot({ path: "../docs/shot-cobranza-1-propuesta.png" });

// --- 3 · el sí humano: recién acá se registra ------------------------------
await page.getByRole("button", { name: /^Send$|^Mandar$/ }).first().click();
await page.waitForTimeout(2500);
const t3 = await zona();
console.log("3· tras aprobar:", JSON.stringify({
  estado: /Reminded|Recordado/.test(t3),
}, null, 1));
await page.screenshot({ path: "../docs/shot-cobranza-2-registrado.png" });

console.log("errores de consola:", errores.length ? errores.slice(0, 5) : "ninguno");
await browser.close();
restaurar();
console.log("dataset del demo restaurado.");
