"""
Normalización — LA FRONTERA entre los dos niveles de limpieza, en un solo lugar.

NIVEL 1 (este módulo, se aplica solo al entrar al Staging): transformaciones que
NO alteran el significado comercial del dato — el mismo producto, el mismo precio,
la misma fecha, escritos prolijo:
  - texto: espacios sobrantes, mayúsculas inconsistentes, encoding roto (mojibake)
  - números: "$ 1.234,50" → 1234.50 (separadores es-AR), sólo cuando es INEQUÍVOCO
  - fechas: dd/mm/aaaa → ISO

NIVEL 2 (el flujo actual del Staging, intacto): todo lo que implica interpretar
el negocio — precios a pérdida, sin precio, duplicados, outliers, fantasmas — y
CUALQUIER caso ambiguo de acá. La regla de oro: ante la mínima duda, Nivel 2.

Decisiones de frontera (documentadas, testeadas):
  - Coma = decimal SIEMPRE (convención es-AR; los exports son de Faro argentino).
  - Punto: varios puntos = miles (1.234.567). Un punto con 1-2 decimales = decimal
    (12.5). Un punto con EXACTAMENTE 3 dígitos después (1.234) = AMBIGUO → Nivel 2:
    ¿mil doscientos o uno coma dos? Eso lo decide el dueño, no una regex.
  - Fechas dd/mm = convención es-AR (no ambigüedad). Ver core/fechas.py.
  - Mayúsculas: sólo se corrige la INCONSISTENCIA en un texto ya mayoritariamente
    mayúsculo ("MANTECA pilon" → "MANTECA PILON"). Un nombre en Title Case o en
    minúsculas se respeta como vino: cambiarlo sería una decisión de estilo, no
    una normalización mecánica.

Reglas duras del Nivel 1: todo cambio queda registrado con el valor original
(reversible), visible en el Staging, y NUNCA se aplica sobre un dato ambiguo.
"""
from __future__ import annotations

import re

from .fechas import parse_fecha

# Sentinel: "esto no lo decido yo" → Nivel 2.
AMBIGUO = object()

# Mojibake típico de exports Windows (UTF-8 leído como latin-1). Sólo secuencias
# de DOS caracteres inequívocas — nunca la "Ã" sola, que rompería las demás.
_MOJIBAKE = {
    "Ã¡": "á", "Ã©": "é", "Ã­": "í", "Ã³": "ó", "Ãº": "ú",
    "Ã±": "ñ", "Ã‘": "Ñ", "Ã‰": "É", "Ã“": "Ó", "Ãš": "Ú",
    "Â°": "°", "Âº": "º", "Ã¼": "ü",
}

_RE_NUMERICO = re.compile(r"^[\s$]*-?[\d.,\s]+$")
_RE_FECHA = re.compile(r"^\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s*$")


def normalizar_texto(s) -> tuple[str, list[str]]:
    """Devuelve (texto_limpio, reglas_aplicadas). No toca el contenido: el mismo
    nombre, escrito prolijo."""
    original = str(s or "")
    out, reglas = original, []
    for roto, bien in _MOJIBAKE.items():
        if roto in out:
            out = out.replace(roto, bien)
            if "encoding" not in reglas:
                reglas.append("encoding")
    sin_espacios = re.sub(r"\s+", " ", out).strip()
    if sin_espacios != out:
        out = sin_espacios
        reglas.append("espacios")
    # Mayúsculas: SOLO se corrige la inconsistencia dentro de un texto que ya es
    # mayoritariamente mayúsculo ("MANTECA pilon" → "MANTECA PILON", estilo del
    # catálogo). Un texto naturalmente en minúsculas o Title Case ("Autoservicio
    # García") NO se toca: ante la duda, no tocar.
    mayus = sum(1 for c in out if c.isalpha() and c.isupper())
    minus = sum(1 for c in out if c.isalpha() and c.islower())
    if minus and mayus >= minus:  # empate = inconsistencia también
        out = out.upper()
        reglas.append("mayusculas")
    return out, reglas


def normalizar_numero(v):
    """Devuelve (valor, regla|None). valor puede ser float, None (no es un
    número) o AMBIGUO (que lo decida el dueño — Nivel 2)."""
    if v is None:
        return None, None
    if isinstance(v, (int, float)):
        return float(v), None
    s = str(v).strip()
    if not s or s.lower() in ("none", "nan", "-"):
        return None, None
    if not _RE_NUMERICO.match(s):
        return None, None
    crudo = s
    s = s.replace("$", "").replace(" ", "")
    regla = "formato_numero" if crudo != s else None

    tiene_punto, tiene_coma = "." in s, "," in s
    try:
        if tiene_punto and tiene_coma:
            # es-AR completo: 1.234,50 — inequívoco
            return float(s.replace(".", "").replace(",", ".")), "separadores_es_ar"
        if tiene_coma:
            # coma = decimal SIEMPRE (decisión de frontera documentada arriba)
            return float(s.replace(",", ".")), "coma_decimal"
        if tiene_punto:
            partes = s.split(".")
            if len(partes) > 2:
                # 1.234.567 → miles, inequívoco
                return float(s.replace(".", "")), "puntos_miles"
            if len(partes[1]) == 3 and partes[0].lstrip("-"):
                # 1.234 → ¿mil doscientos o uno coma dos? NO lo decidimos solos.
                return AMBIGUO, "punto_tres_digitos"
            return float(s), regla  # 12.5 → decimal, inequívoco
        return float(s), regla
    except ValueError:
        return None, None


def normalizar_fecha(v):
    """Devuelve (iso|original, regla|None). Sólo convierte si parsea con la
    convención es-AR (dd/mm); si no, deja el valor como vino."""
    s = str(v or "").strip()
    if not _RE_FECHA.match(s):
        return v, None
    f = parse_fecha(s)
    if not f:
        return v, None
    iso = f.isoformat()
    return (iso, "fecha_iso") if iso != s else (s, None)


def normalizar_tabla(headers: list[str], filas: list[list]) -> tuple[list[list], dict]:
    """Nivel 1 sobre una tabla cruda (strings del CSV). Devuelve (filas_limpias,
    registro). El registro trae cada cambio con su valor original (reversible) y
    los AMBIGUOS aparte — esos NO se tocan: van al Nivel 2.

    Nota: los números ambiguos se dejan tal cual vinieron (el coerce del staging
    los deja sin valor en vez de inventar uno) y se listan para la card del dueño."""
    cambios, ambiguos = [], []
    limpias = []
    for i, fila in enumerate(filas):
        nueva = []
        for j, celda in enumerate(fila):
            header = headers[j] if j < len(headers) else f"col{j}"
            valor = celda
            if isinstance(celda, str) and celda.strip():
                if _RE_NUMERICO.match(celda) and any(c in celda for c in ".,$"):
                    num, regla = normalizar_numero(celda)
                    if num is AMBIGUO:
                        ambiguos.append({"fila": i, "columna": header, "valor": celda.strip()})
                    elif num is not None and regla:
                        valor = f"{num:g}"
                        cambios.append({"fila": i, "columna": header, "original": celda,
                                        "normalizado": valor, "regla": regla})
                elif _RE_FECHA.match(celda):
                    fecha, regla = normalizar_fecha(celda)
                    if regla:
                        valor = fecha
                        cambios.append({"fila": i, "columna": header, "original": celda,
                                        "normalizado": fecha, "regla": regla})
                else:
                    texto, reglas = normalizar_texto(celda)
                    if reglas:
                        valor = texto
                        cambios.append({"fila": i, "columna": header, "original": celda,
                                        "normalizado": texto, "regla": "+".join(reglas)})
            nueva.append(valor)
        limpias.append(nueva)

    por_regla: dict[str, int] = {}
    for c in cambios:
        por_regla[c["regla"]] = por_regla.get(c["regla"], 0) + 1
    registro = {
        "total_cambios": len(cambios),
        "filas_afectadas": len({c["fila"] for c in cambios}),
        "por_regla": por_regla,
        "cambios": cambios,
        "ambiguos": ambiguos,
    }
    return limpias, registro


# Etiquetas en criollo para el resumen visible ("automático nunca es invisible").
REGLAS_LABEL = {
    "separadores_es_ar": "números con miles y decimales (1.234,50)",
    "coma_decimal": "decimales con coma",
    "puntos_miles": "puntos de miles",
    "formato_numero": "símbolos y espacios en números",
    "fecha_iso": "formatos de fecha",
    "espacios": "espacios sobrantes",
    "mayusculas": "mayúsculas y minúsculas",
    "encoding": "caracteres rotos (encoding)",
}


def _regla_label(regla: str, lang: str | None = None) -> str:
    """La etiqueta de una regla en el idioma pedido (ES byte-igual a REGLAS_LABEL);
    regla desconocida → el id crudo, como siempre."""
    import i18n
    key = f"core.norm.regla_{regla}"
    return i18n.t(key, lang) if key in i18n.CATALOGO else REGLAS_LABEL.get(regla, regla)


def resumen_en_criollo(registro: dict, lang: str | None = None) -> str:
    import i18n
    if not registro or not registro.get("total_cambios"):
        return ""
    partes = [_regla_label(r, lang) for r in registro["por_regla"]]
    base = i18n.t("core.norm.resumen", lang, total=registro["total_cambios"],
                  filas=registro["filas_afectadas"], partes=", ".join(partes))
    if registro.get("ambiguos"):
        base += i18n.t("core.norm.ambiguos", lang, n=len(registro["ambiguos"]))
    return base
