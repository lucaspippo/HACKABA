"""
Generador del dataset DEMO — "Distribuidora del Litoral" (100% FICTICIO).

v2 · EMPRESA SANA: una distribuidora rentable y bien manejada, con 10 años de
historia. PolPilot luce por la INTELIGENCIA que cruza datos, no por encontrar
un negocio fundido. Todo cruza entre sí:

  - La demanda manda: cada SKU tiene rotación (clase A/B/C), estacionalidad de
    su categoría y crecimiento real anual → de ahí salen las ventas de 10 años.
  - El stock actual = demanda diaria × días de cobertura de su clase → el
    inmovilizado ES la rotación (A: 7-15 días, B: 15-35, C: 30-75).
  - Los precios = costo × markup sano por categoría, inflados mes a mes con el
    camino REAL de la inflación argentina 2016-2026 (~×130 acumulado).
  - Las recepciones de mercadería de las últimas semanas reponen lo vendido.

Archivos: inventory.json (catálogo ~420 SKUs), apartados.json (ventas 10 años:
últimos 24 meses POR SKU y años previos por categoría; depósito WMS; logística
TMS; recepciones), cuentas.json (24 clientes, 3 morosos moderados),
ventas_validacion.json (confirmada), caja.json (60 cierres, si no existe),
staging: un batch pendiente con los "puntitos" de una carga real (si no hay).

Los "puntitos" (5% sucio, no desastre): ~8 sin precio, ~5 costo viejo,
2 balanzas dudosas, ~4 margen fino, 2 negativos chicos, 3 anulados con resto
de stock — más el batch del staging. El agregado SIEMPRE gana plata.

Determinista (seed fija). Correr:  python data-demo/generar.py
Nada de esto toca data/ (el piloto).
"""
from __future__ import annotations

import csv
import datetime
import json
import os
import random

import seed_conocimiento
import seed_notas

R = random.Random(20260707)
HERE = os.path.dirname(os.path.abspath(__file__))
# Fecha de referencia CONGELADA (P9·B): el dataset commiteado se generó el
# 2026-07-07 (mismo día que la seed) y regenerarlo tiene que dar byte-igual —
# nada de date-drift. POLPILOT_DEMO_TODAY permite otra referencia a propósito;
# si se cambia, el backend del demo debe levantarse con la MISMA var.
FECHA_REFERENCIA = "2026-07-07"
HOY = datetime.datetime.strptime(
    os.environ.get("POLPILOT_DEMO_TODAY", "").strip() or FECHA_REFERENCIA,
    "%Y-%m-%d").date()
MES_ACTUAL = HOY.year * 12 + (HOY.month - 1)
ANIOS_HISTORIA = 10

BOCAS = ["Casa Central", "Sucursal Norte", "Sucursal Puerto"]
BOCA_PESO = [0.55, 0.25, 0.20]

# --- inflación argentina, camino anual aproximado (factor dic/dic) -------------
INFLACION_ANUAL = {2016: 1.36, 2017: 1.25, 2018: 1.48, 2019: 1.54, 2020: 1.36,
                   2021: 1.51, 2022: 1.95, 2023: 3.11, 2024: 2.18, 2025: 1.42,
                   2026: 1.28}
# crecimiento REAL anual del negocio (sano, con los baches macro conocidos)
CRECIMIENTO_REAL = {2016: 1.00, 2017: 1.04, 2018: 0.98, 2019: 0.97, 2020: 0.92,
                    2021: 1.07, 2022: 1.05, 2023: 0.96, 2024: 0.98, 2025: 1.06,
                    2026: 1.04}


def _indice_precios():
    """Índice mensual acumulado (base=1 en el primer mes de la historia)."""
    idx, val = {}, 1.0
    inicio = MES_ACTUAL - ANIOS_HISTORIA * 12
    for m_abs in range(inicio, MES_ACTUAL + 1):
        anio = m_abs // 12
        f_mes = INFLACION_ANUAL.get(anio, 1.25) ** (1 / 12)
        val *= f_mes
        idx[m_abs] = val
    return idx


INDICE = _indice_precios()


def _crecimiento_acum(m_abs):
    """Nivel REAL del negocio en ese mes, relativo a HOY (hoy=1)."""
    nivel = 1.0
    anio = m_abs // 12
    for a in range(anio + 1, HOY.year + 1):
        nivel /= CRECIMIENTO_REAL.get(a, 1.0)
    return nivel


# --- catálogo: categorías con markup SANO de distribuidora y estacionalidad ----
# nombre, es_balanza, costo_rango, demanda_rango(u/mes), markup_rango, plantillas
CATEGORIAS = [
    ("aceites y aderezos", False, (2400, 6200), (220, 750), (0.17, 0.25),
     ["ACEITE GIRASOL {m} 900CC (X12U)", "ACEITE MEZCLA {m} 1.5L (X8U)",
      "MAYONESA {m} 500G (X12U)", "KETCHUP {m} 400G (X12U)", "VINAGRE {m} 1L (X12U)"]),
    ("almacén seco", False, (1200, 4100), (300, 1300), (0.15, 0.22),
     ["HARINA 000 {m} X1KG (X10U)", "ARROZ LARGO FINO {m} X1KG (X10U)",
      "FIDEOS GUISEROS {m} 500G (X15U)", "PURE DE TOMATE {m} 520G (X12U)",
      "LENTEJAS {m} 400G (X12U)", "AZUCAR {m} X1KG (X10U)", "YERBA {m} X1KG (X10U)"]),
    ("galletitas y golosinas", False, (1400, 3700), (260, 1050), (0.20, 0.28),
     ["GALLETITAS SURTIDAS {m} 400G (X20U)", "ALFAJOR TRIPLE {m} (X24U)",
      "TURRON {m} (X50U)", "CARAMELOS MASTICABLES {m} X800G"]),
    ("bebidas", False, (1900, 6600), (380, 1600), (0.16, 0.23),
     ["GASEOSA COLA {m} 2.25L (X6U)", "AGUA SIN GAS {m} 2L (X6U)",
      "JUGO EN POLVO {m} (X20S)", "SODA {m} 2L (X6U)", "VINO TINTO {m} 750CC (X6U)"]),
    ("lácteos", False, (2300, 8600), (300, 1150), (0.17, 0.24),
     ["LECHE ENTERA {m} 1L (X12U)", "YOGUR BEBIBLE {m} 900G (X6U)",
      "MANTECA {m} 200G (X30U)", "CREMA DE LECHE {m} 360G (X12U)",
      "DULCE DE LECHE {m} 400G (X12U)"]),
    ("fiambres y quesos (balanza)", True, (8200, 21000), (90, 380), (0.22, 0.30),
     ["JAMON COCIDO {m} (HORMA)", "PALETA {m} (HORMA)", "SALAME MILAN {m} (PLANCHA)",
      "QUESO CREMOSO {m} (HORMA)", "QUESO BARRA {m} (HORMA)", "MORTADELA {m} (PLANCHA)",
      "BONDIOLA {m} (PIEZA)", "QUESO SARDO {m} (HORMA)"]),
    ("congelados", False, (3600, 12400), (130, 580), (0.19, 0.27),
     ["HAMBURGUESAS {m} X4 (X12C)", "PAPAS BASTON {m} 2.5KG (X6U)",
      "FILET MERLUZA {m} X1KG (X8U)", "PATITAS DE POLLO {m} 700G (X12U)"]),
    ("limpieza y perfumería", False, (1700, 5800), (180, 760), (0.18, 0.26),
     ["LAVANDINA {m} 2L (X8U)", "DETERGENTE {m} 750CC (X12U)",
      "JABON EN POLVO {m} 3KG (X4U)", "PAPEL HIGIENICO {m} X4 (X10P)",
      "ROLLO DE COCINA {m} X3 (X10P)"]),
]

# Estacionalidad POR CATEGORÍA (índice por mes calendario; media anual ≈ 1).
ESTACION_CAT = {
    "aceites y aderezos":          {1: 0.95, 2: 0.95, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0, 7: 1.0, 8: 1.0, 9: 1.0, 10: 1.0, 11: 1.05, 12: 1.30},
    "almacén seco":                {1: 0.92, 2: 0.95, 3: 1.02, 4: 1.02, 5: 1.05, 6: 1.05, 7: 1.05, 8: 1.02, 9: 1.0, 10: 1.0, 11: 1.0, 12: 1.12},
    "galletitas y golosinas":      {1: 0.85, 2: 0.90, 3: 1.0, 4: 1.05, 5: 1.10, 6: 1.12, 7: 1.15, 8: 1.05, 9: 0.95, 10: 0.95, 11: 1.0, 12: 1.35},
    "bebidas":                     {1: 1.35, 2: 1.22, 3: 1.05, 4: 0.92, 5: 0.85, 6: 0.80, 7: 0.80, 8: 0.85, 9: 0.95, 10: 1.05, 11: 1.15, 12: 1.55},
    "lácteos":                     {1: 0.98, 2: 0.98, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.02, 7: 1.02, 8: 1.0, 9: 1.0, 10: 1.0, 11: 1.0, 12: 1.10},
    "fiambres y quesos (balanza)": {1: 1.10, 2: 1.02, 3: 0.98, 4: 0.95, 5: 0.92, 6: 0.92, 7: 0.95, 8: 0.95, 9: 0.98, 10: 1.02, 11: 1.10, 12: 1.60},
    "congelados":                  {1: 0.90, 2: 0.92, 3: 1.0, 4: 1.05, 5: 1.12, 6: 1.18, 7: 1.18, 8: 1.12, 9: 1.02, 10: 0.95, 11: 0.92, 12: 1.02},
    "limpieza y perfumería":       {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0, 7: 1.0, 8: 1.0, 9: 1.02, 10: 1.02, 11: 1.02, 12: 1.08},
}

MARCAS = ["EL LITORAL", "DON TIMOTEO", "LA RIBERA", "CAMPO ALEGRE", "SANTA CLARA",
          "GUARANI", "TIERRA ROJA", "EL PARANA", "COSTA DULCE", "MONTE CHICO"]
PROVEEDORES = ["Alimentos del Paraná SA", "Distrib. Mayorista Guaraní", "Frigorífico La Ribera",
               "Lácteos Campo Alegre", "Golosinas Costa Dulce SRL", "Limpieza Total SA"]
UBICACIONES = [f"Pasillo {p} - Rack {r}" for p in range(1, 7) for r in "ABC"] + \
              ["Cámara de frío 1", "Cámara de frío 2", "Cámara congelados"]

DEMANDA_ESCALA = 0.65  # calibra la facturación mensual a ~$700M


def d_iso(m_abs, dia):
    return datetime.date(m_abs // 12, m_abs % 12 + 1, min(dia, 28)).isoformat()


def generar_catalogo():
    arts, codigo = [], 1000
    for (cat, balanza, (c0, c1), (d0, d1), (mk0, mk1), plantillas) in CATEGORIAS:
        for plantilla in plantillas:
            for m in R.sample(MARCAS, 10):
                codigo += 1
                costo = round(R.uniform(c0, c1), 2)
                pvp = round(costo * (1 + R.uniform(mk0, mk1)), 2)
                demanda_mes = R.uniform(d0, d1) * DEMANDA_ESCALA * (0.35 if balanza else 1.0)
                arts.append({
                    "codigo": codigo,
                    "descripcion": plantilla.format(m=m),
                    "estado": "activo",
                    "tipo": cat,
                    "proveedor": R.choice(PROVEEDORES),
                    "um": "KG" if balanza else "UN",
                    "venta_x_peso": balanza,
                    "cota_inf": round(R.uniform(0.2, 0.5), 2) if balanza else None,
                    "cota_sup": round(R.uniform(6.0, 25.0), 2) if balanza else None,
                    "valor_peso": None,
                    "stock": 0.0,
                    "costo_neto": round(costo / 1.21, 2),
                    "costo_iva": costo,
                    "pvp": pvp,
                    "antiguedad_costo_dias": R.uniform(3, 45),
                    "_demanda_mes": demanda_mes,
                })
    R.shuffle(arts)
    return arts


def inyectar_puntitos(arts):
    """Los POCOS problemas realistas de un negocio sano (no un desastre)."""
    pool = arts[:]
    # margen fino (4): quedaron con lista vieja, ganan monedas
    for a in pool[:4]:
        a["pvp"] = round(a["costo_iva"] * R.uniform(1.01, 1.05), 2)
    # sin precio (8): altas recientes a medio cargar
    for a in pool[4:12]:
        a["pvp"] = None
    # costo viejo (5)
    for a in pool[12:17]:
        a["antiguedad_costo_dias"] = R.uniform(380, 560)
    # negativos chicos (2): salidas sin registrar
    for a in pool[17:19]:
        a["stock"] = float(-R.randint(3, 12))
        a["_demanda_mes"] = 0
    # anulados con resto de stock (3)
    for a in pool[19:22]:
        a["estado"] = "anulado"
        a["stock"] = float(R.randint(6, 40))
        a["_demanda_mes"] = 0
    # balanzas: todas calibradas, salvo 2 dudosas
    balanzas = [a for a in arts if a["venta_x_peso"] and a["estado"] == "activo"]
    for a in balanzas:
        a["valor_peso"] = round(R.uniform(a["cota_inf"], a["cota_sup"]), 2)
    for a in R.sample(balanzas, 2):
        a["valor_peso"] = round(a["cota_sup"] * R.uniform(1.8, 3.0), 2)


def asignar_rotacion_y_stock(arts):
    """Clase A/B/C por facturación → días de cobertura → stock. El inmovilizado
    de cada producto SALE de su rotación, no es un número suelto."""
    vendibles = [a for a in arts if a["estado"] == "activo" and a["_demanda_mes"] > 0
                 and a["stock"] == 0.0]
    vendibles.sort(key=lambda a: a["_demanda_mes"] * (a["pvp"] or a["costo_iva"]), reverse=True)
    n = len(vendibles)
    al_borde = set(id(a) for a in R.sample(vendibles[: n // 2], 6))  # pocos quiebres
    for i, a in enumerate(vendibles):
        if i < n * 0.30:
            a["_clase"], dias = "A", R.uniform(7, 15)
        elif i < n * 0.70:
            a["_clase"], dias = "B", R.uniform(15, 35)
        else:
            a["_clase"], dias = "C", R.uniform(30, 75)
        if id(a) in al_borde:
            dias = R.uniform(2, 6)
        a["stock"] = round(a["_demanda_mes"] / 30 * dias, 1 if a["venta_x_peso"] else 0)


def generar_ventas(arts):
    """10 años: últimos 24 meses POR SKU (rotación/margen finos) + 96 meses
    previos por CATEGORÍA (Evolución/estacionalidad decenal, sin reventar el JSON)."""
    filas = []
    vendibles = [a for a in arts if a["estado"] == "activo" and a["_demanda_mes"] > 0
                 and a.get("pvp")]
    idx_hoy = INDICE[MES_ACTUAL]

    # 24 meses recientes, por SKU
    for atras in range(24, 0, -1):
        m_abs = MES_ACTUAL - atras
        mes_cal = m_abs % 12 + 1
        nivel = _crecimiento_acum(m_abs)
        f_precio = INDICE[m_abs] / idx_hoy
        for art in vendibles:
            est = ESTACION_CAT[art["tipo"]][mes_cal]
            qty = art["_demanda_mes"] * est * nivel * R.uniform(0.92, 1.08)
            if qty <= 0:
                continue
            boca = R.choices(BOCAS, weights=BOCA_PESO)[0]
            filas.append({
                "fecha": d_iso(m_abs, R.randint(3, 26)),
                "producto": art["descripcion"],
                "codigo": art["codigo"],
                "categoria": art["tipo"],
                "cantidad": round(qty, 1 if art["venta_x_peso"] else 0),
                "precio": round(art["pvp"] * f_precio, 2),
                "boca": boca,
            })

    # años 3-10, resumen mensual por categoría (histórico para Evolución)
    monto_cat_hoy = {}
    for a in vendibles:
        monto_cat_hoy.setdefault(a["tipo"], 0.0)
        monto_cat_hoy[a["tipo"]] += a["_demanda_mes"] * a["pvp"]
    for atras in range(ANIOS_HISTORIA * 12, 24, -1):
        m_abs = MES_ACTUAL - atras
        mes_cal = m_abs % 12 + 1
        nivel = _crecimiento_acum(m_abs)
        f_precio = INDICE[m_abs] / idx_hoy
        for cat, monto_hoy in monto_cat_hoy.items():
            est = ESTACION_CAT[cat][mes_cal]
            monto = monto_hoy * est * nivel * f_precio * R.uniform(0.96, 1.04)
            filas.append({
                "fecha": d_iso(m_abs, 15),
                "producto": f"VENTAS {cat.upper()} (RESUMEN MENSUAL)",
                "categoria": cat,
                "cantidad": 1,
                "precio": round(monto, 2),
                "boca": "Consolidado",
            })
    return filas


def generar_recepciones(arts):
    """Lo comprado ENTRA: reposición de las últimas 4 semanas coherente con la
    demanda (A semanal, B quincenal). Las compras del sistema real llegarán
    como módulo aparte; esto es el dato que el depósito ya registra."""
    filas = []
    for a in arts:
        if a.get("_clase") not in ("A", "B"):
            continue
        frecuencia = 7 if a["_clase"] == "A" else 14
        for atras_dias in range(frecuencia, 29, frecuencia):
            fecha = HOY - datetime.timedelta(days=atras_dias + R.randint(0, 2))
            qty = a["_demanda_mes"] / 30 * frecuencia * R.uniform(0.9, 1.15)
            filas.append({
                "fecha": fecha.isoformat(),
                "codigo": a["codigo"],
                "producto": a["descripcion"],
                "proveedor": a["proveedor"],
                "cantidad": round(qty, 1 if a["venta_x_peso"] else 0),
                "deposito": "Depósito Central",
            })
    return filas


def generar_deposito(arts):
    """WMS: ubicaciones, lotes y vencimientos. Negocio sano: pocos vencidos."""
    filas = []
    con_stock = sorted([a for a in arts if a["stock"] and a["stock"] > 0],
                       key=lambda a: a["stock"] * a["costo_iva"], reverse=True)[:380]
    vencidos = set(id(a) for a in R.sample(con_stock, 2))
    por_vencer = set(id(a) for a in R.sample([a for a in con_stock if id(a) not in vencidos], 8))
    discrepan = set(id(a) for a in R.sample(con_stock, 5))
    for i, a in enumerate(con_stock):
        if id(a) in vencidos:
            vto = HOY - datetime.timedelta(days=R.randint(2, 12))
        elif id(a) in por_vencer:
            vto = HOY + datetime.timedelta(days=R.randint(3, 14))
        else:
            vto = HOY + datetime.timedelta(days=R.randint(45, 360))
        es_frio = a["venta_x_peso"] or "congelad" in a["tipo"]
        ubic = R.choice(UBICACIONES[-3:]) if es_frio else R.choice(UBICACIONES[:-3])
        cant = a["stock"] * (R.uniform(0.90, 0.97) if id(a) in discrepan else 1.0)
        filas.append({
            "codigo": a["codigo"], "producto": a["descripcion"], "ubicacion": ubic,
            "lote": f"L-{vto.year}-{300 + i}", "vencimiento": vto.isoformat(),
            "cantidad": round(cant, 1),
        })
    # Conciliación — siete lotes CONTADOS con una diferencia contra el sistema:
    # los cinco que ya tenían menos físico que contable, más dos sanos, con un
    # conteo que se pasa o se queda corto. Factores fijos, sin consumir R: el
    # resto del dataset queda byte-igual. Sin esto la pantalla de Conciliación
    # nacía vacía aunque el motor estuviera escrito y testeado.
    factores = iter([0.94, 1.03, 0.97, 0.91, 1.02, 0.96, 0.98])
    contados = [f for f, a in zip(filas, con_stock) if id(a) in discrepan]
    contados += [f for f, a in zip(filas, con_stock)
                 if id(a) not in discrepan and id(a) not in vencidos
                 and id(a) not in por_vencer][:2]
    for f in contados:
        f["counted_qty"] = round(f["cantidad"] * next(factores), 1)

    # Conocimiento · pieza 12 — una discrepancia de BALANZA por debajo del 1%:
    # la que la regla de Aldo ("la balanza 2 desvía <1%: no me alertes") suprime.
    # Determinista, sin consumir R: el fiambre de mayor valor sin otra anomalía,
    # con ~0.7% menos de físico que lo contable.
    fiambre = next((a for a in con_stock if "balanza" in (a.get("tipo") or "")
                    and id(a) not in discrepan and id(a) not in vencidos
                    and id(a) not in por_vencer), None)
    if fiambre:
        for f in filas:
            if f["codigo"] == fiambre["codigo"]:
                f["cantidad"] = round(fiambre["stock"] * 0.993, 1)  # ~0.7% bajo lo contable
                break
    return filas


# 24 clientes; 3 morosos moderados (~$85M en mora: normal para $700M/mes).
# (id, nombre, saldo, límite, plazo, días sin pagar, promedio de pago)
CLIENTES = [
    ("autoservicio_9dejulio", "Autoservicio 9 de Julio", 42_000_000, 60_000_000, 30, 58, 29),
    ("super_el_puente", "Supermercado El Puente", 55_000_000, 80_000_000, 30, 17, 24),
    ("almacen_sanmartin", "Almacén San Martín", 24_500_000, 30_000_000, 30, 49, 27),
    ("mini_costanera", "Minimercado Costanera", 18_900_000, 25_000_000, 30, 21, 26),
    ("despensa_dona_elsa", "Despensa Doña Elsa", 19_200_000, 22_000_000, 30, 66, 31),
    ("hoteleria_del_sol", "Hotelería del Sol", 16_800_000, 25_000_000, 30, 19, 25),
    ("comedor_escolar_12", "Comedor Escolar N°12", 12_600_000, 18_000_000, 45, 28, 41),
    ("super_dos_hermanos", "Súper Dos Hermanos", 21_400_000, 30_000_000, 30, 12, 22),
    ("autoservicio_belgrano", "Autoservicio Belgrano", 14_300_000, 20_000_000, 30, 9, 21),
    ("granja_los_alamos", "Granja Los Álamos", 8_100_000, 12_000_000, 30, 15, 23),
    ("kiosco_la_terminal", "Kiosco La Terminal", 4_200_000, 5_000_000, 15, 11, 14),
    ("rotiseria_avenida", "Rotisería Avenida", 3_800_000, 6_000_000, 15, 8, 12),
    ("bar_el_muelle", "Bar El Muelle", 2_900_000, 4_000_000, 15, 6, 13),
    ("panaderia_trigal", "Panadería El Trigal", 3_400_000, 5_000_000, 15, 5, 11),
    ("despensa_la_union", "Despensa La Unión", 6_700_000, 10_000_000, 30, 24, 27),
    ("super_avenida_norte", "Súper Avenida Norte", 17_500_000, 25_000_000, 30, 14, 23),
    ("almacen_donpedro", "Almacén Don Pedro", 5_900_000, 8_000_000, 30, 20, 25),
    ("mercadito_del_rio", "Mercadito del Río", 7_800_000, 10_000_000, 30, 26, 28),
    ("kiosco_plaza", "Kiosco Plaza", 1_900_000, 3_000_000, 15, 7, 12),
    ("comidas_el_fogon", "Comidas El Fogón", 4_600_000, 7_000_000, 15, 10, 13),
    ("autoservicio_mitre", "Autoservicio Mitre", 11_200_000, 15_000_000, 30, 16, 24),
    ("hosteria_costanera", "Hostería Costanera", 6_300_000, 9_000_000, 30, 13, 22),
    ("proveduria_la_rural", "Proveeduría La Rural", 0, 8_000_000, 15, 0, 14),
    ("bufete_club_regatas", "Bufete Club Regatas", 2_400_000, 4_000_000, 15, 4, 10),
]


def generar_cuentas():
    """P25·B4 — cada cliente trae su HISTORIAL SALDADO (ventas y pagos pasados,
    deterministas, neto CERO): el "paga a X días en promedio" sale de historia
    real visible en el modal, sin mover saldos actuales ni el total adeudado."""
    out = []
    for (cid, nombre, saldo, limite, plazo, dias_sin_pagar, prom) in CLIENTES:
        rng = random.Random(cid)
        base = saldo if saldo > 0 else 5_000_000
        n = rng.randint(6, 9)
        # delays que PROMEDIAN exactamente el promedio_pago_dias declarado
        delays = [max(3, prom + rng.randint(-8, 8)) for _ in range(n - 1)]
        delays.append(max(3, prom * n - sum(delays)))
        movs = []
        fecha = datetime.date(2025, 1, 15) + datetime.timedelta(days=rng.randint(0, 20))
        for i, delay in enumerate(delays):
            monto = int(round(base * rng.uniform(0.35, 0.95), -4))
            venta = fecha + datetime.timedelta(days=i * rng.randint(38, 55))
            pago = venta + datetime.timedelta(days=delay)
            if pago >= datetime.date(2026, 5, 1):
                break
            movs.append({"fecha": venta.isoformat(), "tipo": "venta", "monto": monto,
                         "detalle": "Pedido mayorista", "historico": True})
            movs.append({"fecha": pago.isoformat(), "tipo": "pago", "monto": monto,
                         "detalle": f"Pago a {delay} días", "historico": True})
        if saldo:
            movs.append({"fecha": (HOY - datetime.timedelta(days=dias_sin_pagar)).isoformat(),
                         "tipo": "venta", "monto": saldo, "detalle": "Pedido mayorista"})
        out.append({"id": cid, "nombre": nombre, "saldo": saldo, "limite_credito": limite,
                    "plazo_dias": plazo, "dias_sin_pagar": dias_sin_pagar,
                    "promedio_pago_dias": prom, "movimientos": movs})
    return out


# --- QUÉ COMPRA CADA CLIENTE (el puente que faltaba) --------------------------
#
# Hasta acá, las cuentas corrientes guardaban "Pedido mayorista" y un monto: el
# renglón nunca decía QUÉ se llevó el cliente. Sin ese dato, media docena de
# cruces no se pueden ni plantear ("el que más te debe se lleva justo lo que se
# te vence", "le vendés barato al que te aprieta"), y el grafo tenía que
# INFERIR el puente cliente↔rubro (ver core/grafo.AFINIDAD).
#
# Acá se abre cada pedido en sus renglones. Dos reglas que lo hacen creíble:
#   1. El TOTAL de cada pedido es el monto del movimiento, intacto: la línea
#      final absorbe el redondeo. Ningún saldo, mora ni total adeudado se mueve.
#   2. Los productos salen del rubro del cliente (una panadería no compra lo
#      mismo que un kiosco) y se eligen ponderados por lo que ESE producto vende
#      de verdad — no al azar plano.
# Random propio (20260804): los archivos de arriba quedan byte-iguales.
RUBRO_CLIENTE = [
    (("kiosco",), ("galletitas y golosinas", "bebidas")),
    (("bar", "bufete", "club", "regatas"),
     ("bebidas", "fiambres y quesos (balanza)", "galletitas y golosinas")),
    (("rotiser", "comidas", "comedor", "hoster", "hotel", "granja", "fogon"),
     ("congelados", "aceites y aderezos", "fiambres y quesos (balanza)", "lácteos")),
    (("panader", "trigal"), ("lácteos", "almacén seco", "aceites y aderezos")),
]
# el resto (super, autoservicio, almacén, despensa, minimercado, proveeduría) es
# reventa: surtido ancho, que es exactamente lo que compra un negocio de barrio
RUBRO_REVENTA = ("almacén seco", "lácteos", "bebidas", "limpieza y perfumería",
                 "galletitas y golosinas", "fiambres y quesos (balanza)")


def _rubros_de(nombre: str) -> tuple:
    n = _sin_acentos(nombre).lower()
    for claves, cats in RUBRO_CLIENTE:
        if any(k in n for k in claves):
            return cats
    return RUBRO_REVENTA


def _sin_acentos(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", str(s))
                   if not unicodedata.combining(c))


def generar_ventas_por_cliente(arts, cuentas_, ventas):
    """Abre cada 'Pedido mayorista' de la cuenta corriente en sus renglones."""
    RC = random.Random(20260804)
    # lo que cada producto vende de verdad (12m): pondera la elección
    corte = (HOY - datetime.timedelta(days=365)).isoformat()
    peso_cod = {}
    for f in ventas:
        if f["fecha"] >= corte:
            peso_cod[f["codigo"]] = peso_cod.get(f["codigo"], 0.0) + f["cantidad"] * f["precio"]
    vendibles = [a for a in arts
                 if a["estado"] == "activo" and (a.get("pvp") or 0) > 0 and a.get("tipo")]
    por_cat: dict = {}
    for a in vendibles:
        por_cat.setdefault(a["tipo"], []).append(a)

    salida = []
    for c in cuentas_:
        cats = [x for x in _rubros_de(c["nombre"]) if por_cat.get(x)]
        if not cats:
            continue
        canasta = [a for cat in cats for a in por_cat[cat]]
        pesos = [peso_cod.get(a["codigo"], 0.0) + 1.0 for a in canasta]
        pedidos = []
        for m in c["movimientos"]:
            if m["tipo"] != "venta":
                continue
            total = float(m["monto"])
            n = RC.randint(3, 7)
            elegidos, vistos = [], set()
            for _ in range(n * 3):
                if len(elegidos) >= n:
                    break
                a = RC.choices(canasta, weights=pesos, k=1)[0]
                if a["codigo"] in vistos:
                    continue
                vistos.add(a["codigo"])
                elegidos.append(a)
            # Mate isn't drunk alone: an order that already has yerba, most
            # of the time (not always — the gap IS the opportunity) also
            # picks up sugar from the same basket. Nobody ever set that
            # combo up on purpose: it's a pattern that lives in the orders,
            # waiting for "combo_no_percibido" to notice it.
            mate = next((a for a in elegidos if a["descripcion"].startswith("YERBA")), None)
            sugar = next((a for a in canasta if a["descripcion"].startswith("AZUCAR")
                          and a["codigo"] not in vistos), None)
            if mate and sugar and len(elegidos) >= 3 and RC.random() < 0.8:
                swap_at = next((i for i in range(len(elegidos) - 1, -1, -1)
                                if elegidos[i] is not mate), None)
                if swap_at is not None:
                    vistos.discard(elegidos[swap_at]["codigo"])
                    vistos.add(sugar["codigo"])
                    elegidos[swap_at] = sugar
            partes = [RC.uniform(0.6, 1.6) for _ in elegidos]
            suma = sum(partes)
            items, acumulado = [], 0.0
            for i, (a, p) in enumerate(zip(elegidos, partes)):
                pvp = float(a["pvp"])
                if i < len(elegidos) - 1:
                    monto = round(total * p / suma, 2)
                    cant = round(monto / pvp, 2)
                    monto = round(cant * pvp, 2)
                else:
                    # la última línea CIERRA contra el total del movimiento: el
                    # monto de la cuenta corriente es el número canónico, no esto
                    monto = round(total - acumulado, 2)
                    cant = round(monto / pvp, 2)
                acumulado = round(acumulado + monto, 2)
                items.append({"codigo": a["codigo"], "producto": a["descripcion"],
                              "categoria": a["tipo"], "cantidad": cant,
                              "precio": round(pvp, 2), "monto": monto})
            pedidos.append({"fecha": m["fecha"], "monto": round(total, 2),
                            "historico": bool(m.get("historico")), "items": items})
        salida.append({"cliente_id": c["id"], "nombre": c["nombre"],
                       "rubros": list(cats), "pedidos": pedidos})
    return salida


def generar_logistica():
    camiones = ["Camión 1 - Walter", "Camión 2 - Osmar", "Camión 3 - Tercerizado"]
    filas = []
    nombres = [c[1] for c in CLIENTES]
    pid = 4400
    for delta, estados in ((-1, ["pendiente"]),
                           (0, ["entregado"] * 9 + ["en camino"] * 4 + ["pendiente"] * 5),
                           (1, ["pendiente"] * 8), (2, ["pendiente"] * 6)):
        for e in estados:
            pid += 1
            filas.append({
                "pedido": f"P-{pid}", "cliente": R.choice(nombres),
                "direccion": f"{R.choice(['Av. Costanera', 'San Martín', 'Belgrano', 'Ruta 11 km'])} {R.randint(50, 2100)}",
                "estado": e, "fecha_prevista": (HOY + datetime.timedelta(days=delta)).isoformat(),
                "transporte": R.choice(camiones),
            })
    return filas


def generar_caja():
    """60 cierres diarios sanos (la caja es el mostrador, no la facturación
    mayorista): $2-5M/día, diferencias casi siempre cero. Sólo si no existe.

    Devuelve (creada, historial). El historial se devuelve SIEMPRE (creado o
    leído del disco) porque el canal mostrador se deriva de él: la plata del
    mostrador no se inventa aparte, es la misma caja repartida por local."""
    path = os.path.join(HERE, "caja.json")
    if os.path.exists(path):
        # NO consume el Random compartido: los demás archivos quedan byte-igual.
        return False, json.load(open(path, encoding="utf-8")).get("historial", [])
    hist = []
    for atras in range(60, 0, -1):
        f = HOY - datetime.timedelta(days=atras)
        if f.weekday() == 6:  # domingo cerrado
            continue
        total = round(R.uniform(2_200_000, 4_900_000) * (1.25 if f.weekday() == 5 else 1.0))
        # Same pair of draws as before (same ranges, same list length for
        # R.choice): the shared Random stays BYTE IDENTICAL for everything
        # generated afterward. The only thing that changes is what we build
        # with them: on Saturdays (busier till, more rush, a backup cashier)
        # the shortfall shows up far more often than the rest of the week —
        # a pattern "faltante_caja_patron" can find, that a plain average hides.
        shortfall, overage = R.randint(500, 8000), R.randint(500, 5000)
        options = ([0, 0, -shortfall, -shortfall, -shortfall, -shortfall, -shortfall, -shortfall, overage]
                   if f.weekday() == 5 else
                   [0, 0, 0, 0, 0, 0, 0, -shortfall, overage])
        dif = R.choice(options)
        hist.append({"fecha": f.isoformat(), "total": total, "diferencia": dif})
    caja = {
        "abierta": True, "fecha": HOY.isoformat(), "saldo_inicial": 250_000,
        "movimientos": [
            {"tipo": "ingreso", "medio": "efectivo", "monto": 1_240_000, "detalle": "Ventas mostrador"},
            {"tipo": "ingreso", "medio": "tarjeta", "monto": 860_000, "detalle": "Ventas con tarjeta"},
            {"tipo": "ingreso", "medio": "transferencia", "monto": 1_530_000, "detalle": "Cobro Almacén San Martín"},
            {"tipo": "ingreso", "medio": "mercadopago", "monto": 420_000, "detalle": "QR Mercado Pago"},
            {"tipo": "egreso", "medio": "efectivo", "monto": 180_000, "detalle": "Combustible camiones"},
        ],
        "historial": hist,
    }
    json.dump(caja, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return True, hist


# --- canal MOSTRADOR (minorista) y traslados a locales propios -------------------
# La distribuidora no vende de una sola manera: además del mayorista (los ~430
# SKUs a precio de lista, margen 15-21%) tiene TRES bocas propias donde vende al
# público, con márgenes de mostrador — que son otro planeta: una horma de fiambre
# feteada deja ~80% sobre el costo y vendida entera ~30%. Sin esta separación,
# "¿cuánto gano por grupo?" no tiene respuesta honesta.
#
# Nada de esto se inventa suelto: la plata del mostrador ES la caja diaria que ya
# existe (generar_caja), repartida por local; y lo que los locales venden tuvo que
# SALIR del depósito → de ahí los traslados internos (Bloque F).
#
# Los Random son PROPIOS (20260710 / 20260711): no tocan el stream compartido,
# así inventory.json, apartados.json y cuentas.json quedan byte-igual.

# id, categorías de catálogo que lo alimentan, recargo sobre costo, presentación
GRUPOS_MOSTRADOR = [
    ("feteado", ["fiambres y quesos (balanza)"], 0.80, "feteado"),
    ("pieza_entera", ["fiambres y quesos (balanza)"], 0.30, "pieza entera"),
    ("congelados", ["congelados"], 0.60, None),
    ("lacteos", ["lácteos"], 0.45, None),
    ("almacen", ["almacén seco", "aceites y aderezos"], 0.42, None),
    ("galletitas", ["galletitas y golosinas"], 0.45, None),
    ("bebidas", ["bebidas"], 0.40, None),
    ("limpieza", ["limpieza y perfumería"], 0.45, None),
]
# Qué porción de la venta de mostrador aporta cada grupo (suma 1.0).
MIX_MOSTRADOR = {"feteado": 0.22, "pieza_entera": 0.03, "congelados": 0.08,
                 "lacteos": 0.12, "almacen": 0.22, "galletitas": 0.10,
                 "bebidas": 0.15, "limpieza": 0.08}

# Los locales que SE REPONEN del depósito. Casa Central vende sobre el depósito
# mismo (no hay traslado que registrar); Norte y Puerto sí.
LOCALES_REPUESTOS = ["Sucursal Norte", "Sucursal Puerto"]
# El local le compra al depósito a precio de lista mayorista y recarga ~45% en el
# mostrador: de cada $100 de caja del local, ~$69 salieron como "venta" del ERP.
FACTOR_TRASLADO = 0.69
# Lo que los locales realmente tienen en góndola: rubros de consumo diario, no
# el catálogo entero. Por eso el traslado DEFORMA el ranking del ERP — mueve
# mucho volumen de pocos SKUs baratos.
RUBROS_MOSTRADOR = ["almacén seco", "bebidas", "galletitas y golosinas",
                    "lácteos", "limpieza y perfumería"]
SKUS_POR_LOCAL = 55


def generar_cierres_por_local(caja_hist):
    """Bloque E — el cierre diario de CADA local. Hoy una empleada los imputa a
    mano en un Excel y arma el comparativo cuando el dueño lo pide; acá salen
    solos. Reparten EXACTAMENTE el total de caja de cada día (la caja del negocio
    no cambia: se abre por boca), con una tendencia real adentro — Puerto viene
    creciendo y Norte cayendo — para que el comparativo diga algo."""
    R4 = random.Random(20260710)
    out = []
    n = max(1, len(caja_hist) - 1)
    for i, dia in enumerate(caja_hist):
        t = i / n
        # La tendencia tiene que GANARLE al ruido diario, si no el comparativo
        # semanal no dice nada: Puerto sube fuerte, Norte cae fuerte, Casa
        # Central se mueve poco. Ruido chico (±2.5%) para que se vea la señal.
        base = [0.57 - 0.04 * t, 0.27 - 0.12 * t, 0.16 + 0.16 * t]
        pesos = [p * R4.uniform(0.975, 1.025) for p in base]
        s = sum(pesos)
        montos = [int(round(dia["total"] * p / s)) for p in pesos]
        montos[0] += dia["total"] - sum(montos)   # el redondeo lo absorbe Casa Central
        for nombre, monto in zip(BOCAS, montos):
            out.append({"fecha": dia["fecha"], "local": nombre, "total": monto})
    return out


def generar_mostrador(arts, caja_hist):
    """El canal minorista: qué grupos se venden en el mostrador, con qué recargo,
    y cuánto factura cada local por día. La plata sale de la caja que ya existe."""
    cierres = generar_cierres_por_local(caja_hist)
    dias = len({c["fecha"] for c in cierres}) or 1
    venta_diaria = sum(c["total"] for c in cierres) / dias
    grupos = []
    for gid, cats, recargo, presentacion in GRUPOS_MOSTRADOR:
        grupos.append({
            "id": gid,
            "categorias": cats,
            "presentacion": presentacion,
            "recargo_sobre_costo_pct": round(recargo * 100, 1),
            # margen sobre la VENTA, que es como se mide el margen en el P&L
            "margen_sobre_venta_pct": round(recargo / (1 + recargo) * 100, 1),
            "share_venta": MIX_MOSTRADOR[gid],
        })
    return {
        "_nota": "Canal MOSTRADOR (minorista) del demo — 100% ficticio. La venta "
                 "diaria sale de los cierres de caja que ya existen; los recargos "
                 "por grupo son los del rubro (feteado ~80% sobre costo, pieza "
                 "entera ~30%, congelados ~60%, almacén 40-45%).",
        "locales": BOCAS,
        "venta_diaria_promedio": round(venta_diaria, 2),
        "grupos": grupos,
        "cierres": cierres,
    }


def generar_traslados_internos(arts, caja_hist):
    """Bloque F — la mercadería que sale del depósito HACIA los locales propios.
    El ERP la registra como venta (hay remito y precio de lista), y por eso
    ensucia todas las estadísticas: un local propio aparece como cliente y los
    bultos que se mandan a la góndola aparecen como los productos más vendidos.
    Ángela los separa; acá se generan para que haya qué separar."""
    R3 = random.Random(20260711)
    idx_hoy = INDICE[MES_ACTUAL]
    surtido = [a for a in arts
               if a["estado"] == "activo" and a.get("pvp") and a["_demanda_mes"] > 0
               and a["tipo"] in RUBROS_MOSTRADOR]
    # el surtido de góndola: los de más VOLUMEN (unidades), no los de más plata
    surtido.sort(key=lambda a: -a["_demanda_mes"])
    surtido = surtido[:SKUS_POR_LOCAL]
    total_demanda = sum(a["_demanda_mes"] for a in surtido) or 1.0
    # el ritmo del mostrador sale de la caja real, no de un número suelto
    dia_prom = (sum(c["total"] for c in caja_hist) / len(caja_hist)) if caja_hist else 0.0
    filas = []
    for local in LOCALES_REPUESTOS:
        peso_local = BOCA_PESO[BOCAS.index(local)]
        for atras in range(24, 0, -1):
            m_abs = MES_ACTUAL - atras
            f_precio = INDICE[m_abs] / idx_hoy
            # lo que el local necesita reponer ese mes, a precio de lista mayorista
            objetivo = dia_prom * 26 * peso_local * FACTOR_TRASLADO * f_precio
            for a in surtido:
                share = a["_demanda_mes"] / total_demanda * R3.uniform(0.85, 1.15)
                monto = objetivo * share
                precio = a["pvp"] * f_precio
                qty = monto / precio if precio else 0
                if qty < 1:
                    continue
                filas.append({
                    "fecha": d_iso(m_abs, R3.randint(2, 27)),
                    "codigo": a["codigo"],
                    "producto": a["descripcion"],
                    "categoria": a["tipo"],
                    "cantidad": round(qty, 1 if a["venta_x_peso"] else 0),
                    "precio": round(precio, 2),
                    "destino": local,
                    "motivo": "reposición de local propio",
                })
    return filas


CSV_STAGING = """codigo,descripcion,cantidad,precio unitario,proveedor
5901,QUESO PATEGRAS SANTA CLARA (HORMA),12,18.450,50,Lácteos Campo Alegre
5902,MIEL PURA MONTE CHICO 500G (X12U),48,"4.980",Alimentos del Paraná SA
5903,ACEITUNAS VERDES LA RIBERA 300G (X12U),36,3.120,Alimentos del Paraná SA
5904,PICADILLO DE CARNE GUARANI 90G (X24U),60,,Distrib. Mayorista Guaraní
5905,tostadas de gluten don timoteo (X15U),40,2.590,Alimentos del Paraná SA
5903,ACEITUNAS VERDES LA RIBERA 300G (X12U),36,3.120,Alimentos del Paraná SA
5906,ARVEJAS REMOJADAS EL PARANA 350G (X12U),72,1.980,Alimentos del Paraná SA
5907,DURAZNOS EN ALMIBAR COSTA DULCE 820G,24,5.640,Golosinas Costa Dulce SRL
5908,SAL FINA TIERRA ROJA 500G (X24U),96,1.150,Distrib. Mayorista Guaraní
5909,MERMELADA DE CIRUELA CAMPO ALEGRE 454G,30,,Lácteos Campo Alegre
5910,GALLETAS DE AGUA EL LITORAL 3X100G,55,2.340,Golosinas Costa Dulce SRL
5911,CAFE TORRADO LA RIBERA 500G,18,12.800,Alimentos del Paraná SA
"""


def sembrar_staging():
    """Un batch pendiente en el staging: la carga de la semana con sus puntitos
    (2 sin precio, 1 duplicado, 1 monto con coma dudosa, 1 minúsculas). Se crea
    por el MISMO flujo real (core.staging), sólo si no hay nada pendiente."""
    if os.path.exists(os.path.join(HERE, "staging.json")):
        return False
    import sys
    os.environ.setdefault("POLPILOT_TENANT", "demo")
    os.environ.setdefault("POLPILOT_DATA_DIR", HERE)
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "backend"))
    from core import staging
    staging.crear_batch("altas_proveedores_semana.csv", CSV_STAGING)
    return True


def sembrar_auditoria():
    """Historia de uso: el demo NO es una instalación virgen. La auditoría
    arranca con la semana previa de trabajo (mismos slugs que graban los flujos
    reales — el feed del Inicio y el panel de Ángela ya saben traducirlos).
    Fechas relativas a HOY (congelado): determinista. Siembra sólo si la
    auditoría no registra TRABAJO todavía (los eventos administrativos —
    idioma, solicitudes — no cuentan como historia y se preservan)."""
    path = os.path.join(HERE, "audit.json")
    administrativos = {"editar_descripcion_perfil", "cambiar_foto_perfil",
                       "cambiar_idioma", "solicitar_modulo",
                       "resolver_solicitud_modulo", "cambiar_modulo_empleado"}
    existentes = []
    if os.path.exists(path):
        existentes = json.load(open(path, encoding="utf-8"))
        if any(e.get("accion") not in administrativos for e in existentes):
            return False  # ya hay trabajo real registrado: no se pisa nada
    eventos = [
        (6, "09:12", "marta", "integrar_staging", None, {"archivo": "ventas_junio.csv", "filas": 31}),
        (6, "09:40", "aldo", "validacion_montos_ventas", None, {"mes": "2026-06"}),
        (5, "11:05", "nahuel", "cargar_remito", None, {"proveedor": "Alimentos del Paraná SA"}),
        (5, "16:22", "marta", "cargar_factura", None, {"proveedor": "Alimentos del Paraná SA"}),
        (4, "10:18", "aldo", "sanear_fantasma_custom", {"casos": 4}, {"casos": 1}),
        (4, "12:47", "marta", "cargar_recibo", None, {"cliente": "Súper Dos Hermanos"}),
        (3, "09:55", "aldo", "corregir_precio_perdida", {"productos": 3}, {"productos": 0}),
        (2, "11:31", "nahuel", "cargar_remito", None, {"proveedor": "Lácteos Campo Alegre"}),
        (2, "15:03", "marta", "integrar_staging", None, {"archivo": "lista_precios_guarani.csv", "filas": 58}),
        (1, "10:26", "aldo", "sanear_costo_viejo", {"casos": 12}, {"casos": 5}),
    ]
    # Historial de USO por rol (consultas a Ángela) — puebla la vista de Equipo del
    # dueño SIN tocar el feed "lo que Ángela hizo": `consulta_angela` está excluida
    # del feed por tipo (es administrativa), así que suma "consultas/temas" al panel
    # y nada más — ni stock, ni caja, ni hallazgos, ni contadores del feed. Modesto
    # y coherente con cada rol; fechas ≤ HOY (congelado). A propósito: brian y osmar
    # quedan SIN actividad (más creíble que todos activos), y NO se toca a tomas ni
    # vanesa (sus escenas del video quedan exactamente como están).
    consultas = [
        (2, "08:40", "diego", ["cuenta_estado", "buscar_productos"]),   # preventista: cuenta del cliente + stock
        (4, "17:15", "diego", ["precio"]),
        (6, "09:05", "diego", ["cuentas_corrientes"]),
        (3, "10:20", "celeste", ["lista_precios", "precio"]),           # compras: listas y precios
        (5, "15:48", "celeste", ["buscar_productos"]),
        (2, "07:30", "ramon", ["consultar_deposito"]),                  # encargado depósito: stock/vencimientos
        (7, "16:10", "ramon", ["buscar_productos", "stock"]),
        (9, "11:22", "lucia", ["precio", "buscar_productos"]),          # preventista (más vieja): precios/stock
        (12, "10:03", "lucia", ["cuenta_estado"]),
        (3, "18:20", "norma", ["estado_caja"]),                         # encargada sucursal: caja + reposición
        (8, "09:47", "norma", ["consultar_deposito", "buscar_productos"]),
        (5, "07:12", "walter", ["cuenta_estado"]),                      # repartidor: ¿el cliente debe? (1 sola)
        (4, "08:15", "marta", ["estado_caja", "cuentas_corrientes"]),   # admin: además de sus cargas
    ]
    for atras, hhmm, actor, tools in consultas:
        eventos.append((atras, hhmm, actor, "consulta_angela", None, {"tools": tools}))
    out = []
    for i, (atras, hhmm, actor, accion, antes, despues) in enumerate(eventos, 1):
        f = HOY - datetime.timedelta(days=atras)
        out.append({"id": i, "actor": actor, "accion": accion, "antes": antes,
                    "despues": despues, "cuando": f"{f.isoformat()}T{hhmm}:00"})
    # lo administrativo que ya hubiera queda DESPUÉS de la historia (es más nuevo)
    for e in existentes:
        out.append({**e, "id": len(out) + 1})
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return True


def sembrar_solicitud():
    """Una solicitud de módulo pendiente para el dueño, con el porqué de
    Ángela: Vanesa (mostrador) consulta precios de balanza a diario y pide
    Inventario. Va por el flujo REAL (core.perfiles): valida contra features,
    persiste y notifica al dueño en su idioma. El motivo va en inglés porque
    es el idioma default del tenant demo (los reviewers de YC)."""
    import sys
    os.environ.setdefault("POLPILOT_TENANT", "demo")
    os.environ.setdefault("POLPILOT_DATA_DIR", HERE)
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "backend"))
    from core import perfiles
    if perfiles.solicitudes(estado="pendiente"):
        return False
    try:
        perfiles.crear_solicitud("vanesa", "inventario", motivo_angela=(
            "Vanesa checks the scale prices for cold cuts and cheese every day "
            "from the front counter. With Smart inventory she sees them directly "
            "instead of calling the office."))
        return True
    except ValueError:
        return False


def sembrar_notificaciones():
    """Las 3 notificaciones del dueño (campanita) — DETERMINISTAS e IDÉNTICAS en
    local y Render (el mismo generar.py corre en ambos boots), ANCLADAS a datos
    reales, con fechas ≤ HOY (congelado). Empieza de un archivo LIMPIO: no
    sobrevive la basura de runtime (recordatorios disparados con para='dueño',
    invisibles para el dueño pero sucios en el archivo). Idempotente por ref.

      1 · Marta: corre el pipeline REAL de lista de precios EN PROCESO — números
          ANCLADOS a la fuente (productos, margen antes/después, ítem frenado) —
          y REVIERTE (dataset byte-igual). El cuerpo es el mismo que produce el
          endpoint real (comprobantes.mensaje_proactivo), no texto en paralelo.
      2 · Morosos: el aviso de siempre ($85.7M).
      3 · Gaseosa: del card real `quiebre_inminente` (producto, días, ranking).

    Antes esto dependía de deploy/preparar_historia_marta.py (pipeline por HTTP
    contra el server vivo) que el boot de Render NO corría → desfase local/Render.
    Ahora es seed determinista: ambos entornos producen las MISMAS 3."""
    path = os.path.join(HERE, "notificaciones.json")
    existentes = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else []
    if any(n.get("ref") == "seed_quiebre" for n in existentes):
        return False  # ya sembradas las 3: no re-mutar ni re-limpiar

    import sys
    os.environ.setdefault("POLPILOT_TENANT", "demo")
    os.environ.setdefault("POLPILOT_DATA_DIR", HERE)
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "backend"))
    import i18n
    from core import comprobantes, saneamiento, oportunidades_neg

    notifs = []

    # 1 · Marta — pipeline real (números anclados) + REVERT (dataset byte-igual).
    try:
        filas = list(csv.DictReader(open(os.path.join(
            HERE, "comprobantes", "lista_precios_campo_alegre.csv"), encoding="utf-8")))
        ext = {"tipo_comprobante": "lista_precios",
               "proveedor": {"razon_social": "Lácteos Campo Alegre"},
               "items": [{"codigo": 1318 if f["codigo"] == "1201" else int(f["codigo"]),
                          "descripcion": f["descripcion"],
                          "precio_unitario": float(f["precio_con_iva"])} for f in filas]}
        r = comprobantes.confirmar(ext, actor="Marta", lang="en")
        if r.get("ok"):
            try:
                f1 = HOY - datetime.timedelta(days=2)
                notifs.append({
                    "id": "nseed_marta", "para": "aldo",
                    "titulo": i18n.t("notif.comprobante_t", "en", actor="Marta"),
                    "cuerpo": comprobantes.mensaje_proactivo(r, ext, "en"),
                    "tipo": "comprobante", "ref": "seed_marta", "leida": False,
                    "fecha": f"{f1.isoformat()}T08:53:00"})
            finally:
                saneamiento.revertir(r["version_backup"])  # SIEMPRE: dataset byte-igual
    except Exception as e:
        print(f"  (notif Marta no sembrada: {e})")

    # 2 · Morosos — el aviso de siempre.
    f2 = HOY - datetime.timedelta(days=1)
    notifs.append({
        "id": "nseed01", "para": "aldo",
        "titulo": "Ángela flagged 3 overdue customers",
        "cuerpo": "Three customers are past due for a combined $85.7M — worth a "
                  "call before taking new orders.",
        "tipo": "aviso_equipo", "ref": "seed_aviso_mora", "leida": False,
        "fecha": f"{f2.isoformat()}T08:30:00"})

    # 3 · Gaseosa — quiebre inminente, ANCLADO al card real (producto/días/rank).
    try:
        qi = next((c for c in oportunidades_neg.cards("en")
                   if c.get("id") == "quiebre_inminente"), None)
        if qi:
            d = qi["datos"]
            f3 = HOY - datetime.timedelta(days=1)
            notifs.append({
                "id": "nseed_quiebre", "para": "aldo",
                "titulo": i18n.t("notif.quiebre_t", "en"),
                "cuerpo": i18n.t("notif.quiebre_c", "en", producto=d["producto"].title(),
                                 dias=d["dias_cobertura"], pos=d["rank_facturacion"]),
                "tipo": "aviso_equipo", "ref": "seed_quiebre", "leida": False,
                "fecha": f"{f3.isoformat()}T09:15:00"})
    except Exception as e:
        print(f"  (notif quiebre no sembrada: {e})")

    json.dump(notifs, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return True


def sembrar_fotos():
    """Fotos de perfil reales del equipo (P17·E2b): los seeds optimizados de
    fotos_seed/ pasan por el flujo REAL (core.perfiles.set_foto — valida,
    persiste el archivo y setea `foto` en el perfil). Idempotente: sólo el
    que no tiene foto todavía. El resto del equipo queda con iniciales."""
    seed_dir = os.path.join(HERE, "fotos_seed")
    if not os.path.isdir(seed_dir):
        return False
    import base64
    import sys
    os.environ.setdefault("POLPILOT_TENANT", "demo")
    os.environ.setdefault("POLPILOT_DATA_DIR", HERE)
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "backend"))
    from core import perfiles
    sembradas = 0
    for archivo in sorted(os.listdir(seed_dir)):
        if not archivo.endswith(".jpg"):
            continue
        username = archivo[:-4]
        if perfiles.foto_path(username):
            continue  # ya tiene (subida por el usuario o siembra previa): no se pisa
        with open(os.path.join(seed_dir, archivo), "rb") as f:
            data_url = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("ascii")
        try:
            perfiles.set_foto(username, data_url)
            sembradas += 1
        except ValueError:
            pass  # usuario inexistente en el seed: se reporta con el mapeo, no se adivina
    return sembradas > 0


def generar_finanzas(arts, recepciones):
    """Cuentas por pagar, cuotas de tarjeta por acreditar y cheques en cartera —
    TODO derivado de números que ya existen (recepciones×costo, la caja diaria,
    los clientes de cuentas). Random PROPIO: no consume el Random compartido,
    así los demás archivos quedan byte-igual y los números del guion no se mueven."""
    R2 = random.Random(20260708)
    costo = {a["codigo"]: a["costo_iva"] or 0 for a in arts}

    # Facturas por pagar: parte de lo recibido de cada proveedor, a 21-30 días.
    # Negocio sano: UNA vencida chica, el resto en fecha.
    por_prov = {}
    for r in recepciones:
        por_prov.setdefault(r["proveedor"], 0.0)
        por_prov[r["proveedor"]] += r["cantidad"] * costo.get(r["codigo"], 0)
    pagos, nro = [], 7300
    ordenados = sorted(por_prov.items(), key=lambda kv: -kv[1])[:8]
    for i, (prov, total) in enumerate(ordenados):
        nro += R2.randint(3, 40)
        monto = round(total * R2.uniform(0.35, 0.6), -3)
        vence = HOY + datetime.timedelta(days=(-4 if i == len(ordenados) - 1 else R2.randint(2, 26)))
        pagos.append({
            "proveedor": prov, "numero": f"FC-A-{nro:05d}",
            "emision": (vence - datetime.timedelta(days=30)).isoformat(),
            "vencimiento": vence.isoformat(), "monto": monto, "estado": "pendiente",
        })

    # Tarjeta en cuotas: parte de lo cobrado con tarjeta cada semana acredita
    # a 30/60/90 días (2 y 3 cuotas). Escala coherente con la caja (~$860k/día).
    cuotas = []
    for sem in range(1, 7):
        base = 860_000 * 6 * R2.uniform(0.8, 1.1)   # una semana de tarjeta (6 días hábiles)
        venta = HOY - datetime.timedelta(days=7 * sem)
        for plan, frac in (("2 cuotas", 0.40), ("3 cuotas", 0.25)):
            n = int(plan[0])
            for k in range(1, n + 1):
                acred = venta + datetime.timedelta(days=30 * k)
                if acred <= HOY:
                    continue
                cuotas.append({"venta_semana": venta.isoformat(), "plan": plan,
                               "acredita": acred.isoformat(),
                               "monto": round(base * frac / n, -3)})
    cuotas.sort(key=lambda c: c["acredita"])

    # Cheques en cartera: clientes al día que pagan con cheque diferido.
    cheques = []
    for i, nombre in enumerate(["Supermercado El Puente", "Súper Dos Hermanos",
                                "Autoservicio Belgrano", "Comedor Escolar N°12"]):
        recibido = HOY - datetime.timedelta(days=R2.randint(2, 12))
        cobro = HOY + datetime.timedelta(days=(0 if i == 0 else R2.randint(4, 28)))
        cheques.append({"cliente": nombre, "numero": str(R2.randint(30_000_000, 49_999_999)),
                        "banco": R2.choice(["Banco Nación", "Banco Provincia", "Macro", "Credicoop"]),
                        "recibido": recibido.isoformat(), "cobro": cobro.isoformat(),
                        "monto": round(R2.uniform(2_500_000, 9_000_000), -4)})

    json.dump({"pagos_proveedores": pagos, "tarjeta_cuotas": cuotas, "cheques": cheques},
              open(os.path.join(HERE, "finanzas.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return len(pagos), len(cuotas), len(cheques)


def _id_fijo(prefijo, texto):
    """Un id estable por nombre: el apartado se regenera en cada boot y un id
    nuevo cada vez rompería cualquier referencia (foco, auditoría)."""
    import hashlib
    return prefijo + hashlib.sha1(texto.encode("utf-8")).hexdigest()[:9]


def generar_ubicaciones(dep):
    """Las ubicaciones del depósito como ENTIDAD, derivadas de los strings que
    ya llevan los lotes — no inventadas: cada una existe porque algún lote está
    ahí. El orden es el del layout (UBICACIONES), no el de aparición. Las tres
    cámaras llevan nota; el mapa las trata como zonas propias y los 18 racks
    como «Pasillos y racks» — este apartado no cambia ese conteo, lo respalda."""
    usadas = {f["ubicacion"] for f in dep}
    return [{"id": _id_fijo("u", u), "nombre": u,
             "nota": "Cámara: frío controlado" if u.startswith("Cámara") else ""}
            for u in UBICACIONES if u in usadas]


def generar_proveedores(recepciones):
    """La ficha de cada proveedor, derivada de las recepciones: última entrega y
    cuántas hubo. Contacto, teléfono, mail y CUIT quedan VACÍOS a propósito: no
    existen en ningún lado del dataset y un teléfono inventado es exactamente el
    dato que no se puede auditar. El apartado deja de nacer vacío sin fingir
    nada."""
    out = []
    for p in PROVEEDORES:
        de_p = [r for r in recepciones if r["proveedor"] == p]
        ultima = max((r["fecha"] for r in de_p), default="")
        out.append({"id": _id_fijo("p", p), "nombre": p, "contacto": "", "telefono": "",
                    "email": "", "cuit": "", "source": "", "source_id": "",
                    "notas": f"Última entrega {ultima} · {len(de_p)} recepciones"})
    return out


def generar_ordenes_compra_historicas():
    """Tres órdenes ya cerradas —dos recibidas, una cancelada— para que el
    apartado tenga historia y no una sola fila abierta. Datos fijos, del
    catálogo real, SIN consumir el Random compartido. Los números quedan por
    debajo de la abierta (OC-2026-0847) y de la de la muestra Odoo (0863)."""
    return [
        {"numero": "OC-2026-0791",
         "fecha": (HOY - datetime.timedelta(days=41)).isoformat(),
         "proveedor": "Frigorífico La Ribera", "estado": "recibida",
         "items": [
             {"codigo": 1296, "producto": "QUESO CREMOSO GUARANI (HORMA)", "cantidad": 18},
             {"codigo": 1008, "producto": "ACEITE GIRASOL LA RIBERA 900CC (X12U)", "cantidad": 40},
             {"codigo": 1417, "producto": "PAPEL HIGIENICO LA RIBERA X4 (X10P)", "cantidad": 30},
         ]},
        {"numero": "OC-2026-0812",
         "fecha": (HOY - datetime.timedelta(days=27)).isoformat(),
         "proveedor": "Distrib. Mayorista Guaraní", "estado": "recibida",
         "items": [
             {"codigo": 1092, "producto": "LENTEJAS LA RIBERA 400G (X12U)", "cantidad": 50},
             {"codigo": 1129, "producto": "GALLETITAS SURTIDAS LA RIBERA 400G (X20U)", "cantidad": 36},
             {"codigo": 1027, "producto": "MAYONESA EL PARANA 500G (X12U)", "cantidad": 24},
             {"codigo": 1185, "producto": "JUGO EN POLVO GUARANI (X20S)", "cantidad": 60},
         ]},
        {"numero": "OC-2026-0833",
         "fecha": (HOY - datetime.timedelta(days=12)).isoformat(),
         "proveedor": "Golosinas Costa Dulce SRL", "estado": "cancelada",
         "items": [
             {"codigo": 1135, "producto": "ALFAJOR TRIPLE MONTE CHICO (X24U)", "cantidad": 45},
             {"codigo": 1017, "producto": "ACEITE MEZCLA COSTA DULCE 1.5L (X8U)", "cantidad": 20},
         ]},
    ]


def generar_orden_compra_demo():
    """La orden de compra ABIERTA que espera su remito (P10): los comprobantes
    de muestra (remito → factura) cruzan contra ESTO. Datos fijos, elegidos a
    mano del catálogo real (Lácteos Campo Alegre y sus lácteos), SIN consumir
    el Random compartido: los demás apartados quedan byte-igual."""
    return [{
        "numero": "OC-2026-0847",
        "fecha": (HOY - datetime.timedelta(days=5)).isoformat(),
        "proveedor": "Lácteos Campo Alegre",
        "estado": "abierta",
        "items": [
            {"codigo": 1215, "producto": "LECHE ENTERA CAMPO ALEGRE 1L (X12U)", "cantidad": 60},
            {"codigo": 1211, "producto": "LECHE ENTERA TIERRA ROJA 1L (X12U)", "cantidad": 40},
            {"codigo": 1236, "producto": "MANTECA SANTA CLARA 200G (X30U)", "cantidad": 25},
            {"codigo": 1239, "producto": "MANTECA CAMPO ALEGRE 200G (X30U)", "cantidad": 10},
            {"codigo": 1249, "producto": "CREMA DE LECHE EL PARANA 360G (X12U)", "cantidad": 30},
        ],
    }]


def generar_recepcion_del_caso():
    """LA ENTREGA DEL RECLAMO, con fecha FIJA. No la puede decidir el azar.

    `generar_recepciones` reparte las entregas entre 7 y 28 dias atras al azar,
    y la escena del reclamo (core/escena.py) calcula el plazo restando esa
    fecha contra el plazo del proveedor. O sea que la linea que se dice en voz
    alta —«La entrega fue el 05/07. Quedan 3 dias para reclamar.»— salia
    distinta en cada siembra. En el primer deploy a Render salio:

        «La entrega fue el 28/06. El plazo vencio hace 4 dias.»

    Que no es un detalle cosmetico: da vuelta la historia. En vez de «hay que
    actuar ahora» dice «se te paso», y el caso entero deja de tener sentido.

    Dos dias atras, contra el plazo de 5 dias de Lacteos Campo Alegre (k23),
    da exactamente tres dias restantes. Y sale de una resta real entre dos
    fechas reales: lo unico que se fija es la fecha de la entrega.

    Mismo criterio que generar_orden_compra_demo: datos a mano, SIN consumir el
    Random compartido, para que el resto del dataset quede byte-igual.
    """
    return [{
        "fecha": (HOY - datetime.timedelta(days=2)).isoformat(),
        "codigo": 1215,
        "producto": "LECHE ENTERA CAMPO ALEGRE 1L (X12U)",
        "proveedor": "Lácteos Campo Alegre",
        "cantidad": 60,
        "deposito": "Depósito Central",
    }]


def main():
    # Los seeds que pasan por el core (staging, solicitud → notificación al
    # dueño) hablan el idioma DEFAULT del tenant demo: inglés (reviewers YC).
    os.environ.setdefault("POLPILOT_DEFAULT_LANG", "en")
    arts = generar_catalogo()
    inyectar_puntitos(arts)
    asignar_rotacion_y_stock(arts)
    ventas = generar_ventas(arts)
    recepciones = generar_recepciones(arts)
    # La del caso del reclamo va al final y con fecha fija: es la que
    # `escena._ultima_entrega` toma como ultima (es la mas reciente).
    recepciones += generar_recepcion_del_caso()
    dep = generar_deposito(arts)
    log = generar_logistica()

    # La caja PRIMERO: el canal mostrador y los traslados a locales propios se
    # derivan de ella (Bloques C·E·F). Random propios: nada de arriba se mueve.
    caja_creada, caja_hist = generar_caja()
    mostrador = generar_mostrador(arts, caja_hist)
    traslados = generar_traslados_internos(arts, caja_hist)

    for a in arts:
        stock, costo = a["stock"] or 0, a["costo_iva"] or 0
        a["inmovilizado"] = round(stock * costo, 2) if stock > 0 else 0.0
        a.pop("_demanda_mes", None)
        a.pop("_clase", None)

    inmovilizado = round(sum(a["inmovilizado"] for a in arts), 2)
    por_mes = {}
    for f in ventas:
        por_mes.setdefault(f["fecha"][:7], 0)
        por_mes[f["fecha"][:7]] += f["cantidad"] * f["precio"]
    mes_max = max(m for m in por_mes if m < HOY.strftime("%Y-%m"))
    fact_mes = round(por_mes[mes_max], 2)

    # margen agregado del catálogo vendible (negocio SANO: 15-28%)
    con_precio = [a for a in arts if a["estado"] == "activo" and a.get("pvp") and a["costo_iva"]]
    margen = sum(a["pvp"] - a["costo_iva"] for a in con_precio) / sum(a["costo_iva"] for a in con_precio)

    # cotas de cordura: distribuidora mediana SANA
    assert 450_000_000 < fact_mes < 1_100_000_000, f"facturación rara: {fact_mes:,.0f}"
    assert 250_000_000 < inmovilizado < 900_000_000, f"inmovilizado raro: {inmovilizado:,.0f}"
    dias_cobertura = inmovilizado / (fact_mes / 1.20 / 30)  # a costo aprox
    assert 12 < dias_cobertura < 45, f"cobertura rara: {dias_cobertura:.0f} días"
    assert 0.14 < margen < 0.30, f"margen agregado raro: {margen:.1%}"

    json.dump({"articulos": arts}, open(os.path.join(HERE, "inventory.json"), "w",
              encoding="utf-8"), ensure_ascii=False)
    json.dump({
        "venta": {"nombre": "Ventas", "filas": ventas},
        "deposito": {"nombre": "Depósito", "filas": dep},
        "logistica": {"nombre": "Logística", "filas": log},
        "recepciones": {"nombre": "Recepciones", "filas": recepciones},
        "ordenes_compra": {"nombre": "Órdenes de compra",
                           "filas": generar_ordenes_compra_historicas() + generar_orden_compra_demo()},
        # Dos apartados que nacían vacíos en la demo aunque el dato existiera en
        # otro lado: derivados de `dep` y de `recepciones`, nunca inventados.
        "ubicaciones": {"nombre": "Ubicaciones", "filas": generar_ubicaciones(dep)},
        "proveedores": {"nombre": "Proveedores", "filas": generar_proveedores(recepciones)},
    }, open(os.path.join(HERE, "apartados.json"), "w", encoding="utf-8"), ensure_ascii=False)
    cuentas_ = generar_cuentas()
    json.dump(cuentas_, open(os.path.join(HERE, "cuentas.json"), "w",
              encoding="utf-8"), ensure_ascii=False, indent=1)
    # Qué se llevó el cliente en cada pedido. Deriva de cuentas_ y NO la toca:
    # el total de cada pedido es el monto del movimiento, tal cual.
    ventas_cliente = generar_ventas_por_cliente(arts, cuentas_, ventas)
    json.dump({
        "_nota": "Los renglones de cada 'Pedido mayorista' de la cuenta corriente. El TOTAL de "
                 "cada pedido es el monto del movimiento (número canónico, no se mueve): la "
                 "última línea absorbe el redondeo. Los productos salen del rubro del cliente, "
                 "ponderados por lo que ese producto vende de verdad.",
        "clientes": ventas_cliente,
    }, open(os.path.join(HERE, "ventas_por_cliente.json"), "w", encoding="utf-8"),
        ensure_ascii=False)
    json.dump({"estado": "confirmado", "mes": mes_max, "total_calculado": fact_mes,
               "confirmado_por": "aldo",
               "nota": "dataset sintético del demo: validado por diseño"},
              open(os.path.join(HERE, "ventas_validacion.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(mostrador, open(os.path.join(HERE, "mostrador.json"), "w",
              encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({
        "_nota": "Movimientos de mercadería a locales PROPIOS. El ERP los "
                 "registra como venta (hay remito y precio de lista) y por eso "
                 "ensucian el ranking de clientes y de productos. NO son venta "
                 "real: Ángela los separa.",
        "locales_propios": BOCAS,
        "filas": traslados,
    }, open(os.path.join(HERE, "traslados_internos.json"), "w", encoding="utf-8"),
        ensure_ascii=False)
    staging_creado = sembrar_staging()
    audit_creado = sembrar_auditoria()
    solicitud_creada = sembrar_solicitud()
    aviso_creado = sembrar_notificaciones()
    fotos_sembradas = sembrar_fotos()
    n_pagos, n_cuotas, n_cheques = generar_finanzas(arts, recepciones)
    conocimiento_creado = seed_conocimiento.sembrar()
    notas_creadas = seed_notas.sembrar()

    anios = len({f["fecha"][:4] for f in ventas})
    print(f"SKUs: {len(arts)} ({sum(1 for a in arts if a['venta_x_peso'])} balanza)")
    print(f"Facturación {mes_max}: ${fact_mes:,.0f} | margen catálogo: {margen:.1%}")
    print(f"Inmovilizado: ${inmovilizado:,.0f} ({dias_cobertura:.0f} días de cobertura)")
    print(f"Ventas: {len(ventas)} filas en {anios} años | recepciones: {len(recepciones)}"
          f" | depósito: {len(dep)} | logística: {len(log)}")
    print(f"Caja: {'creada' if caja_creada else 'ya existía'} | staging: "
          f"{'batch pendiente creado' if staging_creado else 'ya había'}")
    trasl_12m = sum(f["cantidad"] * f["precio"] for f in traslados
                    if f["fecha"] >= (HOY - datetime.timedelta(days=365)).isoformat())
    print(f"Mostrador: {len(mostrador['cierres'])} cierres por local "
          f"(${mostrador['venta_diaria_promedio']:,.0f}/día) | traslados a locales "
          f"propios: {len(traslados)} filas (${trasl_12m:,.0f} en 12m)")
    print(f"Auditoría: {'sembrada' if audit_creado else 'ya existía'} | solicitud: "
          f"{'creada (vanesa pide inventario)' if solicitud_creada else 'ya había'}")
    print(f"Finanzas: {n_pagos} facturas por pagar | {n_cuotas} cuotas de tarjeta | {n_cheques} cheques")
    print(f"Conocimiento: {'sembrado (22 piezas de Aldo)' if conocimiento_creado else 'ya existía'}")
    n_ped = sum(len(c["pedidos"]) for c in ventas_cliente)
    n_items = sum(len(p["items"]) for c in ventas_cliente for p in c["pedidos"])
    print(f"Qué compra cada cliente: {n_ped} pedidos abiertos en {n_items} renglones "
          f"({len(ventas_cliente)} clientes)")
    print(f"Notas del equipo: {f'sembradas ({len(seed_notas.NOTAS)})' if notas_creadas else 'ya existían'}")


if __name__ == "__main__":
    main()
