# DragonLab 0.21.1

Se corrige la pérdida de detección al tener más de una pestaña del mismo juego.

El lector anterior rechazaba dos páginas de DragonBound y mostraba «Buscando el navegador» indefinidamente. Ahora selecciona la partida enfocada o la única partida activa; conserva la conexión mientras se consulta otra aplicación y vuelve a resolverla si se cierra una pestaña automática. Si se cambia a otra pestaña con partida, reconecta sin mezclar posiciones, cálculos ni atajos de la anterior. Las pestañas elegidas explícitamente mantienen su selección.

La identidad de lectura y de Q incluye la pestaña, además de la partida y el jugador. Dos páginas con estados nativos idénticos ya no pueden compartir un cálculo o una pulsación pendiente. Los avisos distinguen una selección ambigua de una reconexión normal.

Se conservan la corrección de captura por desplazamientos fraccionarios, la cabeza de dragón original, la paleta y los iconos oficiales de Tabler. No hay cambios de interfaz ni de física en este parche.

Distribución: `DragonLab-Manual-0.21.1.zip`. Automático separado y experimental.
