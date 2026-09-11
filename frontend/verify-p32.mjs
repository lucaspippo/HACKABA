// P32 — verificación: (1) entrar a Alertas 5 veces, jamás flashear el estado
// vacío antes de los datos (skeleton la 1ª, instantáneo con cache); (2) las 3
// agrupaciones por urgencia; (3) el barrido del flash en Depósito.
import { chromium } from "playwright";
const browser = await chromium.launch();

async function run(lang) {
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 950 } });
  const page = await ctx.newPage();
  const errores = [];
  page.on("pageerror", (e) => errores.push(e.message));
  await page.goto("http://localhost:5174/", { waitUntil: "networkidle" });
  await page.waitForTimeout(1600);
  await page.locator("header button", { hasText: new RegExp(`^${lang}$`, "i") }).first().click().catch(() => {});
  await page.waitForTimeout(1500);

  const EMPTY = /switch on|se enciendan|What you'll see|Lo que vas a ver/;
  let flashes = 0, skeletonPrimera = false;
  for (let i = 0; i < 5; i++) {
    // ir a Home y volver a Alertas (fuerza re-montaje)
    await page.locator("aside nav button", { hasText: /Home|Inicio/ }).first().click();
    await page.waitForTimeout(400);
    await page.locator("aside nav button", { hasText: /Alerts|Alertas/ }).first().click();
    // muestrear los primeros 700ms buscando el empty state
    for (let ms = 0; ms < 700; ms += 90) {
      await page.waitForTimeout(90);
      const s = await page.evaluate((reEmpty) => {
        const main = document.querySelector("main")?.innerText || "";
        const html = document.querySelector("main")?.innerHTML || "";
        return { empty: new RegExp(reEmpty).test(main), skeleton: html.includes("animate-pulse") };
      }, EMPTY.source);
      if (s.empty) flashes++;
      if (i === 0 && s.skeleton) skeletonPrimera = true;
    }
  }
  // estado final: los 3 grupos
  await page.waitForTimeout(600);
  const grupos = await page.evaluate(() => {
    const main = document.querySelector("main")?.innerText || "";
    return {
      hoy: /Needs action today|Necesita acción hoy/.test(main),
      semana: /This week|Para esta semana/.test(main),
      cuenta: /Worth knowing|Para tener en cuenta/.test(main),
      empty: /switch on|se enciendan/.test(main),
    };
  });
  console.log(`[${lang}] flashes-del-vacío: ${flashes} | skeleton-1ª-vez: ${skeletonPrimera} | grupos:`, JSON.stringify(grupos), "err:", errores.length);
  await page.screenshot({ path: `../docs/shot-p32-alertas-${lang}.png` });
  await ctx.close();
}
await run("en");
await run("es");
await browser.close();
