// P·layout — VERIFICACIÓN REAL de los tres problemas de responsive de las
// vistas de rol frontline. Corre contra el demo levantado (front 5175 / API
// 8002) en Chromium de verdad, porque el browser embebido no compone frames.
//
//   node verify-layout.mjs
//
// Qué mide (no "se ve bien": números):
//   1. La fila de 5 KPIs del Depósito en MOBILE — que ninguna caja quede
//      huérfana a media fila ni se salga del ancho.
//   2. "Mi día" en DESKTOP — que ocupe el ancho disponible y reparta en dos
//      columnas, y en MOBILE que siga siendo una sola columna.
//   3. Lo mismo para CADA rol frontline (depósito, reparto, mostrador, sucursal).
import { readFileSync } from "node:fs";
import { chromium } from "playwright";

// El contenedor de "Mi día": la clase es `@container`, y en CSS la arroba se
// escapa con backslash — de ahí el doble backslash en el string de JS.
const CONT = "main .\\@container";
const CREDS = JSON.parse(readFileSync("../data-demo/credenciales.json", "utf-8")).plain;
const API = process.env.POLPILOT_API || "http://localhost:8002";
const APP = process.env.POLPILOT_APP || "http://localhost:5175/";

// Un representante de cada rol frontline con vista de trabajo.
const ROLES = [
  { u: "kevin", rol: "depósito (nuevo)" },
  { u: "tomas", rol: "depósito" },
  { u: "walter", rol: "reparto" },
  { u: "vanesa", rol: "mostrador" },
  { u: "norma", rol: "sucursal" },
];

const login = async (username) => {
  const r = await fetch(`${API}/api/login`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password: CREDS[username] }),
  });
  if (!r.ok) throw new Error(`login ${username}: ${r.status}`);
  return r.json();
};

const abrir = async (browser, sesion, viewport, esperar) => {
  const ctx = await browser.newContext({ viewport });
  await ctx.addInitScript(([k, v]) => localStorage.setItem(k, v),
    ["polpilot.session.v1", JSON.stringify(sesion)]);
  const page = await ctx.newPage();
  const errores = [];
  page.on("pageerror", (e) => errores.push(e.message.slice(0, 160)));
  // networkidle NO sirve acá: la campanita hace polling y la red nunca queda
  // quieta. Se espera al DOM y después al nodo que se va a medir.
  await page.goto(APP, { waitUntil: "domcontentloaded" });
  if (esperar) {
    try { await page.waitForSelector(esperar, { timeout: 25000 }); }
    catch { console.log(`   (no apareció ${esperar}: ${(await page.innerText("body")).slice(0, 120).replace(/\n/g, " ")})`); }
  }
  // `/api/inicio` y `/api/onboarding` tardan lo suyo con el cache frío: sin esta
  // espera las capturas salen con la vista a medio llenar (y el bloque del que
  // recién entró todavía sin aparecer).
  await page.waitForTimeout(5000);
  return { ctx, page, errores };
};

// Las cajas de una fila de tiles: ¿cuántas filas visuales, y hay alguna sola?
const medirTiles = (page, selector) => page.evaluate((sel) => {
  const cont = document.querySelector(sel);
  if (!cont) return null;
  const hijos = [...cont.children].map((el) => {
    const r = el.getBoundingClientRect();
    return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), texto: el.innerText.replace(/\n/g, " ") };
  });
  const filas = {};
  for (const h of hijos) (filas[h.y] ||= []).push(h);
  const anchoCont = Math.round(cont.getBoundingClientRect().width);
  return {
    n: hijos.length, anchoCont,
    filas: Object.values(filas).map((f) => ({ cajas: f.length, ancho: f.reduce((s, x) => s + x.w, 0) })),
    // ¿alguna caja se sale del contenedor? (por 2px de tolerancia de subpíxel)
    desborda: hijos.some((h) => h.x + h.w > anchoCont + h.x - hijos[0].x + 2),
    huerfana: Object.values(filas).some((f, i, arr) =>
      i === arr.length - 1 && arr.length > 1 && f.length < arr[0].length
      && f.reduce((s, x) => s + x.w, 0) < anchoCont * 0.9),
    textos: hijos.map((h) => h.texto),
  };
}, selector);

const browser = await chromium.launch();
let fallas = 0;
const di = (ok, msg) => { console.log(`${ok ? "  OK  " : " FALLA"} ${msg}`); if (!ok) fallas++; };

// --- 1 · la fila de KPIs del depósito en MOBILE ------------------------------
{
  const sesion = await login("kevin");
  const { ctx, page, errores } = await abrir(browser, sesion, { width: 375, height: 812 }, "main");
  // ir a la pestaña Depósito de la barra inferior
  await page.locator("nav button").filter({ hasText: /^(dep[oó]sito|warehouse)$/i }).first().click();
  // el WMS se pide al entrar a la sección: hay que esperar la respuesta, no el click
  await page.waitForSelector('main [class*="sm:grid-cols-5"]', { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(600);
  // la fila de KPIs del WMS es la única con `sm:grid-cols-5` (la de
  // fantasmas/negativos también es grid-cols-2 y no es esta)
  const grid = await medirTiles(page, 'main [class*="sm:grid-cols-5"]');
  if (!grid) console.log("   (pantalla tras el click:", (await page.innerText("main")).slice(0, 200), ")");
  console.log("\n== 1 · KPIs del depósito · mobile 375px ==");
  console.log("   tiles:", grid?.textos);
  console.log("   filas:", JSON.stringify(grid?.filas));
  di(!!grid && grid.n === 5, `5 tiles renderizados (${grid?.n})`);
  di(!!grid && !grid.huerfana, "ninguna caja huérfana a media fila");
  di(!!grid && grid.filas.every((f) => f.ancho >= grid.anchoCont * 0.93),
     "todas las filas llenan el ancho");
  di(errores.length === 0, `sin errores de página (${errores.join(" | ")})`);
  // Nada cortado ni pisado: ningún elemento de la vista se pasa del ancho del
  // celular (lo que se sale de una tarjeta con overflow-hidden NO se ve).
  const fuera = await page.evaluate(() => {
    const vw = window.innerWidth;
    return [...document.querySelectorAll("main *")]
      .filter((e) => {
        const r = e.getBoundingClientRect();
        if (!(r.width > 0 && r.right > vw + 1)) return false;
        // un scroller propio es la solución, no el problema
        return !e.closest(".overflow-x-auto");
      })
      .map((e) => `${e.tagName}:${(e.innerText || "").slice(0, 30)}`).slice(0, 5);
  });
  di(fuera.length === 0, `nada se sale del ancho del celular (${fuera.join(" | ")})`);
  await page.screenshot({ path: "../docs/shot-layout-deposito-mobile.png", fullPage: false });
  await ctx.close();
}

// --- 2 y 3 · "Mi día" por rol, en desktop y en mobile ------------------------
console.log("\n== 2/3 · «Mi día» por rol ==");
for (const { u, rol } of ROLES) {
  const sesion = await login(u);
  // DESKTOP: ¿usa el ancho? ¿reparte en dos columnas?
  const d = await abrir(browser, sesion, { width: 1600, height: 950 }, CONT);
  const desk = await d.page.evaluate(() => {
    const cont = document.querySelector("main .\\@container");
    if (!cont) return null;
    const r = cont.getBoundingClientRect();
    const cuerpo = cont.lastElementChild?.previousElementSibling || cont.children[1];
    const cs = cuerpo ? getComputedStyle(cuerpo) : null;
    // las secciones del cuerpo: ¿arrancan en más de una X? = más de una columna
    const xs = cuerpo ? [...cuerpo.children].map((el) => Math.round(el.getBoundingClientRect().x)) : [];
    return {
      ancho: Math.round(r.width), main: Math.round(document.querySelector("main").getBoundingClientRect().width),
      columnas: cs?.columnCount, columnasReales: new Set(xs).size,
      cabecera: cont.firstElementChild ? getComputedStyle(cont.firstElementChild).gridTemplateColumns : null,
    };
  });
  console.log(`   ${u} (${rol}) · desktop:`, JSON.stringify(desk));
  di(!!desk && desk.ancho > 900, `${u}: la vista usa el ancho (${desk?.ancho}px, main ${desk?.main}px)`);
  di(!!desk && desk.columnasReales >= 2, `${u}: cuerpo en 2 columnas (${desk?.columnasReales})`);
  di(!!desk && /px .+px/.test(desk.cabecera || ""), `${u}: cabecera saludo+consulta lado a lado`);
  await d.page.screenshot({ path: `../docs/shot-layout-${u}-desktop.png` });
  await d.ctx.close();

  // MOBILE: una sola columna, sin desbordes horizontales
  const m = await abrir(browser, sesion, { width: 375, height: 812 }, CONT);
  const mob = await m.page.evaluate(() => {
    const cont = document.querySelector("main .\\@container");
    if (!cont) return null;
    const cuerpo = cont.children[1];
    const xs = cuerpo ? [...cuerpo.children].map((el) => Math.round(el.getBoundingClientRect().x)) : [];
    return { columnasReales: new Set(xs).size, scrollX: document.documentElement.scrollWidth > window.innerWidth };
  });
  di(!!mob && mob.columnasReales === 1, `${u}: mobile en UNA columna (${mob?.columnasReales})`);
  di(!!mob && !mob.scrollX, `${u}: mobile sin scroll horizontal`);
  await m.page.screenshot({ path: `../docs/shot-layout-${u}-mobile.png` });
  await m.ctx.close();
}

await browser.close();
console.log(fallas === 0 ? "\nVERDE — layout ok" : `\nROJO — ${fallas} fallas`);
process.exit(fallas === 0 ? 0 : 1);
