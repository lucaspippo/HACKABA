// LA VOZ DEL PISO — verificación real en Chromium.
//
// Web Speech API no se puede accionar desde Playwright (necesita micrófono y
// permiso del usuario), así que se verifica lo que importa y sí es verificable:
// que la tubería completa —transcripción → interpretación → validación
// determinista → aprobación humana— funcione. Las frases preparadas recorren
// EXACTAMENTE el mismo camino que una voz real; solo cambia de dónde sale el
// texto.
//
// ESCRIBE de verdad al confirmar: restaura el dataset al terminar.
import { chromium } from "playwright";
import { rmSync } from "node:fs";

const RAIZ = "../..";
// con fs, no con `rm`: el script tiene que correr igual desde bash o PowerShell
const restaurar = () =>
  rmSync(`${RAIZ}/polpilot-demo/data-demo/piso.json`, { force: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
const errores = [];
page.on("console", (m) => m.type() === "error" && errores.push(m.text()));
page.on("pageerror", (e) => errores.push("PAGEERROR " + e.message));

const zona = () => page.evaluate(() =>
  document.querySelector("div.fixed.inset-0.z-50")?.innerText || "");

await page.goto("http://localhost:5174/", { waitUntil: "domcontentloaded" });
const navDep = page.getByRole("button", { name: /^Depósito$|^Warehouse$/ }).first();
await navDep.waitFor({ state: "visible", timeout: 60000 });
await navDep.click();

const abrir = page.getByRole("button", { name: /Decirle a Ángela|Tell Ángela/i }).first();
await abrir.waitFor({ state: "visible", timeout: 30000 });
console.log("1· botón de voz en Depósito: OK");
await abrir.click();

const M = () => page.locator("div.fixed.inset-0.z-50");
const enModal = (re) => M().locator("button").filter({ hasText: re });
const frase = enModal(/«/);
await frase.first().waitFor({ state: "visible", timeout: 20000 });
console.log("2· frases preparadas ofrecidas:", await frase.count());
await page.screenshot({ path: "../docs/shot-voz-0-abierto.png" });

// --- 3 · el caso que DEBE pasar limpio: ocho cajas falladas ----------------
await enModal(/falladas de gaseosa/i).first().click();
await page.waitForSelector("text=/Entendí|I understood/", { timeout: 25000 });
await page.waitForTimeout(800);
const t3 = await zona();
const btnOk = enModal(/anotalo|note it/i).first();
console.log("3· «ocho cajas falladas»:", JSON.stringify({
  entendio: (t3.match(/(Entendí|I understood)[^\n]*/) || [])[0],
  producto: (t3.match(/GASEOSA[^\n]*/) || [])[0],
  freno: /suelen entrar|usually comes in/.test(t3),
  confirmarHabilitado: await btnOk.isEnabled(),
}, null, 1));
await page.screenshot({ path: "../docs/shot-voz-1-propuesta.png" });

// --- 4 · el sí humano: recién acá se escribe -------------------------------
await btnOk.click();
await page.waitForSelector("text=/Anotado|Noted/", { timeout: 25000 });
console.log("4· confirmado:", ((await zona()).match(/(Anotado|Noted)[^\n]*/) || [])[0]);
await page.screenshot({ path: "../docs/shot-voz-2-anotado.png" });

// --- 5 · el número imposible TIENE que frenar ------------------------------
// recargar en vez de cerrar el modal: un "Cerrar" suelto matchea también un
// botón del sidebar que queda detrás del overlay, y esa pelea no aporta nada
await page.reload({ waitUntil: "domcontentloaded" });
const navDep2 = page.getByRole("button", { name: /^Depósito$|^Warehouse$/ }).first();
await navDep2.waitFor({ state: "visible", timeout: 60000 });
await navDep2.click();
const abrir2 = page.getByRole("button", { name: /Decirle a Ángela|Tell Ángela/i }).first();
await abrir2.waitFor({ state: "visible", timeout: 30000 });
await abrir2.click();
await frase.first().waitFor({ state: "visible", timeout: 20000 });
await enModal(/ocho mil/i).first().click();
await page.waitForSelector("text=/Entendí|I understood/", { timeout: 25000 });
await page.waitForTimeout(800);
const t5 = await zona();
console.log("5· «ocho mil cajas» (el ×48):", JSON.stringify({
  aviso: (t5.match(/[^\n]*(suelen entrar|usually comes in)[^\n]*/) || [])[0],
  confirmarBloqueado: !(await enModal(/anotalo|note it/i).first().isEnabled()),
}, null, 1));
await page.screenshot({ path: "../docs/shot-voz-3-frenado.png" });

console.log("errores de consola:", errores.length ? errores.slice(0, 5) : "ninguno");
await browser.close();
restaurar();
console.log("dataset del demo restaurado.");
