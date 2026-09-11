// BLOQUE B — el flujo del remito por foto, end to end en Chromium real:
// entrar por Depósito → elegir la muestra → lo que Ángela leyó (con lote y
// vencimiento) → el cruce contra la orden → confirmar → stock + lotes +
// la propuesta de reclamo.
//
// OJO: este flujo ESCRIBE de verdad (stock, recepciones, lotes, cierra la OC y
// deja el faltante reportado). Correrlo consume la orden OC-2026-0847, y si no
// se restaura, la segunda corrida ya no encuentra OC abierta y el cruce —el
// momento del demo— no pasa. Por eso el script deja el dataset como lo
// encontró. Lo mismo hay que hacer después de ensayar la demo.
import { chromium } from "playwright";
import { execSync } from "node:child_process";
import { rmSync } from "node:fs";

const RAIZ = "../..";
// con fs, no con `rm`: el script tiene que correr igual desde bash o PowerShell
const restaurar = () => {
  execSync("git checkout -- polpilot-demo/data-demo/apartados.json", { cwd: RAIZ });
  for (const f of ["piso.json", "inventory_actual.json"]) {
    rmSync(`${RAIZ}/polpilot-demo/data-demo/${f}`, { force: true });
  }
};

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
const errores = [];
page.on("console", (m) => m.type() === "error" && errores.push(m.text()));
page.on("pageerror", (e) => errores.push("PAGEERROR " + e.message));

await page.goto("http://localhost:5174/", { waitUntil: "domcontentloaded" });

// --- 1 · la entrada nueva: Depósito ---------------------------------------
const navDep = page.getByRole("button", { name: /^Depósito$|^Warehouse$/ }).first();
await navDep.waitFor({ state: "visible", timeout: 60000 });
await navDep.click();

const abrir = page.getByRole("button", { name: /Cargar remito por foto|Load delivery note by photo/i }).first();
await abrir.waitFor({ state: "visible", timeout: 30000 });
console.log("1· botón en Depósito: OK");
await page.screenshot({ path: "../docs/shot-remito-0-deposito.png" });
await abrir.click();

// --- 2 · elegir el remito de muestra --------------------------------------
const verMuestras = page.getByRole("button", { name: /documento de muestra|sample document/i }).first();
await verMuestras.waitFor({ state: "visible", timeout: 15000 });
await verMuestras.click();
await page.waitForTimeout(600);
// "1 · Remito — llega el camión" / "1 · Delivery note (remito) — the truck arrives".
// Ojo con .last(): la lista tiene 4 muestras y la última es la lista de precios.
const elegirRemito = page.getByRole("button", { name: /^1 · (Remito|Delivery note)/i }).first();
await elegirRemito.click();

// la extracción es determinista (sin LLM): tiene que llegar rápido
await page.waitForSelector("text=/OC-2026-0847/", { timeout: 25000 });
await page.waitForTimeout(800);

const leido = await page.evaluate(() => {
  const txt = document.body.innerText;
  return {
    oc: /OC-2026-0847/.test(txt),
    lote: (txt.match(/lote L-\d{4}-[A-Z]|batch L-\d{4}-[A-Z]/g) || []).length,
    vence: (txt.match(/vence |expires /g) || []).length,
    cruce: (txt.match(/[^\n]*OC-2026-0847[^\n]*/) || [])[0],
    diferencias: (txt.match(/MANTECA[^\n]*/g) || []).slice(0, 4),
  };
});
console.log("2· lo que Ángela leyó:", JSON.stringify(leido, null, 1));
await page.screenshot({ path: "../docs/shot-remito-1-leido.png" });

// --- 3 · confirmar: stock + lotes + reclamo -------------------------------
// acotado AL MODAL: sin esto el selector agarra un botón del sidebar de atrás
const modal = page.locator("div.fixed.inset-0.z-50").first();
const confirmar = modal.getByRole("button", { name: /Sí, cargalo|Yes, load it/i }).first();
await confirmar.click();
await page.waitForSelector("text=/reclam|claim/i", { timeout: 30000 });
await page.waitForTimeout(700);

const res = await page.evaluate(() => {
  const txt = document.body.innerText;
  return {
    resultado: (txt.match(/[^\n]*(al stock|to stock|productos|products)[^\n]*/i) || [])[0],
    lotes: (txt.match(/[^\n]*(lote\(s\)|batch\(es\))[^\n]*/i) || [])[0],
    reclamo: (txt.match(/[^\n]*(reclamo|claim)[^\n]*/i) || [])[0],
    monto: (txt.match(/\$\s?[\d.,]+/g) || []).slice(0, 3),
  };
});
console.log("3· resultado:", JSON.stringify(res, null, 1));
await page.screenshot({ path: "../docs/shot-remito-2-resultado.png" });

// --- 4 · el segundo sí: mandar el reclamo ---------------------------------
const btnReclamar = page.getByRole("button", { name: /Sí, reclamar|Yes, claim it/i }).first();
if (await btnReclamar.count()) {
  await btnReclamar.click();
  await page.waitForTimeout(2500);
  const conf = await page.evaluate(() =>
    (document.body.innerText.match(/[^\n]*(Anotado|Noted)[^\n]*/) || [])[0] || null);
  console.log("4· reclamo enviado:", conf);
  await page.screenshot({ path: "../docs/shot-remito-3-reclamo.png" });
} else {
  console.log("4· NO apareció el botón de reclamar");
}

console.log("errores de consola:", errores.length ? errores.slice(0, 5) : "ninguno");
await browser.close();

restaurar();
console.log("dataset del demo restaurado (OC abierta de nuevo). "
  + "REINICIÁ el backend: tiene el stock viejo en memoria.");
