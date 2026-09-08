"""carpeta.py — the document folder of a delivery, pre-filled from what the
system already knows.

THE IDEA, IN ONE LINE: almost every field of these documents ALREADY EXISTS in
the system. They are in the logistics order, in the customer's account, in the
open order's lines and in the house rules. What a person does today is copy
them by hand from one screen into two or three forms, and every copy is a
chance for a number not to match — which is exactly what makes a customer
argue about a delivery note.

HOW IT IS BUILT, AND WHY LIKE THIS. Each document is a list of FIELDS, and
each field declares three things:

    valor   — what the system already knows (or None)
    fuente  — WHERE it got it from: "pedido P-4401", "cuenta corriente de
              Autoservicio 9 de Julio", "regla de la casa k01". Never "the
              system". A document somebody signs cannot have fields of
              unknown origin, and the value of a copilot is not that it types
              fast: it is that it can be audited box by box.
    estado  — completo | falta | opcional

That triple is everything. It lets the document be shown WITH ITS GAPS
MARKED, say how much is missing to close it, and point at the original datum
behind each box. An incomplete document is shown anyway: the question a
person has is not "generate it when everything is there", it is "what is
missing".

THE CROSS-CHECK is the part no form has on its own: the same module verifies
that the total of the delivery note, the total of the customer's open order
and the balance of their account say THE SAME NUMBER — because all three come
from the same source. Measured on the demo dataset: it holds for 24 of 24
customers, which is the point. Each manual copy is where it stops holding.

Adapted from the pattern of PolPilot-TOP's `core/exportacion.py`. The pattern
is what is reused — the fields with their source, the cross-check, the
incomplete document shown anyway. The content is this business's: a
distributor's delivery note and account statement, not a seed exporter's
phytosanitary certificate.
"""
from __future__ import annotations

from . import conocimiento, cuentas, esquema, paths, ventas_cliente
from .fechas import hoy, parse_fecha
from i18n import t as _i18n


def _t(key: str, lang: str | None = None, **p) -> str:
    return _i18n(f"core.carpeta.{key}", lang, **p)


# (id, título, quién lo emite). Two on purpose: the field engine is the
# expensive half, and with it working the rest are hours.
DOCUMENTOS = ("remito_entrega", "estado_cuenta")


# ---------------------------------------------------------------------------
# The base piece: a field that knows where it came from
# ---------------------------------------------------------------------------
def campo(etiqueta: str, valor, fuente: str | None = None,
          obligatorio: bool = True, nota: str | None = None) -> dict:
    """One box of the form.

    `fuente` is what makes this a copilot and not a PDF generator: if somebody
    asks where a number came from, the answer is next to the number.
    """
    vacio = valor is None or valor == "" or valor == []
    return {
        "etiqueta": etiqueta,
        "valor": valor,
        "fuente": fuente,
        "estado": "falta" if (vacio and obligatorio) else ("opcional" if vacio else "completo"),
        "obligatorio": obligatorio,
        **({"nota": nota} if nota else {}),
    }


def _pesos(v, lang) -> str | None:
    import i18n
    return None if v is None else i18n.pesos(v, lang)


def _dia(iso, lang) -> str | None:
    d = parse_fecha(iso)
    return iso if not d else d.strftime("%d/%m/%Y")


# ---------------------------------------------------------------------------
# Context: everything the two documents share, resolved once
# ---------------------------------------------------------------------------
def pedidos() -> list[dict]:
    """The deliveries a folder can be opened for — the logistics orders."""
    return [{"numero": p.get("pedido"), "cliente": p.get("cliente"),
             "estado": p.get("estado"), "fecha_prevista": p.get("fecha_prevista")}
            for p in esquema.filas("logistica") if p.get("pedido")]


def _regla_del_cliente(nombre: str) -> dict | None:
    """The house rule about this customer, if the owner ever stated one.
    This is the tacit context no ERP holds, and on a document it belongs
    quoted AS A RULE with its source — never folded silently into a number."""
    piezas = conocimiento.listar()
    piezas = piezas.get("piezas", []) if isinstance(piezas, dict) else piezas
    for p in piezas:
        if p.get("ambito") == "cliente" and p.get("entidad") == nombre:
            return p
    return None


def _contexto(numero: str, lang: str | None = None) -> dict | None:
    fila = next((p for p in esquema.filas("logistica")
                 if p.get("pedido") == numero), None)
    if not fila:
        return None
    nombre = fila.get("cliente")
    cta = next((c for c in cuentas.listar() if c.get("nombre") == nombre), None)
    abiertos = []
    for c in (ventas_cliente._load().get("clientes") or []):
        if c.get("nombre") == nombre:
            abiertos = [p for p in c.get("pedidos", []) if not p.get("historico")]
            break
    items = [i for p in abiertos for i in p.get("items", [])]
    total = round(sum(float(i.get("monto") or 0) for i in items), 2)
    return {"pedido": fila, "cliente": nombre, "cuenta": cta, "abiertos": abiertos,
            "items": items, "total": total, "regla": _regla_del_cliente(nombre),
            "hoy": hoy(), "lang": lang}


# ---------------------------------------------------------------------------
# The two documents
# ---------------------------------------------------------------------------
def _remito_entrega(c: dict) -> dict:
    lang, p, cta = c["lang"], c["pedido"], c["cuenta"] or {}
    fu_pedido = _t("fu_pedido", lang, n=p.get("pedido"))
    fu_cuenta = _t("fu_cuenta", lang, cliente=c["cliente"])
    fecha_abierto = (c["abiertos"][0].get("fecha") if c["abiertos"] else None)
    fu_items = _t("fu_pedido_abierto", lang, cliente=c["cliente"],
                  fecha=_dia(fecha_abierto, lang) or "—")
    return {
        "id": "remito_entrega",
        "titulo": _t("remito_t", lang),
        "subtitulo": _t("remito_sub", lang),
        "emisor": paths.EMPRESA,
        "nota_legal": _t("remito_nota", lang),
        "secciones": [
            {"titulo": _t("sec_entrega", lang), "campos": [
                campo(_t("f_numero", lang), _numero_de("remito_entrega", p.get("pedido")), fu_pedido),
                campo(_t("f_pedido", lang), p.get("pedido"), fu_pedido),
                campo(_t("f_fecha_prevista", lang), _dia(p.get("fecha_prevista"), lang), fu_pedido),
                campo(_t("f_transporte", lang), p.get("transporte"), fu_pedido),
                campo(_t("f_direccion", lang), p.get("direccion"), fu_pedido),
                campo(_t("f_estado_pedido", lang), p.get("estado"), fu_pedido),
            ]},
            {"titulo": _t("sec_partes", lang), "campos": [
                campo(_t("f_emisor", lang), paths.EMPRESA, _t("fu_empresa", lang)),
                campo(_t("f_cliente", lang), c["cliente"], fu_cuenta),
                # Deliberately empty in this dataset: the account has no tax id
                # or phone. Shown as MISSING instead of invented — that is the
                # whole point of the state on each field.
                campo(_t("f_cuit_cliente", lang), cta.get("vat"), fu_cuenta),
                campo(_t("f_tel_cliente", lang), cta.get("phone"), fu_cuenta, obligatorio=False),
            ]},
            {"titulo": _t("sec_mercaderia", lang), "campos": [
                campo(_t("f_renglones", lang), len(c["items"]) or None, fu_items),
                campo(_t("f_total", lang), _pesos(c["total"], lang) if c["items"] else None, fu_items),
            ]},
        ],
        "renglones": [{
            "codigo": i.get("codigo"), "producto": i.get("producto"),
            "cantidad": round(float(i.get("cantidad") or 0), 2),
            "precio": _pesos(i.get("precio"), lang),
            "monto": _pesos(i.get("monto"), lang),
            "fuente": fu_items,
        } for i in c["items"]],
    }


def _estado_cuenta(c: dict) -> dict:
    lang, cta = c["lang"], c["cuenta"] or {}
    fu_cuenta = _t("fu_cuenta", lang, cliente=c["cliente"])
    regla = c["regla"]
    fu_regla = _t("fu_regla", lang, id=regla["id"]) if regla else None
    dias = cta.get("dias_sin_pagar")
    tolerancia = ((regla or {}).get("params") or {}).get("tolerancia_dias")
    return {
        "id": "estado_cuenta",
        "titulo": _t("estado_t", lang),
        "subtitulo": _t("estado_sub", lang, cliente=c["cliente"]),
        "emisor": paths.EMPRESA,
        "nota_legal": _t("estado_nota", lang),
        "secciones": [
            {"titulo": _t("sec_cliente", lang), "campos": [
                campo(_t("f_cliente", lang), c["cliente"], fu_cuenta),
                campo(_t("f_cuit_cliente", lang), cta.get("vat"), fu_cuenta),
                campo(_t("f_email", lang), cta.get("email"), fu_cuenta, obligatorio=False),
                campo(_t("f_ciudad", lang), cta.get("city"), fu_cuenta, obligatorio=False),
            ]},
            {"titulo": _t("sec_situacion", lang), "campos": [
                campo(_t("f_saldo", lang), _pesos(cta.get("saldo"), lang), fu_cuenta),
                campo(_t("f_limite", lang), _pesos(cta.get("limite_credito"), lang), fu_cuenta),
                campo(_t("f_disponible", lang), _pesos(cta.get("disponible"), lang), fu_cuenta),
                campo(_t("f_plazo", lang), cta.get("plazo_dias"), fu_cuenta),
                campo(_t("f_dias", lang), dias, fu_cuenta),
                campo(_t("f_promedio", lang), cta.get("promedio_pago_dias"), fu_cuenta),
            ]},
            # The house rule, quoted AS A RULE with its source. Doña Elsa's 45
            # days is the clearest case: the number that decides whether this
            # customer is late is not the commercial term, it is what the
            # owner said once — and the document has to say so, not hide it.
            {"titulo": _t("sec_criterio", lang), "campos": [
                campo(_t("f_regla", lang),
                      (regla.get("texto_en") if lang == "en" and regla.get("texto_en")
                       else regla.get("texto")) if regla else None,
                      fu_regla, obligatorio=False),
                campo(_t("f_tolerancia", lang),
                      _t("dias_n", lang, n=tolerancia) if tolerancia else None,
                      fu_regla, obligatorio=False),
                campo(_t("f_veredicto", lang),
                      _veredicto(dias, tolerancia, cta.get("plazo_dias"), lang),
                      fu_regla or fu_cuenta, obligatorio=False),
            ]},
        ],
        "renglones": [{
            "fecha": _dia(m.get("fecha"), lang), "tipo": m.get("tipo"),
            "detalle": m.get("detalle"), "monto": _pesos(m.get("monto"), lang),
            "fuente": fu_cuenta,
        } for m in (cta.get("movimientos") or [])[-12:]],
    }


def _veredicto(dias, tolerancia, plazo, lang) -> str | None:
    """Late against WHAT — the house rule when there is one, the commercial
    term when there is not. Stated, never computed silently into a colour."""
    if dias is None:
        return None
    umbral = tolerancia or plazo
    if umbral is None:
        return None
    key = "ver_pasado" if dias > umbral else "ver_dentro"
    return _t(key, lang, dias=dias, umbral=umbral,
              cual=_t("umbral_regla" if tolerancia else "umbral_plazo", lang))


_ARMADORES = {"remito_entrega": _remito_entrega, "estado_cuenta": _estado_cuenta}
_PREFIJO = {"remito_entrega": "R", "estado_cuenta": "EC"}


def _numero_de(doc_id: str, numero_pedido: str) -> str:
    """Stable per (document, order): the same folder reopened shows the same
    number, instead of a fresh one every render."""
    digitos = "".join(ch for ch in str(numero_pedido or "") if ch.isdigit()) or "0"
    return f"{_PREFIJO[doc_id]}-{hoy().year}-{int(digitos):05d}"


# ---------------------------------------------------------------------------
# The folder, its completeness and its cross-check
# ---------------------------------------------------------------------------
def _completitud(d: dict) -> dict:
    campos = [x for s in d.get("secciones", []) for x in s["campos"]]
    faltan = [x for x in campos if x["estado"] == "falta"]
    completos = [x for x in campos if x["estado"] == "completo"]
    # The percentage counts REQUIRED fields against required fields. Counting
    # every filled field over only the required ones (the shape this pattern
    # arrived with) reports 100% on a document that is still missing one.
    oblig = [x for x in campos if x["obligatorio"]]
    oblig_ok = [x for x in oblig if x["estado"] == "completo"]
    return {"completos": len(completos), "faltan": len(faltan), "total": len(campos),
            "pct": round(len(oblig_ok) / len(oblig) * 100) if oblig else 100,
            "que_falta": [x["etiqueta"] for x in faltan]}


def documento(numero: str, doc_id: str, lang: str | None = None) -> dict | None:
    c = _contexto(numero, lang)
    if not c or doc_id not in _ARMADORES:
        return None
    d = _ARMADORES[doc_id](c)
    d["pedido"] = numero
    d["cliente"] = c["cliente"]
    d["emitido"] = c["hoy"].isoformat()
    d["numero"] = _numero_de(doc_id, numero)
    d["completitud"] = _completitud(d)
    # The PDF pipeline (core/pdf.py) renders by shape; this tells it which one.
    d["tipo"] = "carpeta"
    return d


def carpeta(numero: str, lang: str | None = None) -> dict | None:
    """The whole folder of one delivery: both documents, how much each one is
    missing, and the cross-check between them."""
    c = _contexto(numero, lang)
    if not c:
        return None
    docs = []
    for did in DOCUMENTOS:
        d = _ARMADORES[did](c)
        docs.append({"id": did, "titulo": d["titulo"],
                     "numero": _numero_de(did, numero),
                     "completitud": _completitud(d)})
    return {
        "pedido": numero,
        "cliente": c["cliente"],
        "estado": c["pedido"].get("estado"),
        "fecha_prevista": c["pedido"].get("fecha_prevista"),
        "transporte": c["pedido"].get("transporte"),
        "renglones": len(c["items"]),
        "total": c["total"],
        "documentos": docs,
        "listos": sum(1 for d in docs if d["completitud"]["faltan"] == 0),
        "total_documentos": len(docs),
        "control_cruzado": control_cruzado(numero, lang),
    }


def control_cruzado(numero: str, lang: str | None = None) -> dict:
    """The check no form does on its own: that the delivery note's total, the
    customer's open order and their account balance say the same thing.

    Trivial when all three come from the same source — which is precisely the
    point. Every manual copy is where it stops being trivial."""
    c = _contexto(numero, lang)
    if not c:
        return {"ok": False, "motivo": "pedido_inexistente"}
    cta = c["cuenta"] or {}
    total_pedido = round(sum(float(p.get("monto") or 0) for p in c["abiertos"]), 2)
    saldo = float(cta.get("saldo") or 0)
    checks = [
        {"que": _t("cc_renglones", lang), "a": c["total"], "b": total_pedido,
         "ok": abs(c["total"] - total_pedido) < 1},
        {"que": _t("cc_saldo", lang), "a": total_pedido, "b": saldo,
         "ok": abs(total_pedido - saldo) < 1},
        {"que": _t("cc_cliente", lang), "a": c["cliente"], "b": cta.get("nombre"),
         "ok": bool(cta) and cta.get("nombre") == c["cliente"]},
    ]
    return {"ok": all(x["ok"] for x in checks), "checks": checks,
            "nota": _t("cc_nota", lang)}


# ---------------------------------------------------------------------------
# What to offer, and when
# ---------------------------------------------------------------------------
# The propose → approve pattern that already exists, applied to paperwork: when
# somebody finishes a collection action the statement is the next thing they
# need; when a delivery is despatched, the delivery note is. This does not send
# anything and does not generate anything — it says WHAT would help now, and
# the person decides. No new infrastructure: the tool it points at
# (`generar_documento`) has existed since P24.
_TRAS = {
    # momento -> (doc_id, la clave de la frase con la que se ofrece)
    "cobranza": ("estado_cuenta", "ofrece_estado"),
    "despacho": ("remito_entrega", "ofrece_remito"),
}


def sugerencia(momento: str, cliente: str | None = None,
               numero: str | None = None, lang: str | None = None) -> dict | None:
    """The document this moment calls for, or None when none does.

    `numero` is a delivery; when only the customer is known (a collection
    action just registered), their open delivery is looked up — and if they
    have none, there is nothing to offer and that is said by returning None
    instead of pointing at a folder that does not exist.
    """
    par = _TRAS.get(momento)
    if not par:
        return None
    doc_id, frase = par
    if not numero and cliente:
        numero = next((p["numero"] for p in pedidos() if p["cliente"] == cliente), None)
    if not numero:
        return None
    c = _contexto(numero, lang)
    if not c:
        return None
    return {"momento": momento, "pedido": numero, "cliente": c["cliente"],
            "documento": doc_id,
            "texto": _t(frase, lang, cliente=c["cliente"], pedido=numero)}
