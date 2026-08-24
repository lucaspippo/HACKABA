"""
Render REAL de documentos a PDF (P17·E1) — WeasyPrint + Jinja2.

Este módulo NO calcula nada de negocio: recibe el documento que Ángela ya
redactó (y el usuario editó en pantalla) y lo maqueta con los mismos design
tokens del frontend. El draft editado viene del cliente porque es la única
copia con sus cambios; los números del PDF son los del draft, textual.

Deps de sistema (WeasyPrint necesita Pango >= 1.44):
  - Windows dev: GTK3-Runtime (instalador tschoonj) — se autodetecta abajo.
  - Linux/deploy: apt-get install libpango-1.0-0 libpangocairo-1.0-0
    libpangoft2-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev libharfbuzz0b
    libglib2.0-0
"""
from __future__ import annotations

import base64
import json
import os
import re
import secrets

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import fechas, paths

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLANTILLAS = os.path.join(BACKEND, "plantillas")
DOCS_DIR = os.path.join(paths.DATA_DIR, "documentos")
INDICE_JSON = os.path.join(DOCS_DIR, "indice.json")

# Windows: si el runtime GTK está en su lugar estándar y nadie seteó el dir de
# DLLs, lo apuntamos nosotros — sin esto el import de weasyprint muere.
_GTK_WIN = r"C:\Program Files\GTK3-Runtime Win64\bin"
if os.name == "nt" and "WEASYPRINT_DLL_DIRECTORIES" not in os.environ and os.path.isdir(_GTK_WIN):
    os.environ["WEASYPRINT_DLL_DIRECTORIES"] = _GTK_WIN

_env = Environment(
    loader=FileSystemLoader(PLANTILLAS),
    autoescape=select_autoescape(["html"]),
)


def disponible() -> bool:
    """¿Se puede renderizar PDF en este entorno? (deps de sistema presentes)"""
    try:
        import weasyprint  # noqa: F401
        return True
    except OSError:
        return False


def _t(key: str, lang: str | None = None, **params) -> str:
    import i18n
    return i18n.t(key, lang, **params)


def _logo_b64() -> str | None:
    """Logo del tenant desde su DATA_DIR (sembrado en el demo). Sin logo →
    None y el template usa la marca de texto (placeholder neutro, honesto)."""
    for nombre in ("logo.jpg", "logo.png", "logo.jpeg"):
        path = os.path.join(paths.DATA_DIR, nombre)
        if os.path.exists(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode("ascii")
    return None


def _monto_num(txt: str) -> float:
    """Para ORDENAR anomalías por $ desc: extrae el número del string formateado."""
    digitos = re.sub(r"[^\d]", "", str(txt or ""))
    return float(digitos) if digitos else 0.0


def render_html(doc: dict, lang: str | None, usuario: str) -> str:
    import i18n
    doc = dict(doc)  # no mutar el original
    # Issues ordenadas por $ descendente (spec del executive summary)
    if doc.get("anomalias"):
        doc["anomalias"] = sorted(doc["anomalias"], key=lambda a: -_monto_num(a.get("impacto")))
    # Costo unitario de la orden, formateado (o "—" si no hay)
    if doc.get("items"):
        doc["items"] = [{**it, "costo_txt": i18n.pesos(it["costo_unitario"], lang)
                         if it.get("costo_unitario") else "—"} for it in doc["items"]]
    etiquetas = {
        "pedido_por": _t("core.pdf.pedido_por", lang),
        "generado_por": _t("core.pdf.generado_por", lang),
        "destinatario": _t("core.pdf.destinatario", lang),
        "proveedor": _t("core.pdf.proveedor", lang),
        "plazo": _t("core.pdf.plazo", lang),
        "col_producto": _t("core.pdf.col_producto", lang),
        "col_cantidad": _t("core.pdf.col_cantidad", lang),
        "col_motivo": _t("core.pdf.col_motivo", lang),
        "col_costo": _t("core.pdf.col_costo", lang),
        "issues_titulo": _t("core.pdf.issues_titulo", lang),
        "col_problema": _t("core.pdf.col_problema", lang),
        "col_items": _t("core.pdf.col_items", lang),
        "col_riesgo": _t("core.pdf.col_riesgo", lang),
        "acciones_titulo": _t("core.pdf.acciones_titulo", lang),
        "hallazgos_titulo": _t("core.pdf.hallazgos_titulo", lang),
        "vigilar_titulo": _t("core.pdf.vigilar_titulo", lang),
        "anexo_titulo": _t("core.pdf.anexo_titulo", lang),
        "orden_total": _t("core.doc.orden_total", lang),
        "disclaimer": _t("core.pdf.disclaimer", lang,
                         fecha=fechas.hoy().strftime("%d/%m/%Y")),
    }
    # El veredicto solo existe si el documento lo trae: el PDF dice lo que el
    # draft dice, jamás agrega afirmaciones propias (verdad literal).
    return _env.get_template("documento.html").render(
        doc=doc, lang=lang or "es", empresa=paths.EMPRESA, usuario=usuario,
        logo_b64=_logo_b64(), veredicto=doc.get("veredicto"), t=etiquetas,
    )


def render_pdf(doc: dict, lang: str | None, usuario: str) -> bytes:
    """Síncrono y CPU-bound: llamar con asyncio.to_thread desde el handler."""
    from weasyprint import CSS, HTML
    html = render_html(doc, lang, usuario)
    return HTML(string=html, base_url=PLANTILLAS).write_pdf(
        stylesheets=[CSS(filename=os.path.join(PLANTILLAS, "report.css"))])


# ----------------------------------------------------------------------------
# Persistencia: los generados quedan listados en la sección Documentos.
# ----------------------------------------------------------------------------

def _leer_indice() -> list[dict]:
    if not os.path.exists(INDICE_JSON):
        return []
    try:
        with open(INDICE_JSON, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def guardar(doc: dict, pdf_bytes: bytes, usuario: str, lang: str | None,
            username: str | None = None) -> dict:
    os.makedirs(DOCS_DIR, exist_ok=True)
    doc_id = secrets.token_hex(6)
    archivo = f"{doc_id}.pdf"
    with open(os.path.join(DOCS_DIR, archivo), "wb") as f:
        f.write(pdf_bytes)
    meta = {
        "id": doc_id,
        "tipo": doc.get("tipo", "documento"),
        "titulo": doc.get("titulo", ""),
        "archivo": archivo,
        "fecha": fechas.hoy().strftime("%Y-%m-%d"),
        "usuario": usuario,           # nombre visible ("pedido por Aldo")
        "username": username or usuario,  # P24·A1: el dueño REAL del documento
        "lang": lang or "es",
    }
    indice = _leer_indice()
    indice.insert(0, meta)
    with open(INDICE_JSON, "w", encoding="utf-8") as f:
        json.dump(indice[:100], f, ensure_ascii=False, indent=1)
    return meta


def render_y_guardar(doc: dict, lang: str | None, usuario: str,
                     username: str | None = None) -> tuple[bytes, dict]:
    pdf_bytes = render_pdf(doc, lang, usuario)
    return pdf_bytes, guardar(doc, pdf_bytes, usuario, lang, username=username)


def listado(username: str | None = None, es_admin: bool = False) -> list[dict]:
    """P24·A1 — los documentos son POR USUARIO, filtrado server-side: cada uno
    ve SOLO los suyos; el dueño ve los suyos + los de todo el equipo (con
    'pedido por X'). username=None y es_admin=False (uso interno) = nada."""
    docs = _leer_indice()
    if es_admin:
        return docs
    if not username:
        return []
    return [d for d in docs if d.get("username", d.get("usuario")) == username]


def puede_ver(doc_id: str, username: str, es_admin: bool) -> bool:
    """El guard de descarga: el dueño baja todo; el resto, solo lo propio."""
    if es_admin:
        return True
    meta = next((d for d in _leer_indice() if d.get("id") == doc_id), None)
    return bool(meta) and meta.get("username", meta.get("usuario")) == username


def archivo_path(doc_id: str) -> str | None:
    if not re.fullmatch(r"[0-9a-f]{12}", doc_id or ""):
        return None  # ids propios, nada de paths del cliente
    path = os.path.join(DOCS_DIR, f"{doc_id}.pdf")
    return path if os.path.exists(path) else None
