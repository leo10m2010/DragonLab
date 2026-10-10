# DragonLab 0.12.5

Corrige una carrera en el arrastre: al pulsar el botón, DragonBound conserva la fuerza anterior hasta procesar el siguiente movimiento. Ya no se acepta esa barra para finalizar o corregir la carga. El programa espera que el historial del arrastre confirme el nuevo movimiento y su posición antes de comparar la fuerza.

Esto también se exige después de cada corrección. Cambios de origen o sensibilidad invalidan el intento. No se inicia otro tiro automáticamente.

El último intento deja un registro pequeño en `ultimo-autotiro.json`: fuerza solicitada, sensibilidad, confirmaciones de movimiento, resultado o motivo de interrupción. Funciona aunque el programa se abra sin opciones de diagnóstico. No incluye conversaciones ni datos de cuenta.

Verificación: 16 pruebas controladas, incluyendo barra anterior igual a la fuerza solicitada y una lectura atrasada de fuerza alta que antes podía provocar una corrección incorrecta. Se comprobó en lectura pasiva que el cliente usa `pageX` y registra los movimientos en `stat`; no se disparó por el usuario. La prueba del tiro completo sigue pendiente de la partida real.
