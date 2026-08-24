// Sonda P43: micrófono en el chat por rol, y el resto de las correcciones.
import { chromium } from "playwright";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
const errores = [];
page.on("console", (m) => m.type() === "error" && errores.push(m.text().slice(0, 160)));
page.on("pageerror", (e) => errores.push("PAGEERROR " + e.message.slice(0, 160)));
const red404 = [];
page.on("response", (r) => { if (r.url().includes("/api/") && r.status() >= 400) red404.push(`${r.status()} ${r.url().split("/api/")[1]}`); });

await page.goto("http://localhost:5174/", { waitUntil: "domcontentloaded" });
await page.waitForTimeout(6000);

const micVisible = () => page.evaluate(() =>
  !!Array.from(document.querySelectorAll("button")).find((b) =>
    /micr|hablar|Talk|Tell/i.test(b.getAttribute("title") || b.getAttribute("aria-label") || "")));

console.log("MIC como Aldo (dueño, NO debe estar):", await micVisible());

const verComo = async (u) => page.evaluate(async (user) => {
  const tok = JSON.parse(localStorage.getItem("polpilot.session.v1") || "{}").token;
  const r = await fetch("/api/demo/ver-como", { method: "POST",
    headers: { "Content-Type": "application/json", Authorization: "Bearer " + tok },
    body: JSON.stringify({ username: user }) });
  localStorage.setItem("polpilot.session.v1", JSON.stringify(await r.json()));
}, u);

for (const u of ["ramon", "walter", "vanesa", "marta"]) {
  await verComo(u);
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.waitForTimeout(5500);
  console.log(`MIC como ${u}:`, await micVisible());
}
console.log("CONSOLA:", errores.length ? JSON.stringify([...new Set(errores)].slice(0, 5)) : "sin errores");
console.log("RED >=400:", red404.length ? JSON.stringify([...new Set(red404)].slice(0, 8)) : "ninguno");
await page.screenshot({ path: "../docs/probe-p43-mic.png" });
await browser.close();
