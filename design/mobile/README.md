# design/mobile — interfaz mobile de PolPilot, por rol

Trabajo de **diseño**, no de integración. Nada de esto está cableado al backend:
son mockups navegables para iterar barato y después decidir qué se construye.

| | |
|---|---|
| [`00-MODELO-FLUJO.md`](00-MODELO-FLUJO.md) | Las cinco palabras (aviso, hallazgo, prioridad, objetivo, tarea) relevadas contra el código, dónde se pisan, el ciclo de vida mapeado y dónde se corta. **Confirmado.** |
| [`01-DEVOLUCIONES-Y-RECLAMOS.md`](01-DEVOLUCIONES-Y-RECLAMOS.md) | El flujo guiado por lo que exige cada proveedor: dónde vive ese conocimiento, los pasos, los toques y qué no tiene motor. |
| [`02-ROLES-Y-SUPERFICIE.md`](02-ROLES-Y-SUPERFICIE.md) | La barra inferior, la superficie de los 12 roles, qué acciones agregué y saqué, los avisos por oficio a cerrar, la búsqueda y las pantallas de datos. |
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

Pendiente de cerrar con Lucas: la lista de avisos por oficio (§5 del documento 02)
antes de sembrar nada, y en otra rama.
