/* oficina.js — el local, la oficina y el dueño. Acá cierra el círculo que
   arranca Nahuel en el depósito: Celeste recibe el aviso, arma el reclamo,
   Aldo lo aprueba, y la novedad vuelve a la pantalla de Nahuel. */

/* ══ BUSCAR · pantalla compartida ════════════════════════════════════════ */

reg('buscar', {
  rol: 'diego', top: 'volver', vuelveA: () => (previo && previo !== 'buscar' ? previo : 'diego.ruta'),
  titulo: 'Buscar', barra: false, oculta: true,
  html: () => `<div class="buscar-res" style="display:flex;flex-direction:column;height:100%">
    <div style="flex:1;overflow:auto">
      <p class="grupo-res">Clientes</p>
      <div class="lista">
        <button class="li" onclick="go('diego.cliente')"><span class="crece">
          <b>Despensa Doña Elsa</b><span>Debe $19.200.000 · 66 días</span></span>${ico('chevron', 18)}</button>
      </div>
      <p class="grupo-res">Productos</p>
      <div class="lista">
        <button class="li"><span class="crece"><b>DULCE DE LECHE CAMPO ALEGRE 400G (X12U)</b>
          <span>Código 1254 · Pasillo 1 · Rack C</span></span>${ico('chevron', 18)}</button>
        <button class="li"><span class="crece"><b>DULCE DE LECHE MONTE CHICO 400G (X12U)</b>
          <span>Código 1253 · Pasillo 1 · Rack A</span></span>${ico('chevron', 18)}</button>
      </div>
      <p class="grupo-res">Preguntarle a Ángela</p>
      <div class="lista">
        <button class="li" onclick="go('diego.angela')"><span class="icoc angela" style="width:32px;height:32px">
          ${ico('angela', 17)}</span><span class="crece"><b>«dulce»</b>
          <span>Como pregunta, no como nombre</span></span>${ico('chevron', 18)}</button>
      </div>
      <p class="fuente" style="margin-top:14px">${ico('info', 14)}<span>
        <b>El orden lo decide el backend, no la pantalla.</b> <code>buscador.parece_pregunta()</code>
        (<code>core/buscador.py:130</code>) ya distingue un nombre de una pregunta: más de
        cuatro palabras o un signo de interrogación mandan la fila de Ángela ARRIBA.
        Acá «dulce» es un nombre, así que Ángela va última.</span></p>
    </div>
    <div class="buscar-caja">
      ${ico('lupa', 20)}
      <input value="dulce" readonly>
      <button class="icobtn" style="margin:0">${ico('escanear', 22)}</button>
    </div>
  </div>`,
  nota: `<b>La caja va abajo, no arriba.</b> Con el teclado abierto queda pegada al
    pulgar y los resultados crecen hacia arriba, con el más cercano a la mano primero.
    El botón de escaneo comparte la caja: para el depósito, un código de barras
    <i>es</i> una búsqueda. Los tipos de resultado y su gate por módulo ya existen en
    <code>/api/buscar-global</code>: quien no tiene <code>cuentas</code> no ve clientes.`,
});

/* ══ VANESA · Mostrador, Casa Central ════════════════════════════════════ */

hoja('vanesa', {
  titulo: 'Escanear', sub: 'Lo que pasa detrás del mostrador.',
  voz: false,
  tiles: [
    ['escanear', ['Escanear', 'Precio y stock al toque'], 'vanesa.prod', 'destaca'],
    ['alerta', ['Me pidieron algo que no hay', 'Queda anotado'], 'vanesa.falta', 'alerta'],
    ['plata', ['Rendir la caja', 'Cierre del día'], 'vanesa.caja'],
  ],
});

reg('vanesa.mostrador', {
  rol: 'vanesa', tab: 'mostrador', titulo: 'Mostrador',
  nota: `<b>Para Vanesa la pantalla de inicio ES la búsqueda.</b> Su trabajo es
    responder «cuánto sale» y «¿hay?» en segundos, delante de alguien que espera.
    Un resumen de la jornada arriba le robaría el lugar a lo único que usa.`,
  html: () => `<div class="cuerpo" style="padding-top:8px">
    <button class="btn pri grande" onclick="go('vanesa.prod')">${ico('escanear', 24)} Escanear un producto</button>
    <button class="btn sec grande" onclick="go('buscar')">${ico('lupa', 24)} Buscarlo por nombre</button>

    <div class="h2">Lo último que buscaste</div>
    <div class="lista">
      <button class="li" onclick="go('vanesa.prod')"><span class="crece">
        <b>JAMON COCIDO GUARANI (HORMA)</b><span>Balanza · $26.836/kg · 33,5 kg</span></span>${ico('chevron', 18)}</button>
      <button class="li" onclick="go('vanesa.prod')"><span class="crece">
        <b>LECHE ENTERA SANTA CLARA 1L (X12U)</b><span>$4.376 la unidad · 422 en stock</span></span>${ico('chevron', 18)}</button>
    </div>

    <div class="h2">De hoy</div>
    <div class="lista">
      <button class="li" onclick="go('vanesa.falta')"><span class="pt oro"></span><span class="crece">
        <b>2 cosas que te pidieron y no había</b><span>Anotadas para Celeste</span></span>
        ${ico('chevron', 18)}</button>
    </div>
  </div>`,
});

reg('vanesa.prod', {
  rol: 'vanesa', top: 'volver', vuelveA: 'vanesa.mostrador', titulo: 'Producto', barra: false,
  titulo_panel: 'Producto (versión mostrador)',
  nota: `<b>La misma ficha, otra cara.</b> Nahuel ve ubicación, lote y vencimiento;
    Vanesa ve precio, stock y qué tan viejo es el costo con el que se calculó.
    La pantalla de datos no se copia entre roles: se recorta a lo que ese oficio viene
    a hacer. Los 536 días de antigüedad del costo son el valor real del dataset
    (<code>antiguedad_costo_dias</code>) — no un adorno: es una alerta que ya existe
    en el motor y que en mobile aparece donde alguien puede hacer algo con ella.`,
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="card">
      <p class="tit">JAMON COCIDO GUARANI (HORMA)</p>
      <p class="meta"><span class="mono">Código 1269</span> · fiambres y quesos (balanza)</p>
      <p style="font-family:var(--display);font-size:38px;margin:14px 0 0;line-height:1">$26.836<span
        style="font-size:16px;font-family:var(--body);color:var(--tinta-suave)"> /kg</span></p>
      <div style="margin-top:12px">
        <div class="dato"><span>Hay</span><b>33,5 kg</b></div>
        <div class="dato"><span>Costo cargado hace</span><b style="color:var(--rojo)">536 días</b></div>
        <div class="dato"><span>Feteado deja</span><b>44,4% de margen</b></div>
      </div>
      <div class="card oro" style="margin-top:12px;padding:12px">
        <p class="txt fuerte" style="font-size:13px">Este precio se calculó sobre un costo
          de hace año y medio. Los precios de fiambres los revisás vos antes de aplicarlos:
          la regla de la casa lo dice con tu nombre.</p>
        <button class="btn sec" style="margin-top:10px">Avisar que hay que revisarlo</button>
      </div>
    </div>
    <button class="btn sec" onclick="go('vanesa.falta')">${ico('alerta', 20)} Se está por acabar</button>
  </div>`,
});

reg('vanesa.falta', {
  rol: 'vanesa', top: 'volver', vuelveA: 'vanesa.mostrador', titulo: 'No había', barra: false,
  titulo_panel: 'Me pidieron algo que no hay',
  nota: `<b>El aviso más barato y más valioso del mostrador:</b> la demanda que no se
    vendió no queda en ningún lado del ERP. Dos toques y va a Compras con el producto
    enganchado.
    <span class="toques">2 toques.</span>`,
  html: () => `<div class="cuerpo" style="padding-top:10px">
    <button class="btn pri grande" onclick="go('vanesa.mostrador')">${ico('escanear', 22)} Escanear lo que faltó</button>
    <div class="h2">Lo de hoy</div>
    <div class="lista">
      <div class="li"><span class="pt oro"></span><span class="crece">
        <b>YOGUR BEBIBLE CAMPO ALEGRE 900G</b><span>Lo pidieron 2 veces · Celeste lo vio</span></span></div>
      <div class="li"><span class="pt oro"></span><span class="crece">
        <b>SALAME MILAN LA RIBERA (PLANCHA)</b><span>Lo pidieron 1 vez</span></span></div>
    </div>
    <p class="fuente">${ico('info', 14)}<span>Cada uno queda a tu nombre. Cuando Celeste
      reponga, te avisa acá.</span></p>
  </div>`,
});

reg('vanesa.caja', {
  rol: 'vanesa', tab: 'caja', titulo: 'Rendir la caja',
  nota: `<b>Propuesta nueva.</b> No estaba en ninguna de las ocho pantallas y es lo
    último que hace Vanesa todos los días. Los cierres por local y por fecha ya existen
    (<code>core/mostrador.py</code> · 153 cierres sembrados); lo que falta es la pantalla
    donde se rinde y la diferencia queda explicada por quien la vio.
    <span class="toques">Rendir sin diferencia: 2 toques.</span>`,
  html: () => `<div class="cuerpo">
    <div class="card">
      <p class="tit chico">Casa Central · lunes 07/07</p>
      <div style="margin-top:12px">
        <div class="dato"><span>Vendido según el sistema</span><b>$1.274.416</b></div>
        <div class="dato"><span>Efectivo contado</span><b>$1.268.900</b></div>
        <div class="dato"><span>Diferencia</span><b style="color:var(--oro-tinta)">−$5.516</b></div>
      </div>
    </div>
    <div class="card oro">
      <p class="txt fuerte">Hay una diferencia. ¿Sabés de qué es?</p>
      <div class="par" style="margin-top:12px">
        <button class="btn sec">Vuelto mal dado</button>
        <button class="btn sec">Anulación</button>
      </div>
      <button class="btn sec" style="margin-top:8px">No sé de qué es</button>
    </div>
    <button class="btn pri grande" onclick="go('vanesa.mostrador')">Rendir así</button>
    <p class="fuente">${ico('info', 14)}<span>La explicación viaja con el cierre. Marta
      la ve mañana con tu nombre, en vez de llamarte a preguntar.</span></p>
  </div>`,
});

reg('vanesa.avisos', {
  rol: 'vanesa', top: 'volver', vuelveA: 'vanesa.mostrador', titulo: 'Avisos', barra: false, oculta: true,
  html: () => `<div class="cuerpo" style="padding-top:12px"><div class="lista">
    <div class="li"><span class="pt salvia"></span><span class="crece">
      <b>Celeste repuso el yogur que pediste</b><span>Entra el 9</span></span></div></div></div>`,
});

reg('vanesa.angela', {
  rol: 'vanesa', tab: 'angela', titulo: 'Ángela (chat)',
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="burb mia">¿El salame tiene el precio actualizado?</div>
    <div class="burb ella">Sí, se actualizó el 04/07 con la última lista de La Ribera.</div>
    <div class="lista">
      <div class="li"><span class="crece"><b>¿Cambió algún precio hoy?</b></span>${ico('chevron', 18)}</div>
      <div class="li"><span class="crece"><b>¿Tenemos stock de esto?</b></span>${ico('chevron', 18)}</div>
    </div>
  </div>`,
});

/* ══ NORMA · Encargada, Sucursal Norte ═══════════════════════════════════ */

hoja('norma', {
  titulo: 'Registrar', sub: 'Lo del local.',
  vozA: 'norma.local',
  tiles: [
    ['caja', ['Me falta stock', 'Pedirle al depósito central'], 'norma.repo', 'destaca'],
    ['alerta', ['Novedad del día', 'Algo que pasó en el local'], 'norma.local', 'alerta'],
    ['plata', ['Cerrar la caja', 'Cierre de sucursal'], 'norma.caja'],
  ],
});

reg('norma.local', {
  rol: 'norma', tab: 'local', titulo: 'Mi local',
  nota: `Norma es encargada: su pantalla es una <b>cola de decisiones chicas</b> de su
    local, no un dashboard de la empresa. Tiene desktop, así que lo que pide ancho
    (comparativos, evolución) se queda allá a propósito.`,
  html: () => `<div class="cuerpo">
    <div class="h2">Hoy en Sucursal Norte</div>
    <div class="card">
      <div class="dato"><span>Vendido hasta ahora</span><b>$598.665</b></div>
      <div class="dato"><span>Contra el lunes pasado</span><b style="color:var(--salvia)">+6%</b></div>
    </div>
    <div class="h2">Para resolver</div>
    <div class="lista">
      <button class="li" onclick="go('norma.repo')"><span class="pt oro"></span><span class="crece">
        <b>3 productos por quebrar</b><span>Yogur, manteca y leche · se venden todos los días</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li" onclick="go('norma.caja')"><span class="pt oro"></span><span class="crece">
        <b>La caja de ayer quedó sin cerrar</b><span>Diferencia de $3.200</span></span>
        ${ico('chevron', 18)}</button>
    </div>
    ${novedadTuya('Tu pedido de reposición de yogur salió: llega mañana con el Camión 2.',
      'Ramón lo despachó', 'norma.local')}
  </div>`,
});

reg('norma.repo', {
  rol: 'norma', top: 'volver', vuelveA: 'norma.local', titulo: 'Pedir reposición', barra: false,
  titulo_panel: 'Pedir reposición al depósito central',
  nota: `El pedido de reposición ya existe en el motor (<code>piso.reportar</code>, tipo
    <code>reposicion</code>). Lo que falta es que Norma vea cuándo salió y cuándo llega:
    hoy el reporte entra y no vuelve.
    <span class="toques">1 toque por renglón + mandar.</span>`,
  html: () => `<div class="cuerpo" style="padding-top:10px">
    <div class="lista">
      <button class="li"><span class="pt rojo"></span><span class="crece">
        <b>YOGUR BEBIBLE CAMPO ALEGRE 900G</b><span>Quedan 6 · vendés 14 por día</span></span>
        <span class="rot rojo">+24</span></button>
      <button class="li"><span class="pt oro"></span><span class="crece">
        <b>MANTECA CAMPO ALEGRE 200G</b><span>Quedan 11 · vendés 5 por día</span></span>
        ${ico('mas', 18)}</button>
      <button class="li"><span class="pt oro"></span><span class="crece">
        <b>LECHE ENTERA CAMPO ALEGRE 1L</b><span>Quedan 18 · vendés 9 por día</span></span>
        ${ico('mas', 18)}</button>
    </div>
    <button class="btn pri" style="margin-top:12px" onclick="go('norma.local')">Pedírselo a Ramón</button>
  </div>`,
});

reg('norma.caja', {
  rol: 'norma', tab: 'caja', titulo: 'Caja de la sucursal',
  html: () => `<div class="cuerpo">
    <div class="card">
      <p class="tit chico">Sucursal Norte · domingo 06/07</p>
      <div style="margin-top:12px">
        <div class="dato"><span>Sistema</span><b>$541.300</b></div>
        <div class="dato"><span>Contado</span><b>$538.100</b></div>
        <div class="dato"><span>Diferencia</span><b style="color:var(--oro-tinta)">−$3.200</b></div>
      </div>
    </div>
    <button class="btn pri grande" onclick="go('norma.local')">Cerrar con esta diferencia</button>
    <button class="btn sec" onclick="go('norma.local')">Explicar la diferencia</button>
  </div>`,
});

reg('norma.avisos', {
  rol: 'norma', top: 'volver', vuelveA: 'norma.local', titulo: 'Avisos', barra: false, oculta: true,
  html: () => `<div class="cuerpo" style="padding-top:12px"><div class="lista">
    <div class="li"><span class="pt salvia"></span><span class="crece">
      <b>Ramón despachó tu reposición</b><span>Llega mañana</span></span></div></div></div>`,
});

reg('norma.angela', {
  rol: 'norma', tab: 'angela', titulo: 'Ángela (chat)',
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="burb ella">La sucursal va +6% contra el lunes pasado.</div>
    <div class="lista">
      <div class="li"><span class="crece"><b>¿Cuánto vendió el local hoy?</b></span>${ico('chevron', 18)}</div>
      <div class="li"><span class="crece"><b>¿Qué me falta reponer?</b></span>${ico('chevron', 18)}</div>
    </div>
  </div>`,
});

/* ══ MARTA · Administración ══════════════════════════════════════════════ */

hoja('marta', {
  titulo: 'Cargar', sub: 'Lo que entra a la oficina.',
  vozA: 'marta.pendientes',
  tiles: [
    ['camara', ['Foto de un comprobante', 'Factura, recibo, remito'], 'marta.pendientes', 'destaca'],
    ['plata', ['Registrar un pago', 'Aplicarlo a una cuenta'], 'marta.pendientes'],
    ['doc', ['Subir un archivo', 'Del mail o del escritorio'], 'marta.docs'],
  ],
});

reg('marta.pendientes', {
  rol: 'marta', tab: 'pendientes', titulo: 'Pendientes', campana: true,
  nota: `Marta trabaja una <b>cola</b>: lo que entró de afuera y espera que ella lo
    revise. En mobile eso es lo único que viaja; los comparativos y la evolución se
    quedan en desktop, que es donde los mira.`,
  html: () => `<div class="cuerpo">
    <div class="h2">Esperan que los revises</div>
    <div class="lista">
      <button class="li"><span class="pt rojo"></span><span class="crece">
        <b>Factura de Campo Alegre</b><span>Vino por el total y entregaron la mitad · no pagar</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li"><span class="pt oro"></span><span class="crece">
        <b>Lista de precios nueva de Guaraní</b><span>Rige desde el 15 · suben gaseosas</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li"><span class="pt oro"></span><span class="crece">
        <b>Cierre de Vanesa con diferencia</b><span>−$5.516 · explicó «vuelto mal dado»</span></span>
        ${ico('chevron', 18)}</button>
    </div>
    <div class="h2">Cobranza</div>
    <div class="lista">
      <button class="li"><span class="pt rojo"></span><span class="crece">
        <b>Despensa Doña Elsa · 66 días</b><span>Pasó el plazo de la casa (45)</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li"><span class="pt rojo"></span><span class="crece">
        <b>Autoservicio 9 de Julio · 58 días</b><span>Pidió hablar con Aldo</span></span>
        ${ico('chevron', 18)}</button>
    </div>
  </div>`,
});

reg('marta.docs', {
  rol: 'marta', tab: 'docs', titulo: 'Documentos',
  nota: `La carpeta de documentos con el patrón campo / valor / fuente / estado ya
    existe (<code>core/carpeta.py</code>). En mobile se queda <b>tal cual</b>: es una de
    las pocas pantallas de datos que no cambia de forma, porque ya es una cola de
    revisión y no una tabla.`,
  html: () => `<div class="cuerpo">
    <div class="lista">
      <button class="li"><span class="pt oro"></span><span class="crece">
        <b>Factura A-0001-00043821</b><span>Lácteos Campo Alegre · 3 campos por confirmar</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li"><span class="pt salvia"></span><span class="crece">
        <b>Remito OC-2026-0812</b><span>Guaraní · confirmado</span></span>${ico('chevron', 18)}</button>
    </div>
  </div>`,
});

reg('marta.avisos', {
  rol: 'marta', top: 'volver', vuelveA: 'marta.pendientes', titulo: 'Avisos', barra: false, oculta: true,
  html: () => `<div class="cuerpo" style="padding-top:12px"><div class="lista">
    <div class="li"><span class="pt oro"></span><span class="crece">
      <b>Vanesa explicó la diferencia de caja</b><span>Hoy 20:10</span></span></div></div></div>`,
});

reg('marta.angela', {
  rol: 'marta', tab: 'angela', titulo: 'Ángela (chat)',
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="burb ella">Tenés 3 cosas en la cola y 2 clientes pasados de plazo.</div>
    <div class="lista">
      <div class="li"><span class="crece"><b>¿Cuánto entró esta semana?</b></span>${ico('chevron', 18)}</div>
      <div class="li"><span class="crece"><b>¿Quién debe y hace cuánto?</b></span>${ico('chevron', 18)}</div>
    </div>
  </div>`,
});

/* ══ CELESTE · Compras. El otro extremo del aviso de Nahuel. ═════════════ */

hoja('celeste', {
  titulo: 'Cargar', sub: 'Proveedores.',
  vozA: 'celeste.compras',
  tiles: [
    ['camara', ['Foto de una lista', 'De precios o un remito'], 'celeste.compras', 'destaca'],
    ['alerta', ['Anotar algo de un proveedor', 'Lo que te dijeron'], 'celeste.compras'],
    ['doc', ['Subir un archivo', 'Del mail'], 'celeste.compras'],
  ],
});

reg('celeste.compras', {
  rol: 'celeste', tab: 'compras', titulo: 'Compras', campana: true,
  nota: `<b>Celeste es la destinataria de la mitad de los avisos del piso.</b> Su
    pantalla es la cola de lo que le dirigieron, ordenada por plata, no por fecha.
    El primer renglón es el aviso que dejó Nahuel hace 40 minutos.`,
  html: () => `<div class="cuerpo">
    <div class="h2">Te lo mandaron a vos</div>
    <div class="card rojo">
      <div class="fila"><span class="icoc rojo">${ico('alerta', 21)}</span><div class="crece">
        <p class="tit chico">Nahuel · 8 cajas rotas</p>
        <p class="txt fuerte">MANTECA SANTA CLARA 200G · Lácteos Campo Alegre</p>
        <p class="meta"><span class="mono">$53.323</span> · hace 40 min · con foto y lote</p>
      </div></div>
      <button class="btn pri" style="margin-top:12px" onclick="go('celeste.reclamo')">Armar el reclamo</button>
    </div>
    <div class="lista">
      <button class="li"><span class="pt oro"></span><span class="crece">
        <b>Brian: faltaron 2 de manteca para el P-4416</b><span>Hay 10 en la OC abierta</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li"><span class="pt oro"></span><span class="crece">
        <b>Vanesa: pidieron yogur 2 veces y no había</b><span>Mostrador · hoy</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li"><span class="pt oro"></span><span class="crece">
        <b>Ramón: la cámara 2 está llena</b><span>Y La Ribera confirmó fiambres para el 9</span></span>
        ${ico('chevron', 18)}</button>
    </div>
  </div>`,
});

reg('celeste.reclamo', {
  rol: 'celeste', top: 'volver', vuelveA: 'celeste.compras', titulo: 'Reclamo armado', barra: false,
  titulo_panel: 'El reclamo, ya armado (propone → aprueba)',
  nota: `<b>La app llega hasta acá y no un paso más.</b> El reclamo queda armado con lo
    que este proveedor exige; <b>mandarlo lo decide una persona</b>, y del otro lado hay
    un tercero y plata. Es el mismo límite que <code>core/ordenes.py</code> ya pone en
    las órdenes de compra: aprobarla no la manda, la deja lista para salir.`,
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="card">
      <p class="tit chico">Reclamo a Lácteos Campo Alegre</p>
      <p class="meta"><span class="mono">OC-2026-0847</span> · <span class="mono">$53.323</span></p>
      <div style="margin-top:12px">
        <div class="dato"><span>Producto</span><b>MANTECA SANTA CLARA 200G</b></div>
        <div class="dato"><span>Cantidad</span><b>8 · rotas</b></div>
        <div class="dato"><span>Lote</span><b>L-2026-368</b></div>
        <div class="dato"><span>Lo reportó</span><b>Nahuel · 09:14</b></div>
      </div>
      <div class="evidencia">foto de Nahuel</div>
    </div>

    <div class="card angela">
      <div class="fila"><span class="icoc angela">${ico('llave', 21)}</span><div class="crece">
        <p class="txt fuerte">Está completo según lo que pide Campo Alegre: foto, lote y remito.
          Va por mail y tenés 5 días.</p>
        <p class="meta">Regla de la casa · aplicada 6 veces</p></div></div>
    </div>

    <div class="card oro">
      <p class="txt fuerte">Y hay algo más de este proveedor</p>
      <p class="txt">Ramón anotó el 02/07 que ya habían entregado incompleto, y Marta
        frenó la factura porque vino por el total. Conviene reclamar las dos cosas juntas.</p>
      <button class="btn sec" style="margin-top:10px">Sumar el faltante de yogur</button>
    </div>

    <button class="btn pri grande" onclick="go('celeste.compras')">Mandárselo a Aldo para que lo apruebe</button>
    <p class="fuente">${ico('info', 14)}<span>Nahuel ve en su pantalla que se lo mandaste,
      sin preguntar por WhatsApp.</span></p>
  </div>`,
});

reg('celeste.prov', {
  rol: 'celeste', tab: 'prov', titulo: 'Proveedores',
  nota: `<b>La ficha del proveedor, no la grilla.</b> Y con lo que ninguna grilla tiene:
    qué exige para un reclamo. Esa pieza vive en <code>core/conocimiento.py</code> como
    un <code>protocolo</code> de ámbito <code>proveedor</code> — la misma forma que
    «A Doña Elsa tolerale hasta 45 días».`,
  html: () => `<div class="cuerpo">
    <div class="card">
      <p class="tit chico">Lácteos Campo Alegre</p>
      <p class="meta">Repone en 4 días · sube la lista todos los meses</p>
      <div class="h2" style="margin-top:14px">Qué pide para un reclamo</div>
      <div class="req listo">${ico('camara', 20)}<span class="crece"><b>Foto del producto</b>
        <span>Sin foto no lo toma</span></span></div>
      <div class="req listo">${ico('doc', 20)}<span class="crece"><b>Lote y número de remito</b>
        <span>Los saco yo del sistema</span></span></div>
      <div class="req listo">${ico('reloj', 20)}<span class="crece"><b>Por mail, dentro de 5 días</b>
        <span>Después no lo acepta</span></span></div>
      <p class="fuente">${ico('info', 14)}<span>Lo enseñó Aldo el 20/06 · aplicado 6 veces ·
        se puede pausar o corregir como cualquier regla de la casa.</span></p>
    </div>

    <div class="card oro">
      <p class="txt fuerte">Golosinas Costa Dulce · todavía no sé qué pide</p>
      <p class="txt">Se aprende con el primer reclamo: si vuelve rechazado por falta de algo,
        eso queda anotado y te lo propongo para confirmar.</p>
    </div>

    <div class="lista">
      <button class="li"><span class="pt salvia"></span><span class="crece">
        <b>Frigorífico La Ribera</b><span>Repone en 3 días · con descripción alcanza</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li"><span class="pt gris"></span><span class="crece">
        <b>Distrib. Mayorista Guaraní</b><span>Repone en 12 días · consolida pedidos</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li"><span class="pt gris"></span><span class="crece">
        <b>Limpieza Total SA</b><span>Repone en 21 días · el más lento</span></span>
        ${ico('chevron', 18)}</button>
    </div>
  </div>`,
});

reg('celeste.avisos', {
  rol: 'celeste', top: 'volver', vuelveA: 'celeste.compras', titulo: 'Avisos', barra: false, oculta: true,
  html: () => `<div class="cuerpo" style="padding-top:12px"><div class="lista">
    <div class="li"><span class="pt rojo"></span><span class="crece">
      <b>Nahuel te mandó un problema de recepción</b><span>Hace 40 min</span></span></div>
    <div class="li"><span class="pt oro"></span><span class="crece">
      <b>Brian: faltó stock para armar el P-4416</b><span>Hace 40 min</span></span></div>
  </div></div>`,
});

reg('celeste.angela', {
  rol: 'celeste', tab: 'angela', titulo: 'Ángela (chat)',
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="burb mia">¿Conviene la oferta de salame de La Ribera?</div>
    <div class="burb ella">18% de descuento sobre 25 planchas, vence el 17/07. El lote
      vence el 15/10 y vendés 8 planchas por mes: te quedarían 17 sin vender.</div>
    <div class="lista">
      <div class="li"><span class="crece"><b>¿Qué está por quebrar?</b></span>${ico('chevron', 18)}</div>
      <div class="li"><span class="crece"><b>¿Cuánto vendemos de esto por mes?</b></span>${ico('chevron', 18)}</div>
    </div>
  </div>`,
});

/* ══ ALDO · Dueño. Hoy en mobile aterriza en un chat vacío. ══════════════ */

hoja('aldo', {
  titulo: 'Cargar', sub: 'Lo que anotás vos.',
  vozA: 'aldo.decidir',
  tiles: [
    ['micro', ['Anotar una regla', 'Así se hacen las cosas acá'], 'aldo.regla', 'destaca ang'],
    ['camara', ['Foto', 'De lo que sea'], 'aldo.decidir'],
    ['persona', ['Pedirle algo a alguien', 'Queda a su nombre'], 'aldo.decidir'],
  ],
});

reg('aldo.decidir', {
  rol: 'aldo', tab: 'decidir', titulo: 'Decidir', campana: true,
  nota: `<b>Hoy el dueño en mobile aterriza en el chat vacío de Ángela</b>
    (<code>MobileApp.jsx:81</code> · <code>defaultView = piso ? 'mi_dia' : 'angela'</code>).
    Su vista-herramienta es su cola de decisiones, en el mismo formato que la de
    cualquier otro: lo que espera un sí, ordenado por plata. La regla del producto
    dice que <code>es_admin</code> es un rol con cola de trabajo, no una excepción.`,
  html: () => `<div class="cuerpo">
    <div class="h2">Esperan tu sí</div>
    <div class="card oro">
      <div class="fila"><span class="icoc oro">${ico('camion', 21)}</span><div class="crece">
        <p class="tit chico">Reclamo a Lácteos Campo Alegre</p>
        <p class="txt fuerte">$53.323 · 8 cajas de manteca rotas</p>
        <p class="meta">Lo reportó Nahuel · lo armó Celeste · con foto, lote y remito</p>
      </div></div>
      <div class="par" style="margin-top:12px">
        <button class="btn pri" onclick="go('aldo.aprobar')">Ver y aprobar</button>
        <button class="btn sec">Después</button>
      </div>
    </div>
    <div class="lista">
      <button class="li"><span class="pt oro"></span><span class="crece">
        <b>Precio especial para Proveeduría La Rural</b><span>Diego · compra gaseosa en otro lado</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li"><span class="pt oro"></span><span class="crece">
        <b>9 de Julio quiere hablar con vos</b><span>Walter · debe $42.000.000 hace 58 días</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li"><span class="pt oro"></span><span class="crece">
        <b>Orden de compra por quiebre de yogur</b><span>Armada · esperando tu OK</span></span>
        ${ico('chevron', 18)}</button>
    </div>

    <div class="h2">Tu equipo cerró hoy</div>
    <div class="card plano">
      <ul class="tl">
        <li><b>Nahuel corrigió 2 balanzas</b><span>09:40</span></li>
        <li><b>Tomás contó 3 ubicaciones</b><span>14:20 · 1 diferencia</span></li>
        <li><b>Walter entregó 6 de 9</b><span>y devolvió 2 yogures golpeados</span></li>
      </ul>
      <p class="fuente">${ico('info', 14)}<span>Sale de la auditoría real, atribuida a cada
        persona. Ninguno de esos números es un promedio.</span></p>
    </div>
  </div>`,
});

reg('aldo.aprobar', {
  rol: 'aldo', top: 'volver', vuelveA: 'aldo.decidir', titulo: 'Aprobar el reclamo', barra: false,
  titulo_panel: 'El sí del dueño (y lo que pasa después)',
  nota: `<b>Aprobar tiene que hacer algo.</b> Un botón que setea estado local y muestra
    un toast es mentira sobre la promesa del producto. Acá el sí produce un registro
    real, atribuido, y —lo que hoy falta— <b>dispara la notificación a Nahuel</b>.
    <span class="toques">1 toque.</span>`,
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="card">
      <p class="tit chico">Lácteos Campo Alegre · $53.323</p>
      <div style="margin-top:10px">
        <div class="dato"><span>8 un.</span><b>MANTECA SANTA CLARA 200G</b></div>
        <div class="dato"><span>Lote</span><b>L-2026-368</b></div>
        <div class="dato"><span>Remito</span><b>OC-2026-0847</b></div>
      </div>
      <div class="evidencia">foto de Nahuel · hoy 09:14</div>
      <p class="fuente">${ico('info', 14)}<span>$53.323 = costo del catálogo ($6.665,39) × 8.
        No es una estimación.</span></p>
    </div>
    <button class="btn pri grande" onclick="go('aldo.decidir')">Aprobar y que salga</button>
    <button class="btn sec" onclick="go('aldo.decidir')">Cambiar algo antes</button>
    <p class="fuente">${ico('info', 14)}<span>Al aprobar: se registra el reclamo, queda a tu
      nombre en la auditoría, y <b>Nahuel y Celeste reciben el aviso</b>.</span></p>
  </div>`,
});

reg('aldo.regla', {
  rol: 'aldo', top: 'volver', vuelveA: 'aldo.decidir', titulo: 'Anotar una regla', barra: false,
  titulo_panel: 'Cómo se aprende lo que pide un proveedor',
  nota: `<b>La respuesta a «dónde vive ese conocimiento»: en <code>core/conocimiento.py</code>,
    sin estructura nueva.</b> Es un <code>protocolo</code> de ámbito <code>proveedor</code>,
    con los requisitos en <code>params</code> — exactamente como <code>k09</code> ya guarda
    <code>{umbral_suba_pct: 15}</code>. Lo único que hace falta agregar es un valor al
    catálogo de <code>EFECTOS</code>. Nace <code>pendiente</code> y no aplica hasta que
    alguien la aprueba: eso ya funciona así.`,
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="card angela">
      <div class="fila"><span class="icoc angela">${ico('angela', 21)}</span><div class="crece">
        <p class="txt fuerte">El reclamo a Costa Dulce volvió rechazado: pedían el número
          de lote y no se lo mandamos.</p>
        <p class="txt">¿Anoto que Costa Dulce siempre pide el lote?</p></div></div>
      <div class="par" style="margin-top:12px">
        <button class="btn ang" onclick="go('aldo.decidir')">Sí, anotalo</button>
        <button class="btn sec" onclick="go('aldo.decidir')">No</button>
      </div>
    </div>

    <div class="h2">Cómo quedaría</div>
    <div class="card plano">
      <div class="dato"><span>Tipo</span><b>protocolo</b></div>
      <div class="dato"><span>Ámbito</span><b>proveedor</b></div>
      <div class="dato"><span>Entidad</span><b>Golosinas Costa Dulce SRL</b></div>
      <div class="dato"><span>Nodo</span><b>proveedores</b></div>
      <div class="dato"><span>Pide</span><b>lote · foto</b></div>
      <div class="dato"><span>Salió de</span><b>reclamo rechazado</b></div>
    </div>

    <div class="h2">Las otras tres formas de aprenderlo</div>
    <div class="lista">
      <div class="li"><span class="pt gris"></span><span class="crece">
        <b>La primera vez, preguntando</b><span>Ángela pregunta tres cosas cuando aprobás el primer reclamo</span></span></div>
      <div class="li"><span class="pt gris"></span><span class="crece">
        <b>Mirando lo que hacés</b><span>Si sumás la misma foto tres veces antes de mandar</span></span></div>
      <div class="li"><span class="pt gris"></span><span class="crece">
        <b>Porque lo anotás vos</b><span>Hablando, desde este mismo botón</span></span></div>
    </div>
    <p class="fuente">${ico('info', 14)}<span>Las cuatro declaran de dónde salieron, como
      las 22 reglas que ya hay (97 aplicaciones).</span></p>
  </div>`,
});

reg('aldo.negocio', {
  rol: 'aldo', tab: 'negocio', titulo: 'Negocio',
  nota: `Lo que en desktop son ocho secciones acá es <b>una sola lectura</b>, y cada
    número abre a las filas reales. Es evidencia, no destino: se llega desde una
    decisión, no al revés.`,
  html: () => `<div class="cuerpo">
    <div class="card">
      <p class="h2" style="margin-top:0">Lo que está trabado</p>
      <div class="dato"><span>Por cobrar</span><b>$311.400.000</b></div>
      <div class="dato"><span>Pasados de 45 días</span><b style="color:var(--rojo)">3 · $85.700.000</b></div>
      <div class="dato"><span>Vencen en 15 días</span><b>8 lotes</b></div>
    </div>
    <div class="lista">
      <button class="li"><span class="pt rojo"></span><span class="crece">
        <b>El mapa de la operación</b><span>14 de 31 avisos no llegaron a tu sistema de gestión</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li"><span class="pt gris"></span><span class="crece">
        <b>Reglas de tu casa</b><span>22 reglas · 97 aplicaciones</span></span>${ico('chevron', 18)}</button>
      <button class="li"><span class="pt gris"></span><span class="crece">
        <b>Objetivos</b><span>7 medidos contra datos reales</span></span>${ico('chevron', 18)}</button>
    </div>
    <p class="fuente">${ico('info', 14)}<span>El «14 de 31» sale de
      <code>canales_de_entrada()</code>: whatsapp 7 + email 4 + foto 3, sobre 31 notas.
      Con la nota dirigida, ese número es el que tiene que bajar.</span></p>
  </div>`,
});

reg('aldo.avisos', {
  rol: 'aldo', top: 'volver', vuelveA: 'aldo.decidir', titulo: 'Avisos', barra: false, oculta: true,
  html: () => `<div class="cuerpo" style="padding-top:12px"><div class="lista">
    <div class="li"><span class="pt oro"></span><span class="crece">
      <b>Celeste te mandó un reclamo para aprobar</b><span>Campo Alegre · $53.323</span></span></div>
    <div class="li"><span class="pt oro"></span><span class="crece">
      <b>Walter: 9 de Julio quiere hablar con vos</b><span>Hace 4 días</span></span></div>
  </div></div>`,
});

reg('aldo.angela', {
  rol: 'aldo', tab: 'angela', titulo: 'Ángela (chat)',
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="burb mia">¿Cuánta plata tengo parada?</div>
    <div class="burb ella">$311.400.000 por cobrar. De eso, $85.700.000 son de tres
      clientes que pasaron los 45 días: 9 de Julio, San Martín y Doña Elsa.</div>
    <div class="lista">
      <div class="li"><span class="crece"><b>¿Qué decisiones tengo pendientes?</b></span>${ico('chevron', 18)}</div>
      <div class="li"><span class="crece"><b>¿Qué resolvió mi equipo esta semana?</b></span>${ico('chevron', 18)}</div>
    </div>
  </div>`,
});
