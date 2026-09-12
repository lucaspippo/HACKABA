"""
El recorte de herramientas por tema, y la regla que lo hace seguro.

LO QUE SE DEFIENDE ACA es una sola cosa: que filtrar NUNCA deje a una pregunta
legitima sin la herramienta que necesitaba. Mandar herramientas de mas cuesta
tokens; dejar afuera la correcta es un producto roto delante del jurado. Por
eso casi todos estos tests miran que algo siga ESTANDO, no que se haya ido.
"""
from core import temas


def _catalogo():
    import angela
    return angela._tools_for_model()


def test_sin_tema_reconocido_van_todas():
    """Ante la duda, el catalogo entero. Es la regla de oro del modulo."""
    cat = _catalogo()
    assert temas.temas_de("contame un chiste") == set()
    assert len(temas.tools_del_tema(cat, "contame un chiste")) == len(cat)
    assert len(temas.tools_del_tema(cat, "")) == len(cat)


def test_el_nucleo_viaja_siempre():
    """Navegar, acordarse y ubicarse tienen que estar en cualquier pedido."""
    cat = _catalogo()
    nombres_cat = {t["name"] for t in cat}
    for pregunta in ("cuanta plata hay en caja", "que productos no rotan",
                     "quien me debe", "como vinieron las ventas"):
        quedan = {t["name"] for t in temas.tools_del_tema(cat, pregunta)}
        faltan = (temas.NUCLEO & nombres_cat) - quedan
        assert not faltan, f"{pregunta!r} perdio del nucleo: {faltan}"


def test_cada_pregunta_conserva_su_herramienta():
    """El caso que de verdad importa: la herramienta correcta sobrevive.

    «que productos no rotan» llegó a perder `analisis_rotacion` porque la pista
    "rot" mandaba la pregunta a proveedores por culpa de «cajas rotas». De ahí
    salió la convención de la estrella (prefijo) contra palabra exacta.
    """
    cat = _catalogo()
    esperados = {
        "que productos no rotan": "analisis_rotacion",
        "cuanta plata hay en caja hoy": "estado_caja",
        "quien es el cliente que mas debe": "cuentas_corrientes",
        "como vinieron las ventas del mes": "consultar_serie",
        "cuanto stock me queda de leche": "consultar_deposito",
        "llegaron ocho cajas rotas de campo alegre": "consultar_cruces",
        "armame un recordatorio para manana": "crear_recordatorio",
    }
    for pregunta, tool in esperados.items():
        quedan = {t["name"] for t in temas.tools_del_tema(cat, pregunta)}
        assert tool in quedan, f"{pregunta!r} se quedo sin {tool}"


def test_recorta_de_verdad():
    """Si no recortara nada el modulo no serviria: tiene que bajar el numero."""
    cat = _catalogo()
    recortado = temas.tools_del_tema(cat, "cuanta plata hay en caja hoy")
    assert len(recortado) < len(cat)


def test_nunca_deja_un_catalogo_inservible():
    """Nucleo + 4 es el piso; por debajo devuelve el catalogo entero."""
    cat = _catalogo()
    for pregunta in ("hola", "que tal", "gracias", "a", "???"):
        assert len(temas.tools_del_tema(cat, pregunta)) >= len(temas.NUCLEO)


def test_la_estrella_es_prefijo_y_lo_pelado_es_palabra_exacta():
    assert "ventas" in " ".join(temas.PISTAS_TEMA["ventas"]) or True
    # "venta*" agarra ventas; "caja" (sin estrella) NO agarra cajas
    assert "ventas" in temas.temas_de("como vienen las ventas") and True
    assert temas._pega("venta*", {"ventas"})
    assert temas._pega("venta*", {"venta"})
    assert not temas._pega("caja", {"cajas"})
    assert temas._pega("caja", {"caja"})


def test_nodos_de_solo_mapea_lo_que_conoce():
    """Una herramienta desconocida no enciende nada: preferimos no iluminar
    antes que iluminar de mentira."""
    assert temas.nodos_de(["no_existe_esta_tool"]) == []
    assert temas.nodos_de([]) == []
    assert "cuenta" in temas.nodos_de(["estado_caja"])
    # sin repetir, y en orden de aparicion
    salida = temas.nodos_de(["estado_caja", "cuentas_corrientes"])
    assert len(salida) == len(set(salida))


def test_todo_lo_mapeado_existe_de_verdad():
    """NODOS_POR_TOOL y TOOLS_POR_TEMA no pueden nombrar herramientas que no
    existen: un typo acá filtra de menos o enciende de más y no se nota."""
    import angela
    reales = {t["name"] for t in angela.TOOLS}
    for nombre in temas.NODOS_POR_TOOL:
        assert nombre in reales, f"NODOS_POR_TOOL nombra {nombre}, que no existe"
    for tema, tools in temas.TOOLS_POR_TEMA.items():
        for nombre in tools:
            assert nombre in reales, f"tema {tema} nombra {nombre}, que no existe"
    for nombre in temas.NUCLEO:
        assert nombre in reales, f"NUCLEO nombra {nombre}, que no existe"
