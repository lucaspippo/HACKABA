import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { CATALOGO, accionesDe, atiendeMostrador, avisaDesdeElPiso, cargaLk, chipsDe, muestrasDe, rolDe, tieneVistaHerramienta } from "./roles";

// The demo team, verbatim from backend/usuarios_demo.py. The role STRING is the
// only input `rolDe` gets — there is no list of usernames anywhere — so these
// strings are the real contract, and a typo in a regex breaks a real person.
const EQUIPO = [
  { username: "aldo", rol: "Dueño", es_admin: true, features: [] },
  { username: "marta", rol: "Administración", es_admin: false,
    features: ["panel", "administracion", "cuentas", "caja", "saneamiento", "documentos", "evolucion", "cargar", "alertas", "equipo", "perfil", "angela"] },
  { username: "celeste", rol: "Compras y proveedores", es_admin: false,
    features: ["panel", "inventario", "saneamiento", "cargar", "documentos", "alertas", "evolucion", "oportunidades", "equipo", "perfil", "angela"] },
  { username: "ramon", rol: "Encargado de depósito", es_admin: false,
    features: ["panel", "deposito", "logistica", "inventario", "saneamiento", "cargar", "alertas", "equipo", "perfil", "angela"] },
  { username: "brian", rol: "Depósito · armado de pedidos", es_admin: false,
    features: ["deposito", "logistica", "alertas", "perfil", "angela"] },
  { username: "nahuel", rol: "Depósito · recepción", es_admin: false,
    features: ["deposito", "saneamiento", "cargar", "alertas", "perfil", "angela"] },
  { username: "tomas", rol: "Depósito · conteos", es_admin: false,
    features: ["deposito", "inventario", "saneamiento", "cargar", "alertas", "perfil", "angela"] },
  { username: "kevin", rol: "Depósito · ayudante general", es_admin: false,
    features: ["deposito", "inventario", "saneamiento", "cargar", "alertas", "perfil", "angela"] },
  { username: "walter", rol: "Reparto · camión 1", es_admin: false,
    features: ["logistica", "deposito", "alertas", "perfil", "angela"] },
  { username: "osmar", rol: "Reparto · camión 2", es_admin: false,
    features: ["logistica", "deposito", "alertas", "perfil", "angela"] },
  { username: "diego", rol: "Preventista · zona centro", es_admin: false,
    features: ["panel", "cobranzas", "cuentas", "documentos", "alertas", "perfil", "angela"] },
  { username: "lucia", rol: "Preventista · zona sur", es_admin: false,
    features: ["panel", "cobranzas", "cuentas", "documentos", "alertas", "perfil", "angela"] },
  { username: "norma", rol: "Encargada · Sucursal Norte", es_admin: false,
    features: ["panel", "caja", "inventario", "cuentas", "saneamiento", "alertas", "equipo", "perfil", "angela"] },
  { username: "vanesa", rol: "Mostrador · Casa Central", es_admin: false,
    features: ["panel", "cobranzas", "cuentas", "caja", "inventario", "alertas", "perfil", "angela"] },
];

const ESPERADO: Record<string, string | null> = {
  aldo: null,
  marta: "administracion",
  celeste: "compras",
  ramon: "deposito_encargado",
  nahuel: "deposito_recepcion",
  tomas: "deposito_conteos",
  brian: "deposito_armado",
  kevin: "deposito_ayudante",
  walter: "reparto",
  osmar: "reparto",
  diego: "preventa",
  lucia: "preventa",
  norma: "sucursal",
  vanesa: "mostrador",
};

const de = (username: string) => EQUIPO.find((u) => u.username === username)!;

describe("rolDe", () => {
  it.each(EQUIPO)("puts $username in their own trade", (u) => {
    expect(rolDe(u)?.id ?? null).toBe(ESPERADO[u.username]);
  });

  it("keeps the five warehouse trades apart", () => {
    // The bug this whole split fixes: one /dep[oó]sito/i took all five, so the
    // picker got the receiver's actions. If two of these ever collapse again,
    // somebody silently loses their job's screen.
    const ids = ["ramon", "nahuel", "tomas", "brian", "kevin"].map((x) => rolDe(de(x))?.id);
    expect(new Set(ids).size).toBe(5);
  });

  it("catches an unknown warehouse role instead of dropping it", () => {
    // A new post, or another tenant naming things its own way: the generic
    // entry is the net. Landing on nothing would be worse than landing on the
    // old shared view.
    const turnoNoche = { rol: "Depósito · turno noche", es_admin: false,
                         features: ["deposito", "cargar", "inventario"] };
    expect(rolDe(turnoNoche)?.id).toBe("deposito");
    expect(accionesDe(turnoNoche).length).toBeGreaterThan(0);
  });

  it("gives the owner no tool view: they have their own panel", () => {
    expect(rolDe(de("aldo"))).toBeNull();
    expect(tieneVistaHerramienta(de("aldo"))).toBe(false);
  });
});

describe("accionesDe", () => {
  it.each(EQUIPO.filter((u) => !u.es_admin))(
    "leaves $username with at least one action they can actually use", (u) => {
      // Every action declares the features it needs, and the matrix filters
      // them. A trade whose actions all get filtered out lands on an empty
      // screen — which is exactly what the split must not produce.
      expect(accionesDe(u).length).toBeGreaterThan(0);
    });

  it("sends the picker to their orders and the receiver to the delivery note", () => {
    // The two that were identical before and should never be again.
    expect(accionesDe(de("brian"))[0]).toMatchObject({ id: "mis_pedidos", a: "logistica" });
    expect(accionesDe(de("nahuel"))[0]).toMatchObject({ id: "cargar_remito", a: "cargar" });
  });

  it("never offers an action whose module the person does not have", () => {
    for (const u of EQUIPO) {
      for (const a of accionesDe(u)) {
        for (const f of a.need ?? []) expect(u.features).toContain(f);
      }
    }
  });

  it("marks exactly one action as the highlighted one per trade", () => {
    for (const u of EQUIPO.filter((x) => !x.es_admin)) {
      const destacadas = accionesDe(u).filter((a) => a.destaca);
      expect(destacadas.length).toBeLessThanOrEqual(1);
    }
  });
});

describe("chipsDe", () => {
  it("never offers a question whose module the person does not have", () => {
    for (const u of EQUIPO) {
      for (const c of chipsDe(u)) {
        for (const f of c.need ?? []) expect(u.features).toContain(f);
      }
    }
  });
});

describe("muestrasDe", () => {
  it("keeps all five warehouse trades on the warehouse voice samples", () => {
    // data-demo/audios tags its samples `rol: "deposito"`. Deriving the family
    // from the id would have left four of the five with no example at all —
    // and the samples are the fallback for whoever has no Web Speech or no
    // signal, which is most of the warehouse.
    for (const x of ["ramon", "nahuel", "tomas", "brian", "kevin"]) {
      expect(muestrasDe(de(x))).toBe("deposito");
    }
    expect(muestrasDe(de("walter"))).toBe("reparto");
    expect(muestrasDe(de("vanesa"))).toBe("mostrador");
  });
});

describe("atiendeMostrador", () => {
  it("is the two people who look at a selling price all day, and nobody else", () => {
    // Decides who gets the stale-cost heads-up. Goes by TRADE and not by
    // feature: half the team has `inventario`, and the warehouse does not
    // price anything.
    const atienden = EQUIPO.filter((u) => atiendeMostrador(u)).map((u) => u.username);
    expect(atienden.sort()).toEqual(["norma", "vanesa"]);
  });

  it("leaves the warehouse out even though it has the same module", () => {
    for (const x of ["ramon", "brian", "tomas", "nahuel", "kevin"]) {
      expect(atiendeMostrador(de(x))).toBe(false);
    }
  });
});

describe("avisaDesdeElPiso", () => {
  // La lista de avisos vive en el backend (data-demo/avisos_por_oficio.json) y
  // el flag de acá decide si la barra lleva el botón de carga. Son dos lugares
  // para un mismo hecho, así que se pinnean uno contra el otro: el día que
  // alguien agregue un oficio a la semilla y no acá, esto lo dice.
  const semilla = JSON.parse(fs.readFileSync(
    path.resolve(__dirname, "../../../data-demo/avisos_por_oficio.json"), "utf8"));

  it("matches exactly the trades the seed gives a list to", () => {
    const conFlag = CATALOGO.filter((r) => r.avisa).map((r) => r.id).sort();
    const enSemilla = Object.keys(semilla.oficios).sort();
    expect(conFlag).toEqual(enSemilla);
  });

  it("leaves the offices and the owner out, as the seed says", () => {
    for (const u of ["marta", "celeste", "aldo"]) {
      expect(avisaDesdeElPiso(de(u))).toBe(false);
    }
  });

  it("gives each trade the verb of its own job", () => {
    // "Contar" and "Log" are not the same thing, and a button that says what it
    // does gets pressed without thinking.
    expect(cargaLk(de("tomas"))).toBe("rol.carga_contar");
    expect(cargaLk(de("brian"))).toBe("rol.carga_armar");
    expect(cargaLk(de("walter"))).toBe("rol.carga_registrar");
    // Whoever has no trade of their own still gets a sane default.
    expect(cargaLk(de("aldo"))).toBe("rol.carga_cargar");
  });
});
