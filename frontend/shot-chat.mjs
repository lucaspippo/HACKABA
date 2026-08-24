import { chromium } from "playwright";

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 402, height: 874 },
  deviceScaleFactor: 2,
});
await page.goto("http://localhost:5173/", { waitUntil: "networkidle" });
await page.getByRole("button", { name: "Ángela", exact: false }).first().click();
await page.waitForTimeout(600);
// clic en un chip de acción rápida
await page.getByText("¿Cuánta plata tengo en manteca?").click();
await page.waitForTimeout(2500); // esperar respuesta del backend
await page.screenshot({ path: "../docs/shot-06-angela-respuesta.png" });
console.log("listo");
await browser.close();
