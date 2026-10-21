# DragonLab 0.14.1 · Continuidad y turnos cortos

Cierra la versión anterior y abre DragonLab-Prueba.exe. Entrenar-Continuo.cmd abre DragonBound e inicia el entrenamiento independiente. Esc o Detener lo cancelan.

## Correcciones

El entrenador lee turn_time y start_turn_time nativos para estimar los segundos disponibles. Reserva margen para cargar y confirmar la fuerza, limita el ajuste de ángulo cuando queda poco tiempo y evita desplazamientos opcionales en turnos cortos. Vuelve a comprobar el reloj antes de cargar. Si el reloj no está disponible, utiliza un presupuesto conservador y mantiene la comprobación de turno.

Un turno vencido o una salida de proyectil no confirmada conservan la reserva de una acción por turno y permiten continuar en el siguiente. No se usan tiros sin atribución confirmada para aprender. Los fallos de control se reinician al cambiar de partida. Tres fallos reales consecutivos dentro de la partida todavía detienen el entrenador; el aviso ahora incluye la última causa y entrenamiento-estado.json conserva hasta 64 incidencias con tipo, turno y motivo.

## Comprobación

183 pruebas automatizadas aprobadas. Prueba real de código fuente con Armor en una partida cuyo turn_time nativo era 10: tiros en turnos 2 y 4, fuerzas solicitadas/medidas 300/299 y 360/359, ajustes nativos 13→54° y 54→39°. La sesión terminó voluntariamente tras esos dos tiros, sin error. Esto comprueba esa partida concreta; no equivale a una prueba de 24 horas.

El registro anterior mostró 23 tiros en seis partidas antes del corte por tres fallos; no conservaba las causas individuales y por tanto no permite afirmar cuál fue el desencadenante original. El nuevo registro evita perder esa información.

## Aprendizaje

Se mantiene el aprendizaje independiente de 0.14.0: explora y mide lanzamientos reales, exige comprobaciones posteriores y no utiliza las fuerzas del Lab como profesor. Al principio puede fallar. No están aprendidos todos los vehículos, climas ni proyectiles secundarios. GunBound World conserva sus perfiles separados y no forma parte del entrenador. Las mediciones autónomas son locales y no se envían al servidor.
