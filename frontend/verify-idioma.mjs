// Auditoría final de TEXTO: recorre todas las secciones del dueño en el idioma
// por default (inglés) y busca dos cosas que arruinan una demo:
//   1. claves i18n crudas en pantalla (`cerebro.t_nota`, `rol.acc_x_sub`…)
//   2. castellano colado en la vista inglesa (con la lista blanca de lo que por
//      regla de la casa NO se traduce: nombres de productos, clientes,
//      proveedores y categorías — son DATOS del cliente, no interfaz).
//
//   POLPILOT_API=http://127.0.0.1:8003 POLPILOT_APP=http://127.0.0.1:8003/ node verify-idioma.mjs
import { readFileSync } from "node:fs";
import { chromium } from "playwright";

const CREDS = JSON.parse(readFileSync("../data-demo/credenciales.json", "utf-8")).plain;
const API = process.env.POLPILOT_API || "http://localhost:8002";
const APP = process.env.POLPILOT_APP || "http://localhost:5175/";

// Una clave cruda se ve así: minúsculas.palabra_con_guiones, sin espacios.
const CLAVE = /\b[a-z]{3,12}\.[a-z][a-z0-9_]{2,30}\b/g;
// Lo que SÍ puede aparecer con punto y no es una clave rota.
const NO_ES_CLAVE = /^(www\.|https?|polpilot\.|\d)|\.(com|ar|js|json|csv|png|jpg|pdf)$/;

// Castellano que delataría interfaz sin traducir (evitando los datos del cliente).
const ES_UI = /\b(el|la|los|las|una|para|desde|hasta|según|más|también|porque|cuando|así|está|tenés|querés|podés|cargar|ver|todos|nada|hoy|ayer|semana|mes|año|plata|cuenta|cliente|proveedor|depósito|pedido|precio|stock)\b/gi;

const login = async (u) => {
  const r = await fetch(`${API}/api/login`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: u, password: CREDS[u] }),
  });
  return r.json();
};

const browser = await chromium.launch();
const sesion = await login("aldo");
console.log("idioma del perfil (server-side):", sesion.usuario.idioma);
const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
await ctx.addInitScript(([k, v]) => localStorage.setItem(k, v),
  ["polpilot.session.v1", JSON.stringify(sesion)]);
const page = await ctx.newPage();
await page.goto(APP, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(8000);

const secciones = (await page.locator("nav button").allInnerTexts()).map((x) => x.split("\n")[0]);
let fallas = 0;
for (const s of secciones) {
  await page.locator("nav button").filter({ hasText: new RegExp("^" + s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")) })
    .first().click().catch(() => {});
  let txt = "";
  for (let i = 0; i < 50; i++) {
    await page.waitForTimeout(250);
    txt = (await page.locator("main").innerText()).trim();
    if (txt.length > 60) break;
  }
  const claves = [...new Set(txt.match(CLAVE) || [])].filter((c) => !NO_ES_CLAVE.test(c));
  // el castellano se cuenta por PALABRAS DE INTERFAZ repetidas, no por un nombre suelto
  const es = [...new Set((txt.match(ES_UI) || []).map((w) => w.toLowerCase()))];
  const sospecha = es.length >= 4;   // 1-3 pueden venir de un dato del cliente
  const ok = claves.length === 0 && !sospecha;
  if (!ok) fallas++;
  console.log(`${ok ? "  OK  " : " REVISAR"} ${s.padEnd(20)} ${claves.length ? "claves: " + claves.join(", ") : ""}${sospecha ? " castellano: " + es.slice(0, 8).join(" ") : ""}`);
}

await browser.close();
console.log(fallas === 0 ? "\nVERDE — sin claves crudas ni mezcla de idiomas" : `\n${fallas} sección(es) a mirar`);
process.exit(0);
