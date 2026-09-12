import { describe, expect, it } from "vitest";
import { ES } from "./locales/es";
import { EN } from "./locales/en";

// La red que faltaba para una regla que ya estaba escrita: toda cadena nueva va
// en los dos idiomas. Hasta ahora eso dependía de que quien la agregaba se
// acordara, y una clave sin traducir no se ve — se ve el texto en español
// dentro de una pantalla en inglés, que es peor que un error.
//
// La comprobación va en UN solo sentido a propósito. `en.js` tiene de más los
// nombres de puesto (`rol.Encargado de depósito`): el valor en español ES el
// dato del dataset y no necesita una entrada que se traduzca a sí misma.

describe("los dos diccionarios", () => {
  it("traduce al inglés todo lo que existe en español", () => {
    const faltan = Object.keys(ES).filter((k) => !(k in EN));
    expect(faltan).toEqual([]);
  });

  it("no deja ninguna cadena vacía", () => {
    for (const dicc of [ES, EN]) {
      const vacias = Object.entries(dicc).filter(([, v]) => typeof v === "string" && !v.trim());
      expect(vacias).toEqual([]);
    }
  });

  it("usa los mismos parámetros en los dos idiomas", () => {
    // `i18n.t` devuelve el texto SIN formatear cuando falta un parámetro: una
    // traducción que pide {producto} donde la otra pide {nombre} sale a
    // pantalla con la llave puesta. Ya nos pasó una vez.
    const params = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
    const distintas: string[] = [];
    for (const [k, v] of Object.entries(ES)) {
      const otro = (EN as Record<string, string>)[k];
      if (typeof v !== "string" || typeof otro !== "string") continue;
      if (params(v).join() !== params(otro).join()) distintas.push(k);
    }
    expect(distintas).toEqual([]);
  });
});
