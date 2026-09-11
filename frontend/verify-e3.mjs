// E3 — verificación del conocimiento en el mapa: badges por nodo, panel "Lo que
// Aldo me enseñó", camino de conocimiento en los 4 hallazgos, franja + panel
// completo, y CERO español con la app en EN. Screenshots EN + ES.
import { chromium } from "playwright";
const browser = await chromium.launch();

const CAMINOS = {
  "Doña Elsa": /overdue|Doña Elsa|113/i,
  "Gaseosa": /run out|GASEOSA/i,
  "Ventana": /Buying window|Lácteos|Campo Alegre/i,
};

async function run(lang) {
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 950 } });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", (e) => errs.push(e.message));
  await page.goto("http://localhost:5174/", { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
  await page.locator("header button", { hasText: new RegExp(`^${lang}$`, "i") }).first().click().catch(() => {});
  await page.waitForTimeout(2600);
  await page.getByRole("button", { name: /mapa de tu negocio|Business Map/i }).first().click();
  await page.waitForSelector(".react-flow__node", { timeout: 55000 });  // ES en frío puede tardar
  // esperar a que el mapa termine de cruzar fuentes
  for (let i = 0; i < 20; i++) {
    const loading = await page.evaluate(() => /Crossing your sources|Cruzando tus fuentes/i.test(document.querySelector("main")?.innerText || ""));
    if (!loading) break;
    await page.waitForTimeout(700);
  }
  await page.waitForTimeout(1200);

  // 1) badges de conocimiento en nodos
  const badges = await page.evaluate(() =>
    [...document.querySelectorAll(".react-flow__node")].filter(n => (n.getAttribute("data-id") && !n.getAttribute("data-id").includes(":")))
      .map(n => ({ id: n.getAttribute("data-id"), txt: n.innerText.replace(/\n/g, " ") })));
  const conBadge = badges.filter(b => /🎓|Owner|Aldo/i.test(b.txt) || b.txt.match(/\b\d\b/));

  // 2) abrir Clientes → panel "Lo que Aldo me enseñó" (el panel de insight vive
  //    en el ÚLTIMO aside — el de Ángela a la derecha; leer TODOS por las dudas)
  await page.click('[data-id="clientes"]').catch(() => {});
  await page.waitForTimeout(1400);
  const panelTxt = await page.evaluate(() =>
    [...document.querySelectorAll("aside")].map(a => a.innerText).join("\n") + "\n" + (document.querySelector("main")?.innerText || ""));
  const panelK = /What Aldo taught me|Lo que Aldo me enseñó/i.test(panelTxt);
  const applied = /applied \d+ times|aplicad[ao] \d+ vec/i.test(panelTxt);
  const influye = /takes it into account|lo tiene en cuenta/i.test(panelTxt);

  await page.screenshot({ path: `../docs/shot-e3-clientes-${lang}.png` });

  // 2b) CAMINO DE CONOCIMIENTO (#5): tocar el hallazgo de concentración (k04) y
  //     verificar que aparece un nodo de conocimiento (data-id k-*) en la ruta.
  let caminoK = false;
  if (lang === "en") {
    await page.locator("aside", { hasText: /3 customers carry too much/i }).getByText(/3 customers carry too much/i).first().click().catch(() => {});
    await page.waitForTimeout(2600);
    caminoK = await page.evaluate(() =>
      [...document.querySelectorAll(".react-flow__node")].some(n => (n.getAttribute("data-id") || "").startsWith("k:")));
    await page.screenshot({ path: `../docs/shot-e3-camino-conocimiento.png` });
  }

  // 3) franja "What you taught me" → panel completo
  const franja = await page.evaluate(() => /What you taught me|Lo que me enseñaste/i.test(document.querySelector("main")?.innerText || ""));

  // 4) español colado en EN
  let espanol = [];
  if (lang === "en") {
    const full = await page.evaluate(() => document.querySelector("main")?.innerText || "");
    espanol = ["Regla de Aldo", "aplicada", "veces", "Lo que", "fiambres", "lácteos", "Cobrar", "Despertar", "concentran", "morosos", "Ninguno", "Al día"].filter(s => full.includes(s));
  }

  console.log(`\n[${lang}] nodos con badge: ${conBadge.length} | panel-conocimiento: ${panelK} | aplicada-N-veces: ${applied} | influye-contexto: ${influye} | camino-conocimiento: ${lang === "en" ? caminoK : "n/a"} | franja: ${franja} | pageerror: ${errs.length}`);
  if (lang === "en") console.log(`  español colado:`, JSON.stringify(espanol));
  if (errs.length) console.log("  ERRORS:", JSON.stringify(errs.slice(0, 3)));
  await ctx.close();
  return { panelK, applied, influye, franja, espanol, caminoK, errs: errs.length };
}

// ES primero y EN al final: el toggle PERSISTE el idioma en el perfil del
// servidor; terminar en EN deja el demo listo para grabar (evita dejarlo en ES).
const es = await run("es");
const en = await run("en");
await browser.close();
const ok = en.panelK && en.applied && en.influye && en.franja && en.caminoK && en.espanol.length === 0 && en.errs === 0 && es.panelK;
console.log(`\n=== E3 ${ok ? "OK ✓" : "revisar ✗"} ===`);
process.exit(ok ? 0 : 1);
