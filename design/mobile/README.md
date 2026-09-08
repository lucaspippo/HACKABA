# design/mobile — interfaz mobile de PolPilot, por rol

Trabajo de **diseño**, no de integración. Nada de esto está cableado al backend:
son mockups navegables para iterar barato y después decidir qué se construye.

| | |
|---|---|
| [`00-MODELO-FLUJO.md`](00-MODELO-FLUJO.md) | Las cinco palabras (aviso, hallazgo, prioridad, objetivo, tarea) relevadas contra el código, dónde se pisan, el ciclo de vida mapeado y dónde se corta. **Confirmado.** |
| [`01-DEVOLUCIONES-Y-RECLAMOS.md`](01-DEVOLUCIONES-Y-RECLAMOS.md) | El flujo guiado por lo que exige cada proveedor: dónde vive ese conocimiento, los pasos, los toques y qué no tiene motor. |
| [`02-ROLES-Y-SUPERFICIE.md`](02-ROLES-Y-SUPERFICIE.md) | La barra inferior, la superficie de los 12 roles, qué acciones agregué y saqué, los avisos por oficio a cerrar, la búsqueda y las pantallas de datos. |
| [`03-CRUCES.md`](03-CRUCES.md) | Los cruces que están en el dataset de verdad: qué fuentes junta cada uno, qué aparece, a quién le sirve, dónde vive y qué cuesta. Y el motor de cruces que ya existe y llega a una sola persona. |
| [`prototipo/`](prototipo/index.html) | 12 roles · 79 pantallas · navegable. Abrilo con doble clic. |

## El prototipo

`prototipo/index.html` anda con doble clic (`file://`) o servido por HTTP. El
panel de la izquierda no es parte del producto: es para recorrerlo. Debajo del
teléfono, cada pantalla explica en qué se apoya y cuántos toques cuesta.

- Tipografías, paleta y radios salen de `DESIGN.md`; el logo, de
  `frontend/public/logos/polpilot.png`. Los `@font-face` apuntan a los archivos
  reales del repo, no a copias.
- Todas las personas, productos, clientes, proveedores, lotes, órdenes y pedidos
  son del dataset del demo, con "hoy" = **2026-07-07**. Ninguna entidad
  inventada, ninguna marca real.

## Estado

Confirmado por Lucas (2026-09-08): la barra de tres destinos con la carga al
centro, los dos presupuestos de toques, sacar Nota y Voz como botones, el azul
reservado para Ángela, `exige_evidencia` en `EFECTOS`, y las tres cosas donde el
diseño se apartó de las imágenes. Los avisos por oficio quedaron aprobados y
sembrados en [`data-demo/avisos_por_oficio.json`](../../data-demo/avisos_por_oficio.json)
— son datos, todavía no están cableados a ninguna pantalla.

Plan de construcción acordado, en orden:

1. **Partir la regex de `roles.js` en cinco** — hecho, en su propia rama
   (`feat/roles-deposito-en-cinco`), no acá.
2. **Cerrar el círculo**: destinatario y estado en el reporte de piso,
   `piso.resolver` emitiendo la notificación, y «lo que reportaste» consumiendo
   el endpoint que ya existe. Los tres juntos.
3. La ficha de armado de Brian, con la pantalla de picking.
4. La antigüedad del costo en la ficha de mostrador y «preguntarle a Ramón»
   para Kevin.
