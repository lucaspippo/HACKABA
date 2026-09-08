/* chrome.js — el marco común: iconos, catálogo de roles, barra inferior,
   hoja de captura y el router del prototipo.

   El catálogo de roles de acá es la PROPUESTA: parte el rol `deposito` de
   lib/roles.js (que hoy se come a cinco personas con oficios distintos) en
   cuatro, y le da al dueño una vista-herramienta. Los `features` de cada
   persona son los REALES de backend/usuarios_demo.py, sin tocar. */

/* ── Iconos (trazo 2, 22px, hereda color) ────────────────────────────────── */
const IC = {
  escanear: 'M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2M3 12h18',
  camara: 'M14.5 4h-5L8 6H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-4l-1.5-2ZM12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z',
  micro: 'M12 2a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3ZM19 10v1a7 7 0 0 1-14 0v-1M12 18v4M8 22h8',
  caja: 'm12 2 9 4.5v11L12 22l-9-4.5v-11L12 2ZM3 6.5 12 11l9-4.5M12 11v11',
  alerta: 'M10.3 3.5 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.5a2 2 0 0 0-3.4 0ZM12 9v4M12 17h.01',
  tilde: 'm20 6-11 11-5-5',
  chevron: 'm9 18 6-6-6-6',
  atras: 'm15 18-6-6 6-6',
  casa: 'M3 9.5 12 3l9 6.5V20a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9.5Z',
  lista: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01',
  camion: 'M1 6h13v11H1zM14 10h4l3 3v4h-7M6 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM18 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z',
  persona: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z',
  lupa: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16ZM21 21l-4.3-4.3',
  campana: 'M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0',
  mas: 'M12 5v14M5 12h14',
  reloj: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20ZM12 6v6l4 2',
  plata: 'M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6',
  angela: 'M12 3a7 7 0 0 1 7 7v3l2 4h-4a5 5 0 0 1-10 0H3l2-4v-3a7 7 0 0 1 7-7Z',
  doc: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6ZM14 2v6h6M9 13h6M9 17h6',
  pin: 'M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0ZM12 12a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z',
  balanza: 'M12 3v18M7 21h10M5 8h14l3 7a4 4 0 0 1-8 0l3-7M5 8l-3 7a4 4 0 0 0 8 0L5 8Z',
  contar: 'M9 6h12M9 12h12M9 18h12M4 6h.01M4 12h.01M4 18h.01',
  vuelta: 'M9 14 4 9l5-5M4 9h11a5 5 0 0 1 0 10h-3',
  nube: 'M17 18a4 4 0 0 0 .3-8A6 6 0 0 0 6 11a4 4 0 0 0 .5 8h10.5ZM12 12v6M9.5 15.5 12 18l2.5-2.5',
  info: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20ZM12 16v-4M12 8h.01',
  fuego: 'M12 2S7 8 7 13a5 5 0 0 0 10 0c0-5-5-11-5-11Z',
  llave: 'M15 7a4 4 0 1 0-3.9 5L8 15v3h3l1-1h2l1-1v-2l1-1h1l2-2-3-3.5A4 4 0 0 0 15 7Z',
  ojo: 'M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7ZM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z',
};
function ico(n, s = 22) {
  return `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="${IC[n] || IC.info}"/></svg>`;
}

/* ── Catálogo de roles propuesto ─────────────────────────────────────────────
   `tabs`  : 3 (o 2) destinos + el botón de carga al centro. Nunca 5.
   `cargar`: lo que abre el botón central, POR OFICIO. Nunca las mismas nueve.
   `buscar`: si el ícono de búsqueda aparece en el encabezado de ese rol.       */
const ROLES = {
  nahuel: {
    nombre: 'Nahuel', oficio: 'Depósito · recepción', grupo: 'Depósito',
    feats: 'deposito · saneamiento · cargar · alertas', solo_mobile: false, buscar: false,
    tabs: [['dia', 'Mi día', 'casa'], ['recepcion', 'Recepción', 'caja'], ['angela', 'Ángela', 'angela']],
    cargarLabel: 'Cargar',
  },
  tomas: {
    nombre: 'Tomás', oficio: 'Depósito · conteos', grupo: 'Depósito',
    feats: 'deposito · inventario · saneamiento · cargar · alertas', solo_mobile: true, buscar: false,
    tabs: [['dia', 'Mi día', 'casa'], ['conteo', 'Conteo', 'contar'], ['angela', 'Ángela', 'angela']],
    cargarLabel: 'Contar',
  },
  brian: {
    nombre: 'Brian', oficio: 'Depósito · armado de pedidos', grupo: 'Depósito',
    feats: 'deposito · logistica · alertas', solo_mobile: true, buscar: false,
    tabs: [['dia', 'Mi día', 'casa'], ['armado', 'Armado', 'lista'], ['angela', 'Ángela', 'angela']],
    cargarLabel: 'Escanear',
  },
  kevin: {
    nombre: 'Kevin', oficio: 'Depósito · ayudante (entró hace una semana)', grupo: 'Depósito',
    feats: 'deposito · inventario · saneamiento · cargar · alertas', solo_mobile: true, buscar: false,
    tabs: [['dia', 'Mi día', 'casa'], ['angela', 'Ángela', 'angela']],
    cargarLabel: 'Cargar',
  },
  ramon: {
    nombre: 'Ramón', oficio: 'Encargado de depósito', grupo: 'Depósito',
    feats: 'panel · deposito · logistica · inventario · saneamiento · cargar · alertas · equipo',
    solo_mobile: false, buscar: true,
    tabs: [['dia', 'Mi día', 'casa'], ['deposito', 'Depósito', 'caja'], ['angela', 'Ángela', 'angela']],
    cargarLabel: 'Cargar',
  },
  walter: {
    nombre: 'Walter', oficio: 'Reparto · camión 1', grupo: 'La calle',
    feats: 'logistica · deposito · alertas', solo_mobile: true, buscar: false,
    tabs: [['ruta', 'Mi ruta', 'camion'], ['dia', 'Lo mío', 'casa'], ['angela', 'Ángela', 'angela']],
    cargarLabel: 'Registrar',
  },
  diego: {
    nombre: 'Diego', oficio: 'Preventista · zona centro', grupo: 'La calle',
    feats: 'panel · cobranzas · cuentas · documentos · alertas', solo_mobile: true, buscar: true,
    tabs: [['ruta', 'Mi ruta', 'pin'], ['clientes', 'Clientes', 'persona'], ['angela', 'Ángela', 'angela']],
    cargarLabel: 'Registrar',
  },
  vanesa: {
    nombre: 'Vanesa', oficio: 'Mostrador · Casa Central', grupo: 'El local',
    feats: 'panel · cobranzas · cuentas · caja · inventario · alertas', solo_mobile: false, buscar: true,
    tabs: [['mostrador', 'Mostrador', 'lupa'], ['caja', 'Caja', 'plata'], ['angela', 'Ángela', 'angela']],
    cargarLabel: 'Escanear',
  },
  norma: {
    nombre: 'Norma', oficio: 'Encargada · Sucursal Norte', grupo: 'El local',
    feats: 'panel · caja · inventario · cuentas · saneamiento · alertas · equipo',
    solo_mobile: false, buscar: true,
    tabs: [['local', 'Mi local', 'casa'], ['caja', 'Caja', 'plata'], ['angela', 'Ángela', 'angela']],
    cargarLabel: 'Registrar',
  },
  marta: {
    nombre: 'Marta', oficio: 'Administración', grupo: 'La oficina',
    feats: 'panel · administracion · cuentas · caja · saneamiento · documentos · evolucion · cargar · alertas · equipo',
    solo_mobile: false, buscar: true,
    tabs: [['pendientes', 'Pendientes', 'lista'], ['docs', 'Documentos', 'doc'], ['angela', 'Ángela', 'angela']],
    cargarLabel: 'Cargar',
  },
  celeste: {
    nombre: 'Celeste', oficio: 'Compras y proveedores', grupo: 'La oficina',
    feats: 'panel · inventario · saneamiento · cargar · documentos · alertas · evolucion · oportunidades · equipo',
    solo_mobile: false, buscar: true,
    tabs: [['compras', 'Compras', 'lista'], ['prov', 'Proveedores', 'camion'], ['angela', 'Ángela', 'angela']],
    cargarLabel: 'Cargar',
  },
  aldo: {
    nombre: 'Aldo', oficio: 'Dueño', grupo: 'La oficina',
    feats: 'todos los módulos', solo_mobile: false, buscar: true,
    tabs: [['decidir', 'Decidir', 'tilde'], ['negocio', 'Negocio', 'fuego'], ['angela', 'Ángela', 'angela']],
    cargarLabel: 'Cargar',
  },
};

/* ── Registro de pantallas ───────────────────────────────────────────────── */
const S = {};        // id → {rol, tab, titulo, nota, html()}
function reg(id, def) { S[id] = def; }

/* ── Router ──────────────────────────────────────────────────────────────── */
let actual = null;
let previo = null;
function go(id) {
  const p = S[id];
  if (!p) return;
  if (id !== actual && actual) previo = actual;
  actual = id;
  const rol = ROLES[p.rol];
  document.getElementById('chrome-top').innerHTML = p.top === false ? '' : topBar(p, rol);
  document.getElementById('vista').innerHTML = p.html();
  document.getElementById('vista').scrollTop = 0;
  document.getElementById('chrome-bot').innerHTML = p.barra === false ? '' : barra(p, rol);
  document.getElementById('nota-pantalla').innerHTML = p.nota || '';
  cerrarHoja();
  pintarPanel();
}

function topBar(p, rol) {
  if (p.top === 'volver') {
    const atras = typeof p.vuelveA === 'function' ? p.vuelveA() : p.vuelveA;
    return `<div class="volver">
      <button onclick="go('${atras}')" aria-label="Volver">${ico('atras', 24)}</button>
      <h1>${p.titulo}</h1>
      ${p.paso ? `<span class="paso">${p.paso}</span>` : ''}
    </div>${p.pasos ? pasosHtml(p.pasos[0], p.pasos[1]) : ''}`;
  }
  return `<div class="top">
    <img src="polpilot.png" alt="PolPilot" class="top-logo">
    <div class="top-quien"><b>${p.encabezado || rol.nombre}</b><span>${p.subencabezado || rol.oficio}</span></div>
    <div class="top-act">
      ${rol.buscar ? `<button class="icobtn" onclick="go('buscar')" aria-label="Buscar">${ico('lupa')}</button>` : ''}
      <button class="icobtn" onclick="go('${p.rol}.avisos')" aria-label="Avisos">${ico('campana')}${p.campana ? '<i class="punto"></i>' : ''}</button>
    </div>
  </div>`;
}
function pasosHtml(n, total) {
  return `<div class="pasos">${Array.from({ length: total },
    (_, i) => `<i class="${i < n ? 'on' : ''}"></i>`).join('')}</div>`;
}

function barra(p, rol) {
  const t = rol.tabs;
  const tab = (x) => `<button class="tab ${p.tab === x[0] ? 'on' : ''}"
      onclick="go('${p.rol}.${x[0]}')">${ico(x[2], 23)}<span>${x[1]}</span></button>`;
  const centro = `<button class="cargar" onclick="abrirHoja('${p.rol}')">
      <i>${ico('mas', 28)}</i><span>${rol.cargarLabel}</span></button>`;
  if (t.length === 2) return `<nav class="barra dos">${tab(t[0])}${centro}${tab(t[1])}</nav>`;
  return `<nav class="barra">${tab(t[0])}${tab(t[1])}${centro}${tab(t[2])}</nav>`;
}

/* ── Hoja de captura ─────────────────────────────────────────────────────── */
const HOJAS = {};
function hoja(rol, def) { HOJAS[rol] = def; }
function abrirHoja(rol) {
  const h = HOJAS[rol];
  if (!h) return;
  const el = document.getElementById('hoja');
  el.innerHTML = `<div class="hoja-fondo" onclick="cerrarHoja()"></div>
    <div class="hoja-caja">
      <h2>${h.titulo}</h2>
      <p class="sub">${h.sub}</p>
      <div class="mosaico ${h.tiles.length <= 3 ? 'tres' : ''}">
        ${h.tiles.map((t) => `<button class="tile ${t[3] || ''}" onclick="${t[2] ? `go('${t[2]}')` : 'cerrarHoja()'}">
            <span class="ti">${ico(t[0], 20)}</span>
            <span><b>${t[1][0]}</b><span>${t[1][1]}</span></span>
          </button>`).join('')}
      </div>
      ${h.voz === false ? '' : `<button class="voz" onclick="${h.vozA ? `go('${h.vozA}')` : 'cerrarHoja()'}">
        ${ico('micro', 22)}<span><b>Decirlo hablando</b><span>Ángela entiende y te muestra qué entendió</span></span></button>`}
    </div>`;
  el.classList.add('on');
}
function cerrarHoja() {
  const el = document.getElementById('hoja');
  el.classList.remove('on');
  el.innerHTML = '';
}

/* ── Panel lateral de revisión ───────────────────────────────────────────── */
function pintarPanel() {
  const cont = document.getElementById('p-roles');
  const rolActual = actual ? S[actual].rol : null;
  const grupos = {};
  Object.entries(ROLES).forEach(([k, r]) => { (grupos[r.grupo] ||= []).push([k, r]); });
  cont.innerHTML = Object.entries(grupos).map(([g, rs]) => `
    <div class="p-grupo">${g}</div>
    ${rs.map(([k, r]) => {
      const pants = Object.entries(S).filter(([, p]) => p.rol === k && !p.oculta);
      const on = k === rolActual;
      return `<button class="p-rol ${on ? 'on' : ''}" onclick="go('${pants[0][0]}')">
          <b>${r.nombre} · ${r.oficio}</b>
          <span>${r.solo_mobile ? 'sólo mobile · ' : ''}${r.tabs.length} destinos + carga</span>
        </button>
        <div class="p-pants">${pants.map(([id, p]) =>
          `<button class="p-pant ${id === actual ? 'on' : ''}" onclick="go('${id}')">${p.titulo}</button>`).join('')}</div>`;
    }).join('')}`).join('');
}
