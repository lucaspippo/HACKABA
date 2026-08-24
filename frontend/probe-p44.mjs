// A1 · estabilidad de montos. Compara el CONJUNTO de importes, sin puntuación.
import { chromium } from "playwright";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
await page.goto("http://localhost:5174/", { waitUntil: "domcontentloaded" });
await page.waitForTimeout(6000);

const preg = (q) => page.evaluate(async (msg) => {
  const tok = JSON.parse(localStorage.getItem("polpilot.session.v1") || "{}").token;
  const t0 = Date.now();
  const r = await fetch("/api/angela", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mensaje: msg, historial: [], token: tok }) });
  const d = await r.json(); const txt = d.respuesta || "";
  const montos = [...new Set((txt.match(/\$\s?[\d][\d.,]*\d/g) || [])
    .map((s) => s.replace(/[.,]$/, "").replace(/\s/g, "")))];
  return { ms: Date.now() - t0, montos: montos.sort(), frag: txt.slice(0, 200).replace(/\n+/g, " ") };
}, q);

const PREGUNTAS = [
  "¿Cuánta plata tengo parada en stock?",
  "¿A quién tengo que cobrar?",
  "¿Cuál es mi capital recuperable?",
];
let todoEstable = true;
for (const q of PREGUNTAS) {
  const rondas = [];
  for (let i = 0; i < 3; i++) rondas.push(await preg(q));
  // union de los montos vistos; estable = ningun importe aparece en dos variantes
  const union = [...new Set(rondas.flatMap((r) => r.montos))].sort();
  const numeros = union.map((s) => s.replace(/[^\d]/g, ""));
  const casiIguales = numeros.filter((n, i) =>
    numeros.some((m, j) => i !== j && Math.abs(Number(n) - Number(m)) <= 2 && n !== m));
  const ok = casiIguales.length === 0;
  todoEstable = todoEstable && ok;
  console.log(`\n${q}`);
  rondas.forEach((r, i) => console.log(`  #${i + 1} (${r.ms}ms) ${JSON.stringify(r.montos)}`));
  console.log("  ESTABLE:", ok ? "SÍ" : `NO ← variantes: ${JSON.stringify(casiIguales)}`);
  console.log("  fraseo:", rondas[0].frag.slice(0, 150));
}
console.log("\n=== RESULTADO:", todoEstable ? "todos los montos estables" : "HAY DERIVA");
await browser.close();
