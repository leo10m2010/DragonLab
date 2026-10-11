# DragonLab 0.12.7

## Comprobación de Q

Después de soltar se observa el juego, sin repetir el disparo. Se excluyen proyectiles que ya estaban presentes, tiros de otros jugadores y fragmentos demorados. La comprobación distingue fuerza confirmada, diferencia, observación parcial y ausencia de datos. Una barra coincidente por sí sola no prueba la fuerza del proyectil: hace falta fuerza nativa atribuida o contraste con una salida calibrada. Si falta ese dato, la interfaz lo dice.

El contexto conserva jugador, modalidad, posición, fuerza y viento de ese intento. La comprobación no utiliza el viento de otro turno. El resultado se guarda en `ultimo-autotiro.json`. La espera posterior dura como máximo 2,5 segundos y no demora la liberación del tiro.

## Aprendizaje reversible

Los ajustes candidatos se preparan con al menos cuatro mediciones que pasan la validación existente. No afectan la guía mientras se prueban. Para activarse necesitan al menos tres mediciones posteriores, distintas de las de entrenamiento, con dos o más fuerzas y un rango mínimo de 40. Además deben pasar los límites de velocidad/aceleración y mejorar el ajuste activo cuando es comparable.

Una muestra incompatible no borra el ajuste activo. Tras tres discrepancias se revisa el régimen; el ajuste previo se recupera únicamente si explica esas mediciones. Si ambos ajustes fallan, se conserva el historial y se suspende el uso del ajuste cuestionado. Los ajustes existentes siguen guardados. Se eliminó el atajo que aplicaba velocidad o aceleración a partir de una sola muestra sin validar.

El aprendizaje separa clon, carro y tiro 1/2/SS. Los fragmentos secundarios no se mezclan con el lanzamiento principal; la fase subterránea de Nak conserva su colección separada. Esto valida parámetros de salida, no demuestra una calibración completa de Nak, Kalsiddon o todos los climas.

## Interfaz y rendimiento

La vista principal muestra «Listo», «Aprendiendo» o «Bloqueado». La información técnica queda en Ajustes → Ver diagnóstico. Allí también pueden exportarse los casos de prueba.

En el lobby se omite la búsqueda del estado interno del juego y se reduce la frecuencia de consulta. Entre turnos se reduce la captura; el canal independiente de Q se mantiene. Los registros de revisión tienen límites de tamaño y escrituras atómicas, con tratamiento de bloqueos transitorios de archivos en Windows.

## Casos reproducibles y pruebas

Se guardan hasta ocho casos locales de bloqueo o comprobación fallida, de hasta 512 KiB cada uno, para un máximo aproximado de 4 MiB. Incluyen datos necesarios para simular el tiro; no incluyen nombres, chat ni datos de cuentas. Se pueden reproducir con `replay_cases.py` sin conectarse al juego. Un caso sin resultado esperado solo informa del cálculo; no se presenta como una prueba aprobada.

Validación: 50 pruebas locales de lógica, aprendizaje, atribución, Q, almacenamiento concurrente y UI, incluida la apertura de Ajustes y Diagnóstico en Windows; escenarios controlados de tiro normal, alto, roca, varios enemigos, Mirror y Tornado; dos pruebas con Chrome aislado. La prueba de ventanas se omite en sistemas sin escritorio. Las situaciones controladas están etiquetadas como tales, no como mediciones de partidas. Falta contrastar un nuevo tiro Q en la partida del usuario. No se automatizó ningún tiro real durante estas pruebas.
