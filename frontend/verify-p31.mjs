// P31 — verificación FINAL del pulido, en el uso REAL: fijar idioma → recargar
// (persist) → entrar al mapa. Verifica consistencia total UI + backend en EN/ES.
import { chromium } from "playwright";
const browser = await chromium.launch();

async function corr(lang) {
  const ctx = await browser.newContext({ viewport: { width: 1680, height: 1000 } });
  const page = await ctx.newPage();
  const errores = [];
  page.on("pageerror", (e) => errores.push(e.message));
  await page.goto("http://localhost:5174/", { waitUntil: "networkidle" });
  await page.waitForTimeout(1600);
  // fijar idioma y ESPERAR a que persista + refresque la sesión, luego recargar
  await page.locator("header button", { hasText: new RegExp(`^${lang}$`, "i") }).first().click().catch(() => {});
  await page.waitForTimeout(1800);
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(1800);
  await page.locator("aside nav button", { hasText: /Business Map|mapa de tu negocio/i }).first().click();
  await page.waitForSelector(".react-flow__node", { timeout: 15000 });
  await page.waitForTimeout(1800);

  const r = await page.evaluate(() => {
    const main = document.querySelector("main")?.innerText || "";
    const aside = [...document.querySelectorAll("aside")].pop()?.innerText || "";
    const chip = [...document.querySelectorAll("button")].find((x) => /concentran demasiado|carry too much/.test(x.textContent) && x.querySelector(".plata"));
    const tituloEl = chip?.querySelector("span.block");
    return {
      frase: main.split("\n").find((l) => /years of sales|años de ventas/.test(l))?.slice(0, 55),
      cardTitulo: chip ? chip.textContent.replace(/\s+/g, " ").trim().slice(0, 40) : null,
      tituloW: tituloEl ? Math.round(tituloEl.getBoundingClientRect().width) : 0,
      saludo: aside.split("\n").find((l) => /Ángela/.test(l)) && aside.match(/I'm Ángela|Soy Ángela/)?.[0],
      leyenda: [...document.querySelectorAll("span")].map((s) => s.textContent).find((x) => /open an area|abrir un área/.test(x)),
    };
  });
  await page.screenshot({ path: `../docs/shot-p31-${lang}.png` });
  console.log(`[${lang}]`, JSON.stringify(r), "err:", errores.length);
  await ctx.close();
}
await corr("en");
await corr("es");
await browser.close();
