// A2 · el micrófono del CHAT es de todos; el de la VISTA DE TRABAJO, de los del piso.
import { chromium } from "playwright";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
const errores = [];
page.on("pageerror", (e) => errores.push("PAGEERROR " + e.message.slice(0, 140)));
await page.goto("http://localhost:5174/", { waitUntil: "domcontentloaded" });
await page.waitForTimeout(6000);

const medir = () => page.evaluate(() => {
  const bs = Array.from(document.querySelectorAll("button"));
  const re = /Contale a .ngela|Tell .ngela/i;
  // el del chat: title/aria-label, y vive en la barra de escribir (input hermano)
  const chat = bs.some((b) => re.test(b.getAttribute("title") || b.getAttribute("aria-label") || "")
                              && b.parentElement && b.parentElement.querySelector("input"));
  // el de la vista de trabajo / sección: lleva el texto visible
  const trabajo = bs.some((b) => re.test(b.innerText || ""));
  const main = document.querySelector("main");
  const seccion = main ? main.innerText.split("\n")[0].slice(0, 24) : "";
  return { chat, trabajo, seccion };
});

const verComo = (u) => page.evaluate(async (user) => {
  const tok = JSON.parse(localStorage.getItem("polpilot.session.v1") || "{}").token;
  const r = await fetch("/api/demo/ver-como", { method: "POST",
    headers: { "Content-Type": "application/json", Authorization: "Bearer " + tok },
    body: JSON.stringify({ username: user }) });
  localStorage.setItem("polpilot.session.v1", JSON.stringify(await r.json()));
}, u);

console.log("usuario         chat / vista-trabajo / seccion");
console.log("aldo (dueño)   ", JSON.stringify(await medir()));
for (const u of ["marta", "celeste", "diego", "ramon", "walter", "vanesa", "norma", "nahuel"]) {
  await verComo(u);
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.waitForTimeout(5200);
  console.log(u.padEnd(15), JSON.stringify(await medir()));
}
console.log("ERRORES:", errores.length ? JSON.stringify(errores) : "ninguno");
await browser.close();
