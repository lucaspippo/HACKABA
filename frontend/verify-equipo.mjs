// P29·B — verificación EN VIVO de la administración del equipo, punto por punto:
// (1) ficha por persona con datos reales, (2) loop de objetivos asignar→avance→
// dueño lo ve, (3) aviso de Ángela ENTREGADO por la campanita real del empleado.
import { readFileSync } from "node:fs";
import { chromium } from "playwright";

const CREDS = JSON.parse(readFileSync("../data-demo/credenciales.json", "utf-8")).plain;
const API = "http://localhost:8001";
const login = async (u) => {
  const r = await fetch(`${API}/api/login`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: u, password: CREDS[u] }),
  });
  return r.json();
};
const aldo = await login("aldo");
const marta = await login("marta");

const browser = await chromium.launch();
const abrir = async (sesion) => {
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 950 } });
  await ctx.addInitScript(([k, v]) => localStorage.setItem(k, v),
    ["polpilot.session.v1", JSON.stringify(sesion)]);
  const page = await ctx.newPage();
  await page.goto("http://localhost:5174/", { waitUntil: "networkidle" });
  await page.waitForTimeout(1200);
  return { ctx, page };
};

// --- (1) La ficha por persona, como dueño --------------------------------------
{
  const { ctx, page } = await abrir(aldo);
  await page.getByRole("button", { name: /^Team$|^Equipo$/ }).first().click();
  await page.waitForTimeout(1500);
  const fichas = page.getByRole("button", { name: /^Profile$|^Ficha$/ });
  console.log("(1) botones de ficha:", await fichas.count());
  // la de Vanesa (tiene solicitud pendiente + actividad real sembrada)
  const cardVanesa = page.locator("div.sombra-papel")
    .filter({ hasText: "Vanesa" })
    .filter({ has: page.getByRole("button", { name: /^Profile$|^Ficha$/ }) }).last();
  await cardVanesa.getByRole("button", { name: /^Profile$|^Ficha$/ }).click();
  await page.waitForTimeout(500);
  console.log("(1) ficha Vanesa:", JSON.stringify((await cardVanesa.innerText()).slice(200, 700)));
  await page.screenshot({ path: "../docs/shot-p29-ficha.png" });

  // --- (3) el aviso propuesto por Ángela → campanita real ----------------------
  const enviar = page.getByRole("button", { name: /Send to|Enviar a/ }).first();
  if (await enviar.count()) {
    const label = await enviar.innerText();
    await enviar.click();
    await page.waitForTimeout(800);
    console.log("(3) aviso enviado via:", JSON.stringify(label));
  } else {
    console.log("(3) sin propuestas visibles (¿ya enviadas?)");
  }
  await ctx.close();
}

// el aviso llegó a la campanita del destinatario (canal real, no fingido)
{
  const r = await fetch(`${API}/api/notificaciones?token=${encodeURIComponent(marta.token)}`);
  const d = await r.json();
  const avisos = (d.notificaciones || d.eventos || []).slice(0, 4);
  console.log("(3) campanita de marta:", JSON.stringify(avisos.map((n) => n.titulo || n.cuerpo).slice(0, 4)));
}

// --- (2) loop de objetivos: asignar → el empleado lo ve y marca avance → dueño --
{
  const oid = `p29-verif-${Math.floor(performance.now())}`;
  const rc = await fetch(`${API}/api/objetivos`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${aldo.token}` },
    body: JSON.stringify({ nombre: "Verificación P29: revisar cheques en cartera",
                           responsable: "Marta", fecha: "esta semana", id: oid }),
  });
  console.log("(2) POST objetivo:", rc.status);
  const { ctx, page } = await abrir(marta);
  await page.getByRole("button", { name: /^Team$|^Equipo$/ }).first().click();
  await page.waitForTimeout(1500);
  const obj = page.getByText("Verificación P29", { exact: false }).first();
  console.log("(2) marta VE el objetivo:", !!(await obj.count()));
  // marca avance: el botón de estado de ESA card
  const card = page.locator("div.sombra-papel").filter({ hasText: "Verificación P29" }).last();
  await card.getByRole("button").last().click();
  await page.waitForTimeout(900);
  console.log("(2) marta marcó avance:", JSON.stringify(await card.getByRole("button").last().innerText()));
  await ctx.close();

  const r = await fetch(`${API}/api/objetivos`, { headers: { Authorization: `Bearer ${aldo.token}` } });
  const d = await r.json();
  const mio = (d.objetivos || []).find((o) => o.id === oid);
  console.log("(2) el dueño lo ve (server):", JSON.stringify(mio));
}

await browser.close();
console.log("listo");
