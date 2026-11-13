# DragonLab 0.21.0

Corrección de la barra y los controles del manual.

- La validación de captura descartaba el juego completo si quedaba parcialmente recortado o desplazado una fracción de píxel. Se conserva ahora el rectángulo original del mapa y su escala, aunque interseque parcialmente el navegador. La barra conserva su rango completo; no se estira ni se desplaza la fuerza calculada.
- Verificación en partida: rectángulo del juego con Y = -0.565 y alto 944.827, dentro de un navegador de alto 944. La barra se detectó, el overlay y la guía quedaron visibles, y se calculó fuerza 228. No se disparó desde la verificación.
- Los desplegables ya no se cierran por eventos de ventana sin cambio de geometría. El foco se toma al mostrarse; se puede seleccionar, reabrir, salir con Esc y regresar al diálogo anterior. Se conserva el grab modal.
- Los interruptores respetan su estado desactivado y ejecutan su acción una sola vez. Se conservan Ctrl/Q y las preferencias existentes.
- Iconos originales de `@tabler/icons-png` 3.51.0, biblioteca MIT: recursos locales y licencia en `assets/icons/tabler`. Se retiraron los trazos propios. No se descargan iconos al ejecutar el programa.
- La mascota usa el archivo original `head-dragon.webp` del usuario, sin modificarlo, con transparencia y caché de tamaños.
- Launcher compacto con paleta #181916 / #BAFF00 y barra propia. Los estilos de ventana se conservan; el área de título se personaliza con WM_NCCALCSIZE y se mantiene el ciclo de vida nativo de Tk/Windows. Minimizar, maximizar, restaurar y cerrar tienen acciones reales.

Distribución manual: `DragonLab-Manual-0.21.0.zip`. El automático continúa separado y experimental. La corrección no declara nuevas calibraciones de carros ni climas.

Pruebas focalizadas: captura con mapa recortado, identidad de lectura, recursos originales, iconos de biblioteca, interacción de menús, guardado y controles de ventana. Los ejecutables incluyen comprobación de ambas DLL, PNG/JPEG/BMP, WebP de la mascota y los veinte iconos de Tabler con `--native-check`.
