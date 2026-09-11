import { chromium } from "playwright";
const b = await chromium.launch();
async function cap(lang) {
  const p = await (await b.newContext({ viewport: { width: 1600, height: 950 } })).newPage();
  await p.goto("http://localhost:5174/", { waitUntil: "domcontentloaded" });
  await p.waitForTimeout(2500);
  if (lang === "es") { await p.locator("header button", { hasText: /^es$/i }).first().click().catch(() => {}); await p.waitForTimeout(2600); }
  await p.getByRole("button", { name: /mapa de tu negocio|Business Map/i }).first().click().catch(() => {});
  await p.waitForSelector(".react-flow__node", { timeout: 55000 });
  for (let i = 0; i < 25; i++) { const l = await p.evaluate(() => /Crossing your sources|Cruzando tus fuentes/i.test(document.querySelector("main")?.innerText || "")); if (!l) break; await p.waitForTimeout(700); }
  await p.waitForTimeout(1000);
  await p.click('[data-id="memory"]').catch(() => {});
  await p.waitForTimeout(1400);
  const txt = await p.evaluate(() => ([...document.querySelectorAll("aside")].pop()?.innerText || ""));
  const rawKeys = (txt.match(/mapa\.[a-z_]+/g) || []);
  console.log(`[${lang}] rawKeys=${JSON.stringify(rawKeys)} | sample="${txt.replace(/\n+/g, " ").slice(0, 260)}"`);
  await p.screenshot({ path: `../docs/shot-s4-memory-${lang}.png` });
  await p.context().close();
}
await cap("en");
await cap("es");
await b.close();
