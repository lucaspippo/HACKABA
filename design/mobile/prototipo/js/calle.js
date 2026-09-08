/* calle.js — los dos oficios que trabajan afuera: el chofer y el preventista.
   Las paradas y los clientes son los del dataset (apartados.logistica,
   cuentas.json, notas_equipo.json). Camión 1 es el de Walter. */

/* ══ WALTER · Reparto, camión 1 ══════════════════════════════════════════ */

hoja('walter', {
  titulo: 'Registrar', sub: 'Parado, con el motor andando.',
  vozA: 'walter.ruta',
  tiles: [
    ['tilde', ['Entregué', 'Con foto del remito'], 'walter.entrega', 'destaca'],
    ['vuelta', ['Me devolvió', 'Rechazó parte o todo'], 'walter.dev1', 'alerta'],
    ['plata', ['Me pagó', 'Registrar la cobranza'], 'walter.ruta'],
    ['alerta', ['No estaba / no pude', 'Y por qué'], 'walter.noestaba'],
  ],
});

reg('walter.ruta', {
  rol: 'walter', tab: 'ruta', titulo: 'Mi ruta (una parada por pantalla)',
  encabezado: 'Parada 4 de 9', subencabezado: 'Camión 1 · hoy 07/07',
  nota: `<b>Una parada por pantalla, no una lista.</b> Walter mira esto parado, al sol,
    con el motor andando: la lista de nueve no le sirve, la parada de ahora sí.
    Los tres botones son de 70px y están en la mitad baja del teléfono.
    <span class="toques">Entregar sin novedad: 2 toques (Entregué + foto).</span>`,
  html: () => `<div class="cuerpo">
    <div class="card" style="margin-top:6px">
      <p class="tit">Comedor Escolar N°12</p>
      <p class="txt fuerte">San Martín 731</p>
      <p class="meta"><span class="mono">P-4412</span> · 8 bultos · en camino</p>
      <div class="card angela" style="margin-top:12px;padding:12px">
        <p class="txt fuerte" style="font-size:13px">Deben $12.600.000 hace 28 días,
          con 45 de plazo. Pagan en promedio a 41: no hay nada que reclamarle.</p>
        <p class="meta">Cuenta corriente · al 07/07</p>
      </div>
    </div>

    <button class="btn pri grande" onclick="go('walter.entrega')">${ico('tilde', 22)} Entregué todo</button>
    <button class="btn sec grande" onclick="go('walter.dev1')">${ico('vuelta', 22)} Me devolvió algo</button>
    <button class="btn sec grande" onclick="go('walter.noestaba')">${ico('alerta', 22)} No pude entregar</button>

    <div class="h2">Después de ésta</div>
    <div class="lista">
      <div class="li"><span class="pt gris"></span><span class="crece">
        <b>Comidas El Fogón</b><span>Ruta 11 km 1317 · P-4418</span></span></div>
      <div class="li"><span class="pt gris"></span><span class="crece">
        <b>Mercadito del Río</b><span>Belgrano 1797 · P-4429</span></span></div>
    </div>
    ${sinSenal()}
  </div>`,
});

reg('walter.entrega', {
  rol: 'walter', top: 'volver', vuelveA: 'walter.ruta', titulo: 'Entregué', barra: false,
  titulo_panel: 'Confirmar una entrega',
  nota: `La foto del remito firmado no es decorativa: es el respaldo de Walter si el
    cliente después dice que no recibió. Ya existe en el código
    (<code>roles.js</code> · campo <code>prueba</code>, y <code>piso.py</code> la guarda
    como archivo). Es opcional: una entrega sin foto igual se confirma.
    <span class="toques">2 toques.</span>`,
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="card">
      <p class="tit chico">Comedor Escolar N°12 · P-4412</p>
      <p class="txt">8 bultos</p>
      <div class="evidencia">foto del remito firmado</div>
      <button class="btn sec" style="margin-top:10px">${ico('camara', 20)} Sacar la foto</button>
    </div>
    <button class="btn pri grande" onclick="go('walter.ruta')">Confirmar la entrega</button>
    <p class="fuente">${ico('info', 14)}<span>Sin señal se guarda igual y sale solo.
      Vos ya podés arrancar para la próxima.</span></p>
  </div>`,
});

/* ── Devolución del cliente en la puerta. Mismo motor que el reclamo de
     recepción, pantalla distinta: acá el interlocutor es un cliente, no un
     proveedor, y la persona está parada. ─────────────────────────────────── */

reg('walter.dev1', {
  rol: 'walter', top: 'volver', vuelveA: 'walter.ruta', titulo: 'Qué te devolvió', barra: false,
  pasos: [1, 3], paso: '1 de 3',
  titulo_panel: 'Devolución · 1 · qué pasó',
  nota: `<b>Tres pasos, no cuatro.</b> El chofer no completa requisitos de proveedor:
    el cliente ya está enfrente y el reclamo, si corresponde, lo arma después Compras.
    Lo único que se le pide es lo que sólo él puede aportar.
    <span class="toques">1 toque.</span>`,
  html: () => `<div class="cuerpo" style="padding-top:8px">
    <p class="txt fuerte" style="margin-bottom:14px">Comedor Escolar N°12 · P-4412</p>
    <button class="btn sec grande" onclick="go('walter.dev2')">Vino roto o golpeado</button>
    <button class="btn sec grande" onclick="go('walter.dev2')">No era lo que pidió</button>
    <button class="btn sec grande" onclick="go('walter.dev2')">Está vencido o por vencer</button>
    <button class="btn sec grande" onclick="go('walter.dev2')">No lo quiso recibir</button>
    <button class="voz" onclick="go('walter.dev2')">${ico('micro', 22)}
      <span><b>Decirlo hablando</b><span>Con la puerta del camión en la mano</span></span></button>
  </div>`,
});

reg('walter.dev2', {
  rol: 'walter', top: 'volver', vuelveA: 'walter.dev1', titulo: 'Cuánto vuelve', barra: false,
  pasos: [2, 3], paso: '2 de 3',
  titulo_panel: 'Devolución · 2 · cuánto vuelve',
  nota: `Los renglones del pedido ya están en pantalla: no se escribe el nombre del
    producto, se toca. Un toque por renglón devuelto, y la cantidad arranca en el total.
    <span class="toques">2 toques (renglón + foto).</span>`,
  html: () => `<div class="cuerpo" style="padding-top:10px">
    <div class="h2">Del pedido P-4412</div>
    <div class="lista">
      <button class="li"><span class="pt rojo"></span><span class="crece">
        <b>YOGUR BEBIBLE TIERRA ROJA 900G</b><span>Lote L-2026-309 · vuelven <b>2</b> de 12</span></span>
        <span class="rot rojo">Vuelve</span></button>
      <button class="li"><span class="pt gris"></span><span class="crece">
        <b>LECHE ENTERA SANTA CLARA 1L</b><span>Llevabas 24</span></span>${ico('chevron', 18)}</button>
      <button class="li"><span class="pt gris"></span><span class="crece">
        <b>GALLETITAS SURTIDAS LA RIBERA 400G</b><span>Llevabas 6</span></span>${ico('chevron', 18)}</button>
    </div>
    <div class="card" style="margin-top:12px">
      <p class="txt fuerte">Foto de cómo vuelve</p>
      <div class="evidencia">la caja golpeada</div>
      <button class="btn sec" style="margin-top:10px">${ico('camara', 20)} Sacar la foto</button>
    </div>
    <button class="btn pri" onclick="go('walter.dev3')">Seguir</button>
  </div>`,
});

reg('walter.dev3', {
  rol: 'walter', top: 'volver', vuelveA: 'walter.dev2', titulo: 'A dónde va', barra: false,
  pasos: [3, 3], paso: '3 de 3',
  titulo_panel: 'Devolución · 3 · a dónde va',
  nota: `<b>Acá se enganchan los dos flujos.</b> Ángela ya cruzó el producto con su
    proveedor real (Alimentos del Paraná SA — en este dataset la marca del producto y
    el proveedor no coinciden) y avisa que puede terminar en reclamo. Pero el reclamo
    lo arma Compras, no el chofer: Walter confirma un destinatario y arranca.
    <span class="toques">1 toque.</span>`,
  html: () => `<div class="cuerpo" style="padding-top:10px">
    <div class="card">
      <p class="tit chico">Vuelven 2 de YOGUR BEBIBLE TIERRA ROJA 900G</p>
      <p class="txt">Comedor Escolar N°12 · golpeadas · con foto</p>
    </div>
    <div class="card angela">
      <div class="fila"><span class="icoc angela">${ico('angela', 21)}</span><div class="crece">
        <p class="txt fuerte">Lo ve <b>Ramón</b> para recibir la mercadería de vuelta,
          y le aviso a <b>Celeste</b>: el yogur es de Alimentos del Paraná y es el
          segundo golpe de este lote.</p>
        <p class="meta">Osmar reportó lo mismo en Rotisería Avenida el 27/06</p>
      </div></div>
      <button class="btn ang" style="margin-top:12px" onclick="go('walter.devok')">Mandarlo así</button>
      <div class="par" style="margin-top:8px">
        <button class="btn sec">Sólo a Ramón</button>
        <button class="btn sec">A otro</button>
      </div>
    </div>
  </div>`,
});

reg('walter.devok', {
  rol: 'walter', top: 'volver', vuelveA: 'walter.ruta', titulo: 'Listo', barra: false, oculta: true,
  html: () => `<div class="cuerpo" style="padding-top:26px;text-align:center">
    <span class="icoc salvia" style="width:64px;height:64px;margin:0 auto 16px;border-radius:var(--r-full)">
      ${ico('tilde', 32)}</span>
    <p class="tit">Cargado</p>
    <p class="txt" style="margin-bottom:18px">2 yogures vuelven · Comedor Escolar N°12</p>
    <div class="card plano" style="text-align:left">
      <ul class="tl">
        <li><b>Guardado en tu teléfono</b><span>Con la foto</span></li>
        <li class="espera"><b>Se manda cuando haya señal</b><span>Estás en Ruta 11</span></li>
        <li class="futuro"><b>Ramón y Celeste lo ven</b><span>Te aviso</span></li>
      </ul>
    </div>
    <button class="btn pri" style="margin-top:14px" onclick="go('walter.ruta')">Seguir la ruta</button>
  </div>`,
});

reg('walter.noestaba', {
  rol: 'walter', top: 'volver', vuelveA: 'walter.ruta', titulo: 'No pude entregar', barra: false,
  titulo_panel: 'No pude entregar',
  nota: `<b>Este flujo es el que hoy se muere en WhatsApp.</b> Walter dejó dos notas
    de voz sobre Almacén San Martín cerrado (nt01, nt02) y una sobre 9 de Julio
    pidiendo hablar con Aldo (nt04): están en el dataset y no llegan a nadie con nombre.
    <span class="toques">2 toques.</span>`,
  html: () => `<div class="cuerpo" style="padding-top:8px">
    <button class="btn sec grande" onclick="go('walter.noestaba2')">Estaba cerrado</button>
    <button class="btn sec grande" onclick="go('walter.noestaba2')">No pudo pagar</button>
    <button class="btn sec grande" onclick="go('walter.noestaba2')">La dirección está mal</button>
    <button class="btn sec grande" onclick="go('walter.noestaba2')">Me hicieron esperar y no pude</button>
  </div>`,
});

reg('walter.noestaba2', {
  rol: 'walter', top: 'volver', vuelveA: 'walter.noestaba', titulo: 'A quién le llega', barra: false, oculta: true,
  html: () => `<div class="cuerpo" style="padding-top:10px">
    <div class="card angela">
      <div class="fila"><span class="icoc angela">${ico('angela', 21)}</span><div class="crece">
        <p class="txt fuerte">Es la <b>tercera vez</b> que Almacén San Martín está cerrado.
          Las dos anteriores también las anotaste vos.</p>
        <p class="txt">Esto lo ve <b>Diego</b>, que lo visita, y queda en la ficha del cliente.</p>
      </div></div>
      <button class="btn ang" style="margin-top:12px" onclick="go('walter.ruta')">Mandárselo a Diego</button>
      <div class="par" style="margin-top:8px">
        <button class="btn sec">A Marta</button>
        <button class="btn sec">A otro</button>
      </div>
    </div>
    <p class="fuente">${ico('info', 14)}<span>Sin este paso, el aviso queda como las 31
      notas del dataset: con autor, sin destinatario y sin nadie que lo cierre.</span></p>
  </div>`,
});

reg('walter.dia', {
  rol: 'walter', tab: 'dia', titulo: 'Lo mío',
  nota: `Para un chofer, «Mi día» no es la agenda —eso es la ruta— sino <b>qué pasó con
    lo que él cargó</b>. Por eso la segunda pestaña se llama «Lo mío» y no «Mi día».`,
  html: () => `<div class="cuerpo">
    ${novedadTuya('Lo que avisaste de Almacén San Martín llegó a Diego: pasa el jueves a hablar con el dueño.',
      'Diego lo vio ayer', 'walter.dia')}

    <div class="h2">Lo que reportaste</div>
    <div class="lista">
      <button class="li"><span class="pt salvia"></span><span class="crece">
        <b>Almacén San Martín cerrado · 3ª vez</b><span>Diego lo tomó · visita el jueves</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li"><span class="pt oro"></span><span class="crece">
        <b>9 de Julio pidió hablar con Aldo</b><span>Esperando · hace 4 días</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li"><span class="pt salvia"></span><span class="crece">
        <b>2 yogures devueltos · Comedor Escolar</b><span>Ramón los recibió</span></span>
        ${ico('chevron', 18)}</button>
    </div>

    <div class="h2">Tu día</div>
    <div class="card plano">
      <p class="txt fuerte">6 de 9 entregas hechas.</p>
      <div class="progreso"><i style="width:67%"></i></div>
    </div>
  </div>`,
});

reg('walter.avisos', {
  rol: 'walter', top: 'volver', vuelveA: 'walter.ruta', titulo: 'Avisos', barra: false, oculta: true,
  html: () => `<div class="cuerpo" style="padding-top:12px"><div class="lista">
    <div class="li"><span class="pt salvia"></span><span class="crece">
      <b>Diego tomó tu aviso de San Martín</b><span>Ayer 18:40</span></span></div></div></div>`,
});

reg('walter.angela', {
  rol: 'walter', tab: 'angela', titulo: 'Ángela (chat)',
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="burb ella">Te quedan 3 paradas. La próxima es Comidas El Fogón.</div>
    <div class="lista">
      <div class="li"><span class="crece"><b>¿Cuánto me falta entregar?</b></span>${ico('chevron', 18)}</div>
      <div class="li"><span class="crece"><b>¿Cuántos bultos lleva esta parada?</b></span>${ico('chevron', 18)}</div>
    </div>
  </div>`,
});

/* ══ DIEGO · Preventista, zona centro ════════════════════════════════════ */

hoja('diego', {
  titulo: 'Registrar', sub: 'Adentro del local del cliente.',
  vozA: 'diego.ruta',
  tiles: [
    ['lista', ['Tomar el pedido', 'Con lo que suele llevar'], 'diego.pedido', 'destaca'],
    ['plata', ['Me pagó', 'Registrar la cobranza'], 'diego.cliente'],
    ['alerta', ['Me pidió algo que no tenemos', 'O a otro precio'], 'diego.aviso'],
    ['camara', ['Foto de la góndola', 'Cómo está exhibido'], 'diego.cliente'],
  ],
});

reg('diego.ruta', {
  rol: 'diego', tab: 'ruta', titulo: 'Mi ruta',
  nota: `El preventista es, junto con mostrador, el que más usa la <b>búsqueda</b>:
    por eso la lupa aparece en su encabezado y no en el de Tomás.`,
  html: () => `<div class="cuerpo">
    <div class="h2">Ahora</div>
    <div class="card">
      <div class="fila"><span class="icoc oro">${ico('pin', 21)}</span><div class="crece">
        <p class="tit chico">Despensa Doña Elsa</p>
        <p class="txt">Ruta 11 km 1065 · cliente desde 2011</p>
      </div></div>
      <button class="btn pri" style="margin-top:12px" onclick="go('diego.cliente')">Abrir la ficha</button>
    </div>

    <div class="h2">Después</div>
    <div class="lista">
      <button class="li" onclick="go('diego.cliente')"><span class="pt rojo"></span><span class="crece">
        <b>Almacén San Martín</b><span>Walter lo encontró cerrado 3 veces</span></span>${ico('chevron', 18)}</button>
      <button class="li" onclick="go('diego.cliente')"><span class="pt oro"></span><span class="crece">
        <b>Proveeduría La Rural</b><span>Te pidió precio por cantidad de gaseosa</span></span>${ico('chevron', 18)}</button>
      <button class="li" onclick="go('diego.cliente')"><span class="pt gris"></span><span class="crece">
        <b>Kiosco La Terminal</b><span>Debe $4.200.000 · 11 días</span></span>${ico('chevron', 18)}</button>
    </div>
  </div>`,
});

reg('diego.cliente', {
  rol: 'diego', top: 'volver', vuelveA: 'diego.ruta', titulo: 'Ficha del cliente', barra: false,
  titulo_panel: 'Ficha del cliente (con lo que sabe el equipo)',
  nota: `<b>Propuesta nueva: «lo último de este cliente».</b> Cruza <code>core/notas.py</code>
    con <code>core/cuentas.py</code> y le pone delante a Diego lo que dijeron Walter y
    él mismo antes de entrar. Hoy eso vive sólo en el mapa del dueño, y el preventista
    —que es el que puede hacer algo— no lo ve. La banda ámbar del plazo de casa ya
    existe en <code>mapa_operacion.cobranza()</code>.`,
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="card">
      <p class="tit">Despensa Doña Elsa</p>
      <p class="meta">Ruta 11 km 1065</p>
      <div style="margin-top:12px">
        <div class="dato"><span>Debe</span><b>$19.200.000</b></div>
        <div class="dato"><span>Hace</span><b style="color:var(--rojo)">66 días</b></div>
        <div class="dato"><span>Última compra</span><b>02/05</b></div>
        <div class="dato"><span>Paga en promedio a</span><b>31 días</b></div>
      </div>
      <div class="card oro" style="margin-top:12px;padding:12px">
        <p class="txt fuerte" style="font-size:13px">«A Doña Elsa tolerale hasta 45 días —
          es cliente desde 2011 y nunca me falló.»</p>
        <p class="meta">Regla de la casa, la enseñó Aldo · <b>y ya pasó los 45</b></p>
      </div>
    </div>

    <div class="h2">Lo último que se dijo de este cliente</div>
    <div class="card plano">
      <ul class="tl">
        <li class="futuro"><b>Walter · 08/07</b><span>Entrega prevista para hoy, P-4426</span></li>
        <li><b>Vos · 30/06</b><span>«Preguntó por promoción de gaseosa por cantidad»</span></li>
      </ul>
    </div>

    <button class="btn pri" onclick="go('diego.pedido')">${ico('lista', 20)} Tomar el pedido</button>
    <button class="btn sec" onclick="go('diego.aviso')">${ico('plata', 20)} Registrar una cobranza</button>
  </div>`,
});

reg('diego.pedido', {
  rol: 'diego', top: 'volver', vuelveA: 'diego.cliente', titulo: 'Pedido', barra: false,
  titulo_panel: 'Tomar el pedido',
  nota: `<b>Lo que suele llevar, no el catálogo.</b> Nadie arma un pedido scrolleando
    430 productos parado en un mostrador: arranca con lo que este cliente compró las
    últimas veces, sale de <code>data-demo/ventas_por_cliente.json</code>. El catálogo
    entero se alcanza por búsqueda o escaneo, nunca por lista.
    <span class="toques">Un renglón habitual: 1 toque.</span>`,
  html: () => `<div class="cuerpo" style="padding-top:10px">
    <p class="txt fuerte">Despensa Doña Elsa · pedido nuevo</p>
    <div class="h2">Lo que suele llevar</div>
    <div class="lista">
      <button class="li"><span class="pt salvia"></span><span class="crece">
        <b>LECHE ENTERA SANTA CLARA 1L (X12U)</b><span>Últimas 3 veces · 24 un.</span></span>
        <span class="rot salvia">+24</span></button>
      <button class="li"><span class="pt gris"></span><span class="crece">
        <b>GALLETITAS SURTIDAS LA RIBERA 400G</b><span>Últimas 3 veces · 12 un.</span></span>
        ${ico('mas', 18)}</button>
      <button class="li"><span class="pt gris"></span><span class="crece">
        <b>AZUCAR EL PARANA X1KG (X10U)</b><span>Últimas 2 veces · 10 un.</span></span>
        ${ico('mas', 18)}</button>
    </div>
    <div class="card angela" style="margin-top:12px">
      <div class="fila"><span class="icoc angela">${ico('angela', 21)}</span><div class="crece">
        <p class="txt fuerte">Con 66 días de deuda, este pedido pasa el plazo que le dio Aldo.
          Se puede tomar igual, pero queda marcado para que él lo vea.</p></div></div>
    </div>
    <button class="btn pri" onclick="go('diego.ruta')">Registrar el pedido</button>
    <p class="fuente">${ico('info', 14)}<span>Esto NO factura: la venta la sigue haciendo el
      ERP. Acá queda el hecho de que Diego lo levantó, con su nombre.</span></p>
  </div>`,
});

reg('diego.aviso', {
  rol: 'diego', top: 'volver', vuelveA: 'diego.cliente', titulo: 'Dejar un aviso', barra: false,
  titulo_panel: 'Aviso del preventista',
  nota: `Los cuatro botones son los avisos que este oficio deja de verdad —salen de las
    notas del dataset, no de una lluvia de ideas. <b>[SUPUESTO]</b> que son los más
    frecuentes: PolPilot no tiene usuarios activos todavía.
    <span class="toques">2 toques.</span>`,
  html: () => `<div class="cuerpo" style="padding-top:8px">
    <button class="btn sec grande" onclick="go('diego.aviso2')">Me pidió algo que no tenemos</button>
    <button class="btn sec grande" onclick="go('diego.aviso2')">Me pidió otro precio</button>
    <button class="btn sec grande" onclick="go('diego.aviso2')">Está comprando en otro lado</button>
    <button class="btn sec grande" onclick="go('diego.aviso2')">Está por cerrar / complicado</button>
    <button class="voz" onclick="go('diego.aviso2')">${ico('micro', 22)}
      <span><b>Es otra cosa · decilo hablando</b><span>Saliendo del local</span></span></button>
  </div>`,
});

reg('diego.aviso2', {
  rol: 'diego', top: 'volver', vuelveA: 'diego.aviso', titulo: 'A quién le llega', barra: false, oculta: true,
  html: () => `<div class="cuerpo" style="padding-top:10px">
    <div class="card">
      <p class="tit chico">«La Rural compra gaseosa en otro lado, le dejan más barato»</p>
      <p class="txt">Proveeduría La Rural · pidió precio por cantidad</p>
    </div>
    <div class="card angela">
      <div class="fila"><span class="icoc angela">${ico('angela', 21)}</span><div class="crece">
        <p class="txt fuerte">Un precio especial lo decide <b>Aldo</b>. Se lo mando con
          lo que este cliente compró el último año para que tenga con qué decidir.</p></div></div>
      <button class="btn ang" style="margin-top:12px" onclick="go('diego.ruta')">Mandárselo a Aldo</button>
      <div class="par" style="margin-top:8px">
        <button class="btn sec">A Celeste</button>
        <button class="btn sec">A otro</button>
      </div>
    </div>
  </div>`,
});

reg('diego.clientes', {
  rol: 'diego', tab: 'clientes', titulo: 'Clientes',
  nota: `La lista de 24 clientes sí cabe en un teléfono —y es la única lista de datos
    que sobrevive tal cual—, porque son 24 y son <b>suyos</b>. Ordenados por lo que
    hay que hacer, no alfabéticamente.`,
  html: () => `<div class="cuerpo">
    <div class="h2">Necesitan algo</div>
    <div class="lista">
      <button class="li" onclick="go('diego.cliente')"><span class="pt rojo"></span><span class="crece">
        <b>Despensa Doña Elsa</b><span>$19.200.000 · 66 días · pasó el plazo de la casa</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li" onclick="go('diego.cliente')"><span class="pt rojo"></span><span class="crece">
        <b>Autoservicio 9 de Julio</b><span>$42.000.000 · 58 días · pidió hablar con Aldo</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li" onclick="go('diego.cliente')"><span class="pt oro"></span><span class="crece">
        <b>Almacén San Martín</b><span>$24.500.000 · 49 días · cerrado 3 veces</span></span>
        ${ico('chevron', 18)}</button>
    </div>
    <div class="h2">El resto</div>
    <div class="lista">
      <button class="li" onclick="go('diego.cliente')"><span class="pt gris"></span><span class="crece">
        <b>Kiosco La Terminal</b><span>$4.200.000 · 11 días</span></span>${ico('chevron', 18)}</button>
      <button class="li" onclick="go('diego.cliente')"><span class="pt gris"></span><span class="crece">
        <b>Rotisería Avenida</b><span>$3.800.000 · 8 días</span></span>${ico('chevron', 18)}</button>
      <button class="li" onclick="go('diego.cliente')"><span class="pt gris"></span><span class="crece">
        <b>Bar El Muelle</b><span>$2.900.000 · 6 días</span></span>${ico('chevron', 18)}</button>
    </div>
  </div>`,
});

reg('diego.avisos', {
  rol: 'diego', top: 'volver', vuelveA: 'diego.ruta', titulo: 'Avisos', barra: false, oculta: true,
  html: () => `<div class="cuerpo" style="padding-top:12px"><div class="lista">
    <div class="li"><span class="pt oro"></span><span class="crece">
      <b>Walter: San Martín cerrado otra vez</b><span>Te lo dirigió ayer</span></span></div>
  </div></div>`,
});

reg('diego.angela', {
  rol: 'diego', tab: 'angela', titulo: 'Ángela (chat)',
  nota: `Las dos velocidades: «¿qué pasa con Doña Elsa?» es para acá; «abrime la ficha
    de Doña Elsa» es la búsqueda del encabezado, 300 ms y sin gastar un turno de chat.`,
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="burb mia">¿Le puedo dar plazo a Doña Elsa?</div>
    <div class="burb ella">Debe $19.200.000 hace 66 días. La regla de la casa dice
      tolerarle hasta 45 — ya los pasó. Con Aldo, sí; solo, no.</div>
    <div class="lista">
      <div class="li"><span class="crece"><b>¿Qué plazo le puedo dar sin riesgo?</b></span>${ico('chevron', 18)}</div>
      <div class="li"><span class="crece"><b>¿Está al día este cliente?</b></span>${ico('chevron', 18)}</div>
      <div class="li"><span class="crece"><b>¿Cuál es el precio actual de este producto?</b></span>${ico('chevron', 18)}</div>
    </div>
  </div>`,
});
