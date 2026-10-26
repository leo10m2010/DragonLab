# DragonLab 0.16.4 · Continuidad y aprendizaje dirigido

Para activar esta versión, cierra solo DragonLab, conserva ambas ventanas de Chrome e inicia `Entrenar-2-Sesiones.cmd` desde la carpeta nueva. Las cuentas, perfiles y mediciones se conservan.

## Recuperación de las dos sesiones

Se encontró por qué quedaba una sola cuenta jugando: la primera se detuvo después de tres fallos de inicio de Drag. Los fallos conocidos de carga ahora conservan el mismo controlador, sus modelos, el plazo y los turnos ya reservados. Después de un problema de Drag se usa Espacio durante 180 segundos, siempre en turnos posteriores. Nunca se repite una carga ambigua en el mismo turno.

La zona de arrastre excluye las capas de chat y ayuda que el propio juego ignora. Esto corrige una condición real de falta de inicio; los registros anteriores no permiten atribuir todos los fallos de SS a esa causa.

Si el estado nativo permanece sin cambios durante dos minutos, se renueva la conexión local de esa pestaña. No recarga la página ni abandona la partida. Las pausas por chat, avisos desconocidos, carga del perfil y penalizaciones conocidas conservan su tratamiento propio. Se corrigió además un bloqueo entre bloques de evaluación que podía impedir procesar un aviso conocido.

El panel indica cuántas sesiones están activas y distingue funcionamiento parcial o falta de respuesta. Los registros incluyen actividad del controlador, último progreso real, último tiro confirmado, recuperaciones y reconexiones. Consultar repetidamente el navegador no se cuenta como progreso del aprendizaje. Los errores desconocidos y la imposibilidad de archivar mediciones siguen deteniendo el trabajador afectado y mostrando el motivo.

## Mejor uso de las mediciones

El selector ya no permanece indefinidamente en Armor. Tras tres selecciones busca otro carro con datos compatibles, priorizando los menos utilizados. Las balas sin mecanismo comprobado no se habilitan por tener muchas muestras de otra modalidad.

La calibración normal que está avanzando tiene prioridad sobre una SS todavía sin comprobar. Una SS con evidencia suficiente para terminar al rival conserva su prioridad. Mientras falte validar el modelo se siguen proponiendo ángulos variados y calculados; la fuerza siempre procede de las mediciones y debe pasar las comprobaciones de terreno y clima. No se sustituyen por disparos arbitrarios ni se reducen los umbrales de validación.

El diagnóstico diferencia muestras nativas actuales, amplitud de fuerzas y tiros de comprobación independientes. Ver `REVISION-CONTINUIDAD-0.16.4.md` para los hallazgos y sus límites.

## Validación

489 pruebas Python y seis suites de navegador aprobadas. Incluyen una reproducción de mil turnos con pérdidas de conexión y errores de carga: cada turno se intenta una sola vez y el límite de 24 horas simuladas se respeta. También comprueban el cambio a Espacio en turnos posteriores, la conservación del aprendizaje al reconectar, los avisos entre bloques y las zonas de chat excluidas. Una simulación no certifica haber completado 24 horas reales; esa continuidad y el efecto sobre las victorias necesitan observarse con esta versión activada.

Para usar: `DragonLab-Prueba-0.16.4.zip`. Para preparación y código: `DragonLabCloud-Preparacion.zip`.
