// P45 · el mismo concepto = el mismo número en todas las pantallas y en Ángela.
import { chromium } from "playwright";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
await page.goto("http://localhost:5174/", { waitUntil: "domcontentloaded" });
await page.waitForTimeout(7000);

const api = (u) => page.evaluate(async (url) => {
  const tok = JSON.parse(localStorage.getItem("polpilot.session.v1") || "{}").token;
  const r = await fetch(url, { headers: { Authorization: "Bearer " + tok } });
  return r.ok ? r.json() : { __s: r.status };
}, u);

const preg = (q) => page.evaluate(async (msg) => {
  const tok = JSON.parse(localStorage.getItem("polpilot.session.v1") || "{}").token;
  const r = await fetch("/api/angela", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mensaje: msg, historial: [], token: tok }) });
  const d = await r.json(); const txt = d.respuesta || "";
  return { tools: d.tools_usadas || [],
           montos: [...new Set((txt.match(/\$\s?[\d][\d.,]*\d/g) || []).map((s) => s.replace(/[.,]$/, "")))],
           frag: txt.slice(0, 210).replace(/\n+/g, " ") };
}, q);

const inv = await api("/api/inventario");
const an = await api("/api/analisis");
console.log("=== T1 · PLATA PARADA ===");
console.log("  Home/mapa (resumen.inmovilizado_total):", inv.resumen?.inmovilizado_total);
console.log("  Trend/rotación (rotacion.inmovilizado_total):", an.rotacion?.inmovilizado_total);
console.log("  IDÉNTICOS:", inv.resumen?.inmovilizado_total === an.rotacion?.inmovilizado_total);
console.log("  por_estado:", JSON.stringify(an.rotacion?.por_estado));
console.log("  sin_clasificar:", JSON.stringify(an.rotacion?.sin_clasificar));

for (let i = 0; i < 2; i++) {
  const r = await preg("¿Cuánta plata tengo parada en stock?");
  console.log(`  Ángela #${i + 1} tools=${JSON.stringify(r.tools)} montos=${JSON.stringify(r.montos.slice(0, 4))}`);
}

console.log("\n=== T2 · CAPITAL RECUPERABLE ===");
for (let i = 0; i < 2; i++) {
  const r = await preg("¿Cuál es mi capital recuperable?");
  console.log(`  #${i + 1} tools=${JSON.stringify(r.tools)} montos=${JSON.stringify(r.montos.slice(0, 5))}`);
  if (i === 0) console.log("     ", r.frag);
}
await browser.close();
