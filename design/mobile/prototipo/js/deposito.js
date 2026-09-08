/* deposito.js — los cinco oficios que hoy comparten UNA sola ficha de rol.
   lib/roles.js:21 usa /dep[oó]sito/i y con eso Ramón, Nahuel, Tomás, Brian y
   Kevin ven las mismas tres acciones. Acá se parten en cinco vistas distintas.
   Todos los datos salen del dataset del demo (hoy = 2026-07-07). */

/* Bloque reutilizable: EL CÍRCULO CERRADO (P3).
   Es lo primero de la pantalla cuando hay novedad, y desaparece cuando no la
   hay. No es una pestaña: si fuera pestaña, estaría vacía casi siempre. */
function novedadTuya(txt, cuando, a) {
  return `<div class="card salvia">
    <div class="fila">
      <span class="icoc salvia">${ico('tilde', 21)}</span>
      <div class="crece">
        <p class="tit chico">Lo que reportaste sirvió</p>
        <p class="txt fuerte">${txt}</p>
        <p class="meta">${cuando}</p>
      </div>
    </div>
    <button class="btn sec" style="margin-top:12px" onclick="go('${a}')">Ver cómo terminó</button>
  </div>`;
}

function sinSenal() {
  return `<span class="chip-off">${ico('nube', 14)} Sin señal · se manda solo</span>`;
}

/* ══ NAHUEL · Depósito / recepción ═══════════════════════════════════════ */

hoja('nahuel', {
  titulo: 'Cargar', sub: 'Lo que hacés cuando baja un camión.',
  vozA: 'nahuel.voz',
  tiles: [
    ['escanear', ['Escanear', 'Remito o producto'], 'nahuel.esc', 'destaca'],
    ['alerta', ['Hay un problema', 'De menos, roto, vencido'], 'nahuel.r1', 'alerta'],
    ['camara', ['Foto', 'Dejar constancia'], 'nahuel.esc'],
    ['tilde', ['Terminé de recibir', 'Cerrar la descarga'], 'nahuel.recepcion'],
  ],
});

reg('nahuel.dia', {
  rol: 'nahuel', tab: 'dia', titulo: 'Mi día', campana: true,
  nota: `<b>Lo primero que se ve es el círculo cerrado</b>, no un saludo ni el clima.
    El bloque verde sale de un endpoint que HOY EXISTE y ninguna pantalla llama
    (<code>api.piso.reportes</code>, <code>lib/api.js:277</code>).
    <span class="toques">Cerrar la tarea de balanza: 2 toques.</span>`,
  html: () => `<div class="cuerpo">
    ${novedadTuya(
      'Tus 8 cajas de manteca rotas se reclamaron a Lácteos Campo Alegre.',
      'Aldo lo aprobó hoy 11:03', 'nahuel.rep1')}

    <div class="h2">Lo que llega hoy</div>
    <div class="card">
      <div class="fila">
        <span class="icoc oro">${ico('caja', 21)}</span>
        <div class="crece">
          <p class="tit chico">Lácteos Campo Alegre</p>
          <p class="txt">OC-2026-0847 · 5 productos · 165 unidades</p>
          <p class="meta"><span class="rot oro">Descargando</span>
            <span class="mono">3 de 5 controlados</span></p>
        </div>
      </div>
      <div class="progreso"><i style="width:60%"></i></div>
      <button class="btn pri" style="margin-top:12px" onclick="go('nahuel.recepcion')">Seguir controlando</button>
    </div>

    <div class="h2">Tu trabajo</div>
    <div class="lista">
      <button class="li" onclick="go('nahuel.balanza')">
        <span class="pt oro"></span>
        <span class="crece"><b>2 balanzas descalibradas</b><span>Se corrige desde acá</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li" onclick="go('nahuel.angela')">
        <span class="pt gris"></span>
        <span class="crece"><b>Cámara de frío 2 al 100%</b><span>Ramón y vos ya avisaron · 3 avisos</span></span>
        ${ico('chevron', 18)}</button>
    </div>

    <div class="h2">Lo que reportaste</div>
    <div class="lista">
      <button class="li" onclick="go('nahuel.rep1')">
        <span class="pt salvia"></span>
        <span class="crece"><b>8 cajas rotas · MANTECA SANTA CLARA 200G</b>
          <span>Reclamado y enviado · hoy 11:03</span></span>${ico('chevron', 18)}</button>
      <button class="li" onclick="go('nahuel.rep1')">
        <span class="pt oro"></span>
        <span class="crece"><b>Faltaron 2 pallets · yogur</b>
          <span>Visto por Celeste · esperando decisión</span></span>${ico('chevron', 18)}</button>
    </div>
  </div>`,
});

reg('nahuel.rep1', {
  rol: 'nahuel', top: 'volver', vuelveA: 'nahuel.dia', titulo: 'Tu reporte', barra: false,
  titulo_panel: 'Un reporte tuyo, de punta a punta',
  nota: `<b>Ésta es la pantalla que decide si la persona vuelve a abrir la app.</b>
    Hoy no existe: <code>piso.resolver</code> (<code>core/piso.py:174</code>) audita
    y no llama a <code>notificaciones.emitir</code>, así que el que reportó nunca
    se entera. El último renglón —la nota de crédito— es el único que le importa a Nahuel.`,
  html: () => `<div class="cuerpo">
    <div class="card">
      <p class="tit">8 cajas rotas</p>
      <p class="txt fuerte">MANTECA SANTA CLARA 200G (X30U)</p>
      <p class="meta"><span class="mono">Lote L-2026-368</span> · <span class="mono">OC-2026-0847</span></p>
      <div class="evidencia">foto que sacaste · hoy 09:14</div>
    </div>

    <div class="h2">Qué pasó con esto</div>
    <div class="card">
      <ul class="tl">
        <li><b>Lo reportaste</b><span>Hoy 09:14 · desde Recepción</span></li>
        <li><b>Celeste lo vio</b><span>Hoy 09:31</span></li>
        <li><b>Se armó el reclamo a Lácteos Campo Alegre</b>
            <span>Con tu foto, el lote y el remito · $53.323</span></li>
        <li><b>Aldo lo aprobó y salió</b><span>Hoy 11:03 · por mail, como pide el proveedor</span></li>
        <li class="espera"><b>Esperando la nota de crédito</b>
            <span>Campo Alegre contesta en 5 días hábiles · te aviso</span></li>
      </ul>
      <p class="fuente">${ico('info', 14)}
        <span>El monto sale del costo del catálogo × 8, no de una estimación.</span></p>
    </div>
  </div>`,
});

reg('nahuel.recepcion', {
  rol: 'nahuel', tab: 'recepcion', titulo: 'Recepción (control contra remito)',
  encabezado: 'OC-2026-0847', subencabezado: 'Lácteos Campo Alegre · desde 08:40',
  nota: `Control renglón por renglón, con lo pedido y lo que efectivamente bajó.
    Sale de <code>apartados.ordenes_compra</code> cruzado con
    <code>apartados.recepciones</code>. El renglón en rojo ya tiene el reclamo armado.
    <span class="toques">Confirmar un renglón que vino completo: 1 toque.</span>`,
  html: () => `<div class="cuerpo">
    <div class="lista" style="margin-top:8px">
      <div class="li"><span class="pt salvia"></span><span class="crece">
        <b>LECHE ENTERA CAMPO ALEGRE 1L (X12U)</b><span>Pedidas 60 · bajaron 60</span></span>
        <span class="rot salvia">OK</span></div>
      <div class="li"><span class="pt salvia"></span><span class="crece">
        <b>LECHE ENTERA TIERRA ROJA 1L (X12U)</b><span>Pedidas 40 · bajaron 40</span></span>
        <span class="rot salvia">OK</span></div>
      <button class="li" onclick="go('nahuel.rep1')"><span class="pt rojo"></span><span class="crece">
        <b>MANTECA SANTA CLARA 200G (X30U)</b><span>Pedidas 25 · bajaron 25 · <b style="color:var(--rojo)">8 rotas</b></span></span>
        <span class="rot rojo">Reclamado</span></button>
      <button class="li" onclick="go('nahuel.r1')"><span class="pt gris"></span><span class="crece">
        <b>MANTECA CAMPO ALEGRE 200G (X30U)</b><span>Pedidas 10 · sin controlar</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li" onclick="go('nahuel.r1')"><span class="pt gris"></span><span class="crece">
        <b>CREMA DE LECHE EL PARANA 360G (X12U)</b><span>Pedidas 30 · sin controlar</span></span>
        ${ico('chevron', 18)}</button>
    </div>

    <div class="card angela" style="margin-top:14px">
      <div class="fila"><span class="icoc angela">${ico('angela', 21)}</span><div class="crece">
        <p class="txt fuerte">Ramón anotó el 2 de julio que Campo Alegre ya había entregado
          incompleto. Si vuelve a faltar algo, conviene dejarlo asentado.</p>
        <p class="meta">Nota de voz de Ramón · 02/07</p></div></div>
    </div>

    <button class="btn pri" style="margin-top:14px" onclick="go('nahuel.esc')">
      ${ico('escanear', 20)} Escanear el próximo</button>
  </div>`,
});

reg('nahuel.esc', {
  rol: 'nahuel', top: 'volver', vuelveA: 'nahuel.recepcion', titulo: 'Escanear', barra: false,
  nota: `El escaneo es la ENTRADA a la ficha del producto, no una búsqueda. Nadie
    scrollea 430 filas con guantes: se apunta y listo.
    <span class="toques">Producto en pantalla: 1 toque (abrir) + apuntar.</span>`,
  html: () => `<div class="camara">
      <div class="retic"><i></i><i></i><i></i><i></i></div>
      <p>Apuntá al código de barras o al remito</p>
    </div>
    <div class="cuerpo" style="padding-top:16px">
      <button class="btn pri grande" onclick="go('nahuel.prod')">Simular lectura</button>
      <button class="voz" onclick="go('nahuel.voz')">${ico('micro', 22)}
        <span><b>No puedo escanear, prefiero decirlo</b><span>El código no siempre se lee: con el sol o con la caja mojada</span></span></button>
    </div>`,
});

reg('nahuel.prod', {
  rol: 'nahuel', top: 'volver', vuelveA: 'nahuel.esc', titulo: 'Producto', barra: false,
  titulo_panel: 'Ficha de producto (llegada por escaneo)',
  nota: `Ésta es la pantalla que reemplaza a <b>Productos</b> en mobile. Los datos
    son los que hacen falta parado frente a la caja: dónde va, qué lote es, cuándo
    vence y de quién vino. Nada de historial de ventas.`,
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="card">
      <p class="tit">MANTECA SANTA CLARA 200G (X30U)</p>
      <p class="meta"><span class="mono">Código 1236</span> · Lácteos Campo Alegre</p>
      <div style="margin-top:12px">
        <div class="dato"><span>Ubicación</span><b>Pasillo 5 · Rack A</b></div>
        <div class="dato"><span>Lote</span><b>L-2026-368</b></div>
        <div class="dato"><span>Vence</span><b>08/12/2026</b></div>
        <div class="dato"><span>En sistema</span><b>222 un.</b></div>
        <div class="dato"><span>Entra por</span><b>OC-2026-0847</b></div>
      </div>
    </div>
    <button class="btn pri" onclick="go('nahuel.recepcion')">${ico('tilde', 20)} Recibí las 25, sin problemas</button>
    <button class="btn peligro" onclick="go('nahuel.r1')">${ico('alerta', 20)} Hay un problema con esto</button>
  </div>`,
});

/* ── El flujo guiado de reclamo. Cuatro pasos, y el tercero lo arma la app. ── */

reg('nahuel.r1', {
  rol: 'nahuel', top: 'volver', vuelveA: 'nahuel.prod', titulo: 'Qué pasó', barra: false,
  pasos: [1, 4], paso: '1 de 4',
  titulo_panel: 'Reclamo · 1 · qué pasó',
  nota: `Los cuatro motivos son los de <code>core/piso.py:62</code>
    (<code>roto · faltante · vencido · no_pedido</code>): no invento un vocabulario nuevo.
    Botones de 70px porque se tocan con guante.
    <span class="toques">1 toque.</span>`,
  html: () => `<div class="cuerpo" style="padding-top:8px">
    <p class="txt fuerte" style="margin-bottom:14px">MANTECA SANTA CLARA 200G · Lácteos Campo Alegre</p>
    <button class="btn sec grande" onclick="go('nahuel.r2')">Vino roto</button>
    <button class="btn sec grande" onclick="go('nahuel.r2')">Vino de menos</button>
    <button class="btn sec grande" onclick="go('nahuel.r2')">Vino vencido o por vencer</button>
    <button class="btn sec grande" onclick="go('nahuel.r2')">No era lo que pedimos</button>
    <button class="voz" onclick="go('nahuel.voz')">${ico('micro', 22)}
      <span><b>Es otra cosa · decilo hablando</b><span>Ángela lo entiende y te muestra qué entendió</span></span></button>
  </div>`,
});

reg('nahuel.r2', {
  rol: 'nahuel', top: 'volver', vuelveA: 'nahuel.r1', titulo: 'Cuántas', barra: false,
  pasos: [2, 4], paso: '2 de 4',
  titulo_panel: 'Reclamo · 2 · cuántas',
  nota: `El número pasa por <code>core/validacion</code>, el mismo peaje que una
    cantidad leída de un remito (<code>core/voz.py</code> lo dice explícito:
    "ocho" y "ochocientos" suenan parecido).
    <span class="toques">1 dígito + confirmar = 2 toques.</span>`,
  html: () => `<div class="cuerpo" style="padding-top:4px">
    <div class="visor">8<small>de 25 recibidas · manteca rota</small></div>
    <div class="numpad">
      ${[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => `<button>${n}</button>`).join('')}
      <button>,</button><button>0</button><button>←</button>
    </div>
    <button class="btn pri" style="margin-top:14px" onclick="go('nahuel.r3')">Seguir</button>
  </div>`,
});

reg('nahuel.r3', {
  rol: 'nahuel', top: 'volver', vuelveA: 'nahuel.r2', titulo: 'Lo que pide este proveedor', barra: false,
  pasos: [3, 4], paso: '3 de 4',
  titulo_panel: 'Reclamo · 3 · lo que pide Campo Alegre',
  nota: `<b>El paso que distingue esto de un formulario.</b> La app ya sabe qué exige
    este proveedor y ya completó lo que podía sacar del dataset: el lote sale de
    <code>apartados.deposito</code> y el remito, de la OC abierta. Al de depósito le
    queda <b>una sola</b> cosa por hacer.
    <span class="toques">1 toque (la foto).</span>`,
  html: () => `<div class="cuerpo" style="padding-top:8px">
    <div class="card angela">
      <div class="fila"><span class="icoc angela">${ico('llave', 21)}</span><div class="crece">
        <p class="txt fuerte">Campo Alegre acepta reclamos por mail, con foto del producto,
          el lote y el número de remito. Tiene 5 días de plazo.</p>
        <p class="meta">Regla de la casa · la enseñó Aldo el 20/06 · aplicada 6 veces</p></div></div>
    </div>

    <div class="h2">Ya lo tengo</div>
    <div class="req listo">${ico('tilde', 20)}<span class="crece">
      <b>Lote L-2026-368</b><span>Del lote que estás recibiendo</span></span></div>
    <div class="req listo">${ico('tilde', 20)}<span class="crece">
      <b>Remito OC-2026-0847</b><span>De la orden abierta de este proveedor</span></span></div>
    <div class="req listo">${ico('tilde', 20)}<span class="crece">
      <b>8 unidades · rotas</b><span>Lo que acabás de cargar</span></span></div>

    <div class="h2">Falta esto</div>
    <button class="req pide" onclick="go('nahuel.r4')">${ico('camara', 22)}<span class="crece">
      <b>Foto del producto roto</b><span>Es lo único que Campo Alegre no acepta sin ver</span></span>
      ${ico('chevron', 18)}</button>

    <button class="btn sec" style="margin-top:6px" onclick="go('nahuel.r3b')">
      Ver qué pasa con un proveedor que no conocemos</button>
  </div>`,
});

reg('nahuel.r3b', {
  rol: 'nahuel', top: 'volver', vuelveA: 'nahuel.r3', titulo: 'Proveedor sin regla', barra: false,
  pasos: [3, 4], paso: '3 de 4',
  titulo_panel: 'Reclamo · 3b · proveedor que no conocemos',
  nota: `<b>La honestidad como pantalla.</b> Cuando no hay pieza de conocimiento para
    ese proveedor, se dice — no se muestra un set genérico fingiendo que es el correcto.
    Y se aprende con la respuesta: si el reclamo vuelve rechazado por falta de algo,
    eso entra a <code>core/conocimiento.py</code> como <code>estado: "pendiente"</code>
    hasta que alguien lo aprueba.`,
  html: () => `<div class="cuerpo" style="padding-top:8px">
    <div class="card oro">
      <div class="fila"><span class="icoc oro">${ico('info', 21)}</span><div class="crece">
        <p class="txt fuerte">De Golosinas Costa Dulce todavía no sé qué pide para un reclamo.</p>
        <p class="txt">Junto lo básico y lo aprendemos con la respuesta.</p></div></div>
    </div>
    <div class="req listo">${ico('tilde', 20)}<span class="crece"><b>12 unidades · vencidas</b><span>Lo que cargaste</span></span></div>
    <button class="req pide">${ico('camara', 22)}<span class="crece">
      <b>Foto</b><span>Sirve casi siempre</span></span>${ico('chevron', 18)}</button>
    <button class="req pide">${ico('doc', 22)}<span class="crece">
      <b>Lote o fecha de vencimiento</b><span>Lo leo de la etiqueta si sacás la foto</span></span>${ico('chevron', 18)}</button>
    <button class="btn pri" style="margin-top:10px" onclick="go('nahuel.r4')">Mandar así</button>
  </div>`,
});

reg('nahuel.r4', {
  rol: 'nahuel', top: 'volver', vuelveA: 'nahuel.r3', titulo: 'A quién le llega', barra: false,
  pasos: [4, 4], paso: '4 de 4',
  titulo_panel: 'Reclamo · 4 · a quién le llega',
  nota: `<b>Ángela propone el destinatario, la persona confirma.</b> Nadie del piso
    elige de una lista de 14. Si Ángela se equivoca, cambiarlo es un toque y quedan
    dos opciones, no catorce.
    <span class="toques">1 toque para mandar.</span>`,
  html: () => `<div class="cuerpo" style="padding-top:8px">
    <div class="card">
      <p class="tit chico">8 cajas rotas · MANTECA SANTA CLARA 200G</p>
      <p class="txt">Lácteos Campo Alegre · lote L-2026-368 · OC-2026-0847</p>
      <div class="evidencia">tu foto</div>
      <p class="meta"><span class="mono">$53.323</span> · costo del catálogo × 8</p>
    </div>

    <div class="card angela">
      <div class="fila"><span class="icoc angela">${ico('angela', 21)}</span><div class="crece">
        <p class="txt fuerte">Esto lo ve <b>Celeste</b>, que lleva a Campo Alegre.
          Ella arma el reclamo y Aldo lo aprueba antes de que salga.</p></div></div>
      <button class="btn ang" style="margin-top:12px" onclick="go('nahuel.r5')">Mandárselo a Celeste</button>
      <div class="par" style="margin-top:8px">
        <button class="btn sec">A Ramón</button>
        <button class="btn sec">A otro</button>
      </div>
    </div>

    <p class="fuente">${ico('info', 14)}<span>Queda a tu nombre y podés ver en qué anda
      desde «Lo que reportaste».</span></p>
  </div>`,
});

reg('nahuel.r5', {
  rol: 'nahuel', top: 'volver', vuelveA: 'nahuel.dia', titulo: 'Listo', barra: false,
  titulo_panel: 'Guardado sin señal (pantalla sin motor)',
  nota: `<b>Esto no se puede construir hoy.</b> No hay service worker, ni manifest,
    ni IndexedDB en el repo (verificado). El estado offline está diseñado y declarado
    como pendiente de motor. Los tres estados —guardado / enviado / visto— son lo
    mínimo para que alguien confíe en cargar algo en la cámara de frío.`,
  html: () => `<div class="cuerpo" style="padding-top:26px;text-align:center">
    <span class="icoc salvia" style="width:64px;height:64px;margin:0 auto 16px;border-radius:var(--r-full)">
      ${ico('tilde', 32)}</span>
    <p class="tit">Quedó cargado</p>
    <p class="txt" style="margin-bottom:18px">8 cajas rotas · Campo Alegre</p>
    <div class="card plano" style="text-align:left">
      <ul class="tl">
        <li><b>Guardado en tu teléfono</b><span>09:14 · no se pierde aunque cierres la app</span></li>
        <li class="espera"><b>Esperando señal para mandarlo a Celeste</b>
            <span>Estás en la cámara de frío · sale solo cuando haya</span></li>
        <li class="futuro"><b>Celeste lo ve</b><span>Te aviso cuando lo abra</span></li>
      </ul>
    </div>
    <button class="btn pri" style="margin-top:14px" onclick="go('nahuel.dia')">Seguir descargando</button>
  </div>`,
});

reg('nahuel.voz', {
  rol: 'nahuel', top: 'volver', vuelveA: 'nahuel.r1', titulo: 'Decilo hablando', barra: false,
  titulo_panel: 'Voz: los cuatro pasos en uno',
  nota: `<b>El argumento real de la voz no es que sea cómoda: es que colapsa pasos.</b>
    Una frase llena motivo, cantidad y lote de una vez → el reclamo entero en 3 toques.
    Lo que se muestra es lo que <code>voz.proponer</code> (<code>core/voz.py:210</code>)
    ya devuelve hoy: transcripción, candidatos de producto, avisos y bloqueos.
    <span class="toques">Micrófono + parar + mandar = 3 toques.</span>`,
  html: () => `<div class="cuerpo" style="padding-top:14px">
    <div class="card angela">
      <p class="meta" style="margin:0 0 8px">Escuché</p>
      <p class="txt fuerte" style="font-size:15px">«Ocho cajas de manteca Santa Clara vinieron
        rotas, del lote L-2026-368»</p>
    </div>

    <div class="h2">Entendí esto</div>
    <div class="card">
      <div class="dato"><span>Qué pasó</span><b>Roto</b></div>
      <div class="dato"><span>Producto</span><b>MANTECA SANTA CLARA 200G</b></div>
      <div class="dato"><span>Cantidad</span><b>8</b></div>
      <div class="dato"><span>Lote</span><b>L-2026-368</b></div>
      <p class="fuente">${ico('info', 14)}<span>El número lo valida el código, no el modelo.
        Si dijeras 800 sobre una entrega de 25, te lo freno antes de guardarlo.</span></p>
    </div>

    <button class="btn ang" onclick="go('nahuel.r4')">Está bien, seguir</button>
    <button class="btn sec" onclick="go('nahuel.r1')">Corregir a mano</button>
  </div>`,
});

reg('nahuel.balanza', {
  rol: 'nahuel', top: 'volver', vuelveA: 'nahuel.dia', titulo: 'Balanzas', barra: false,
  titulo_panel: 'Tarea cerrable desde el piso',
  nota: `Esto YA FUNCIONA hoy (<code>MiDia.jsx:105</code>): aplica <code>saneamiento</code>
    de verdad y la auditoría queda a nombre de Nahuel. Es el único lugar del producto
    donde alguien del piso cambia el sistema con un toque, y por eso es el modelo a copiar.
    <span class="toques">2 toques (abrir + confirmar).</span>`,
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="card oro">
      <p class="tit chico">2 productos con precio de balanza mal calculado</p>
      <p class="txt">Se corrige acá y queda a tu nombre.</p>
    </div>
    <div class="lista">
      <div class="li"><span class="pt oro"></span><span class="crece">
        <b>JAMON COCIDO GUARANI (HORMA)</b><span>Balanza 2 · desvío 2,4%</span></span></div>
      <div class="li"><span class="pt oro"></span><span class="crece">
        <b>SALAME MILAN LA RIBERA (PLANCHA)</b><span>Balanza 2 · desvío 3,1%</span></span></div>
    </div>
    <button class="btn pri" style="margin-top:12px" onclick="go('nahuel.dia')">${ico('tilde', 20)} Corregir las 2</button>
    <p class="fuente">${ico('info', 14)}<span>La regla dice que menos de 1% no se alerta
      («La balanza 2 desvía siempre un poco»). Estas dos la pasan.</span></p>
  </div>`,
});

reg('nahuel.avisos', {
  rol: 'nahuel', top: 'volver', vuelveA: 'nahuel.dia', titulo: 'Avisos', barra: false, oculta: true,
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="lista">
      <div class="li"><span class="pt salvia"></span><span class="crece">
        <b>Aldo aprobó tu reclamo</b><span>Campo Alegre · $53.323 · hoy 11:03</span></span></div>
      <div class="li"><span class="pt angela"></span><span class="crece">
        <b>Celeste vio tu aviso de los pallets</b><span>Hoy 09:31</span></span></div>
    </div>
  </div>`,
});

reg('nahuel.angela', {
  rol: 'nahuel', tab: 'angela', titulo: 'Ángela (chat)',
  nota: `El chat NO es la puerta de entrada a los datos: para «abrime la ficha de X»
    está la búsqueda. Acá quedan las preguntas de oficio, que son otra velocidad.`,
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="burb ella">Hola Nahuel. Estás recibiendo Campo Alegre, OC-2026-0847.</div>
    <div class="burb mia">¿Dónde va la crema de leche?</div>
    <div class="burb ella">Pasillo 1 · Rack A. Es donde está el lote L-2027-459 que ya tenés.</div>
    <div class="h2">Lo que preguntás siempre</div>
    <div class="lista">
      <div class="li"><span class="crece"><b>¿Dónde está guardado este producto?</b></span>${ico('chevron', 18)}</div>
      <div class="li"><span class="crece"><b>¿Qué remito entró último?</b></span>${ico('chevron', 18)}</div>
      <div class="li"><span class="crece"><b>¿Hay algo con stock negativo?</b></span>${ico('chevron', 18)}</div>
    </div>
  </div>`,
});

/* ══ TOMÁS · Depósito / conteos ══════════════════════════════════════════ */

hoja('tomas', {
  titulo: 'Contar', sub: 'Tres cosas. Nada más.',
  vozA: 'tomas.dia',
  tiles: [
    ['escanear', ['Escanear y contar', 'Lo más rápido'], 'tomas.contar', 'destaca'],
    ['pin', ['Contar una ubicación', 'Pasillo, rack o cámara'], 'tomas.conteo'],
    ['alerta', ['No encuentro el producto', 'O está en otro lado'], 'tomas.dia', 'alerta'],
  ],
});

reg('tomas.dia', {
  rol: 'tomas', tab: 'dia', titulo: 'Mi día',
  nota: `<b>Tres acciones y grandes, no nueve chiquitas.</b> Tomás no cobra, no crea
    pedidos, no recibe devoluciones. Todo eso desaparece de su app.
    El bloque verde de arriba es lo único que le devuelve algo por contar.`,
  html: () => `<div class="cuerpo">
    ${novedadTuya('Tu conteo del jamón cocido corrigió el stock: había 34 unidades de más.',
      'Ramón lo aplicó ayer', 'tomas.dia')}

    <div class="h2">Para contar hoy</div>
    <div class="lista">
      <button class="li" onclick="go('tomas.contar')"><span class="pt oro"></span><span class="crece">
        <b>PAPEL HIGIENICO SANTA CLARA X4</b><span>Pasillo 6 · Rack C · sistema dice 381</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li" onclick="go('tomas.contar')"><span class="pt oro"></span><span class="crece">
        <b>ROLLO DE COCINA GUARANI X3</b><span>Pasillo 5 · Rack B · sistema dice 909,8</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li" onclick="go('tomas.contar')"><span class="pt gris"></span><span class="crece">
        <b>VINO TINTO LA RIBERA 750CC</b><span>Pasillo 2 · Rack C · sistema dice 479</span></span>
        ${ico('chevron', 18)}</button>
    </div>

    <div class="h2">Progreso de la semana</div>
    <div class="card plano">
      <p class="txt fuerte">Contaste 14 de 21 ubicaciones.</p>
      <div class="progreso"><i style="width:67%"></i></div>
      <p class="fuente" style="margin-top:12px">${ico('info', 14)}
        <span>Es tu propio avance, no una comparación con nadie. Los rankings entre
        compañeros empeoran el clima en trabajo de primera línea, así que no hay ninguno.</span></p>
    </div>
  </div>`,
});

reg('tomas.contar', {
  rol: 'tomas', top: 'volver', vuelveA: 'tomas.dia', titulo: 'Contar', barra: false,
  titulo_panel: 'Contar un producto',
  nota: `Se llega acá <b>desde la tarea o desde el escaneo</b>, nunca desde una lista
    de 430. El número del sistema se muestra DESPUÉS de contar, no antes: mostrarlo
    antes es sugerir la respuesta.
    <span class="toques">Escanear + tipear + confirmar = 3 toques.</span>`,
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="card">
      <p class="tit chico">PAPEL HIGIENICO SANTA CLARA X4 (X10P)</p>
      <p class="meta"><span class="mono">Código 1414</span> · Pasillo 6 · Rack C</p>
    </div>
    <div class="visor">347<small>lo que contaste</small></div>
    <div class="numpad">
      ${[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => `<button>${n}</button>`).join('')}
      <button>,</button><button>0</button><button>←</button>
    </div>
    <div class="card oro" style="margin-top:14px">
      <p class="txt fuerte">El sistema dice 381. Hay 34 menos.</p>
      <p class="txt">Va como diferencia para que Ramón la resuelva. Vos no tenés que decidir nada.</p>
    </div>
    <button class="btn pri" onclick="go('tomas.dia')">Confirmar el conteo</button>
    <button class="voz" onclick="go('tomas.dia')">${ico('micro', 22)}
      <span><b>Contar hablando</b><span>Con las manos ocupadas en la caja</span></span></button>
  </div>`,
});

reg('tomas.conteo', {
  rol: 'tomas', tab: 'conteo', titulo: 'Conteo por ubicación',
  nota: `Las diferencias salen de <code>deposito.discrepancias()</code>
    (<code>core/deposito.py:69</code>), que compara <code>cantidad</code> contra
    <code>counted_qty</code> — dos columnas que YA están en el dataset.`,
  html: () => `<div class="cuerpo">
    <div class="h2">Tus ubicaciones</div>
    <div class="lista">
      <button class="li"><span class="pt rojo"></span><span class="crece">
        <b>Cámara de frío 2</b><span>Al 100% · 3 avisos del equipo · 41 lotes</span></span>${ico('chevron', 18)}</button>
      <button class="li"><span class="pt oro"></span><span class="crece">
        <b>Pasillo 6 · Rack C</b><span>2 diferencias sin resolver</span></span>${ico('chevron', 18)}</button>
      <button class="li"><span class="pt salvia"></span><span class="crece">
        <b>Pasillo 1 · Rack A</b><span>Contado ayer · sin diferencias</span></span>${ico('chevron', 18)}</button>
      <button class="li"><span class="pt gris"></span><span class="crece">
        <b>Pasillo 2 · Rack C</b><span>Sin contar desde el 24/06</span></span>${ico('chevron', 18)}</button>
    </div>
    <p class="fuente" style="margin-top:12px">${ico('info', 14)}<span>Las 21 ubicaciones del
      dataset, agrupadas. Las cámaras van sueltas porque son las que duelen.</span></p>
  </div>`,
});

reg('tomas.avisos', {
  rol: 'tomas', top: 'volver', vuelveA: 'tomas.dia', titulo: 'Avisos', barra: false, oculta: true,
  html: () => `<div class="cuerpo" style="padding-top:12px"><div class="lista">
    <div class="li"><span class="pt salvia"></span><span class="crece">
      <b>Ramón aplicó tu conteo</b><span>Jamón cocido El Paraná · ayer 16:20</span></span></div>
  </div></div>`,
});

reg('tomas.angela', {
  rol: 'tomas', tab: 'angela', titulo: 'Ángela (chat)',
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="burb ella">Hola Tomás. Te quedan 3 conteos de hoy.</div>
    <div class="h2">Lo que preguntás siempre</div>
    <div class="lista">
      <div class="li"><span class="crece"><b>¿Dónde está guardado este producto?</b></span>${ico('chevron', 18)}</div>
      <div class="li"><span class="crece"><b>¿Hay algo con stock negativo?</b></span>${ico('chevron', 18)}</div>
    </div>
  </div>`,
});

/* ══ BRIAN · Depósito / armado de pedidos ════════════════════════════════ */

hoja('brian', {
  titulo: 'Armado', sub: 'Lo que hacés mientras armás.',
  voz: false,
  tiles: [
    ['escanear', ['Escanear', 'Confirmar un renglón'], 'brian.linea', 'destaca'],
    ['alerta', ['No hay stock', 'De este renglón'], 'brian.sinstock', 'alerta'],
    ['tilde', ['Pedido armado', 'Cerrarlo y avisar'], 'brian.dia'],
  ],
});

reg('brian.dia', {
  rol: 'brian', tab: 'dia', titulo: 'Mi día',
  nota: `<b>Brian es el agujero más grande del producto hoy: arma pedidos todo el día
    y no tiene una sola acción de picking</b> — la regex de <code>lib/roles.js:21</code>
    lo mete en «depósito» y le ofrece cargar remitos y marcar conteos, que no son su trabajo.
    Los pedidos salen de <code>apartados.logistica</code>, filas pendientes de hoy.`,
  html: () => `<div class="cuerpo">
    <div class="h2">Para armar hoy</div>
    <div class="card">
      <div class="fila"><span class="icoc oro">${ico('lista', 21)}</span><div class="crece">
        <p class="tit chico">P-4416 · Panadería El Trigal</p>
        <p class="txt">Av. Costanera 660 · sale con el Camión 3</p>
        <p class="meta"><span class="rot oro">Armando</span><span class="mono">4 de 9 renglones</span></p>
      </div></div>
      <div class="progreso"><i style="width:44%"></i></div>
      <button class="btn pri" style="margin-top:12px" onclick="go('brian.armado')">Seguir armando</button>
    </div>
    <div class="lista">
      <button class="li" onclick="go('brian.armado')"><span class="pt gris"></span><span class="crece">
        <b>P-4418 · Comidas El Fogón</b><span>Ruta 11 km 1317 · Camión 1 · Walter</span></span>${ico('chevron', 18)}</button>
      <button class="li" onclick="go('brian.armado')"><span class="pt gris"></span><span class="crece">
        <b>P-4419 · Bufete Club Regatas</b><span>Ruta 11 km 1615 · Camión 2 · Osmar</span></span>${ico('chevron', 18)}</button>
      <button class="li" onclick="go('brian.armado')"><span class="pt gris"></span><span class="crece">
        <b>P-4417 · Panadería El Trigal</b><span>Ruta 11 km 1533 · Camión 2 · Osmar</span></span>${ico('chevron', 18)}</button>
    </div>

    <div class="h2">Lo que avisaste</div>
    <div class="lista">
      <button class="li"><span class="pt oro"></span><span class="crece">
        <b>El salame de Monte Chico vence el 18/07</b><span>Cámara de frío 2 · Celeste lo vio</span></span>
        ${ico('chevron', 18)}</button>
    </div>
  </div>`,
});

reg('brian.armado', {
  rol: 'brian', tab: 'armado', titulo: 'Armado (renglón por renglón)',
  encabezado: 'P-4416', subencabezado: 'Panadería El Trigal · 9 renglones',
  nota: `<b>Un renglón, una ubicación, un escaneo.</b> El escaneo no es opcional:
    previene agarrar el producto equivocado, que es el error caro. La voz sirve para
    la cantidad, no para identificar el producto.
    <span class="toques">Confirmar un renglón: 1 toque (escanear).</span>`,
  html: () => `<div class="cuerpo">
    <div class="card" style="margin-top:8px">
      <p class="meta" style="margin:0 0 6px">Renglón 5 de 9</p>
      <p class="tit">LECHE ENTERA EL PARANA 1L (X12U)</p>
      <p class="txt fuerte" style="font-size:26px;font-family:var(--display);margin-top:10px">12 unidades</p>
      <div style="margin-top:10px">
        <div class="dato"><span>Está en</span><b>Pasillo 4 · Rack B</b></div>
        <div class="dato"><span>Lote</span><b>L-2026-301</b></div>
      </div>
      <div class="card angela" style="margin-top:12px;padding:12px">
        <p class="txt fuerte" style="font-size:13px">Nahuel corrió las cajas del pasillo 4:
          quedaron del lado de la pared.</p>
        <p class="meta">Aviso de Nahuel · ayer</p>
      </div>
      <button class="btn pri grande" style="margin-top:12px" onclick="go('brian.armado')">
        ${ico('escanear', 22)} Escanear y confirmar</button>
      <button class="btn sec" onclick="go('brian.sinstock')">No hay stock acá</button>
    </div>

    <div class="h2">Lo que ya armaste</div>
    <div class="lista">
      <div class="li"><span class="pt salvia"></span><span class="crece">
        <b>GALLETITAS SURTIDAS LA RIBERA 400G</b><span>6 un. · Pasillo 3 · Rack C</span></span>
        <span class="rot salvia">OK</span></div>
      <div class="li"><span class="pt salvia"></span><span class="crece">
        <b>HARINA 000 CAMPO ALEGRE X1KG</b><span>10 un. · Pasillo 5 · Rack C</span></span>
        <span class="rot salvia">OK</span></div>
      <div class="li"><span class="pt rojo"></span><span class="crece">
        <b>MANTECA CAMPO ALEGRE 200G</b><span>Pediste 4 · sólo había 2</span></span>
        <span class="rot rojo">Faltó</span></div>
    </div>
  </div>`,
});

reg('brian.sinstock', {
  rol: 'brian', top: 'volver', vuelveA: 'brian.armado', titulo: 'No hay stock', barra: false,
  titulo_panel: 'Falta stock en un renglón',
  nota: `<b>Esto NO reserva ni descuenta stock: eso es del ERP.</b> Lo que se registra
    es un hecho —«armé 2 de 4»— y un aviso dirigido. Respeta la regla de P4 sin excepción.
    <span class="toques">Elegir cuánto + mandar = 2 toques.</span>`,
  html: () => `<div class="cuerpo" style="padding-top:10px">
    <div class="card">
      <p class="tit chico">MANTECA CAMPO ALEGRE 200G (X30U)</p>
      <p class="txt">Pedido P-4416 · pedía 4 unidades</p>
    </div>
    <div class="h2">¿Cuántas pudiste poner?</div>
    <div class="par">
      <button class="btn sec grande">0</button>
      <button class="btn sec grande">1</button>
      <button class="btn pri grande">2</button>
      <button class="btn sec grande">3</button>
    </div>
    <div class="card angela" style="margin-top:14px">
      <div class="fila"><span class="icoc angela">${ico('angela', 21)}</span><div class="crece">
        <p class="txt fuerte">Esto lo ve <b>Celeste</b>: hay una orden abierta a Campo Alegre
          (OC-2026-0847) con 10 de este producto.</p></div></div>
      <button class="btn ang" style="margin-top:12px" onclick="go('brian.armado')">Avisarle a Celeste</button>
    </div>
    ${sinSenal()}
  </div>`,
});

reg('brian.avisos', {
  rol: 'brian', top: 'volver', vuelveA: 'brian.dia', titulo: 'Avisos', barra: false, oculta: true,
  html: () => `<div class="cuerpo" style="padding-top:12px"><div class="lista">
    <div class="li"><span class="pt salvia"></span><span class="crece">
      <b>Celeste puso el salame en oferta</b><span>Por tu aviso del 04/07</span></span></div>
  </div></div>`,
});

reg('brian.angela', {
  rol: 'brian', tab: 'angela', titulo: 'Ángela (chat)',
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="burb ella">Te faltan 5 renglones del P-4416.</div>
    <div class="lista"><div class="li"><span class="crece">
      <b>¿Dónde está guardado este producto?</b></span>${ico('chevron', 18)}</div></div>
  </div>`,
});

/* ══ KEVIN · ayudante, entró hace una semana ═════════════════════════════ */

hoja('kevin', {
  titulo: 'Cargar', sub: 'Lo básico. Nada más, por ahora.',
  vozA: 'kevin.dia',
  tiles: [
    ['escanear', ['Escanear', 'Ver qué es y dónde va'], 'kevin.dia', 'destaca'],
    ['alerta', ['Hay un problema', 'Contale a Ramón'], 'kevin.dia', 'alerta'],
  ],
});

reg('kevin.dia', {
  rol: 'kevin', tab: 'dia', titulo: 'Mi día',
  nota: `<b>Dos destinos, no tres.</b> Kevin entró hace una semana; menos es mejor.
    El botón «Preguntarle a Ramón» sale de un dato que YA está sembrado y que
    ninguna pantalla usa: <code>usuarios_demo.py</code> le declara
    <code>mentor: "ramon"</code>. El bloque de onboarding ya existe
    (<code>MiDia.jsx</code>, se apaga solo cuando deja de ser nuevo).`,
  html: () => `<div class="cuerpo">
    <div class="card angela">
      <div class="fila"><span class="icoc angela">${ico('angela', 21)}</span><div class="crece">
        <p class="tit chico">Tu primera semana</p>
        <p class="txt">Ramón es tu referente. Si algo no cierra, preguntale a él antes de mover nada.</p>
      </div></div>
      <button class="btn ang" style="margin-top:12px">${ico('micro', 20)} Preguntarle a Ramón</button>
    </div>

    <div class="h2">Lo que te pidieron</div>
    <div class="lista">
      <button class="li"><span class="pt oro"></span><span class="crece">
        <b>Acomodar el pasillo 4</b><span>Te lo dejó Ramón · hoy</span></span>${ico('chevron', 18)}</button>
    </div>

    ${novedadTuya('Lo que avisaste del pasillo 4 quedó anotado: la leche estaba en otro rack.',
      'Ramón lo corrigió', 'kevin.dia')}

    <p class="fuente" style="margin-top:14px">${ico('info', 14)}<span>Kevin no cuenta stock,
      no arma pedidos y no controla remitos todavía. Cuando lo haga, esos destinos aparecen solos:
      salen de sus features, no de código nuevo.</span></p>
  </div>`,
});

reg('kevin.avisos', {
  rol: 'kevin', top: 'volver', vuelveA: 'kevin.dia', titulo: 'Avisos', barra: false, oculta: true,
  html: () => `<div class="cuerpo" style="padding-top:12px"><div class="lista">
    <div class="li"><span class="pt salvia"></span><span class="crece">
      <b>Ramón vio tu aviso</b><span>Pasillo 4 · ayer</span></span></div></div></div>`,
});

reg('kevin.angela', {
  rol: 'kevin', tab: 'angela', titulo: 'Ángela (chat)',
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="burb ella">Hola Kevin. Preguntame lo que sea, no hay pregunta boba.</div>
    <div class="lista">
      <div class="li"><span class="crece"><b>¿Dónde va este producto?</b></span>${ico('chevron', 18)}</div>
      <div class="li"><span class="crece"><b>¿Qué significa «lote»?</b></span>${ico('chevron', 18)}</div>
    </div>
  </div>`,
});

/* ══ RAMÓN · encargado de depósito ═══════════════════════════════════════ */

hoja('ramon', {
  titulo: 'Cargar', sub: 'Lo tuyo y lo de tu gente.',
  vozA: 'ramon.dia',
  tiles: [
    ['escanear', ['Escanear', 'Producto o remito'], 'ramon.dia', 'destaca'],
    ['alerta', ['Hay un problema', 'Y a quién le llega'], 'ramon.dia', 'alerta'],
    ['lista', ['Pedir un conteo', 'A Tomás o a Kevin'], 'ramon.dia'],
    ['camara', ['Foto', 'Dejar constancia'], 'ramon.dia'],
  ],
});

reg('ramon.dia', {
  rol: 'ramon', tab: 'dia', titulo: 'Mi día (cola de decisiones)', campana: true,
  nota: `<b>La pantalla que hoy no puede existir.</b> Resolver un reporte del piso es
    <code>require_admin</code> (<code>main.py:1323</code>): Ramón, con 9 años en el
    galpón, no puede cerrar un faltante de su propia gente. Está diseñada como si el
    permiso existiera, y <b>no se construye</b> — tocar <code>authz</code> lo decide Agustín.`,
  html: () => `<div class="cuerpo">
    <div class="h2">Esperan que decidas vos</div>
    <div class="lista">
      <button class="li" onclick="go('ramon.decidir1')"><span class="pt oro"></span><span class="crece">
        <b>Tomás contó 34 menos de papel higiénico</b><span>Pasillo 6 · Rack C · hace 2 h</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li" onclick="go('ramon.decidir1')"><span class="pt oro"></span><span class="crece">
        <b>Brian no pudo armar 2 unidades de manteca</b><span>P-4416 · hace 40 min</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li" onclick="go('ramon.decidir1')"><span class="pt rojo"></span><span class="crece">
        <b>Nahuel reportó 8 cajas rotas de Campo Alegre</b><span>Ya salió como reclamo</span></span>
        ${ico('chevron', 18)}</button>
    </div>

    <div class="h2">Tu galpón hoy</div>
    <div class="card rojo">
      <div class="fila"><span class="icoc rojo">${ico('alerta', 21)}</span><div class="crece">
        <p class="tit chico">Cámara de frío 2 al 100%</p>
        <p class="txt fuerte">Y La Ribera confirmó la orden de fiambres para el 9.</p>
        <p class="meta">3 avisos tuyos y de Nahuel · 41 lotes adentro</p>
      </div></div>
      <button class="btn pri" style="margin-top:12px">Avisarle a Celeste que no entra</button>
    </div>

    <div class="lista">
      <button class="li"><span class="pt oro"></span><span class="crece">
        <b>8 lotes vencen en 15 días</b><span>El más cercano, jabón en polvo: 13/07</span></span>
        ${ico('chevron', 18)}</button>
      <button class="li"><span class="pt gris"></span><span class="crece">
        <b>Camión de Campo Alegre descargando</b><span>Nahuel · 3 de 5 controlados</span></span>
        ${ico('chevron', 18)}</button>
    </div>
  </div>`,
});

reg('ramon.decidir1', {
  rol: 'ramon', top: 'volver', vuelveA: 'ramon.dia', titulo: 'Diferencia de conteo', barra: false,
  titulo_panel: 'Decidir una diferencia (rol nuevo)',
  nota: `Tres salidas, no una lista de opciones: <b>aceptar el conteo</b> (aplica la
    corrección y queda auditada), <b>mandarlo a recontar</b> (vuelve a Tomás con el
    motivo) o <b>subirlo</b> si es plata grande. Cualquiera de las tres le devuelve
    algo a Tomás, que es lo que hoy no pasa.
    <span class="toques">1 toque.</span>`,
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="card">
      <p class="tit chico">PAPEL HIGIENICO SANTA CLARA X4 (X10P)</p>
      <p class="meta">Pasillo 6 · Rack C · contó Tomás hoy 14:20</p>
      <div style="margin-top:12px">
        <div class="dato"><span>Sistema</span><b>381,0</b></div>
        <div class="dato"><span>Contado</span><b>346,7</b></div>
        <div class="dato"><span>Diferencia</span><b style="color:var(--rojo)">−34,3</b></div>
        <div class="dato"><span>Vale</span><b>$118.400</b></div>
      </div>
    </div>
    <button class="btn pri" onclick="go('ramon.dia')">${ico('tilde', 20)} Aceptar el conteo de Tomás</button>
    <button class="btn sec" onclick="go('ramon.dia')">${ico('vuelta', 20)} Que lo recuente</button>
    <button class="btn sec" onclick="go('ramon.dia')">${ico('chevron', 20)} Subírselo a Aldo</button>
    <p class="fuente">${ico('info', 14)}<span>Decidas lo que decidas, Tomás lo ve en su
      pantalla con tu nombre. Es la mitad que hoy falta.</span></p>
  </div>`,
});

reg('ramon.deposito', {
  rol: 'ramon', tab: 'deposito', titulo: 'Depósito',
  nota: `El «Depósito» de mobile deja de ser tabla y se vuelve <b>dos colas de decisión</b>:
    vencimientos y diferencias. Ambas salen de <code>core/deposito.py</code>. La grilla
    de 380 lotes no viaja al teléfono.`,
  html: () => `<div class="cuerpo">
    <div class="h2">Vence pronto</div>
    <div class="lista">
      <div class="li"><span class="pt rojo"></span><span class="crece">
        <b>JABON EN POLVO SANTA CLARA 3KG</b><span>Vence 13/07 · 227 un. · Pasillo 6 · Rack B</span></span></div>
      <div class="li"><span class="pt oro"></span><span class="crece">
        <b>YOGUR BEBIBLE TIERRA ROJA 900G</b><span>Vence 14/07 · 304 un. · Pasillo 1 · Rack A</span></span></div>
      <div class="li"><span class="pt oro"></span><span class="crece">
        <b>YOGUR BEBIBLE CAMPO ALEGRE 900G</b><span>Vence 18/07 · 208 un. · Pasillo 5 · Rack C</span></span></div>
    </div>
    <div class="h2">Diferencias sin resolver</div>
    <div class="lista">
      <button class="li" onclick="go('ramon.decidir1')"><span class="pt oro"></span><span class="crece">
        <b>PAPEL HIGIENICO SANTA CLARA X4</b><span>−34,3 · contó Tomás</span></span>${ico('chevron', 18)}</button>
      <button class="li" onclick="go('ramon.decidir1')"><span class="pt oro"></span><span class="crece">
        <b>ROLLO DE COCINA GUARANI X3</b><span>−54,6 · contó Tomás</span></span>${ico('chevron', 18)}</button>
    </div>
  </div>`,
});

reg('ramon.avisos', {
  rol: 'ramon', top: 'volver', vuelveA: 'ramon.dia', titulo: 'Avisos', barra: false, oculta: true,
  html: () => `<div class="cuerpo" style="padding-top:12px"><div class="lista">
    <div class="li"><span class="pt oro"></span><span class="crece">
      <b>Celeste: La Ribera llega el 9</b><span>Pidieron avisar si no hay lugar en cámara</span></span></div>
    <div class="li"><span class="pt gris"></span><span class="crece">
      <b>Kevin avisó del pasillo 4</b><span>Ayer</span></span></div>
  </div></div>`,
});

reg('ramon.angela', {
  rol: 'ramon', tab: 'angela', titulo: 'Ángela (chat)',
  html: () => `<div class="cuerpo" style="padding-top:12px">
    <div class="burb ella">Tenés 3 cosas esperando tu decisión y la cámara 2 al 100%.</div>
    <div class="lista">
      <div class="li"><span class="crece"><b>¿Qué vence en los próximos 15 días?</b></span>${ico('chevron', 18)}</div>
      <div class="li"><span class="crece"><b>¿Qué remito entró último?</b></span>${ico('chevron', 18)}</div>
    </div>
  </div>`,
});
